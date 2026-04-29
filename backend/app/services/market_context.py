"""
行情上下文服务 — 为 L3 深度分析注入真实市场数据

在 analyzer.py 调用 L3 之前调用本模块，将以下数据嵌入 Prompt：
- premarket_gap_pct / afterhours_move_pct  盘前/盘后涨幅
- rel_volume                                相对成交量（vs 20日均量）
- prev_5d_return                            近5日涨幅（是否已被提前炒作）
- spy_change_pct / qqq_change_pct           大盘环境
- vwap                                      全天成交均价（判断开盘强弱）

数据来源：Polygon.io（已有 API Key）
所有字段均有 None fallback，不会阻塞 L3 调用。
"""
import logging
from datetime import date, timedelta
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

POLYGON_BASE = "https://api.polygon.io"

# 代理市场环境的 benchmark ETF
_BENCHMARK_TICKERS = ["SPY", "QQQ"]

# 模块级别的 HTTP 客户端（复用连接池）
_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=15)
    return _client


async def _fetch_bars(ticker: str, start: str, end: str, limit: int = 30) -> list:
    """拉取 OHLCV 日线数据，返回 bars 列表，出错返回 []"""
    url = f"{POLYGON_BASE}/v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}"
    params = {
        "adjusted": "true",
        "sort": "asc",
        "limit": limit,
        "apiKey": settings.POLYGON_API_KEY,
    }
    try:
        resp = await _get_client().get(url, params=params)
        if resp.status_code == 200:
            return resp.json().get("results", [])
    except Exception as e:
        logger.debug(f"[MarketCtx] {ticker} bars fetch failed: {e}")
    return []


async def _fetch_prev_close(ticker: str) -> Optional[float]:
    """获取前一交易日收盘价（用于计算盘前 gap）"""
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=5)
    bars = await _fetch_bars(ticker, start.isoformat(), end.isoformat(), limit=5)
    if bars:
        return bars[-1].get("c")  # 最近一日收盘价
    return None


async def _fetch_snapshot_price(ticker: str) -> Optional[dict]:
    """
    获取 Polygon 最新快照（包含盘前/盘后数据，需要 Starter+ 计划）
    返回 {"premarket": float, "postmarket": float, "close": float}
    如果 API 不支持则返回 None
    """
    url = f"{POLYGON_BASE}/v2/snapshot/locale/us/markets/stocks/tickers/{ticker}"
    params = {"apiKey": settings.POLYGON_API_KEY}
    try:
        resp = await _get_client().get(url, params=params)
        if resp.status_code == 200:
            data = resp.json()
            ticker_data = data.get("ticker", {})
            day = ticker_data.get("day", {})
            prev_day = ticker_data.get("prevDay", {})
            return {
                "premarket": ticker_data.get("lastQuote", {}).get("P"),  # 盘前最后报价
                "close": day.get("c"),
                "prev_close": prev_day.get("c"),
                "vwap": day.get("vw"),          # 当日成交均价
                "volume": day.get("v"),
                "prev_volume": prev_day.get("v"),
            }
    except Exception as e:
        logger.debug(f"[MarketCtx] {ticker} snapshot failed: {e}")
    return None


