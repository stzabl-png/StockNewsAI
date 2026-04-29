"""
三级 LLM 分析引擎（Gemini + OpenAI 混合）
融入生物医药专业筛选框架：
- 公司筛选（A 类小盘 / B 类大盘）
- 事件类型（强事件 / 中间层事件）
- 预期差评估
- 影响范围评估
- 综合评分 → 判定高概率 30%+ 波动机会
"""
import json
import logging
from typing import Optional

import google.generativeai as genai
from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.config import settings
from app.database import async_session
from app.models.news import News
from app.models.analysis import Analysis

logger = logging.getLogger(__name__)

# =====================================================
#  全局规则（所有层共用）
# =====================================================

GLOBAL_POLICY = """你是一个美股多行业事件驱动交易分析系统。你的目标不是简单判断"利好/利空"，而是判断新闻是否足以改变市场预期并具备可交易价值。

必须遵守：
1. 不得编造数据。没有金额、客户、指引、临床数据或财务影响时，标记为 unknown。
2. 区分"好消息"和"可交易消息"。只有超预期、可量化、影响财务模型的新闻才有交易价值。
3. 重点评估"预期差"。股票上涨来自结果高于预期，不是新闻看起来积极。
4. 来源优先级：公司公告/SEC文件 > Reuters/Bloomberg/WSJ > 行业媒体 > 分析师 > 社媒。
5. 财报中指引变化比EPS beat更重要。EPS+收入beat但指引低于预期 → 降分甚至判为利空。
6. 盘前涨幅过大、过去5日已大涨 → 提高风险评分。
7. 输出必须是严格JSON，禁止Markdown或解释文字。
8. 信息不足时也必须输出JSON，在uncertainty_flags中说明。"""

# =====================================================
#  Prompt 模板
# =====================================================

LEVEL1_SYSTEM_PROMPT = GLOBAL_POLICY + """

你负责对每条新闻进行快速初筛，判断是否具有引发股票显著波动的潜力。

【强事件 high 标准】
1. 财报/指引：EPS或收入超预期≥10%、上调或下调指引、毛利率/FCF/backlog明显改善或恶化
2. AI/数据中心：明确订单金额+客户、云厂商资本开支变化、供不应求+产能扩张+价格上涨
3. 半导体/光通信/存储：重大design win、HBM/GPU/ASIC/光模块需求强劲、价格上涨、库存去化
4. 并购：已宣布且溢价≥20%，或可信媒体报道收购/私有化/分拆
5. 生物医药：FDA approval/CRL、Phase2/Phase3关键数据、重大安全性问题
6. 政策/关税：重大关税变化、出口限制/制裁、大型政府/国防合同
7. 能源：OPEC/库存/地缘导致供需变化；公司产量/现金流/分红/回购显著变化

【弱事件 low】：无金额的合作、普通产品发布、管理层访谈、小幅调价、已知信息重复、纯概念AI

【company_type】 A=大中型高流动性 B=小中盘高弹性 C=低质量高风险

【event_strength】0-100整数：85+=极强 70-84=强 50-69=中等 30-49=弱 0-29=噪音

【pass_filter进入L2】：impact_level=high，或medium且event_strength≥55，或属于强事件category

强事件category（即使信息不完整也进L2）：
earnings_beat, earnings_miss, guidance_raise, guidance_cut, ai_order, datacenter_demand, semiconductor_demand, storage_demand, major_customer_win, mna_announced, mna_rumor, fda_approval, fda_crl, clinical_success, clinical_failure, government_contract, tariff_policy, financing_dilution, bankruptcy_risk

只返回JSON，不要任何其他文字。"""

LEVEL1_USER_TEMPLATE = """请对以下新闻进行快速初筛。

公司: {ticker}
公司名称: {company_name}
GICS 板块: {gics_sector}
行业: {industry}
新闻来源: {source}
发布时间: {published_at}
新闻标题: {title}
新闻内容:
{content}

请只输出严格JSON:
{{
  "ticker": "{ticker}",
  "sentiment": "bullish | bearish | neutral | mixed",
  "confidence": 0.0到1.0,
  "impact_level": "high | medium | low",
  "impact_duration": "short_term | medium_term | long_term",
  "category": "earnings_beat/earnings_miss/guidance_raise/guidance_cut/ai_order/datacenter_demand/semiconductor_demand/storage_demand/optical_networking/price_increase/supply_shortage/major_customer_win/product_cycle/mna_announced/mna_rumor/spin_off/asset_sale/fda_approval/fda_crl/clinical_success/clinical_failure/regulatory_approval/regulatory_risk/government_contract/tariff_policy/oil_supply_shock/energy_inventory/analyst_upgrade/analyst_downgrade/insider_buying/insider_selling/financing_dilution/lawsuit_risk/bankruptcy_risk/vague_partnership/product_launch/management_change/other 中选一个",
  "company_type": "A | B | C | unknown",
  "event_strength": 0到100的整数,
  "sector_tag": "ai_infra | semiconductor | storage | biotech | energy | financials | consumer | industrials | software | other",
  "pass_filter": true或false,
  "summary_cn": "一句话中文摘要",
  "reason_cn": "为什么该新闻可能或不可能引发股价波动",
  "positive_factors": ["string"],
  "negative_factors": ["string"],
  "uncertainty_flags": ["string"]
}}"""

