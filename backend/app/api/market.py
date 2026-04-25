"""
行情数据 API
- /api/market/chart/{ticker}  → 30天日线 K 线数据
- /api/market/quote/{ticker}  → 最新报价
"""
import asyncio
from datetime import date, timedelta
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Path, Query
from fastapi.responses import JSONResponse

from app.config import settings

router = APIRouter(tags=["Market"])

POLYGON_BASE = "https://api.polygon.io"
_http_client: Optional[httpx.AsyncClient] = None


def get_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=15)
    return _http_client


# ── 常见 Ticker 别名映射（DB ticker → Polygon ticker）────────────────────────
# 当公司存储的 ticker 和实际交易代码不一致时使用
TICKER_ALIASES = {
    "TSMC":   "TSM",    # Taiwan Semiconductor ADR
    "BABA":   "BABA",   # Already correct
    "BRK_B":  "BRK.B",  # Berkshire B
    "BRK_A":  "BRK.A",  # Berkshire A
    "GE_WS":  "GE.WS",
    "GOOGL":  "GOOGL",
    # ADR suffix patterns - strip common suffixes
}

def _normalize_ticker(ticker: str) -> list[str]:
    """Return a list of ticker variants to try, most likely first."""
    t = ticker.upper().strip()
    candidates = [t]

    # Try alias table
    if t in TICKER_ALIASES:
        candidates.insert(0, TICKER_ALIASES[t])

    # Strip common ADR/warrant suffixes and try
    for suffix in [".WS", ".WT", ".R", ".U", ".W", "W", "P"]:
        if t.endswith(suffix) and len(t) > len(suffix) + 1:
            candidates.append(t[: -len(suffix)])

    return list(dict.fromkeys(candidates))  # deduplicate preserving order


async def _fetch_bars(ticker: str, start: str, end: str, limit: int) -> list:
    """Fetch OHLCV bars from Polygon for a single ticker. Returns [] on no data."""
    url = (
        f"{POLYGON_BASE}/v2/aggs/ticker/{ticker}/range/1/day"
        f"/{start}/{end}"
    )
    params = {
        "adjusted": "true",
        "sort": "asc",
        "limit": limit,
        "apiKey": settings.POLYGON_API_KEY,
    }
    try:
        resp = await get_client().get(url, params=params)
        if resp.status_code == 200:
            return resp.json().get("results", [])
    except Exception:
        pass
    return []


@router.get("/market/chart/{ticker}")
async def get_price_chart(
    ticker: str = Path(..., description="股票代码，如 AAPL"),
    days: int = Query(30, ge=5, le=365, description="返回多少天的数据"),
):
    """
    获取指定股票最近 N 天的日线 OHLCV 数据（用于前端 K线图）
    返回格式: {ticker, bars:[{date, open, high, low, close, volume, change_pct}], ...}
    自动尝试多种 ticker 变体（别名映射 + ADR 后缀处理）
    """
    if not settings.POLYGON_API_KEY:
        raise HTTPException(status_code=503, detail="Polygon API Key 未配置")

    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=days + 15)
    limit = days + 15

    # Try ticker variants in order until we get data
    candidates = _normalize_ticker(ticker)
    bars = []
    used_ticker = candidates[0]
    for candidate in candidates:
        bars = await _fetch_bars(candidate, start.isoformat(), end.isoformat(), limit)
        if bars:
            used_ticker = candidate
            break

    if not bars:
        return JSONResponse({
            "ticker": ticker.upper(),
            "bars": [],
            "message": f"暂无数据 (尝试了: {', '.join(candidates)})",
        })

    # 取最近 days 个交易日
    bars = bars[-days:]

    processed = []
    for i, b in enumerate(bars):
        prev_close = bars[i - 1]["c"] if i > 0 else b["o"]
        change_pct = round((b["c"] - prev_close) / prev_close * 100, 2) if prev_close else 0
        processed.append({
            "date":       date.fromtimestamp(b["t"] / 1000).isoformat(),
            "open":       b.get("o"),
            "high":       b.get("h"),
            "low":        b.get("l"),
            "close":      b.get("c"),
            "volume":     b.get("v"),
            "change_pct": change_pct,
        })

    # 整体涨跌
    total_change = round(
        (processed[-1]["close"] - processed[0]["open"]) / processed[0]["open"] * 100, 2
    ) if processed[0]["open"] else 0

    return {
        "ticker":        used_ticker,   # return the actual ticker that worked
        "query_ticker":  ticker.upper(),
        "bars":          processed,
        "latest_close":  processed[-1]["close"],
        "latest_date":   processed[-1]["date"],
        "period_change": total_change,
        "days":          len(processed),
    }