async def get_market_context(ticker: str) -> dict:
    """
    获取用于 L3 Prompt 注入的行情上下文。

    返回字段说明：
    - premarket_gap_pct:    盘前涨跌幅（%）。None = 无法获取
    - rel_volume:           当日成交量 / 20日均量。>3 代表异常放量
    - prev_5d_return:       过去5个交易日收益率（%）
    - spy_change_pct:       SPY当日涨跌（判断大盘环境）
    - qqq_change_pct:       QQQ当日涨跌（判断成长股环境）
    - vwap:                 当日成交加权均价
    - avg_volume_20d:       20日平均成交量
    - has_data:             True = 至少有部分行情数据，False = 完全无数据

    调用方须处理所有字段为 None 的情况。
    """
    if not settings.POLYGON_API_KEY:
        logger.warning("[MarketCtx] POLYGON_API_KEY 未配置，跳过行情上下文获取")
        return _empty_context()

    import asyncio

    # 并行拉取目标股票 + SPY + QQQ 的最近30天数据
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=35)  # 多取几天确保有25个交易日
    start_str, end_str = start.isoformat(), end.isoformat()

    ticker_bars_task  = _fetch_bars(ticker, start_str, end_str, limit=35)
    spy_bars_task     = _fetch_bars("SPY", start_str, end_str, limit=35)
    qqq_bars_task     = _fetch_bars("QQQ", start_str, end_str, limit=35)
    snapshot_task     = _fetch_snapshot_price(ticker)

    ticker_bars, spy_bars, qqq_bars, snapshot = await asyncio.gather(
        ticker_bars_task, spy_bars_task, qqq_bars_task, snapshot_task,
        return_exceptions=True,
    )

    # 处理 gather 异常
    ticker_bars = ticker_bars if isinstance(ticker_bars, list) else []
    spy_bars    = spy_bars    if isinstance(spy_bars,    list) else []
    qqq_bars    = qqq_bars    if isinstance(qqq_bars,    list) else []
    snapshot    = snapshot    if isinstance(snapshot,    dict) else None

    if not ticker_bars:
        logger.info(f"[MarketCtx] {ticker} 无历史行情数据")
        return _empty_context()

    ctx: dict = {"has_data": True}

    # ── 1. 近5日收益率（提前炒作判断）─────────────────────────────────────────
    if len(ticker_bars) >= 6:
        price_5d_ago = ticker_bars[-6]["c"]
        price_now    = ticker_bars[-1]["c"]
        if price_5d_ago and price_5d_ago > 0:
            ctx["prev_5d_return"] = round((price_now - price_5d_ago) / price_5d_ago * 100, 2)
        else:
            ctx["prev_5d_return"] = None
    else:
        ctx["prev_5d_return"] = None

    # ── 2. 相对成交量（资金是否真的进来）──────────────────────────────────────
    recent_volumes = [b.get("v", 0) for b in ticker_bars[-21:-1] if b.get("v")]  # 取最近20日（不含今天）
    avg_volume_20d = sum(recent_volumes) / len(recent_volumes) if recent_volumes else None
    latest_volume  = ticker_bars[-1].get("v")
    ctx["avg_volume_20d"] = round(avg_volume_20d) if avg_volume_20d else None
    if avg_volume_20d and latest_volume and avg_volume_20d > 0:
        ctx["rel_volume"] = round(latest_volume / avg_volume_20d, 2)
    else:
        ctx["rel_volume"] = None

    # ── 3. 盘前 gap（从 Snapshot API 或日线数据估算）────────────────────────────
    premarket_gap_pct = None
    vwap = None
    if snapshot:
        prev_close = snapshot.get("prev_close") or (ticker_bars[-2]["c"] if len(ticker_bars) >= 2 else None)
        pre_price  = snapshot.get("premarket")
        if pre_price and prev_close and prev_close > 0:
            premarket_gap_pct = round((pre_price - prev_close) / prev_close * 100, 2)
        vwap = snapshot.get("vwap")
        # 如果snapshot有当日成交量，用于更准确的rel_volume
        if snapshot.get("volume") and avg_volume_20d and avg_volume_20d > 0:
            ctx["rel_volume"] = round(snapshot["volume"] / avg_volume_20d, 2)
    else:
        # 无Snapshot时，用昨日open vs 前日close估算gap
        if len(ticker_bars) >= 2:
            prev_close = ticker_bars[-2]["c"]
            today_open = ticker_bars[-1]["o"]
            if prev_close and today_open and prev_close > 0:
                premarket_gap_pct = round((today_open - prev_close) / prev_close * 100, 2)

    ctx["premarket_gap_pct"] = premarket_gap_pct
    ctx["vwap"] = round(vwap, 2) if vwap else None
    ctx["current_price"] = ticker_bars[-1]["c"]
    ctx["prev_close"] = ticker_bars[-2]["c"] if len(ticker_bars) >= 2 else None

    # ── 4. 大盘环境（SPY / QQQ）──────────────────────────────────────────────
    ctx["spy_change_pct"]  = _last_day_change(spy_bars)
    ctx["qqq_change_pct"]  = _last_day_change(qqq_bars)

    logger.info(
        f"[MarketCtx] {ticker} | gap={premarket_gap_pct}% | "
        f"relVol={ctx.get('rel_volume')}x | "
        f"5d={ctx.get('prev_5d_return')}% | "
        f"SPY={ctx.get('spy_change_pct')}% QQQ={ctx.get('qqq_change_pct')}%"
    )
    return ctx


def _last_day_change(bars: list) -> Optional[float]:
    """计算bars最后一天的开盘→收盘涨跌幅"""
    if not bars:
        return None
    b = bars[-1]
    o, c = b.get("o"), b.get("c")
    if o and c and o > 0:
        return round((c - o) / o * 100, 2)
    return None