# ---------------------------------------------------------

LEVEL2_SYSTEM_PROMPT = GLOBAL_POLICY + """

你是一位美股多行业事件驱动投资分析师，负责对已通过L1初筛的新闻进行中层深度评估，判断是否真正具备交易价值并给出量化评分。

【七维评分体系】

1. source_reliability（来源可靠性）0-10：
   10=SEC文件/公司公告/财报电话会/监管文件
   8=Reuters/Bloomberg/WSJ/CNBC/AP
   6=行业媒体/专业数据平台
   4=分析师报告/市场传闻
   2=社交媒体/小道消息  0=无法验证

2. event_quality（事件质量）0-20：
   高分：财报超预期+上调指引、明确大订单+客户+金额、AI/数据中心/半导体需求加速、FDA批准/Phase3成功、已宣布并购+高溢价、重大政策/关税/政府合同
   低分：模糊合作、普通产品发布、管理层泛泛表态、无金额/无客户/无财务影响的AI新闻

3. expectation_gap（预期差）0-20：
   18-20=明确超预期且未被市场定价
   14-17=较强超预期
   10-13=有一定超预期但不确定
   5-9=基本符合预期
   0-4=低于预期或已充分反映
   注：好消息≠超预期；近期已大涨则降分

4. financial_materiality（财务重要性）0-25：
   22-25=可能显著改变未来12个月收入/利润/估值
   18-21=对未来业绩有明确正负影响
   12-17=有潜在影响但金额或持续性不明确
   6-11=对财务模型影响有限
   0-5=几乎无法量化
   有金额时需估算：合同金额/TTM收入、指引变化幅度、EPS/revenue beat幅度

5. sector_heat（赛道热度）0-10：
   高热度：AI数据中心、半导体、HBM/存储、光通信、电力散热、GLP-1、肿瘤、国防、能源供需冲击
   低热度：传统低增长消费、无明显催化的工业股

6. tradability（交易可执行性）0-10：
   高分：流动性好、新闻适合盘前/盘后交易、有明确相关ticker、同板块存在联动股、可能gap continuation
   低分：流动性差、新闻复杂难定价、只有长期影响、容易高开低走

7. risk_penalty（风险扣分）0-25：
   扣分因素：新闻缺少关键数据、盘前已大涨过多、过去5日已大涨、估值过高、公司亏损严重、融资稀释风险、临床数据样本小或安全性差、财报beat但guidance差、宏观环境不配合、大盘/板块明显走弱、新闻属于传闻

【composite_score计算】
= source_reliability + event_quality + expectation_gap + financial_materiality + sector_heat + tradability - risk_penalty
限制在0-100之间

85-100=极强，进L3 | 75-84=强，进L3需行情确认 | 60-74=中等，观察 | 40-59=弱 | 0-39=无价值

【财报专项规则】
- guidance raise > EPS beat（指引上调是强加分）
- guidance cut是强扣分（即使beat也要降分）
- 毛利率/FCF/backlog/订单比单季EPS更重要
- beat但revenue miss → 谨慎
- 云业务/AI订单/backlog/毛利率比EPS更重要

只返回JSON，不要任何其他文字。"""