@router.get("/market/quote/{ticker}")
async def get_latest_quote(
    ticker: str = Path(..., description="股票代码"),
):
    """
    获取最新收盘价（Polygon 前一交易日数据，Starter plan 为延迟数据）
    """
    if not settings.POLYGON_API_KEY:
        raise HTTPException(status_code=503, detail="Polygon API Key 未配置")

    yesterday = date.today() - timedelta(days=1)
    url = (
        f"{POLYGON_BASE}/v2/aggs/ticker/{ticker.upper()}/range/1/day"
        f"/{yesterday}/{yesterday}"
    )
    params = {"adjusted": "true", "limit": 1, "apiKey": settings.POLYGON_API_KEY}

    try:
        resp = await get_client().get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        bars = data.get("results", [])
        if not bars:
            raise HTTPException(status_code=404, detail="暂无报价数据")
        b = bars[0]
        change_pct = round((b["c"] - b["o"]) / b["o"] * 100, 2) if b.get("o") else 0
        return {
            "ticker":     ticker.upper(),
            "close":      b.get("c"),
            "open":       b.get("o"),
            "high":       b.get("h"),
            "low":        b.get("l"),
            "volume":     b.get("v"),
            "date":       yesterday.isoformat(),
            "change_pct": change_pct,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

# ============================================================
# 板块/概念 行情概览  /api/market/overview
# ============================================================
import json, logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# 85 自定义中国风行业板块（与数据库 sector 字段对应）
CUSTOM_SECTORS = [
    # ── 科技 ──
    {"name": "半导体",     "icon": "🔬", "group": "科技"},
    {"name": "软件开发",   "icon": "💻", "group": "科技"},
    {"name": "互联网服务", "icon": "🌐", "group": "科技"},
    {"name": "计算机设备", "icon": "🖥️", "group": "科技"},
    {"name": "通信设备",   "icon": "📡", "group": "科技"},
    {"name": "电子元件",   "icon": "⚙️", "group": "科技"},
    {"name": "消费电子",   "icon": "📱", "group": "科技"},
    {"name": "光学光电子", "icon": "🔭", "group": "科技"},
    {"name": "仪器仪表",   "icon": "🧰", "group": "科技"},
    {"name": "专业设备",   "icon": "🛠️", "group": "科技"},
    # ── 新能源 ──
    {"name": "光伏设备",   "icon": "☀️", "group": "新能源"},
    {"name": "风电设备",   "icon": "💨", "group": "新能源"},
    {"name": "电池",       "icon": "🔋", "group": "新能源"},
    {"name": "电源设备",   "icon": "🔌", "group": "新能源"},
    {"name": "电网设备",   "icon": "⚡", "group": "新能源"},
    {"name": "电机",       "icon": "🔩", "group": "新能源"},
    {"name": "通用设备",   "icon": "🏗️", "group": "新能源"},
    # ── 医疗 ──
    {"name": "生物制品",   "icon": "🧬", "group": "医疗"},
    {"name": "化学制药",   "icon": "💊", "group": "医疗"},
    {"name": "医疗器械",   "icon": "🩺", "group": "医疗"},
    {"name": "医疗服务",   "icon": "🏥", "group": "医疗"},
    {"name": "医药商业",   "icon": "💉", "group": "医疗"},
    {"name": "农药兽药",   "icon": "🐾", "group": "医疗"},
    # ── 金融 ──
    {"name": "银行类",     "icon": "🏦", "group": "金融"},
    {"name": "保险类",     "icon": "🛡️", "group": "金融"},
    {"name": "券商类",     "icon": "📈", "group": "金融"},
    {"name": "多元金融",   "icon": "💳", "group": "金融"},
    {"name": "房地产服务", "icon": "🏠", "group": "金融"},
    # ── 能源 ──
    {"name": "石油类",     "icon": "🛢️", "group": "能源"},
    {"name": "天然气",     "icon": "🔥", "group": "能源"},
    {"name": "煤炭",       "icon": "⛏️", "group": "能源"},
    {"name": "电力",       "icon": "💡", "group": "能源"},
    {"name": "燃气",       "icon": "🌡️", "group": "能源"},
    {"name": "公用事业",   "icon": "🚰", "group": "能源"},
    {"name": "能源金属",   "icon": "⚒️", "group": "能源"},
    # ── 材料 ──
    {"name": "钢铁类",     "icon": "🏭", "group": "材料"},
    {"name": "有色",       "icon": "🥇", "group": "材料"},
    {"name": "黄金矿业",   "icon": "✨", "group": "材料"},
    {"name": "小金属",     "icon": "🪙", "group": "材料"},
    {"name": "化学制品",   "icon": "⚗️", "group": "材料"},
    {"name": "化学原料",   "icon": "🧪", "group": "材料"},
    {"name": "电子化学品", "icon": "🔮", "group": "材料"},
    {"name": "化肥类",     "icon": "🌾", "group": "材料"},
    {"name": "橡胶制品",   "icon": "⭕", "group": "材料"},
    {"name": "塑料制品",   "icon": "📦", "group": "材料"},
    {"name": "非金属材料", "icon": "🪨", "group": "材料"},
    {"name": "水泥建材",   "icon": "🏗️", "group": "材料"},
    {"name": "玻璃纤维",   "icon": "🔵", "group": "材料"},
    {"name": "包装材料",   "icon": "📫", "group": "材料"},
    {"name": "造纸印刷",   "icon": "📰", "group": "材料"},
    # ── 消费 ──
    {"name": "食品饮料",   "icon": "🍔", "group": "消费"},
    {"name": "酒类",       "icon": "🍷", "group": "消费"},
    {"name": "美容护理",   "icon": "💄", "group": "消费"},
    {"name": "纺织服饰",   "icon": "👗", "group": "消费"},
    {"name": "商业百货",   "icon": "🛒", "group": "消费"},
    {"name": "家电类",     "icon": "🏠", "group": "消费"},
    {"name": "家用轻工",   "icon": "🧹", "group": "消费"},
    {"name": "珠宝首饰",   "icon": "💎", "group": "消费"},
    {"name": "宠物经济",   "icon": "🐾", "group": "消费"},
    {"name": "贸易行业",   "icon": "🔄", "group": "消费"},
    # ── 工业 ──
    {"name": "航空航天",   "icon": "🚀", "group": "工业"},
    {"name": "船舶制造",   "icon": "🚢", "group": "工业"},
    {"name": "汽车整车",   "icon": "🚗", "group": "工业"},
    {"name": "汽车零部件", "icon": "🔧", "group": "工业"},
    {"name": "汽车服务",   "icon": "🔩", "group": "工业"},
    {"name": "工程建设",   "icon": "🏗️", "group": "工业"},
    {"name": "工程咨询服务","icon": "📋", "group": "工业"},
    {"name": "工程机械",   "icon": "⚙️", "group": "工业"},
    {"name": "物流行业",   "icon": "📦", "group": "工业"},
    {"name": "航运港口",   "icon": "⚓", "group": "工业"},
    {"name": "铁路公路",   "icon": "🚂", "group": "工业"},
    {"name": "航空机场",   "icon": "✈️", "group": "工业"},
    {"name": "轨道交通",   "icon": "🚈", "group": "工业"},
    {"name": "交运设备",   "icon": "🚛", "group": "工业"},
    # ── 建筑地产 ──
    {"name": "房地产开发", "icon": "🏘️", "group": "建筑地产"},
    {"name": "装修建材",   "icon": "🔨", "group": "建筑地产"},
    {"name": "装修装饰",   "icon": "🎨", "group": "建筑地产"},
    # ── 农业 ──
    {"name": "农牧饲渔",   "icon": "🌾", "group": "农业"},
    {"name": "环保类",     "icon": "♻️", "group": "农业"},
    {"name": "水务",       "icon": "💧", "group": "农业"},
    # ── 文化传媒 ──
    {"name": "文化传媒",   "icon": "🎬", "group": "文化"},
    {"name": "游戏",       "icon": "🎮", "group": "文化"},
    {"name": "教育",       "icon": "📚", "group": "文化"},
    {"name": "旅游酒店",   "icon": "🏨", "group": "文化"},
    # ── 通信 ──
    {"name": "通信服务",   "icon": "📶", "group": "通信"},
    # ── 综合 ──
    {"name": "综合类",     "icon": "🏢", "group": "综合"},
]

# 风格 ETF
STYLE_ETFS = [
    {"name": "科技成长",    "name_en": "Tech Growth",    "ticker": "QQQ",  "icon": "📈"},
    {"name": "大盘科技",    "name_en": "Large Cap Tech",  "ticker": "XLK",  "icon": "💻"},
    {"name": "价值蓝筹",    "name_en": "Value Blue Chip", "ticker": "VTV",  "icon": "🏛️"},
    {"name": "高股息",      "name_en": "High Dividend",   "ticker": "VYM",  "icon": "💰"},
    {"name": "小盘成长",    "name_en": "Small Cap Growth","ticker": "IWM",  "icon": "🌱"},
    {"name": "标普500指数", "name_en": "S&P 500 Index",   "ticker": "SPY",  "icon": "🇺🇸"},
    {"name": "清洁能源",    "name_en": "Clean Energy",    "ticker": "ICLN", "icon": "☀️"},
    {"name": "生物科技ETF", "name_en": "Biotech",         "ticker": "XBI",  "icon": "🧬"},
]

_overview_cache: dict = {}
_cache_ts: float = 0.0
CACHE_TTL = 3600  # 1小时缓存


async def _get_etf_change(ticker: str, api_key: str) -> dict:
    """获取单个ETF的日涨跌幅"""
    from datetime import date, timedelta
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=5)
    url = f"{POLYGON_BASE}/v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}"
    params = {"adjusted": "true", "sort": "desc", "limit": 2, "apiKey": api_key}
    try:
        resp = await get_client().get(url, params=params)
        data = resp.json()
        bars = data.get("results", [])
        if len(bars) >= 1:
            b = bars[0]
            pct = round((b["c"] - b["o"]) / b["o"] * 100, 2) if b.get("o") else 0
            return {"close": b["c"], "change_pct": pct, "date": str(end)}
    except Exception as e:
        logger.warning(f"ETF {ticker}: {e}")
    return {"close": None, "change_pct": None}


