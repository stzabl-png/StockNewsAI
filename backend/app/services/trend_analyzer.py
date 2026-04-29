"""
趋势分析引擎
- 计算 MA20/50/200、Higher High/Low、相对强度、成交量确认
- 输出 trend_score (0-100) 和交易建议
"""
import logging
import statistics
from datetime import date, timedelta
from typing import Optional
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.price_history import PriceHistory

logger = logging.getLogger(__name__)

# 参考指数 & 行业ETF
BENCHMARK_TICKERS = ["SPY", "QQQ"]

# 行业ETF映射（公司ticker → 所属行业ETF）
SECTOR_ETF_MAP: dict[str, str] = {
    # 科技/AI
    "NVDA": "SMH", "AMD": "SMH", "AVGO": "SMH", "MRVL": "SMH",
    "QCOM": "SMH", "INTC": "SMH", "MU": "SMH", "AMAT": "SMH",
    "SMCI": "SMH", "VRT": "XLK", "CRDO": "SMH",
    # 光通信
    "LITE": "SMH", "AAOI": "SMH", "COHR": "SMH", "CIEN": "SMH",
    # 软件
    "MSFT": "IGV", "CRM": "IGV", "SNOW": "IGV", "DDOG": "IGV",
    "NOW": "IGV", "HUBS": "IGV",
    # 大型科技
    "AAPL": "QQQ", "GOOGL": "QQQ", "META": "QQQ", "AMZN": "QQQ",
    # 生物医药
    "MRNA": "XBI", "BNTX": "XBI", "REGN": "XBI", "BIIB": "XBI",
    # 能源
    "XOM": "XLE", "CVX": "XLE", "SLB": "XLE",
    # 消费
    "SBUX": "XLY", "MCD": "XLY", "NKE": "XLY",
    "KO": "XLP", "PG": "XLP", "PEP": "XLP",
    # 金融
    "JPM": "XLF", "BAC": "XLF", "GS": "XLF",
    # 数据中心电力
    "SEI": "XLU", "CEG": "XLU", "ETN": "XLI",
    # 默认
    "DEFAULT": "SPY",
}


