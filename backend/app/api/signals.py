"""
交易信号 API
- GET /api/signals/today       → 今日所有高分交易信号（按 final_score 排序）
- GET /api/signals/{news_id}   → 单条新闻的信号详情（实时重算）
- GET /api/signals/ticker/{ticker} → 指定股票的最新信号
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Path
from sqlalchemy import select, desc

from app.database import async_session
from app.models.analysis import Analysis
from app.models.news import News

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Signals"])


# ── 辅助：从 detailed_analysis 提取信号摘要 ────────────────────────────────────

def _extract_signal_summary(analysis: Analysis, news: News) -> dict:
    """从 Analysis 对象提取信号摘要，供列表视图使用"""
    da = analysis.detailed_analysis or {}
    trade_signal = da.get("trade_signal", {})
    scores = da.get("scores", {})
    mkt_ctx = da.get("market_context", {})
    verdict = da.get("final_verdict", {})

    company = news.company
    ticker = company.ticker if company else "?"
    company_name = company.name if company else "?"

    return {
        "news_id":        news.id,
        "ticker":         ticker,
        "company_name":   company_name,
        "news_title":     news.title,
        "published_at":   news.published_at.isoformat() if news.published_at else None,
        "analyzed_at":    analysis.created_at.isoformat(),

        # 核心信号
        "signal":         trade_signal.get("signal", "N/A"),
        "signal_label":   trade_signal.get("signal_label", ""),
        "risk_level":     trade_signal.get("risk_level", ""),
        "entry_rule":     trade_signal.get("entry_rule", ""),
        "stop_loss_rule": trade_signal.get("stop_loss_rule", ""),
        "position_size":  trade_signal.get("position_size", ""),
        "reason_cn":      trade_signal.get("reason_cn", ""),
        "sympathy_tickers": trade_signal.get("sympathy_tickers", []),
        "sector_etfs":    trade_signal.get("sector_etfs", []),

        # 评分
        "event_score":    scores.get("event_score"),
        "market_score":   scores.get("market_score"),
        "risk_score":     scores.get("risk_score"),
        "final_score":    scores.get("final_score"),

        # LLM 输出
        "sentiment":      analysis.sentiment,
        "confidence":     analysis.confidence,
        "summary_cn":     analysis.summary_cn,
        "conviction_level": verdict.get("conviction_level"),
        "composite_score":  verdict.get("composite_score"),
        "price_move_estimate": verdict.get("price_move_estimate"),
        "action_suggestion":   verdict.get("action_suggestion"),
        "related_tickers": analysis.related_tickers or [],

        # 行情快照
        "market": {
            "premarket_gap_pct": mkt_ctx.get("premarket_gap_pct"),
            "rel_volume":        mkt_ctx.get("rel_volume"),
            "prev_5d_return":    mkt_ctx.get("prev_5d_return"),
            "spy_change_pct":    mkt_ctx.get("spy_change_pct"),
            "qqq_change_pct":    mkt_ctx.get("qqq_change_pct"),
            "current_price":     mkt_ctx.get("current_price"),
            "vwap":              mkt_ctx.get("vwap"),
            "has_data":          mkt_ctx.get("has_data", False),
        },
    }


# ── GET /api/signals/today ─────────────────────────────────────────────────────

@router.get("/signals/today")
async def get_today_signals(
    min_final_score: int = Query(50, ge=0, le=100, description="最低综合分筛选"),
    min_event_score: int = Query(60, ge=0, le=100, description="最低事件分筛选"),
    limit: int = Query(20, ge=1, le=100, description="返回条数"),
    signal_filter: Optional[str] = Query(None, description="按信号类型筛选，如 BUY_ON_VWAP_HOLD"),
):
    """
    返回最近24小时内所有 L3 高影响事件的交易信号，按综合分排序。

    这是盘前 Scanner 的数据源。
    """
    since = datetime.now(timezone.utc) - timedelta(hours=24)

    async with async_session() as db:
        from sqlalchemy.orm import joinedload
        result = await db.execute(
            select(Analysis, News)
            .join(News, Analysis.news_id == News.id)
            .options(joinedload(Analysis.news))
            .where(Analysis.level == 3)
            .where(Analysis.impact_level == "high")
            .where(Analysis.created_at >= since)
            .order_by(desc(Analysis.created_at))
            .limit(200)  # 先拉多一点，再在内存中过滤排序
        )
        rows = result.all()

    signals = []
    for analysis, news in rows:
        try:
            summary = _extract_signal_summary(analysis, news)
        except Exception as e:
            logger.warning(f"[Signals] 提取信号摘要失败 news_id={news.id}: {e}")
            continue

        # 评分过滤
        final_score = summary.get("final_score")
        event_score = summary.get("event_score")
        if final_score is not None and final_score < min_final_score:
            continue
        if event_score is not None and event_score < min_event_score:
            continue

        # 信号类型过滤
        if signal_filter and summary.get("signal") != signal_filter:
            continue

        signals.append(summary)

    # 按 final_score 降序排序（无score的排到最后）
    signals.sort(key=lambda x: x.get("final_score") or 0, reverse=True)
    signals = signals[:limit]

    return {
        "count": len(signals),
        "since": since.isoformat(),
        "filters": {
            "min_final_score": min_final_score,
            "min_event_score": min_event_score,
            "signal_filter": signal_filter,
        },
        "signals": signals,
    }


# ── GET /api/signals/{news_id} ─────────────────────────────────────────────────

@router.get("/signals/{news_id}")
async def get_signal_detail(
    news_id: int = Path(..., description="新闻ID"),
    refresh_market: bool = Query(False, description="是否实时刷新行情数据"),
):
    """
    返回单条新闻的完整信号详情。
    如果 refresh_market=True，重新拉取最新行情数据重算信号（不写DB）。
    """
    async with async_session() as db:
        from sqlalchemy.orm import joinedload
        result = await db.execute(
            select(Analysis)
            .join(News, Analysis.news_id == News.id)
            .options(joinedload(Analysis.news).joinedload(News.company))
            .where(Analysis.news_id == news_id)
        )
        analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(status_code=404, detail=f"news_id={news_id} 无分析记录")

    news = analysis.news
    if not news:
        raise HTTPException(status_code=404, detail="关联新闻不存在")

    summary = _extract_signal_summary(analysis, news)

    # 可选：实时刷新行情数据重算信号
    if refresh_market and news.company:
        try:
            from app.services.market_context import get_market_context, format_market_context_for_prompt
            from app.services.event_scorer import score_analysis
            from app.services.signal_generator import generate_trade_signal

            mkt_ctx = await get_market_context(news.company.ticker)
            da = analysis.detailed_analysis or {}
            l3_verdict = da.get("final_verdict", {})
            l3_step6 = da.get("step6_trading_trigger", {})

            scores = score_analysis(
                category=da.get("company_type", "general"),
                sentiment=analysis.sentiment,
                confidence=analysis.confidence,
                impact_level=analysis.impact_level,
                l3_composite_score=l3_verdict.get("composite_score"),
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
                ticker=news.company.ticker,
                l3_suggested_signal=l3_step6.get("suggested_signal"),
            )
            summary["signal"]          = trade_signal["signal"]
            summary["signal_label"]    = trade_signal["signal_label"]
            summary["risk_level"]      = trade_signal["risk_level"]
            summary["entry_rule"]      = trade_signal["entry_rule"]
            summary["stop_loss_rule"]  = trade_signal["stop_loss_rule"]
            summary["position_size"]   = trade_signal["position_size"]
            summary["reason_cn"]       = trade_signal["reason_cn"]
            summary["sympathy_tickers"] = trade_signal["sympathy_tickers"]
            summary["sector_etfs"]     = trade_signal["sector_etfs"]
            summary["event_score"]     = scores["event_score"]
            summary["market_score"]    = scores["market_score"]
            summary["risk_score"]      = scores["risk_score"]
            summary["final_score"]     = scores["final_score"]
            summary["market"]          = {
                "premarket_gap_pct": mkt_ctx.get("premarket_gap_pct"),
                "rel_volume":        mkt_ctx.get("rel_volume"),
                "prev_5d_return":    mkt_ctx.get("prev_5d_return"),
                "spy_change_pct":    mkt_ctx.get("spy_change_pct"),
                "qqq_change_pct":    mkt_ctx.get("qqq_change_pct"),
                "current_price":     mkt_ctx.get("current_price"),
                "vwap":              mkt_ctx.get("vwap"),
                "has_data":          mkt_ctx.get("has_data", False),
            }
            summary["market_refreshed_at"] = datetime.now(timezone.utc).isoformat()
        except Exception as e:
            logger.warning(f"[Signals] 行情刷新失败: {e}")
            summary["market_refresh_error"] = str(e)

    # 附加完整的 detailed_analysis（详情页需要）
    summary["full_analysis"] = analysis.detailed_analysis

    return summary


# ── GET /api/signals/ticker/{ticker} ──────────────────────────────────────────

@router.get("/signals/ticker/{ticker}")
async def get_ticker_latest_signal(
    ticker: str = Path(..., description="股票代码，如 NVDA"),
    days: int = Query(7, ge=1, le=30, description="查询最近几天"),
):
    """返回指定股票最近 N 天内的所有信号，按时间倒序"""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    async with async_session() as db:
        from sqlalchemy.orm import joinedload
        from app.models.company import Company
        result = await db.execute(
            select(Analysis, News)
            .join(News, Analysis.news_id == News.id)
            .join(Company, News.company_id == Company.id)
            .options(joinedload(Analysis.news).joinedload(News.company))
            .where(Company.ticker == ticker.upper())
            .where(Analysis.level == 3)
            .where(Analysis.created_at >= since)
            .order_by(desc(Analysis.created_at))
            .limit(10)
        )
        rows = result.all()

    if not rows:
        return {"ticker": ticker.upper(), "count": 0, "signals": []}

    signals = []
    for analysis, news in rows:
        try:
            signals.append(_extract_signal_summary(analysis, news))
        except Exception as e:
            logger.warning(f"[Signals] ticker={ticker} 提取失败: {e}")

    return {
        "ticker": ticker.upper(),
        "count": len(signals),
        "days": days,
        "signals": signals,
    }