LEVEL2_USER_TEMPLATE = """以下新闻已通过L1初筛，请进行多行业事件驱动中层分析。

L1结果:
{l1_result_json}

公司: {ticker}
公司名称: {company_name}
GICS板块: {gics_sector}
行业: {industry}
新闻来源: {source}
发布时间: {published_at}
新闻标题: {title}
新闻内容:
{content}

如果新闻缺少市场预期、金额、客户、指引或实时行情，不要编造，标记为unknown。

请只输出严格JSON:
{{
  "ticker": "{ticker}",
  "event_type": "string",
  "source_reliability": {{"score": 0, "reason": "string"}},
  "event_quality": {{"score": 0, "reason": "string"}},
  "expectation_gap": {{"score": 0, "assessment": "strong_positive | positive | neutral | negative | unknown", "reason": "string"}},
  "financial_materiality": {{"score": 0, "revenue_impact": "high | medium | low | unknown", "earnings_impact": "high | medium | low | unknown", "valuation_impact": "high | medium | low | unknown", "reason": "string"}},
  "sector_heat": {{"score": 0, "sector_tag": "string", "reason": "string"}},
  "tradability": {{"score": 0, "reason": "string"}},
  "risk_penalty": {{"score": 0, "risks": ["string"]}},
  "composite_score": 0,
  "price_move_estimate": {{"direction": "up | down | mixed | unknown", "expected_range": "0-3% | 3-7% | 7-15% | 15%+ | unknown", "confidence": 0.0}},
  "related_tickers": {{"direct_beneficiaries": ["string"], "sympathy_tickers": ["string"], "sector_etfs": ["string"]}},
  "l3_recommendation": {{"send_to_l3": true, "reason": "string"}},
  "brief_analysis_cn": "string",
  "uncertainty_flags": ["string"]
}}"""

# ---------------------------------------------------------

LEVEL3_SYSTEM_PROMPT = GLOBAL_POLICY + """

你是一位专业的美股事件驱动交易策略分析师，负责对L2评分较高的新闻进行最终交易判断，输出可执行的交易计划。

【六步分析框架】

Step1 公司质量与股票属性：
A=大中型高流动性，适合趋势确认，不适合追过大gap
B=中小盘高弹性，可能大幅波动，风险更高
C=低质量炒作股，容易冲高回落或被稀释
考虑：市值、流动性、是否盈利、估值、融资稀释风险、是否属于热门板块

Step2 事件类型与强度：
strong_event：财报超预期+上调指引、明确大订单、AI/数据中心需求强劲且可量化、FDA approval/Phase3 success、正式并购+高溢价、重大政府合同、行业供需反转
weak_event：模糊合作、无金额AI新闻、普通产品发布、分析师小幅上调

Step3 预期差与财务影响：
是否明显高于市场预期、是否改变未来收入/利润/现金流/估值、是否只是一次性影响、是否已被股价提前反映
财报特别规则：guidance raise=强加分；guidance cut=强扣分；beat但revenue miss要谨慎；beat但capex过高可能利空高估值科技股；云/AI订单/backlog/毛利率比单季EPS更重要

Step4 影响范围：
company_specific/sector_wide/supply_chain/macro_sensitive
如果sector_wide或supply_chain，必须输出sympathy_tickers

Step5 市场环境（严格使用实时行情数据）：
盘前/盘后涨幅判断：
  0-5%：反应温和，若新闻强可能还有空间
  5-12%：健康gap，看VWAP和成交量
  12-20%：涨幅较大，谨慎追高
  20-30%：高开低走风险上升，通常不追
  30%+：除非并购或极强FDA，否则默认不追

相对成交量判断：
  <1.5x：资金确认不足
  1.5-3x：有一定关注
  3-6x：明显放量，资金介入
  >6x：极端放量，可能强趋势也可能冲高出货

近5日涨幅：
  0-5%：正常  5-15%：部分提前反应  15-30%：追高风险上升  30%+：大概率拥挤

VWAP：价格在VWAP上方且回踩不破=强势；跌破VWAP且无法收回=弱势不追

大盘：SPY/QQQ同涨利于科技股；QQQ跌>1%则成长股信号降低；VIX上升则降仓位

Step6 交易触发与执行（必须从以下选一个信号）：
BUY_NOW：新闻极强、涨幅<8%、成交量确认、大盘配合
BUY_ON_VWAP_HOLD：新闻强，开盘后10-30分钟守住VWAP不破，成交量持续
WAIT_FOR_PULLBACK：新闻强但涨幅>12%，或过去5日已涨较多；等回踩5-10%企稳
WATCH_SYMPATHY：原股已涨过多，关注板块补涨股
WATCH_ONLY：行情确认不足、市场环境差、或风险过高
AVOID：新闻弱、已充分反映、风险大、流动性差、高开低走概率高

仓位规则：
large：极强事件+涨幅合理+放量确认+大盘配合+风险低；不用于盘前已涨15%+
medium：事件强，行情较好，仍有一定风险
small：事件强但涨幅大、风险高、或需等开盘确认
none：不建议交易

风险控制硬规则：
- 盘前涨幅>20% → 不能BUY_NOW
- 盘前涨幅>30% → 默认WAIT_FOR_PULLBACK或WATCH_SYMPATHY
- 跌破VWAP且无法收回 → 不能买
- 大盘明显弱时 → 降低所有成长股仓位
- 财报股不建议重仓隔夜追涨
- 小盘生物医药有融资风险 → small或none
- 新闻是传闻 → 不能large
- 缺少实时行情数据 → 不能BUY_NOW，只能WATCH_ONLY或WAIT_FOR_PULLBACK

只返回JSON，不要任何其他文字。"""

