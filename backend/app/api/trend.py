"""
趋势分析 API
- GET  /api/trend/scanner        → 批量趋势扫描（watchlist）
- GET  /api/trend/ticker/{ticker} → 单只股票趋势详情
- POST /api/trend/fetch-history   → 后台拉取历史数据
"""
import logging
from typing import Optional

from fastapi import APIRouter, Query, BackgroundTasks, Request
from sqlalchemy import select, func

from app.database import async_session, get_db
from app.models.company import Company
from app.models.price_history import PriceHistory
from app.services.trend_analyzer import TrendAnalyzer
from app.services.fetchers.polygon_history import PolygonHistoryFetcher

logger = logging.getLogger(__name__)
router = APIRouter()


async def _get_watchlist_tickers(limit: int = 600) -> list[str]:
    """从数据库取 Watchlist 公司 ticker（按关注度排序）"""
    async with async_session() as db:
        result = await db.execute(
            select(Company.ticker)
            .where(Company.is_active == True)
            .limit(limit)
        )
        return [r[0] for r in result.all() if r[0]]


async def _get_qqq_3m_return() -> Optional[float]:
    """从 price_history 取 QQQ 近3个月收益率"""
    async with async_session() as db:
        result = await db.execute(
            select(PriceHistory.close, PriceHistory.date)
            .where(PriceHistory.ticker == "QQQ")
            .order_by(PriceHistory.date.desc())
            .limit(65)
        )
        rows = result.all()
        if len(rows) < 65:
            return None
        latest = rows[0].close
        oldest = rows[-1].close
        return round((latest / oldest - 1) * 100, 2)


@router.get("/trend/scanner")
async def trend_scanner(
    min_score: int = Query(50, ge=0, le=100, description="最低趋势分"),
    limit: int = Query(30, ge=1, le=100, description="返回条数"),
    stage: Optional[str] = Query(None, description="筛选趋势阶段: strong_uptrend/moderate_uptrend/sideways"),
):
    """
    趋势股扫描 — 返回 Watchlist 中趋势最强的标的
    """
    tickers = await _get_watchlist_tickers(limit=500)
    qqq_3m = await _get_qqq_3m_return()

    async with async_session() as db:
        analyzer = TrendAnalyzer(session=db)
        results = await analyzer.scan_tickers(
            tickers=tickers,
            qqq_ret_3m=qqq_3m,
            min_trend_score=min_score,
        )

    if stage:
        results = [r for r in results if r["trend_stage"] == stage]

    return {
        "count": len(results[:limit]),
        "qqq_3m_return": qqq_3m,
        "results": results[:limit],
    }


@router.get("/trend/ticker/{ticker}")
async def get_ticker_trend(
    ticker: str,
    premarket_gap: Optional[float] = Query(None, description="盘前涨幅%（可选）"),
):
    """单只股票趋势详情"""
    ticker = ticker.upper()
    qqq_3m = await _get_qqq_3m_return()

    async with async_session() as db:
        analyzer = TrendAnalyzer(session=db)
        result = await analyzer.analyze_ticker(
            ticker=ticker,
            premarket_gap=premarket_gap,
            qqq_ret_3m=qqq_3m,
        )

    if not result:
        return {"error": f"{ticker} 无足够历史数据，请先运行 /api/trend/fetch-history"}

    return result


@router.post("/trend/fetch-history")
async def fetch_price_history(
    background_tasks: BackgroundTasks,
    tickers: Optional[list[str]] = None,
    days: int = Query(250, ge=20, le=365, description="历史天数"),
):
    """
    后台拉取历史 OHLCV 数据（首次运行约需 5-10 分钟）
    不传 tickers 则自动拉取全部 Watchlist
    """
    async def _run():
        target = tickers or await _get_watchlist_tickers(limit=600)
        # 加上指数和主要 ETF
        indices = ["SPY", "QQQ", "SMH", "XBI", "XLF", "XLE", "XLY", "XLP", "IGV", "SOXX"]
        all_tickers = list(set(indices + target))

        async with async_session() as db:
            fetcher = PolygonHistoryFetcher(session=db)
            result = await fetcher.fetch_batch(all_tickers, days=days, delay=0.25)
            await fetcher.close()
            logger.info(f"[History] 历史数据拉取完成: {result}")

    background_tasks.add_task(_run)
    n = len(tickers) if tickers else "watchlist全量"
    return {
        "message": f"历史数据拉取已在后台启动（{n} 只，{days} 天），约需 5-15 分钟",
        "status": "started",
    }
