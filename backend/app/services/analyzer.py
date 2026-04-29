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
#  Prompt 模板
# =====================================================

LEVEL1_SYSTEM_PROMPT = """你是一位专业的美股多行业量化研究分析师。
你的任务是快速筛选新闻，判断其是否具有引发股价大幅波动的潜力。

## 全市场强事件（impact_level = "high"）

### 财报/指引类
- 财报大幅超预期（EPS/营收超预期≥+10%）
- 上调全年指引（黄金组合）
- 下调全年指引（明确利空信号）

### AI / 数据中心类
- 明确大型 AI / 数据中心订单（具体金额）
- 主要云厂商 AI 训练计划/投资
- 数据中心需求激增/供应紧张

### 半导体 / 光通信
- 产品生命周期转折点（内存/存储/光芯片供应紧张）
- 主要平台订单超预期（半导体采购奇迹）
- 技术跨代产品发布（GPU/光芯片）

### 并购/私有化
- 并购收购（溢价≥±30%）
- 私有化/分拆传言

### 生物医药类（保留）
- Phase 3 顶线结果（成功或失败）
- Phase 2 中期数据（明确超预期或不及预期）
- FDA 批准 / CRL（完整回复函）/ AdCom 投票结果

### 政策/关税
- 重大关税政策变化（影响具体行业）
- 大型政府合同订单（防务/基础设施）

## 中间层事件（impact_level = "medium"）
- 小幅超预期财报（没有指引上调）
- 分析师上调/下调评级（告价调整）
- 大型商业合作/授权协议
- 内部人员大量买入
- 产品涨价宣布（市场尚不确定）
- 生物医药: 剂量确定/试验设计变化/监管路径变化/关键安全性问题

## 低影响事件（impact_level = "low"）
- 一般行业评论、市场分析文章
- 人事变动、会议参与
- 常规业务更新
- 与目标公司仅间接相关的新闻

## 公司分类标准

### A 类（小公司路径）
- 估计市值 < 10B USD
- 单产品或核心资产占比高
- 未完全商业化

### B 类（大公司路径）
- 估计市值 > 50B USD
- 事件涉及潜在市场规模 ≥ 10B USD
- 涉及核心管线或主要增长方向

只返回 JSON，不要任何其他文字、markdown 格式或代码块。"""

LEVEL1_USER_TEMPLATE = """公司: {ticker} ({company_name})
板块: {gics_sector}
新闻标题: {title}
新闻内容: {content}

请返回以下 JSON:
{{
  "sentiment": "bullish 或 bearish 或 neutral",
  "confidence": 0.0到1.0,
  "impact_level": "high 或 medium 或 low",
  "impact_duration": "short_term 或 medium_term 或 long_term",
  "category": "事件类型，从以下当中选择最匹配的一个: earnings_beat / earnings_miss / guidance_raise / guidance_cut / ai_datacenter_order / ai_partnership_major / supply_chain_tightness / price_increase / price_cut / phase3_data / phase2_data / fda_decision / merger_acquisition / mna_rumor / government_contract / defense_award / tariff_impact / analyst_upgrade / analyst_downgrade / insider_buying / short_squeeze / product_launch / product_recall / safety_event / trial_design_change / regulatory_change / dose_response / major_partnership / general_partnership / sec_filing_unusual / general",
  "company_type": "A_small 或 B_large 或 other",
  "event_strength": "strong 或 intermediate 或 weak",
  "sector_tag": "该公司所属赛道类型，如: AI基础设施/半导体/存储/光通信/生物医药/能源/防务/金融/消费/工业",
  "summary_cn": "一句话中文摘要",
  "pass_filter": true或false（是否值得进一步分析）
}}"""

# ---------------------------------------------------------

LEVEL2_SYSTEM_PROMPT = """你是一位生物医药投资分析师，专注于评估新闻事件对股价的中期影响。

## 你的评估框架

### 1. 预期差评估
- 实际结果是否 ≥ 市场预期 +20%？
- 是否显著低于预期（未达主要终点 / 效果不足）？
- 是否达到或落后行业最佳标准？

### 2. 影响范围评估
- 单产品公司：是否影响公司估值 ≥ 50%？
- 多管线公司：是否影响核心资产？
- 大公司：是否影响未来 ≥ 3年增长路径？
- 是否改变行业竞争格局？

### 3. 赛道评估
热门赛道加分：GLP-1/减肥药、MASH/NASH、肿瘤、CNS、基因疗法

### 4. 综合评分（0-100）
- 80-100: 高概率 30%+ 波动机会
- 60-79: 中等波动潜力（10-30%）
- 40-59: 有限影响（5-10%）
- 0-39: 噪音

只返回 JSON，不要任何其他文字、markdown 格式或代码块。"""

