"""
回测服务 — 收盘后自动回填事件结果价格数据

流程：
1. 查询所有 HIGH 影响的 L3 分析，但尚未有 EventOutcome 记录的
2. 为每条新闻创建 EventOutcome 占位记录（存入AI预测的信号和评分）
3. 每天收盘后（美东 20:30）回填当日的价格数据
4. 5个交易日后标记 is_complete=True

提供回测统计 API 数据：
- 按事件类型统计胜率
- 按信号类型统计胜率
- 按conviction_level统计胜率
- 盘前涨幅与后续表现相关性
"""
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import httpx
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session
from app.models.event_outcome import EventOutcome
from app.models.analysis import Analysis
from app.models.news import News

logger = logging.getLogger(__name__)

POLYGON_BASE = "https://api.polygon.io"


class BacktestService:
    """事件结果回填服务"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=20)
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()

    # ── 主入口：创建占位记录 ─────────────────────────────────────────────────

    async def create_pending_outcomes(self) -> dict:
        """
        为所有 L3 HIGH 影响新闻创建 EventOutcome 占位记录。
        调用时机：L3 分析完成后立即调用，或每日定时任务补充。
        """
        # 查找有L3分析但没有EventOutcome的新闻
        result = await self.session.execute(
            select(Analysis, News)
            .join(News, Analysis.news_id == News.id)
            .outerjoin(EventOutcome, EventOutcome.news_id == News.id)
            .where(Analysis.level == 3)
            .where(Analysis.impact_level == "high")
            .where(EventOutcome.id == None)  # noqa: E711
            .order_by(Analysis.created_at.desc())
            .limit(100)
        )
        rows = result.all()

        created = 0
        for analysis, news in rows:
            try:
                da = analysis.detailed_analysis or {}
                trade_signal = da.get("trade_signal", {})
                scores = da.get("scores", {})
                verdict = da.get("final_verdict", {})

                outcome = EventOutcome(
                    news_id=news.id,
                    ticker=news.company.ticker if news.company else "",
                    news_published_at=news.published_at,
                    predicted_signal=trade_signal.get("signal"),
                    predicted_conviction=verdict.get("conviction_level"),
                    predicted_event_score=scores.get("event_score"),
                    predicted_final_score=scores.get("final_score"),
                    event_category=da.get("pass_filter") and news.category or news.category,
                    sector_tag=da.get("step1_company", {}).get("company_type"),
                    is_complete=False,
                )
                self.session.add(outcome)
                created += 1
            except Exception as e:
                logger.warning(f"[Backtest] 创建占位记录失败 news_id={news.id}: {e}")

        await self.session.commit()
        logger.info(f"[Backtest] 创建 {created} 条 EventOutcome 占位记录")
        return {"created": created}

    # ── 主入口：回填价格数据 ─────────────────────────────────────────────────

    async def fill_price_data(self, target_date: Optional[date] = None) -> dict:
        """
        收盘后回填价格数据。
        target_date 默认为今日（美东时区）。
        """
        d = target_date or date.today()

        # 找所有未完成的EventOutcome
        result = await self.session.execute(
            select(EventOutcome)
            .where(EventOutcome.is_complete == False)  # noqa: E711
            .where(EventOutcome.ticker != "")
            .order_by(EventOutcome.created_at)
            .limit(200)
        )
        outcomes = result.scalars().all()

        filled = 0
        errors = 0

        for outcome in outcomes:
            try:
                # 获取新闻发布日的前一交易日（基准价格）
                news_date = outcome.news_published_at.date() if outcome.news_published_at else d - timedelta(days=1)

                # 拉取该股票最近10个交易日数据
                bars = await self._fetch_bars(
                    outcome.ticker,
                    start=(news_date - timedelta(days=2)).isoformat(),
                    end=(d + timedelta(days=1)).isoformat(),
                    limit=15
                )

                if not bars:
                    continue

                # 找到新闻发布日前一收盘价
                prev_close = self._find_prev_close(bars, news_date)
                if not prev_close:
                    continue

                # 找各时间节点价格
                bars_after = [b for b in bars if date.fromtimestamp(b["t"] / 1000) > news_date]

                outcome.price_prev_close = prev_close

                if len(bars_after) >= 1:
                    b0 = bars_after[0]
                    outcome.price_next_open = b0.get("o")
                    outcome.price_close_day1 = b0.get("c")
                    if prev_close and b0.get("o") and prev_close > 0:
                        outcome.gap_pct = round((b0["o"] - prev_close) / prev_close * 100, 2)
                        outcome.return_open = outcome.gap_pct
                    if prev_close and b0.get("c") and prev_close > 0:
                        outcome.return_day1 = round((b0["c"] - prev_close) / prev_close * 100, 2)
                    # 日内最大浮盈/回撤
                    if b0.get("h") and prev_close and prev_close > 0:
                        outcome.max_intraday_gain_day1 = round((b0["h"] - prev_close) / prev_close * 100, 2)
                    if b0.get("l") and prev_close and prev_close > 0:
                        outcome.max_intraday_drawdown_day1 = round((b0["l"] - prev_close) / prev_close * 100, 2)

                if len(bars_after) >= 2:
                    b1 = bars_after[1]
                    outcome.price_close_day2 = b1.get("c")
                    if prev_close and b1.get("c") and prev_close > 0:
                        outcome.return_day2 = round((b1["c"] - prev_close) / prev_close * 100, 2)

                if len(bars_after) >= 5:
                    b4 = bars_after[4]
                    outcome.price_close_day5 = b4.get("c")
                    if prev_close and b4.get("c") and prev_close > 0:
                        outcome.return_day5 = round((b4["c"] - prev_close) / prev_close * 100, 2)
                    outcome.is_complete = True

                # 计算行为标签
                self._compute_labels(outcome)

                outcome.filled_at = datetime.now(timezone.utc)
                filled += 1

            except Exception as e:
                logger.warning(f"[Backtest] {outcome.ticker} 回填失败: {e}")
                errors += 1

        await self.session.commit()
        logger.info(f"[Backtest] 回填完成: {filled} 条成功, {errors} 条失败")
        return {"filled": filled, "errors": errors, "date": d.isoformat()}

    # ── 回测统计 ─────────────────────────────────────────────────────────────

    async def get_backtest_stats(self) -> dict:
        """
        返回回测统计数据，供 Dashboard 使用。
        """
        result = await self.session.execute(
            select(EventOutcome).where(EventOutcome.is_complete == True)
        )
        outcomes = result.scalars().all()

        if not outcomes:
            return {"total": 0, "message": "暂无完整回测数据"}

        total = len(outcomes)

        # 整体胜率（day1 盈利）
        profitable_day1 = sum(1 for o in outcomes if o.label_profitable_day1)
        profitable_day5 = sum(1 for o in outcomes if o.label_profitable_day5)
        gap_fade = sum(1 for o in outcomes if o.label_gap_and_fade)
        continuation = sum(1 for o in outcomes if o.label_open_continuation)

        # 按事件类型统计
        by_category: dict[str, dict] = {}
        for o in outcomes:
            cat = o.event_category or "unknown"
            if cat not in by_category:
                by_category[cat] = {"count": 0, "profitable": 0, "total_return": 0.0}
            by_category[cat]["count"] += 1
            if o.label_profitable_day1:
                by_category[cat]["profitable"] += 1
            if o.return_day1:
                by_category[cat]["total_return"] += o.return_day1

        category_stats = []
        for cat, data in sorted(by_category.items(), key=lambda x: -x[1]["count"]):
            count = data["count"]
            category_stats.append({
                "category":     cat,
                "count":        count,
                "win_rate_d1":  round(data["profitable"] / count * 100, 1) if count else 0,
                "avg_return_d1": round(data["total_return"] / count, 2) if count else 0,
            })

        # 按信号类型统计
        by_signal: dict[str, dict] = {}
        for o in outcomes:
            sig = o.predicted_signal or "unknown"
            if sig not in by_signal:
                by_signal[sig] = {"count": 0, "profitable": 0, "total_return": 0.0}
            by_signal[sig]["count"] += 1
            if o.label_profitable_day1:
                by_signal[sig]["profitable"] += 1
            if o.return_day1:
                by_signal[sig]["total_return"] += o.return_day1

        signal_stats = []
        for sig, data in sorted(by_signal.items(), key=lambda x: -x[1]["count"]):
            count = data["count"]
            signal_stats.append({
                "signal":       sig,
                "count":        count,
                "win_rate_d1":  round(data["profitable"] / count * 100, 1) if count else 0,
                "avg_return_d1": round(data["total_return"] / count, 2) if count else 0,
            })

        # 平均收益率
        returns_d1 = [o.return_day1 for o in outcomes if o.return_day1 is not None]
        returns_d5 = [o.return_day5 for o in outcomes if o.return_day5 is not None]
        avg_return_d1 = round(sum(returns_d1) / len(returns_d1), 2) if returns_d1 else None
        avg_return_d5 = round(sum(returns_d5) / len(returns_d5), 2) if returns_d5 else None

        return {
            "total": total,
            "win_rate_day1": round(profitable_day1 / total * 100, 1),
            "win_rate_day5": round(profitable_day5 / total * 100, 1),
            "gap_fade_rate": round(gap_fade / total * 100, 1),
            "continuation_rate": round(continuation / total * 100, 1),
            "avg_return_day1": avg_return_d1,
            "avg_return_day5": avg_return_d5,
            "by_category": category_stats,
            "by_signal": signal_stats,
        }

    # ── 私有工具 ──────────────────────────────────────────────────────────────

    async def _fetch_bars(self, ticker: str, start: str, end: str, limit: int = 15) -> list:
        url = f"{POLYGON_BASE}/v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}"
        params = {"adjusted": "true", "sort": "asc", "limit": limit, "apiKey": settings.POLYGON_API_KEY}
        try:
            resp = await self.client.get(url, params=params)
            if resp.status_code == 200:
                return resp.json().get("results", [])
        except Exception as e:
            logger.debug(f"[Backtest] {ticker} bars fetch: {e}")
        return []

    @staticmethod
    def _find_prev_close(bars: list, news_date: date) -> Optional[float]:
        """找新闻日之前最近一个交易日的收盘价"""
        for b in reversed(bars):
            bar_date = date.fromtimestamp(b["t"] / 1000)
            if bar_date <= news_date and b.get("c"):
                return b["c"]
        return None

    @staticmethod
    def _compute_labels(outcome: EventOutcome):
        """根据价格数据计算行为标签"""
        gap = outcome.gap_pct or 0
        r1 = outcome.return_day1

        if r1 is not None:
            outcome.label_profitable_day1 = r1 > 0

        if outcome.return_day5 is not None:
            outcome.label_profitable_day5 = outcome.return_day5 > 0

        # Gap and Fade: 高开但日内收益率 < gap/2
        if gap > 3 and r1 is not None:
            outcome.label_gap_and_fade = (r1 < gap * 0.5)

        # Open Continuation: 日收益率 > gap * 1.2（开盘后继续拉升）
        if gap > 2 and r1 is not None:
            outcome.label_open_continuation = (r1 > gap * 1.2)


# ── 后台任务入口 ──────────────────────────────────────────────────────────────

async def run_backtest_fill():
    """定时任务入口：收盘后回填价格数据"""
    logger.info("[Backtest] 开始价格数据回填...")
    async with async_session() as session:
        svc = BacktestService(session=session)
        try:
            # 先创建新的占位记录
            create_result = await svc.create_pending_outcomes()
            # 再回填历史价格
            fill_result = await svc.fill_price_data()
            logger.info(f"[Backtest] 完成: 创建={create_result}, 回填={fill_result}")
            return {**create_result, **fill_result}
        finally:
            await svc.close()