async def _get_grouped_daily(target_date: str, api_key: str) -> dict:
    """获取全市场当日快照，返回 {ticker: change_pct} 字典"""
    url = f"{POLYGON_BASE}/v2/aggs/grouped/locale/us/market/stocks/{target_date}"
    params = {"adjusted": "true", "apiKey": api_key}
    try:
        resp = await get_client().get(url, params=params, timeout=30)
        data = resp.json()
        result = {}
        for b in data.get("results", []):
            t = b.get("T", "")
            o, c = b.get("o"), b.get("c")
            if t and o and c and o > 0:
                result[t] = {
                    "change_pct": round((c - o) / o * 100, 2),
                    "close": c,
                    "volume": b.get("v", 0),
                }
        return result
    except Exception as e:
        logger.error(f"grouped daily failed: {e}")
        return {}


@router.get("/market/overview")
async def get_market_overview():
    """
    返回板块/概念/风格的日涨跌幅 + 领涨股
    用于分类页面截图风格展示
    """
    global _overview_cache, _cache_ts
    import time
    if _overview_cache and (time.time() - _cache_ts) < CACHE_TTL:
        return _overview_cache

    if not settings.POLYGON_API_KEY:
        raise HTTPException(status_code=503, detail="Polygon API Key 未配置")

    from datetime import date, timedelta
    # 找最近交易日（跳过周末）
    d = date.today() - timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    target_date = d.isoformat()

    # 并行获取：全市场快照 + 风格ETF（板块性能现从成分股均值计算，不依赖ETF）
    all_etf_tickers = [s["ticker"] for s in STYLE_ETFS]

    grouped_task = _get_grouped_daily(target_date, settings.POLYGON_API_KEY)
    etf_tasks = [_get_etf_change(t, settings.POLYGON_API_KEY) for t in all_etf_tickers]

    import asyncio as _asyncio
    results = await _asyncio.gather(grouped_task, *etf_tasks, return_exceptions=True)
    daily_prices = results[0] if isinstance(results[0], dict) else {}
    etf_results = {}
    for i, t in enumerate(all_etf_tickers):
        r = results[i + 1]
        etf_results[t] = r if isinstance(r, dict) else {"change_pct": None, "close": None}

    # ── 1. 板块涨跌 ── 从DB读取所有公司的 sector 字段 ──────────────────────────
    from app.database import async_session as _session

    async with _session() as db:
        from sqlalchemy import text as _text
        rows = (await db.execute(_text(
            "SELECT ticker, sector FROM companies WHERE is_active=true AND sector IS NOT NULL"
        ))).fetchall()

    sector_map: dict[str, list] = {}
    for ticker_row, sector_row in rows:
        sector_map.setdefault(sector_row, []).append(ticker_row)

    sectors_out = []
    for info in CUSTOM_SECTORS:
        sname = info["name"]
        tickers_in_sector = sector_map.get(sname, [])
        # Calculate avg change from constituent companies
        changes = [daily_prices[t]["change_pct"] for t in tickers_in_sector
                   if t in daily_prices and daily_prices[t].get("change_pct") is not None]
        avg_change = round(sum(changes) / len(changes), 2) if changes else None

        leader = leader_chg = None
        if changes:
            best = max(changes)
            for t in tickers_in_sector:
                if t in daily_prices and daily_prices[t].get("change_pct") == best:
                    leader = t; leader_chg = best; break

        sectors_out.append({
            "name":          sname,
            "name_en":       sname,
            "icon":          info["icon"],
            "group":         info.get("group", "其他"),
            "change_pct":    avg_change,
            "leader":        leader,
            "leader_change": leader_chg,
            "company_count": len(tickers_in_sector),
        })

    # ── 2. 概念涨跌 ── 从DB读取所有concepts ───────────────────────────────
    # Schema from init_us_concepts.py: id, name, keywords, related_tickers, is_active
    # We stored icon and name_en in older concepts; for new ones we need fallback
    CONCEPT_ICONS = {
        100:"🤖",101:"✨",102:"🔬",103:"☁️",104:"🛡️",105:"⚡",106:"🧬",107:"🦾",
        108:"🏢",109:"⚙️",110:"📡",111:"📶",112:"🛸",113:"🌐",114:"💾",115:"💿",
        116:"🔗",117:"🥽",118:"📊",120:"☀️",121:"💨",122:"🔋",123:"🔌",124:"⚗️",
        125:"⚡",126:"♻️",130:"💊",131:"🔬",132:"🩺",133:"💉",134:"🐾",
        140:"💳",141:"🏦",142:"🛡️",143:"📈",150:"✈️",151:"🚜",152:"📦",153:"🚂",
        154:"🚢",155:"🚗",156:"🔩",160:"🛢️",161:"⛏️",162:"🪨",163:"🥇",164:"🧪",
        165:"🌱",170:"🍔",171:"🍷",172:"💄",173:"🛒",174:"🎮",175:"✈️",176:"📚",
        180:"🏠",181:"🏗️",182:"🌉",183:"💧",190:"💡",191:"🔥",195:"🌾",196:"🌍",
        # Old concept ids
        1:"🤖",2:"☁️",3:"🔬",4:"⚡",5:"🧬",6:"🛡️",7:"🤖",8:"💊",
        9:"🏥",10:"📡",11:"🌐",12:"🚀",13:"💰",14:"🏦",15:"💎",16:"⚙️",
        17:"🛒",18:"☀️",19:"💡",20:"🏗️",
    }
    DEFAULT_IDS = {100,101,102,103,104,105,106,107}  # tech-first defaults

    async with _session() as db:
        concept_rows = (await db.execute(_text(
            "SELECT id, name, related_tickers FROM concepts WHERE is_active=true ORDER BY id"
        ))).fetchall()

    concepts_out = []
    for cid, cname, tickers_arr in concept_rows:
        tickers = tickers_arr or []
        changes = [daily_prices[t]["change_pct"] for t in tickers if t in daily_prices]
        avg_change = round(sum(changes) / len(changes), 2) if changes else None
        leader = leader_chg = None
        if changes:
            best = max(changes)
            for t in tickers:
                if t in daily_prices and daily_prices[t]["change_pct"] == best:
                    leader = t; leader_chg = best; break
        concepts_out.append({
            "id":            cid,
            "name":          cname,
            "name_en":       cname,
            "icon":          CONCEPT_ICONS.get(cid, "📌"),
            "change_pct":    avg_change,
            "leader":        leader,
            "leader_change": leader_chg,
            "is_default":    cid in DEFAULT_IDS,
        })

    # ── 3. 风格涨跌 ──────────────────────────────────────────────
    styles_out = []
    for s in STYLE_ETFS:
        etf_data = etf_results.get(s["ticker"], {})
        styles_out.append({
            "name":       s["name"],
            "name_en":    s["name_en"],
            "icon":       s["icon"],
            "ticker":     s["ticker"],
            "close":      etf_data.get("close"),
            "change_pct": etf_data.get("change_pct"),
            "leader":     s["ticker"],
            "leader_change": etf_data.get("change_pct"),
        })

    _overview_cache = {
        "date":     target_date,
        "sectors":  sectors_out,
        "concepts": concepts_out,
        "styles":   styles_out,
        "cached_at": datetime.now(timezone.utc).isoformat(),
    }
    _cache_ts = time.time()
    return _overview_cache