LEVEL3_USER_TEMPLATE = """以下新闻已通过L1和L2，请进行最终交易分析。

L1结果:
{l1_result_json}

L2结果:
{l2_result_json}

公司: {ticker}
公司名称: {company_name}
GICS板块: {gics_sector}
行业: {industry}
新闻来源: {source}
发布时间: {published_at}
新闻标题: {title}
新闻内容:
{content}

{market_context_section}

请严格使用实时行情数据进行Step5和Step6分析。如果行情数据缺失，请不要假设价格走势。

请只输出严格JSON:
{{
  "ticker": "{ticker}",
  "sentiment": "bullish | bearish | neutral",
  "confidence": 0.0到1.0,
  "impact_duration": "short_term | medium_term | long_term",
  "summary_cn": "2-3句中文深度摘要",
  "step1_company_profile": {{
    "company_type": "A | B | C | unknown",
    "liquidity_assessment": "high | medium | low | unknown",
    "risk_profile": "low | medium | high | very_high",
    "reason_cn": "string"
  }},
  "step2_event_assessment": {{
    "event_strength": "strong_event | medium_event | weak_event | uncertain_event",
    "event_type": "string",
    "reason_cn": "string"
  }},
  "step3_expectation_and_financial_impact": {{
    "expectation_gap": "strong_positive | positive | neutral | negative | unknown",
    "financial_impact": "high | medium | low | unknown",
    "is_likely_priced_in": true,
    "reason_cn": "string"
  }},
  "step4_impact_scope": {{
    "scope": "company_specific | sector_wide | supply_chain | macro_sensitive | unknown",
    "direct_beneficiaries": ["string"],
    "sympathy_tickers": ["string"],
    "sector_etfs": ["string"],
    "reason_cn": "string"
  }},
  "step5_market_env": {{
    "premarket_afterhours_move_assessment": "healthy_gap | extended_gap | extreme_gap | weak_reaction | unknown",
    "volume_assessment": "strong | moderate | weak | unknown",
    "recent_momentum_assessment": "normal | extended | crowded | unknown",
    "vwap_assessment": "above_vwap | below_vwap | need_open_confirmation | unknown",
    "market_background": "supportive | neutral | hostile | unknown",
    "reason_cn": "string"
  }},
  "step6_trading_trigger": {{
    "suggested_signal": "BUY_NOW | BUY_ON_VWAP_HOLD | WAIT_FOR_PULLBACK | WATCH_SYMPATHY | WATCH_ONLY | AVOID",
    "entry_rule": "string",
    "stop_loss_rule": "string",
    "take_profit_rule": "string",
    "invalid_condition": "string",
    "position_size": "large | medium | small | none",
    "time_horizon": "intraday | 1-3 days | swing | unknown"
  }},
  "final_verdict": {{
    "trade_signal": "BUY_NOW | BUY_ON_VWAP_HOLD | WAIT_FOR_PULLBACK | WATCH_SYMPATHY | WATCH_ONLY | AVOID",
    "conviction_score": 0到100,
    "risk_score": 0到100,
    "position_size": "large | medium | small | none",
    "action_suggestion_cn": "string",
    "one_sentence_summary_cn": "string"
  }},
  "key_reasons": ["string"],
  "key_risks": ["string"],
  "related_tickers": ["string"],
  "key_dates_to_watch": ["string"],
  "uncertainty_flags": ["string"]
}}"""