class TrendAnalyzer:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_prices(self, ticker: str, days: int = 210) -> list[dict]:
        """获取 ticker 最近 N 天日线数据，按日期升序"""
        since = date.today() - timedelta(days=days)
        result = await self.session.execute(
            select(PriceHistory)
            .where(PriceHistory.ticker == ticker)
            .where(PriceHistory.date >= since)
            .order_by(PriceHistory.date.asc())
        )
        rows = result.scalars().all()
        return [
            {
                "date":   r.date,
                "close":  r.close,
                "high":   r.high,
                "low":    r.low,
                "volume": r.volume or 0,
                "vwap":   r.vwap,
            }
            for r in rows
        ]

    # ─────────────────────────────────────────────────────────────
    # 核心指标计算
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _ma(closes: list[float], n: int) -> Optional[float]:
        if len(closes) < n:
            return None
        return sum(closes[-n:]) / n

    @staticmethod
    def _detect_higher_high_low(highs: list[float], lows: list[float], window: int = 10) -> dict:
        """检测最近 window 根 K 线是否形成 Higher High + Higher Low"""
        if len(highs) < window * 2:
            return {"higher_high": False, "higher_low": False, "trend_structure": "insufficient_data"}

        prev_h = highs[-window * 2:-window]
        curr_h = highs[-window:]
        prev_l = lows[-window * 2:-window]
        curr_l = lows[-window:]

        hh = max(curr_h) > max(prev_h)
        hl = min(curr_l) > min(prev_l)

        if hh and hl:
            structure = "higher_high_higher_low"
        elif not hh and not hl:
            structure = "lower_high_lower_low"
        elif hh and not hl:
            structure = "higher_high_lower_low"
        else:
            structure = "lower_high_higher_low"

        return {"higher_high": hh, "higher_low": hl, "trend_structure": structure}

    @staticmethod
    def _volume_confirmation(volumes: list[float], closes: list[float], window: int = 20) -> dict:
        """分析最近 window 天的量价关系"""
        if len(volumes) < window + 1 or len(closes) < window + 1:
            return {"up_vol_avg": None, "down_vol_avg": None, "vol_confirmation": "insufficient_data"}

        recent_vol = volumes[-window:]
        recent_cls = closes[-window:]
        avg_vol = sum(volumes[-window:]) / window if recent_vol else 1

        up_vols, down_vols = [], []
        for i in range(1, len(recent_cls)):
            if recent_cls[i] > recent_cls[i - 1]:
                up_vols.append(recent_vol[i])
            elif recent_cls[i] < recent_cls[i - 1]:
                down_vols.append(recent_vol[i])

        up_avg   = sum(up_vols)   / len(up_vols)   if up_vols   else 0
        down_avg = sum(down_vols) / len(down_vols) if down_vols else 0

        # 上涨日量 > 下跌日量 = 良好量价确认
        if up_avg > down_avg * 1.2:
            confirmation = "positive"
        elif up_avg < down_avg * 0.8:
            confirmation = "negative"
        else:
            confirmation = "neutral"

        return {
            "up_vol_avg":     round(up_avg, 0),
            "down_vol_avg":   round(down_avg, 0),
            "avg_vol_20":     round(avg_vol, 0),
            "vol_confirmation": confirmation,
        }

    @staticmethod
    def _relative_strength(ticker_ret: float, bench_ret: float) -> float:
        """RS = ticker 涨幅 - benchmark 涨幅（简单差值，越大越强）"""
        return round(ticker_ret - bench_ret, 2)

    @staticmethod
    def _period_return(closes: list[float], days: int) -> Optional[float]:
        if len(closes) <= days:
            return None
        return round((closes[-1] / closes[-(days + 1)] - 1) * 100, 2)

    @staticmethod
    def _distance_from_52w_high(highs: list[float]) -> Optional[float]:
        if len(highs) < 5:
            return None
        high_52w = max(highs)
        current  = highs[-1]
        return round((current / high_52w - 1) * 100, 2)  # 负数表示距高点百分比

    # ─────────────────────────────────────────────────────────────
    # 趋势评分
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _compute_trend_score(
        price: float,
        ma20: Optional[float],
        ma50: Optional[float],
        ma200: Optional[float],
        ret_1m: Optional[float],
        ret_3m: Optional[float],
        ret_6m: Optional[float],
        qqq_ret_3m: Optional[float],
        dist_52w: Optional[float],
        vol_conf: str,
        hh_hl: dict,
        up_vol_avg: Optional[float],
        down_vol_avg: Optional[float],
        premarket_gap: Optional[float],
    ) -> int:
        score = 0

        # 1. 均线排列 (+25)
        if ma20 and ma50 and ma200:
            if price > ma20 > ma50 > ma200:
                score += 25
            elif price > ma50 > ma200:
                score += 15
            elif price > ma200:
                score += 8

        # 2. 相对强度 vs QQQ 3个月 (+15+15)
        if ret_3m is not None and qqq_ret_3m is not None:
            rs_3m = ret_3m - qqq_ret_3m
            if rs_3m > 10:
                score += 15
            elif rs_3m > 5:
                score += 10
            elif rs_3m > 0:
                score += 5

        if ret_6m is not None and qqq_ret_3m is not None:
            # 用 qqq_ret_3m 近似行业基准（简化）
            rs_6m = (ret_6m or 0) - (qqq_ret_3m * 2)
            if rs_6m > 20:
                score += 15
            elif rs_6m > 10:
                score += 10
            elif rs_6m > 0:
                score += 5

        # 3. 距52周高点 (+10)
        if dist_52w is not None:
            if dist_52w >= -5:
                score += 10   # 接近历史高点
            elif dist_52w >= -15:
                score += 5

        # 4. 成交量确认 (+10)
        if vol_conf == "positive":
            score += 10
        elif vol_conf == "neutral":
            score += 4

        # 5. HH/HL 结构 (+10)
        if hh_hl.get("higher_high") and hh_hl.get("higher_low"):
            score += 10
        elif hh_hl.get("higher_high") or hh_hl.get("higher_low"):
            score += 4

        # 6. 扣分项
        if dist_52w is not None and dist_52w < -30:
            score -= 15     # 距高点超30%，趋势受损
        if ma50 and price < ma50:
            score -= 25     # 跌破MA50，趋势破坏
        if ret_3m is not None and ret_3m > 40:
            score -= 15     # 近3月涨幅过大，追高风险
        if premarket_gap and abs(premarket_gap) > 20:
            score -= 20     # 单日暴涨，不是趋势

        return max(0, min(100, score))

    # ─────────────────────────────────────────────────────────────
    # 主入口
    # ─────────────────────────────────────────────────────────────

    async def analyze_ticker(
        self,
        ticker: str,
        premarket_gap: Optional[float] = None,
        qqq_ret_3m: Optional[float] = None,
    ) -> Optional[dict]:
        """分析单个 ticker 的趋势，返回结构化结果"""
        prices = await self._get_prices(ticker, days=210)
        if len(prices) < 20:
            return None

        closes  = [p["close"] for p in prices]
        highs   = [p["high"]  for p in prices if p["high"]]
        lows    = [p["low"]   for p in prices if p["low"]]
        volumes = [p["volume"] for p in prices]
        latest  = prices[-1]

        # 均线
        ma20  = self._ma(closes, 20)
        ma50  = self._ma(closes, 50)
        ma200 = self._ma(closes, 200)

        # 区间收益率
        ret_1m = self._period_return(closes, 21)
        ret_3m = self._period_return(closes, 63)
        ret_6m = self._period_return(closes, 126)

        # 52周高点距离
        dist_52w = self._distance_from_52w_high(highs)

        # 高低点结构
        hh_hl = self._detect_higher_high_low(highs, lows, window=10)

        # 成交量确认
        vol_data = self._volume_confirmation(volumes, closes, window=20)

        # 均线状态
        price = closes[-1]
        if ma20 and ma50 and ma200 and price > ma20 > ma50 > ma200:
            ma_status = "price_above_20_50_200"
        elif ma50 and ma200 and price > ma50 > ma200:
            ma_status = "price_above_50_200"
        elif ma200 and price > ma200:
            ma_status = "price_above_200_only"
        else:
            ma_status = "below_ma200"

        # 趋势阶段
        trend_score = self._compute_trend_score(
            price=price, ma20=ma20, ma50=ma50, ma200=ma200,
            ret_1m=ret_1m, ret_3m=ret_3m, ret_6m=ret_6m,
            qqq_ret_3m=qqq_ret_3m,
            dist_52w=dist_52w,
            vol_conf=vol_data["vol_confirmation"],
            hh_hl=hh_hl,
            up_vol_avg=vol_data.get("up_vol_avg"),
            down_vol_avg=vol_data.get("down_vol_avg"),
            premarket_gap=premarket_gap,
        )

        if trend_score >= 80:
            trend_stage = "strong_uptrend"
        elif trend_score >= 65:
            trend_stage = "moderate_uptrend"
        elif trend_score >= 50:
            trend_stage = "weak_uptrend"
        elif trend_score >= 35:
            trend_stage = "sideways"
        else:
            trend_stage = "downtrend"

        # 最佳买点建议
        if trend_stage in ("strong_uptrend", "moderate_uptrend"):
            if ret_1m and ret_1m > 15:
                best_entry = "wait_for_pullback_to_ma20"
            elif premarket_gap and premarket_gap > 5:
                best_entry = "wait_for_vwap_hold"
            else:
                best_entry = "buy_on_vwap_hold_or_ma20_hold"
        elif trend_stage == "weak_uptrend":
            best_entry = "wait_for_confirmation"
        else:
            best_entry = "avoid_no_trend"

        sector_etf = SECTOR_ETF_MAP.get(ticker.upper(), SECTOR_ETF_MAP["DEFAULT"])

        return {
            "ticker":          ticker,
            "trend_score":     trend_score,
            "trend_stage":     trend_stage,
            "price":           round(price, 2),
            "ma20":            round(ma20, 2)  if ma20  else None,
            "ma50":            round(ma50, 2)  if ma50  else None,
            "ma200":           round(ma200, 2) if ma200 else None,
            "moving_average_status": ma_status,
            "price_structure": hh_hl["trend_structure"],
            "higher_high":     hh_hl["higher_high"],
            "higher_low":      hh_hl["higher_low"],
            "ret_1m":          ret_1m,
            "ret_3m":          ret_3m,
            "ret_6m":          ret_6m,
            "dist_52w_high_pct": dist_52w,
            "volume_confirmation": vol_data["vol_confirmation"],
            "avg_vol_20":      vol_data.get("avg_vol_20"),
            "sector_etf":      sector_etf,
            "best_entry":      best_entry,
            "risk": "extended_short_term" if (ret_1m or 0) > 20 else "normal",
            "invalid_condition": "break_below_ma50_with_volume",
            "as_of":           str(latest["date"]),
        }

    async def scan_tickers(
        self,
        tickers: list[str],
        qqq_ret_3m: Optional[float] = None,
        min_trend_score: int = 50,
    ) -> list[dict]:
        """批量扫描，返回按 trend_score 降序的结果"""
        results = []
        for ticker in tickers:
            try:
                r = await self.analyze_ticker(ticker, qqq_ret_3m=qqq_ret_3m)
                if r and r["trend_score"] >= min_trend_score:
                    results.append(r)
            except Exception as e:
                logger.warning(f"[Trend] {ticker} 分析失败: {e}")

        results.sort(key=lambda x: x["trend_score"], reverse=True)
        return results