LEVEL2_USER_TEMPLATE = """公司: {ticker} ({company_name})
新闻标题: {title}
新闻内容: {content}

初筛结果:
- 情感: {sentiment}, 置信度: {confidence}
- 事件分类: {category}
- 公司类型: {company_type}
- 事件强度: {event_strength}
- 初步摘要: {summary_cn}

请返回以下 JSON:
{{
  "sentiment": "bullish 或 bearish 或 neutral",
  "confidence": 0.0到1.0,
  "impact_duration": "short_term 或 medium_term 或 long_term",
  "summary_cn": "2-3句中文深度摘要",
  "expectation_gap": {{
    "exists": true或false,
    "description": "预期差描述",
    "magnitude": "超预期20%以上 / 略超预期 / 符合预期 / 不及预期 / 严重不及预期"
  }},
  "impact_scope": {{
    "valuation_impact_pct": 预估对公司估值的影响百分比(数字),
    "affects_core_asset": true或false,
    "changes_competitive_landscape": true或false,
    "description": "影响范围描述"
  }},
  "sector_heat": {{
    "is_hot_sector": true或false,
    "sector_name": "具体赛道名称"
  }},
  "composite_score": 0到100的综合评分(整数),
  "price_move_estimate": "预估股价波动范围，如 +15%~+25%",
  "related_tickers": ["相关股票代码"],
  "brief_analysis": "对投资者的简要建议"
}}"""

# ---------------------------------------------------------

LEVEL3_SYSTEM_PROMPT = """你是一位资深的生物医药投资研究分析师，专注于美股生物医药板块深度研究。
你的分析将用于判断"高概率 30%+ 股价波动机会"。

## 完整评估框架

### 第一步：公司筛选
A类（小公司）: 市值<10B, 单产品占比>50%, 未完全商业化
B类（大公司）: 市值>50B, 涉及≥10B市场, 涉及核心管线

### 第二步：事件类型
强事件: Phase 3 顶线 / Phase 2 中期 / FDA决定 / 大型并购
中间层: 剂量确定 / 试验设计变化 / 监管路径 / 安全性问题

### 第三步：预期差
实际结果 ≥ 预期+20%？或显著不及预期？

### 第四步：影响范围
单产品公司估值影响≥50%？核心资产？3年增长路径？竞争格局？

### 第五步：市场环境（标注"需市场数据验证"）
热门赛道？近期涨幅？Short interest？

### 第六步：交易触发（标注"需实时数据验证"）
成交量、波动幅度、流动性

### 最终判定
通过全部筛选 = "HIGH_CONVICTION"（高概率30%+波动）
通过4/6步 = "MODERATE_CONVICTION"
不足4步 = "LOW_CONVICTION"

只返回 JSON，不要任何其他文字、markdown 格式或代码块。"""

