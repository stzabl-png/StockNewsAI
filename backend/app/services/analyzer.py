"""
LLM 两级分析引擎（纯 OpenAI）
- Level 1: GPT-4o-mini 初筛（所有新闻 → 分类 + 评级）
- Level 2: GPT-5 深度分析（仅高影响事件）
"""
import json
import logging
from typing import Optional

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

LEVEL1_SYSTEM_PROMPT = """你是一位专业的美股生物医药研究分析师，擅长判断新闻对股价的影响。
请分析新闻并返回 JSON 格式的结构化判断。

判定 HIGH impact 的标准:
- FDA 审批结果（批准/拒绝/CRL/完整回复函）
- Phase 3 临床试验关键数据读出
- 重大药物安全事件（黑框警告/撤市）
- 大型并购或重要合作协议（>$1B）
- 财报大幅超出/低于预期（EPS miss/beat >15%）

判定 MEDIUM impact 的标准:
- 分析师评级变化
- Phase 2 试验数据
- 一般合作/授权协议
- 管线更新、适应症扩展

判定 LOW impact 的标准:
- 一般行业新闻、市场评论
- 人事变动
- 会议/学术报告参与
- 常规业务更新

只返回 JSON，不要任何其他文字或 markdown 格式。"""

LEVEL1_USER_TEMPLATE = """公司: {ticker} ({company_name})
新闻标题: {title}
新闻内容: {content}

请返回以下 JSON:
{{
  "sentiment": "bullish 或 bearish 或 neutral",
  "confidence": 0.0到1.0之间的数字,
  "impact_level": "high 或 medium 或 low",
  "impact_duration": "short_term 或 medium_term 或 long_term",
  "category": "fda_approval/clinical_trial/earnings/partnership/safety_alert/regulatory/analyst_rating/general",
  "summary_cn": "一句话中文摘要"
}}"""

LEVEL2_SYSTEM_PROMPT = """你是一位资深的生物医药投资研究分析师，专注于美股生物医药板块深度研究。
你的分析将用于投资决策辅助，请确保分析准确、专业、有深度。

分析框架:
1. 消息是否超出/符合/低于市场预期？
2. 对公司短期（1周内）和中期（1-3月）的影响
3. 对同赛道竞品公司的间接影响
4. 后续需要关注的催化剂/风险事件

只返回 JSON，不要任何其他文字或 markdown 格式。"""

LEVEL2_USER_TEMPLATE = """## 事件信息
- 公司: {ticker} ({company_name})
- 板块: {sector}
- 治疗领域: {therapeutic_area}
- 新闻标题: {title}
- 新闻内容: {content}

## 初步研判（GPT-4o-mini）
- 情感: {sentiment}
- 置信度: {confidence}
- 影响级别: {impact_level}
- 事件分类: {category}
- 初步摘要: {summary_cn}

## 请给出深度分析，返回以下 JSON:
{{
  "sentiment": "bullish 或 bearish 或 neutral",
  "confidence": 0.0到1.0,
  "impact_level": "high",
  "impact_duration": "short_term 或 medium_term 或 long_term",
  "summary_cn": "2-3句中文深度摘要",
  "detailed_analysis": {{
    "direct_impact": "对公司股价的直接影响分析",
    "pipeline_impact": "对公司管线和长期价值的影响",
    "competitive_landscape": "对同赛道竞品公司的影响",
    "revenue_impact": "对营收预期的影响",
    "risk_factors": ["风险因素1", "风险因素2"]
  }},
  "related_tickers": ["相关股票代码1", "相关股票代码2"],
  "key_dates_to_watch": ["后续关键日期/事件1", "后续关键日期/事件2"]
}}"""


