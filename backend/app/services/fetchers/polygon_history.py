"""
Polygon 历史日线 OHLCV 采集器
- 一次性拉取 watchlist 的 250 天历史
- 每日增量更新（只拉最新1天）
"""
import logging
import asyncio
from datetime import date, timedelta
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.config import settings
from app.models.price_history import PriceHistory

logger = logging.getLogger(__name__)

POLYGON_BASE = "https://api.polygon.io"


class PolygonHistoryFetcher:
    def __init__(self, session: AsyncSession, api_key: Optional[str] = None):
        self.session = session
        self.api_key = api_key or settings.POLYGON_API_KEY
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def fetch_ticker_history(
        self,
        ticker: str,
        days: int = 250,
        end_date: Optional[date] = None,
    ) -> int:
        """拉取单个 ticker 的日线历史，返回写入条数"""
        if not self.api_key:
            logger.warning("[History] 未配置 POLYGON_API_KEY")
            return 0

        end = end_date or date.today()
        start = end - timedelta(days=days)
        client = await self._get_client()

        url = f"{POLYGON_BASE}/v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}"
        params = {
            "adjusted": "true",
            "sort": "asc",
            "limit": 300,
            "apiKey": self.api_key,
        }

        try:
            resp = await client.get(url, params=params)
            if resp.status_code == 429:
                logger.warning(f"[History] {ticker} 429限速，跳过")
                return 0
            if resp.status_code != 200:
                logger.warning(f"[History] {ticker} HTTP {resp.status_code}")
                return 0

            data = resp.json()
            results = data.get("results", [])
            if not results:
                return 0

            # 批量 upsert
            rows = []
            for r in results:
                dt = date.fromtimestamp(r["t"] / 1000)
                rows.append({
                    "ticker":  ticker,
                    "date":    dt,
                    "open":    r.get("o"),
                    "high":    r.get("h"),
                    "low":     r.get("l"),
                    "close":   r["c"],
                    "volume":  r.get("v"),
                    "vwap":    r.get("vw"),
                })

            if rows:
                stmt = pg_insert(PriceHistory).values(rows)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["ticker", "date"],
                    set_={
                        "open": stmt.excluded.open,
                        "high": stmt.excluded.high,
                        "low":  stmt.excluded.low,
                        "close": stmt.excluded.close,
                        "volume": stmt.excluded.volume,
                        "vwap":  stmt.excluded.vwap,
                    }
                )
                await self.session.execute(stmt)
                await self.session.commit()

            return len(rows)

        except Exception as e:
            logger.error(f"[History] {ticker} 拉取失败: {e}")
            return 0

    async def fetch_batch(self, tickers: list[str], days: int = 250, delay: float = 0.3) -> dict:
        """批量拉取多个 ticker 的历史，带速率限制"""
        total = 0
        errors = 0
        for i, ticker in enumerate(tickers):
            try:
                n = await self.fetch_ticker_history(ticker, days=days)
                total += n
                if n > 0:
                    logger.debug(f"[History] {ticker}: {n} 条")
            except Exception as e:
                logger.error(f"[History] {ticker} 异常: {e}")
                errors += 1

            if delay > 0:
                await asyncio.sleep(delay)

            # 进度日志
            if (i + 1) % 50 == 0:
                logger.info(f"[History] 进度 {i+1}/{len(tickers)}, 已写入 {total} 条")

        logger.info(f"[History] 完成: {len(tickers)} 只, {total} 条数据, {errors} 错误")
        return {"tickers": len(tickers), "rows": total, "errors": errors}