class NewsAnalyzer:
    """新闻分析引擎 — 三级 LLM 分析（Gemini + OpenAI）"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._openai = None
        self._gemini_configured = False

    @property
    def openai_client(self) -> Optional[AsyncOpenAI]:
        if self._openai is None and settings.OPENAI_API_KEY:
            self._openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._openai

    def _ensure_gemini(self):
        pass  # Gemini disabled due to 429 quota block, using OpenAI instead

    # =================================================
    #  主入口
    # =================================================

    async def analyze_news(self, news: News) -> Optional[Analysis]:
        """
        分析单条新闻（三级策略）:
        1. L1: GPT-4o-mini 初筛（全量）— 事件分类 + 公司分类
        2. L2: GPT-4o-mini 中级分析（MEDIUM）— 预期差 + 影响范围 + 评分
        3. L3: GPT-4o 深度分析（HIGH）— 六步框架全评估
        """
        if not settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY 未配置，跳过分析")
            return None

        company = news.company
        if not company:
            logger.warning(f"新闻 {news.id} 缺少关联公司信息，跳过")
            return None

        try:
            # ---- Level 1: 初筛 ----
            level1 = await self._level1_screen(news, company)
            if not level1:
                return None

            impact = level1.get("impact_level", "low")
            pass_filter = level1.get("pass_filter", True)

            logger.info(
                f"[L1·Flash] {company.ticker} | {level1.get('sentiment')} | "
                f"{impact} | {level1.get('event_strength','?')} | "
                f"pass={pass_filter} | {level1.get('summary_cn', '')[:50]}"
            )

            # 更新新闻分类
            if level1.get("category"):
                news.category = level1["category"]

            # 创建分析记录
            analysis = Analysis(
                news_id=news.id,
                level=1,
                sentiment=level1.get("sentiment", "neutral"),
                confidence=float(level1.get("confidence", 0.5)),
                impact_level=impact,
                impact_duration=level1.get("impact_duration"),
                summary_cn=level1.get("summary_cn", ""),
            )

            # 保存 L1 的筛选元数据
            l1_meta = {
                "company_type": level1.get("company_type"),
                "event_strength": level1.get("event_strength"),
                "pass_filter": pass_filter,
            }

            level2 = None

            # ---- Level 2: GPT-4o-mini 中级分析（MEDIUM / HIGH 都可以进）----
            if pass_filter and impact in ("medium", "high"):
                level2 = await self._level2_medium_analysis(news, company, level1)
                if level2:
                    score = level2.get("composite_score", 0)
                    rt = level2.get("related_tickers", {})
                    if isinstance(rt, dict):
                        all_tickers = (rt.get("direct_beneficiaries") or []) + (rt.get("sympathy_tickers") or [])
                    else:
                        all_tickers = rt or []
                    logger.info(
                        f"[L2·GPT] {company.ticker} | 评分={score} | "
                        f"{level2.get('brief_analysis_cn', '')[:50]}"
                    )
                    analysis.level = 2
                    analysis.related_tickers = all_tickers or None
                    analysis.detailed_analysis = {
                        **l1_meta,
                        "event_type": level2.get("event_type"),
                        "source_reliability": level2.get("source_reliability"),
                        "event_quality": level2.get("event_quality"),
                        "expectation_gap": level2.get("expectation_gap"),
                        "financial_materiality": level2.get("financial_materiality"),
                        "sector_heat": level2.get("sector_heat"),
                        "tradability": level2.get("tradability"),
                        "risk_penalty": level2.get("risk_penalty"),
                        "composite_score": score,
                        "price_move_estimate": level2.get("price_move_estimate"),
                        "related_tickers": level2.get("related_tickers"),
                        "brief_analysis_cn": level2.get("brief_analysis_cn"),
                        "uncertainty_flags": level2.get("uncertainty_flags"),
                    }

                    # 评分 >= 75 升级为 HIGH 并触发 L3
                    if score >= 75 and impact != "high":
                        logger.info(f"[L2→L3] {company.ticker} | 评分{score}>=75, 升级为 HIGH")
                        analysis.impact_level = "high"
                        impact = "high"

            # ---- Level 3: 深度分析（HIGH）----
            if impact == "high" and pass_filter:
                level3 = await self._level3_deep_analysis(news, company, level1, level2)
                if level3:
                    verdict = level3.get("final_verdict", {})
                    logger.info(
                        f"[L3·Pro] {company.ticker} | "
                        f"conviction={verdict.get('conviction_score','?')} "
                        f"risk={verdict.get('risk_score','?')} | "
                        f"{level3.get('summary_cn', '')[:50]}"
                    )
                    analysis.level = 3
                    analysis.sentiment = level3.get("sentiment", analysis.sentiment)
                    analysis.confidence = float(level3.get("confidence", analysis.confidence))
                    analysis.impact_duration = level3.get("impact_duration", analysis.impact_duration)
                    analysis.summary_cn = level3.get("summary_cn", analysis.summary_cn)
                    analysis.related_tickers = level3.get("related_tickers")
                    analysis.key_dates = level3.get("key_dates_to_watch")

                    # ── 评分 + 信号生成 ──────────────────────────────────────
                    mkt_ctx = level3.get("_market_context", {})
                    l3_step6 = level3.get("step6_trading_trigger", {})
                    l3_verdict = level3.get("final_verdict", {})

                    from app.services.event_scorer import score_analysis
                    from app.services.signal_generator import generate_trade_signal

                    scores = score_analysis(
                        category=level1.get("category", "general"),
                        sentiment=level3.get("sentiment", "neutral"),
                        confidence=float(level3.get("confidence", 0.5)),
                        impact_level="high",
                        event_strength=level1.get("event_strength"),
                        l3_composite_score=l3_verdict.get("conviction_score"),
                        market_context=mkt_ctx,
                    )

                    # L3直接给出的信号优先，再做硬规则校验
                    raw_signal = l3_step6.get("suggested_signal") or l3_verdict.get("trade_signal")
                    trade_signal = generate_trade_signal(
                        event_score=scores["event_score"],
                        market_score=scores["market_score"],
                        risk_score=scores["risk_score"],
                        final_score=scores["final_score"],
                        premarket_gap_pct=mkt_ctx.get("premarket_gap_pct"),
                        rel_volume=mkt_ctx.get("rel_volume"),
                        qqq_change_pct=mkt_ctx.get("qqq_change_pct"),
                        spy_change_pct=mkt_ctx.get("spy_change_pct"),
                        ticker=company.ticker,
                        l3_suggested_signal=raw_signal,
                    )
                    # 硬规则兜底校验
                    trade_signal = _enforce_signal_rules(trade_signal, mkt_ctx)

                    logger.info(
                        f"[Signal] {company.ticker} | "
                        f"event={scores['event_score']} mkt={scores['market_score']} "
                        f"risk={scores['risk_score']} final={scores['final_score']} | "
                        f"{trade_signal['signal']}"
                    )

                    analysis.detailed_analysis = {
                        **l1_meta,
                        "step1_company_profile": level3.get("step1_company_profile"),
                        "step2_event_assessment": level3.get("step2_event_assessment"),
                        "step3_expectation_and_financial_impact": level3.get("step3_expectation_and_financial_impact"),
                        "step4_impact_scope": level3.get("step4_impact_scope"),
                        "step5_market_env": level3.get("step5_market_env"),
                        "step6_trading_trigger": level3.get("step6_trading_trigger"),
                        "final_verdict": l3_verdict,
                        "key_reasons": level3.get("key_reasons"),
                        "key_risks": level3.get("key_risks"),
                        "uncertainty_flags": level3.get("uncertainty_flags"),
                        "market_context": mkt_ctx,
                        "scores": scores,
                        "trade_signal": trade_signal,
                    }

            # 如果 L1 判定不通过且是 LOW，只保存基础数据
            if not pass_filter:
                analysis.detailed_analysis = l1_meta

            self.session.add(analysis)
            await self.session.commit()
            await self.session.refresh(analysis)

            # ---- 高影响事件推送微信 ----
            if analysis.impact_level == "high":
                try:
                    from app.services.notifier import notify_high_impact
                    da = analysis.detailed_analysis or {}
                    await notify_high_impact({
                        "ticker": company.ticker,
                        "company_name": company.name,
                        "news_title": news.title,
                        "sentiment": analysis.sentiment,
                        "confidence": analysis.confidence,
                        "impact_level": analysis.impact_level,
                        "impact_duration": analysis.impact_duration,
                        "summary_cn": analysis.summary_cn,
                        "detailed_analysis": da,
                        "related_tickers": analysis.related_tickers,
                        "key_dates": analysis.key_dates,
                        # 新增：交易信号和评分
                        "trade_signal": da.get("trade_signal"),
                        "scores": da.get("scores"),
                        "market_context": da.get("market_context"),
                    })
                except Exception as e:
                    logger.warning(f"微信推送失败（不影响分析）: {e}")

            return analysis

        except Exception as e:
            err_str = str(e)
            await self.session.rollback()
            # OpenAI 账户额度耗尽 → 立即上抛，停止整个 batch
            if "insufficient_quota" in err_str:
                raise RuntimeError("OPENAI_QUOTA_EXCEEDED: " + err_str)
            logger.error(f"分析新闻失败: {err_str[:200]}")
            raise RuntimeError(err_str)

    async def analyze_batch(self, redis=None) -> dict:
        """批量分析所有未分析的新闻（支持进度追踪）"""
        result = await self.session.execute(
            select(News)
            .outerjoin(Analysis)
            .where(Analysis.id == None)  # noqa: E711
            .options(joinedload(News.company))
            .order_by(News.published_at.desc())
        )
        unanalyzed = result.unique().scalars().all()
        total = len(unanalyzed)

        if not unanalyzed:
            if redis:
                await redis.delete("analysis_progress")
            return {"total": 0, "analyzed": 0, "high_impact": 0, "errors": 0}

        analyzed = 0
        high_impact = 0
        errors = 0

        # 写入初始进度
        if redis:
            await redis.hset("analysis_progress", mapping={
                "status": "running",
                "total": str(total),
                "completed": "0",
                "high_impact": "0",
                "errors": "0",
                "current": "",
            })

        for i, news in enumerate(unanalyzed):
            # ── 提前记录关键字段，避免异步 lazy-load 导致 MissingGreenlet ────────
            news_id = news.id
            ticker = news.company.ticker if news.company else "?"
            title_short = (news.title or "")[:40]

            current_label = f"{ticker}: {title_short}"
            if redis:
                await redis.hset("analysis_progress", mapping={
                    "completed": str(analyzed + errors),
                    "high_impact": str(high_impact),
                    "errors": str(errors),
                    "current": current_label,
                })

            try:
                analysis = await self.analyze_news(news)
                if analysis:
                    analyzed += 1
                    if analysis.impact_level == "high":
                        high_impact += 1
            except RuntimeError as e:
                err_str = str(e)
                if "OPENAI_QUOTA_EXCEEDED" in err_str:
                    logger.error("[Analyzer] ❌ OpenAI 账户额度耗尽，停止分析批次。请充值后重试。")
                    if redis:
                        await redis.hset("analysis_progress", mapping={
                            "status": "quota_exceeded",
                            "current": "OpenAI 额度耗尽，请充值",
                        })
                    break  # 立即停止，不继续浪费重试
                logger.error(f"[Analyzer] 新闻 {news_id} ({ticker}) 分析失败: {err_str[:150]}")
                errors += 1
            except Exception as e:
                logger.error(f"[Analyzer] 新闻 {news_id} ({ticker}) 未知错误: {e}")
                errors += 1

        # 标记完成
        if redis:
            await redis.hset("analysis_progress", mapping={
                "status": "done",
                "completed": str(analyzed + errors),
                "high_impact": str(high_impact),
                "errors": str(errors),
                "current": "",
            })

        return {
            "total": total,
            "analyzed": analyzed,
            "high_impact": high_impact,
            "errors": errors,
        }

    # =================================================
    #  Level 1: Gemini 2.0 Flash 初筛
    # =================================================

    async def _level1_screen(self, news: News, company) -> Optional[dict]:
        """GPT-4o-mini 初筛 — 全市场事件分类 + 公司分类 + 过滤"""
        if not self.openai_client:
            raise RuntimeError("L1 缺少 OpenAI API Key")

        user_msg = LEVEL1_USER_TEMPLATE.format(
            ticker=company.ticker,
            company_name=company.name,
            gics_sector=company.gics_sector or company.sector or "未分类",
            industry=getattr(company, "industry", "") or "",
            source=news.source or "unknown",
            published_at=str(news.published_at)[:16] if news.published_at else "unknown",
            title=news.title,
            content=(news.content or news.summary or news.title)[:4000],
        )

        try:
            response = await self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL_L1,
                messages=[
                    {"role": "system", "content": LEVEL1_SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=700,
            )
            return json.loads(response.choices[0].message.content)

        except json.JSONDecodeError as e:
            logger.error(f"L1 JSON 解析失败: {e}")
            raise RuntimeError(f"L1 JSON 解析失败: {e}")
        except Exception as e:
            logger.error(f"L1 OpenAI 调用失败: {e}")
            raise RuntimeError(f"L1 OpenAI 调用失败: {e}")

    # =================================================
    #  Level 2: GPT-4o-mini 中级分析
    # =================================================

    async def _level2_medium_analysis(
        self, news: News, company, level1: dict
    ) -> Optional[dict]:
        """GPT-4o-mini 中级分析 — 七维评分体系（多行业全市场）"""
        if not self.openai_client:
            logger.warning("OpenAI API Key 未配置，跳过 L2")
            return None

        user_msg = LEVEL2_USER_TEMPLATE.format(
            ticker=company.ticker,
            company_name=company.name,
            gics_sector=company.gics_sector or company.sector or "未分类",
            industry=getattr(company, "industry", "") or "",
            source=news.source or "unknown",
            published_at=str(news.published_at)[:16] if news.published_at else "unknown",
            title=news.title,
            content=(news.content or news.summary or news.title)[:4000],
            l1_result_json=json.dumps(level1, ensure_ascii=False),
        )

        try:
            response = await self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL_L2,
                messages=[
                    {"role": "system", "content": LEVEL2_SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=1500,
            )
            content = response.choices[0].message.content
            return json.loads(content)

        except json.JSONDecodeError as e:
            logger.error(f"L2 JSON 解析失败: {e}")
            return None
        except Exception as e:
            logger.error(f"L2 GPT-4o-mini 调用失败: {e}")
            return None

    # =================================================
    #  Level 3: Gemini 2.5 Pro 深度分析
    # =================================================

    async def _level3_deep_analysis(
        self, news: News, company, level1: dict, level2: Optional[dict] = None
    ) -> Optional[dict]:
        """GPT-4o 深度分析 — 六步框架全评估（注入真实行情数据 + L1/L2结果）"""
        if not self.openai_client:
            logger.warning("L3 缺少 OpenAI API Key")
            return None

        from app.services.market_context import (
            get_market_context,
            format_market_context_for_prompt,
        )
        try:
            mkt_ctx = await get_market_context(company.ticker)
        except Exception as e:
            logger.warning(f"[L3] {company.ticker} 行情上下文获取失败（继续分析）: {e}")
            mkt_ctx = {"has_data": False}

        market_context_section = format_market_context_for_prompt(mkt_ctx, company.ticker)

        user_msg = LEVEL3_USER_TEMPLATE.format(
            ticker=company.ticker,
            company_name=company.name,
            gics_sector=company.gics_sector or company.sector or "未分类",
            industry=getattr(company, "industry", "") or "",
            source=news.source or "unknown",
            published_at=str(news.published_at)[:16] if news.published_at else "unknown",
            title=news.title,
            content=(news.content or news.summary or news.title)[:8000],
            l1_result_json=json.dumps(level1, ensure_ascii=False),
            l2_result_json=json.dumps(level2, ensure_ascii=False) if level2 else "{}",
            market_context_section=market_context_section,
        )

        try:
            response = await self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL_L3,
                messages=[
                    {"role": "system", "content": LEVEL3_SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=3500,
            )
            result = json.loads(response.choices[0].message.content)
            result["_market_context"] = mkt_ctx
            return result

        except json.JSONDecodeError as e:
            logger.error(f"L3 JSON 解析失败: {e}")
            return None
        except Exception as e:
            logger.error(f"L3 OpenAI 调用失败: {e}")
            return None


# =====================================================
#  硬规则校验（防止 LLM 在极端行情下给 BUY_NOW）
# =====================================================

def _enforce_signal_rules(trade_signal: dict, market: dict) -> dict:
    """对 L3 输出的信号做最终硬规则兜底校验，避免追涨过大或成交量不足的情况。"""
    if not trade_signal or not market:
        return trade_signal

    signal = trade_signal.copy()
    gap = market.get("premarket_gap_pct")
    rel_volume = market.get("rel_volume")
    qqq_return = market.get("qqq_change_pct")
    five_day = market.get("five_day_return_pct")

    sig = signal.get("signal", "")
    size = signal.get("position_size", "")

    # 涨幅过大，禁止直接 BUY_NOW
    if gap is not None and gap > 20 and sig == "BUY_NOW":
        signal["signal"] = "WAIT_FOR_PULLBACK"
        signal["position_size"] = "small"
        signal["_rule_override"] = f"gap {gap:.1f}%>20%, BUY_NOW→WAIT_FOR_PULLBACK"

    # 极端涨幅，优先看联动股
    if gap is not None and gap > 30:
        signal["signal"] = "WATCH_SYMPATHY"
        signal["position_size"] = "small"
        signal["_rule_override"] = f"gap {gap:.1f}%>30%, forced WATCH_SYMPATHY"

    # 成交量不足，禁止 large
    if rel_volume is not None and rel_volume < 1.5 and signal.get("position_size") == "large":
        signal["position_size"] = "medium"
        signal["_rule_override"] = signal.get("_rule_override", "") + f" | vol {rel_volume:.1f}x<1.5, large→medium"

    # 大盘弱，降低科技成长股信号
    if qqq_return is not None and qqq_return < -1:
        if signal.get("position_size") == "large":
            signal["position_size"] = "medium"
        elif signal.get("position_size") == "medium":
            signal["position_size"] = "small"
        signal["_rule_override"] = signal.get("_rule_override", "") + f" | QQQ {qqq_return:.1f}%<-1, size downgraded"

    # 近5日已大涨，降低追高信号
    if five_day is not None and five_day > 20 and sig == "BUY_NOW":
        signal["signal"] = "WAIT_FOR_PULLBACK"
        signal["position_size"] = "small"
        signal["_rule_override"] = signal.get("_rule_override", "") + f" | 5d +{five_day:.1f}%>20, BUY_NOW→WAIT"

    return signal


# =====================================================
#  后台分析任务
# =====================================================

async def run_analysis_background():
    """后台任务入口 — 分析所有未处理的新闻（带进度追踪）"""
    import redis.asyncio as aioredis
    logger.info("[Analyzer] 后台分析任务启动...")
    redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        async with async_session() as session:
            analyzer = NewsAnalyzer(session=session)
            result = await analyzer.analyze_batch(redis=redis)
            logger.info(
                f"[Analyzer] 后台分析完成: "
                f"总计 {result['total']}, 已分析 {result['analyzed']}, "
                f"高影响 {result['high_impact']}, 错误 {result['errors']}"
            )
        return result
    finally:
        await redis.close()