class NewsAnalyzer:
    """新闻分析引擎 — 两级 LLM 分析"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._openai = None

    @property
    def openai_client(self) -> Optional[AsyncOpenAI]:
        if self._openai is None and settings.OPENAI_API_KEY:
            self._openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._openai

    # =================================================
    #  主入口
    # =================================================

    async def analyze_news(self, news: News) -> Optional[Analysis]:
        """
        分析单条新闻
        1. Level 1: GPT-4o-mini 初筛
        2. 如果是高影响事件 → Level 2: Claude 深度分析
        """
        if not self.openai_client:
            logger.warning("OpenAI API Key 未配置，跳过分析")
            return None

        company = news.company
        if not company:
            logger.warning(f"新闻 {news.id} 缺少关联公司信息，跳过")
            return None

        try:
            # ---- Level 1: GPT-4o-mini 初筛 ----
            level1 = await self._level1_screen(news, company)
            if not level1:
                return None

            logger.info(
                f"[L1] {company.ticker} | {level1.get('sentiment')} | "
                f"{level1.get('impact_level')} | {level1.get('summary_cn', '')[:50]}"
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
                impact_level=level1.get("impact_level", "low"),
                impact_duration=level1.get("impact_duration"),
                summary_cn=level1.get("summary_cn", ""),
            )

            # ---- Level 2: GPT-5 深度分析（仅高影响事件）----
            if level1.get("impact_level") == "high":
                level2 = await self._level2_deep_analysis(
                    news, company, level1
                )
                if level2:
                    logger.info(
                        f"[L2] {company.ticker} | 深度分析完成 | "
                        f"{level2.get('summary_cn', '')[:50]}"
                    )
                    analysis.level = 2
                    analysis.sentiment = level2.get("sentiment", analysis.sentiment)
                    analysis.confidence = float(
                        level2.get("confidence", analysis.confidence)
                    )
                    analysis.impact_duration = level2.get(
                        "impact_duration", analysis.impact_duration
                    )
                    analysis.summary_cn = level2.get(
                        "summary_cn", analysis.summary_cn
                    )
                    analysis.detailed_analysis = level2.get("detailed_analysis")
                    analysis.related_tickers = level2.get("related_tickers")
                    analysis.key_dates = level2.get("key_dates_to_watch")

            self.session.add(analysis)
            await self.session.commit()
            await self.session.refresh(analysis)
            return analysis

        except Exception as e:
            logger.error(f"分析新闻 {news.id} 失败: {e}")
            await self.session.rollback()
            return None

    async def analyze_batch(self) -> dict:
        """
        批量分析所有未分析的新闻
        返回统计信息
        """
        # 查询未分析的新闻
        result = await self.session.execute(
            select(News)
            .outerjoin(Analysis)
            .where(Analysis.id == None)  # noqa: E711
            .options(joinedload(News.company))
            .order_by(News.published_at.desc())
        )
        unanalyzed = result.unique().scalars().all()

        if not unanalyzed:
            return {"total": 0, "analyzed": 0, "high_impact": 0, "errors": 0}

        analyzed = 0
        high_impact = 0
        errors = 0

        for news in unanalyzed:
            try:
                analysis = await self.analyze_news(news)
                if analysis:
                    analyzed += 1
                    if analysis.impact_level == "high":
                        high_impact += 1
            except Exception as e:
                logger.error(f"批量分析中新闻 {news.id} 失败: {e}")
                errors += 1

        return {
            "total": len(unanalyzed),
            "analyzed": analyzed,
            "high_impact": high_impact,
            "errors": errors,
        }

    # =================================================
    #  Level 1: GPT-4o-mini 初筛
    # =================================================

    async def _level1_screen(self, news: News, company) -> Optional[dict]:
        """GPT-4o-mini 初筛 — 分类 + 情感 + 影响级别"""
        user_msg = LEVEL1_USER_TEMPLATE.format(
            ticker=company.ticker,
            company_name=company.name,
            title=news.title,
            content=news.content or news.summary or news.title,
        )

        try:
            response = await self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": LEVEL1_SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=500,
            )

            content = response.choices[0].message.content
            return json.loads(content)

        except json.JSONDecodeError as e:
            logger.error(f"Level 1 JSON 解析失败: {e}")
            return None
        except Exception as e:
            logger.error(f"Level 1 API 调用失败: {e}")
            return None

    # =================================================
    #  Level 2: GPT-5 深度分析
    # =================================================

    async def _level2_deep_analysis(
        self, news: News, company, level1: dict
    ) -> Optional[dict]:
        """GPT-5 深度分析 — 仅高影响事件触发"""
        user_msg = LEVEL2_USER_TEMPLATE.format(
            ticker=company.ticker,
            company_name=company.name,
            sector=company.sector,
            therapeutic_area=company.therapeutic_area or "未指定",
            title=news.title,
            content=news.content or news.summary or news.title,
            sentiment=level1.get("sentiment", ""),
            confidence=level1.get("confidence", ""),
            impact_level=level1.get("impact_level", ""),
            category=level1.get("category", ""),
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
                max_tokens=2000,
            )

            content = response.choices[0].message.content
            return json.loads(content)

        except json.JSONDecodeError as e:
            logger.error(f"Level 2 JSON 解析失败: {e}")
            return None
        except Exception as e:
            logger.error(f"Level 2 API 调用失败: {e}")
            return None


# =====================================================
#  后台分析任务（供 BackgroundTasks 调用）
# =====================================================

async def run_analysis_background():
    """
    后台任务入口 — 分析所有未处理的新闻
    使用独立的数据库会话，不影响主请求
    """
    logger.info("[Analyzer] 后台分析任务启动...")
    async with async_session() as session:
        analyzer = NewsAnalyzer(session=session)
        result = await analyzer.analyze_batch()
        logger.info(
            f"[Analyzer] 后台分析完成: "
            f"总计 {result['total']}, 已分析 {result['analyzed']}, "
            f"高影响 {result['high_impact']}, 错误 {result['errors']}"
        )
    return result