LEVEL3_USER_TEMPLATE = """## 事件信息
- 公司: {ticker} ({company_name})
- 板块: {sector}
- 治疗领域/行业: {therapeutic_area}
- 新闻标题: {title}
- 新闻内容: {content}

## 初步研判
- 情感: {sentiment}
- 置信度: {confidence}
- 影响级别: {impact_level}
- 事件分类: {category}
- 公司类型: {company_type}
- 事件强度: {event_strength}
- 初步摘要: {summary_cn}

{market_context_section}

## 请按六步框架评估，返回以下 JSON:
{{
  "sentiment": "bullish 或 bearish 或 neutral",
  "confidence": 0.0到1.0,
  "impact_level": "high",
  "impact_duration": "short_term 或 medium_term 或 long_term",
  "summary_cn": "2-3句中文深度摘要",

  "step1_company": {{
    "passed": true或false,
    "company_type": "A_small 或 B_large",
    "estimated_market_cap": "估计市值",
    "reasoning": "判断理由"
  }},
  "step2_event": {{
    "passed": true或false,
    "event_type": "strong 或 intermediate",
    "specific_event": "具体事件分类",
    "reasoning": "判断理由"
  }},
  "step3_expectation_gap": {{
    "passed": true或false,
    "magnitude": "超预期20%以上 / 略超预期 / 符合预期 / 不及预期 / 严重不及预期",
    "reasoning": "与市场预期的对比分析"
  }},
  "step4_impact_scope": {{
    "passed": true或false,
    "valuation_impact_pct": "估计对估值的影响百分比",
    "affects_core_asset": true或false,
    "changes_competitive_landscape": true或false,
    "reasoning": "影响范围分析"
  }},
  "step5_market_env": {{
    "passed": true或false,
    "is_hot_sector": true或false,
    "sector_name": "赛道名称",
    "premarket_gap_assessment": "基于实际盘前涨幅的判断",
    "volume_assessment": "基于实际成交量数据的判断",
    "macro_env_assessment": "基于实际SPY/QQQ数据的大盘环境判断",
    "preliminary_assessment": "step5综合判断"
  }},
  "step6_trading_trigger": {{
    "passed": true或false,
    "gap_chase_risk": "low / medium / high（基于实际盘前涨幅）",
    "volume_confirmation": "confirmed / weak / no_data（基于实际成交量）",
    "suggested_signal": "BUY_ON_VWAP_HOLD / WAIT_FOR_PULLBACK / WATCH_ONLY / WATCH_SYMPATHY / AVOID",
    "entry_rule": "具体入场条件",
    "stop_loss_rule": "止损规则",
    "preliminary_assessment": "step6综合判断"
  }},

  "final_verdict": {{
    "conviction_level": "HIGH_CONVICTION 或 MODERATE_CONVICTION 或 LOW_CONVICTION",
    "steps_passed": 通过了几步(数字),
    "composite_score": 0到100,
    "price_move_estimate": "+30%~+50% 或 -20%~-40% 等",
    "trade_signal": "BUY_ON_VWAP_HOLD / WAIT_FOR_PULLBACK / WATCH_ONLY / WATCH_SYMPATHY / AVOID",
    "position_size": "large / medium / small / none",
    "action_suggestion": "对投资者的具体建议（中文）"
  }},

  "detailed_analysis": {{
    "direct_impact": "对公司股价的直接影响分析",
    "pipeline_impact": "对公司管线/产品线的影响",
    "competitive_landscape": "对同赛道竞品公司的影响",
    "revenue_impact": "对营收预期的影响",
    "sympathy_tickers": ["可能联动上涨的股票代码"],
    "risk_factors": ["风险因素1", "风险因素2"]
  }},
  "related_tickers": ["相关股票代码1", "相关股票代码2"],
  "key_dates_to_watch": ["后续关键日期/事件1", "后续关键日期/事件2"]
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

            # ---- Level 2: GPT-4o-mini 中级分析（MEDIUM）----
            if impact == "medium" and pass_filter:
                level2 = await self._level2_medium_analysis(news, company, level1)
                if level2:
                    score = level2.get("composite_score", 0)
                    logger.info(
                        f"[L2·GPT] {company.ticker} | 评分={score} | "
                        f"{level2.get('summary_cn', '')[:50]}"
                    )
                    analysis.level = 2
                    analysis.sentiment = level2.get("sentiment", analysis.sentiment)
                    analysis.confidence = float(level2.get("confidence", analysis.confidence))
                    analysis.impact_duration = level2.get("impact_duration", analysis.impact_duration)
                    analysis.summary_cn = level2.get("summary_cn", analysis.summary_cn)
                    analysis.related_tickers = level2.get("related_tickers")
                    analysis.detailed_analysis = {
                        **l1_meta,
                        "expectation_gap": level2.get("expectation_gap"),
                        "impact_scope": level2.get("impact_scope"),
                        "sector_heat": level2.get("sector_heat"),
                        "composite_score": score,
                        "price_move_estimate": level2.get("price_move_estimate"),
                        "brief_analysis": level2.get("brief_analysis"),
                    }

                    # 如果评分 >= 80，升级为 HIGH 并触发 L3
                    if score >= 80:
                        logger.info(f"[L2→L3] {company.ticker} | 评分{score}>=80, 升级为 HIGH")
                        analysis.impact_level = "high"
                        impact = "high"

            # ---- Level 3: 深度分析（HIGH）----
            if impact == "high" and pass_filter:
                level3 = await self._level3_deep_analysis(news, company, level1)
                if level3:
                    verdict = level3.get("final_verdict", {})
                    logger.info(
                        f"[L3·Pro] {company.ticker} | "
                        f"{verdict.get('conviction_level','?')} | "
                        f"score={verdict.get('composite_score','?')} | "
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

                    from app.services.event_scorer import score_analysis
                    from app.services.signal_generator import generate_trade_signal

                    scores = score_analysis(
                        category=level1.get("category", "general"),
                        sentiment=level3.get("sentiment", "neutral"),
                        confidence=float(level3.get("confidence", 0.5)),
                        impact_level="high",
                        event_strength=level1.get("event_strength"),
                        l3_composite_score=verdict.get("composite_score"),
                        market_context=mkt_ctx,
                    )

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
                        l3_suggested_signal=l3_step6.get("suggested_signal")
                            or verdict.get("trade_signal"),
                    )

                    logger.info(
                        f"[Signal] {company.ticker} | "
                        f"event={scores['event_score']} mkt={scores['market_score']} "
                        f"risk={scores['risk_score']} final={scores['final_score']} | "
                        f"{trade_signal['signal']}"
                    )

                    analysis.detailed_analysis = {
                        **l1_meta,
                        "step1_company": level3.get("step1_company"),
                        "step2_event": level3.get("step2_event"),
                        "step3_expectation_gap": level3.get("step3_expectation_gap"),
                        "step4_impact_scope": level3.get("step4_impact_scope"),
                        "step5_market_env": level3.get("step5_market_env"),
                        "step6_trading_trigger": level3.get("step6_trading_trigger"),
                        "final_verdict": verdict,
                        "detailed_analysis": level3.get("detailed_analysis"),
                        "market_context": mkt_ctx,   # 行情快照
                        "scores": scores,             # 四维评分
                        "trade_signal": trade_signal, # 交易信号
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
            logger.error(f"分析新闻 {news.id} 失败: {e}")
            await self.session.rollback()
            raise RuntimeError(str(e))

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
            # 更新进度
            current_label = f"{news.company.ticker}: {news.title[:40]}" if news.company else news.title[:50]
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
            except Exception as e:
                logger.error(f"批量分析中新闻 {news.id} 失败: {e}")
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
                max_tokens=600,
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
        """GPT-4o-mini 中级分析 — 预期差 + 影响范围 + 综合评分"""
        if not self.openai_client:
            logger.warning("OpenAI API Key 未配置，跳过 L2")
            return None

        user_msg = LEVEL2_USER_TEMPLATE.format(
            ticker=company.ticker,
            company_name=company.name,
            title=news.title,
            content=(news.content or news.summary or news.title)[:3000],
            sentiment=level1.get("sentiment", ""),
            confidence=level1.get("confidence", ""),
            category=level1.get("category", ""),
            company_type=level1.get("company_type", ""),
            event_strength=level1.get("event_strength", ""),
            summary_cn=level1.get("summary_cn", ""),
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
                max_tokens=1000,
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
        self, news: News, company, level1: dict
    ) -> Optional[dict]:
        """GPT-4o 深度分析 — 六步框架全评估（注入真实行情数据）"""
        if not self.openai_client:
            logger.warning("L3 缺少 OpenAI API Key")
            return None

        # ── 获取实时行情上下文（非阻塞，出错降级为空数据）──────────────────────
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
            sector=company.sector,
            therapeutic_area=company.therapeutic_area or "未指定",
            title=news.title,
            content=(news.content or news.summary or news.title)[:8000],
            sentiment=level1.get("sentiment", ""),
            confidence=level1.get("confidence", ""),
            impact_level=level1.get("impact_level", ""),
            category=level1.get("category", ""),
            company_type=level1.get("company_type", ""),
            event_strength=level1.get("event_strength", ""),
            summary_cn=level1.get("summary_cn", ""),
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
                max_tokens=2800,
            )
            result = json.loads(response.choices[0].message.content)
            # 将行情快照附加到结果中，便于前端展示和回测
            result["_market_context"] = mkt_ctx
            return result

        except json.JSONDecodeError as e:
            logger.error(f"L3 JSON 解析失败: {e}")
            return None
        except Exception as e:
            logger.error(f"L3 OpenAI 调用失败: {e}")
            return None


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