def _empty_context() -> dict:
    """当行情数据完全不可用时返回的空上下文"""
    return {
        "has_data":           False,
        "premarket_gap_pct":  None,
        "rel_volume":         None,
        "prev_5d_return":     None,
        "spy_change_pct":     None,
        "qqq_change_pct":     None,
        "vwap":               None,
        "current_price":      None,
        "prev_close":         None,
        "avg_volume_20d":     None,
    }


def format_market_context_for_prompt(ctx: dict, ticker: str) -> str:
    """
    将行情上下文格式化为 Prompt 文本段落。
    在 has_data=False 时返回说明性占位文本。
    """
    if not ctx.get("has_data"):
        return "## 实时行情数据\n（暂无行情数据，请依据事件本身判断）\n"

    def fmt(val, suffix="", decimals=2, na="暂无"):
        if val is None:
            return na
        return f"{val:.{decimals}f}{suffix}"

    # 判断大盘环境
    spy = ctx.get("spy_change_pct")
    qqq = ctx.get("qqq_change_pct")
    if spy is not None and qqq is not None:
        if spy < -1.0 and qqq < -1.5:
            market_env = "❌ 大盘大幅走弱（风险偏好低，信号可靠性打折）"
        elif spy < -0.5 or qqq < -0.8:
            market_env = "⚠️ 大盘偏弱（需额外确认）"
        elif spy > 0.5 and qqq > 0.5:
            market_env = "✅ 大盘走强（有利于事件驱动行情）"
        else:
            market_env = "➡️ 大盘平稳"
    else:
        market_env = "暂无大盘数据"

    # 判断相对成交量
    rel_vol = ctx.get("rel_volume")
    if rel_vol is None:
        vol_comment = "成交量数据暂无"
    elif rel_vol >= 5:
        vol_comment = f"{rel_vol:.1f}x ⚡ 极度放量（资金高度关注）"
    elif rel_vol >= 3:
        vol_comment = f"{rel_vol:.1f}x 🔥 明显放量（资金介入信号）"
    elif rel_vol >= 1.5:
        vol_comment = f"{rel_vol:.1f}x 📈 温和放量"
    else:
        vol_comment = f"{rel_vol:.1f}x ↘️ 缩量（资金参与度低）"

    # 盘前 gap 判断
    gap = ctx.get("premarket_gap_pct")
    if gap is None:
        gap_comment = "盘前涨幅: 暂无"
    elif gap > 20:
        gap_comment = f"盘前涨幅: +{gap:.1f}% ⚠️ 涨幅极大，追高风险极高"
    elif gap > 10:
        gap_comment = f"盘前涨幅: +{gap:.1f}% ⚠️ 涨幅较大，建议等回踩"
    elif gap > 3:
        gap_comment = f"盘前涨幅: +{gap:.1f}% 📈 中等 gap，可考虑 VWAP 策略"
    elif gap < -5:
        gap_comment = f"盘前跌幅: {gap:.1f}% ↘️ 显著低开"
    else:
        gap_comment = f"盘前涨幅: {gap:+.1f}%（平稳）"

    # 近5日是否提前炒作
    prev5 = ctx.get("prev_5d_return")
    if prev5 is None:
        prev5_comment = "近5日走势: 暂无"
    elif prev5 > 30:
        prev5_comment = f"近5日已涨 +{prev5:.1f}% ⚠️ 可能已被提前炒作，获利盘压力大"
    elif prev5 > 15:
        prev5_comment = f"近5日已涨 +{prev5:.1f}% 📈 有一定涨幅，需注意获利盘"
    elif prev5 < -15:
        prev5_comment = f"近5日已跌 {prev5:.1f}% 💡 超卖反弹空间大"
    else:
        prev5_comment = f"近5日涨跌: {prev5:+.1f}%（正常波动）"

    lines = [
        f"## 实时行情数据（{ticker}）",
        f"- 当前价格: ${fmt(ctx.get('current_price'))}  |  前收: ${fmt(ctx.get('prev_close'))}",
        f"- {gap_comment}",
        f"- 相对成交量: {vol_comment}",
        f"- {prev5_comment}",
        f"- VWAP: ${fmt(ctx.get('vwap'), na='暂无')}",
        f"",
        f"## 大盘环境",
        f"- SPY 当日: {fmt(ctx.get('spy_change_pct'), '%', na='暂无')}  |  QQQ 当日: {fmt(ctx.get('qqq_change_pct'), '%', na='暂无')}",
        f"- 综合判断: {market_env}",
    ]
    return "\n".join(lines)
