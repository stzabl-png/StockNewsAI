"""
Polygon.io 行情采集器
- 每日收盘后拉取 SP500 全量 OHLCV
- 计算成交量倍数（volume_ratio = volume / avg_volume_20d）
- 存入 stock_price_snapshots 表（需先做 DB 迁移）
"""
import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import httpx
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = logging.getLogger(__name__)

POLYGON_BASE = "https://api.polygon.io"
RATE_LIMIT_DELAY = 0.2  # 5 req/s


class PolygonMarketFetcher:
    """每日行情快照采集器"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.api_key = settings.POLYGON_API_KEY
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30)
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()

    # ─── 主入口：获取单只股票当日快照 ─────────────────────────────────────────

    async def fetch_daily_snapshot(self, ticker: str, target_date: Optional[date] = None) -> Optional[dict]:
        """
        拉取单只股票某日的 OHLCV 数据。
        target_date 默认为昨日（收盘数据）。
        """
        if not self.api_key:
            raise RuntimeError("POLYGON_API_KEY 未配置")

        d = target_date or (date.today() - timedelta(days=1))
        date_str = d.strftime("%Y-%m-%d")

        url = f"{POLYGON_BASE}/v2/aggs/ticker/{ticker}/range/1/day/{date_str}/{date_str}"
        params = {"adjusted": "true", "sort": "asc", "limit": 1, "apiKey": self.api_key}

        try:
            resp = await self.client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning(f"[PolygonMarket] {ticker} 行情拉取失败: {e}")
            return None

        results = data.get("results", [])
        if not results:
            logger.debug(f"[PolygonMarket] {ticker} {date_str} 无数据（可能是假期）")
            return None

        bar = results[0]
        return {
            "ticker": ticker,
            "snapshot_date": d,
            "open_price":  bar.get("o"),
            "close_price": bar.get("c"),
            "high_price":  bar.get("h"),
            "low_price":   bar.get("l"),
            "volume":      bar.get("v"),
            "change_pct":  self._calc_change_pct(bar.get("o"), bar.get("c")),
        }

    # ─── 获取20日平均成交量 ────────────────────────────────────────────────────

    async def fetch_avg_volume_20d(self, ticker: str) -> Optional[float]:
        """拉取过去 20 个交易日的平均成交量"""
        end = date.today() - timedelta(days=1)
        start = end - timedelta(days=30)  # 多取几天确保有20个交易日

        url = f"{POLYGON_BASE}/v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}"
        params = {"adjusted": "true", "sort": "asc", "limit": 30, "apiKey": self.api_key}

        try:
            resp = await self.client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            bars = data.get("results", [])
            if not bars:
                return None
            volumes = [b.get("v", 0) for b in bars[-20:]]  # 取最近20天
            return sum(volumes) / len(volumes) if volumes else None
        except Exception as e:
            logger.warning(f"[PolygonMarket] {ticker} 均量拉取失败: {e}")
            return None

    # ─── 批量拉取所有活跃股票 ─────────────────────────────────────────────────

    async def fetch_all_daily(self, target_date: Optional[date] = None) -> dict:
        """
        每日收盘后调用：批量拉取所有公司的行情快照，存入 DB。
        建议在美东时间 20:30 (收盘后4h) 执行。
        """
        from app.models.company import Company

        result = await self.session.execute(
            select(Company).where(Company.is_active == True)  # noqa
        )
        companies = result.scalars().all()

        saved = 0
        errors = 0

        for company in companies:
            try:
                snapshot = await self.fetch_daily_snapshot(company.ticker, target_date)
                await asyncio.sleep(RATE_LIMIT_DELAY)

                if not snapshot:
                    continue

                # 获取20日均量（仅在快照成功时才额外请求）
                avg_vol = await self.fetch_avg_volume_20d(company.ticker)
                await asyncio.sleep(RATE_LIMIT_DELAY)

                snapshot["avg_volume_20d"] = avg_vol
                snapshot["volume_ratio"] = (
                    snapshot["volume"] / avg_vol
                    if avg_vol and avg_vol > 0
                    else None
                )
                snapshot["market_cap"] = company.market_cap

                # 写入数据库（UPSERT）
                await self._upsert_snapshot(snapshot)
                saved += 1

            except Exception as e:
                logger.error(f"[PolygonMarket] {company.ticker} 处理失败: {e}")
                errors += 1

        await self.session.commit()
        logger.info(f"[PolygonMarket] 行情快照完成: 保存 {saved} 条, 错误 {errors} 条")
        return {"saved": saved, "errors": errors}

    # ─── 实时报价（L3 分析触发时调用）────────────────────────────────────────

    async def get_realtime_quote(self, ticker: str) -> Optional[dict]:
        """
        获取最近一笔成交价（延迟≤15min, Starter 计划）
        在 L3 深度分析中注入价格上下文时调用
        """
        url = f"{POLYGON_BASE}/v2/last/trade/{ticker}"
        params = {"apiKey": self.api_key}
        try:
            resp = await self.client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            result = data.get("results", {})
            return {
                "ticker": ticker,
                "price": result.get("p"),
                "size":  result.get("s"),
                "timestamp": result.get("t"),
            }
        except Exception as e:
            logger.warning(f"[PolygonMarket] {ticker} 实时报价失败: {e}")
            return None

    # ─── 私有工具 ─────────────────────────────────────────────────────────────

    @staticmethod
    def _calc_change_pct(open_price, close_price) -> Optional[float]:
        if open_price and close_price and open_price != 0:
            return round((close_price - open_price) / open_price * 100, 2)
        return None

    async def _upsert_snapshot(self, snapshot: dict):
        """写入或更新行情快照（stock_price_snapshots 表）"""
        await self.session.execute(
            text("""
                INSERT INTO stock_price_snapshots
                    (ticker, snapshot_date, open_price, close_price, high_price, low_price,
                     volume, change_pct, avg_volume_20d, volume_ratio, market_cap)
                VALUES
                    (:ticker, :snapshot_date, :open_price, :close_price, :high_price, :low_price,
                     :volume, :change_pct, :avg_volume_20d, :volume_ratio, :market_cap)
                ON CONFLICT (ticker, snapshot_date) DO UPDATE SET
                    open_price    = EXCLUDED.open_price,
                    close_price   = EXCLUDED.close_price,
                    high_price    = EXCLUDED.high_price,
                    low_price     = EXCLUDED.low_price,
                    volume        = EXCLUDED.volume,
                    change_pct    = EXCLUDED.change_pct,
                    avg_volume_20d = EXCLUDED.avg_volume_20d,
                    volume_ratio  = EXCLUDED.volume_ratio,
                    market_cap    = EXCLUDED.market_cap
            """),
            snapshot,
        )
