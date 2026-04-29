"""
交易信号生成器 — 将评分结果翻译成具体交易指令

信号层次：
  BUY_ON_VWAP_HOLD    → 开盘15min后若站稳VWAP则买入（风险中等）
  WAIT_FOR_PULLBACK   → 盘前涨幅过大，等回踩再介入（风险高，需等待）
  WATCH_ONLY          → 事件好但大盘弱/成交量不足，只看不买
  WATCH_SYMPATHY      → 主线追高风险大，考虑联动股/板块ETF
  AVOID               → 不交易（信号质量不足或风险过高）

每个信号附带：
  - entry_rule:     入场规则
  - stop_loss_rule: 止损规则
  - position_size:  仓位建议（large/medium/small/none）
  - reason_cn:      中文原因说明
  - sympathy_tickers: 联动股建议（如有）
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 联动股图谱（sector_map）
# 新闻涉及某个 ticker 时，自动推荐可能联动的同板块/供应链股票
SYMPATHY_MAP: dict[str, dict] = {
    # 存储
    "STX":  {"direct": ["WDC", "SNDK"], "related": ["MU", "PSTG", "NTAP"],  "etfs": ["SMH"]},
    "WDC":  {"direct": ["STX", "SNDK"], "related": ["MU", "PSTG"],           "etfs": ["SMH"]},
    "SNDK": {"direct": ["WDC", "STX"],  "related": ["MU"],                   "etfs": ["SMH"]},

    # AI 基础设施
    "NVDA": {"direct": ["AMD", "AVGO"],   "related": ["MRVL", "SMCI", "VRT"], "etfs": ["SMH", "SOXX"]},
    "AMD":  {"direct": ["NVDA", "INTC"],  "related": ["MRVL", "QCOM"],        "etfs": ["SMH", "SOXX"]},
    "AVGO": {"direct": ["MRVL", "QCOM"],  "related": ["NVDA", "INTC"],        "etfs": ["SMH", "SOXX"]},
    "MRVL": {"direct": ["AVGO", "QCOM"],  "related": ["CIEN", "COHR"],        "etfs": ["SMH"]},
    "QCOM": {"direct": ["AVGO", "MRVL"],  "related": ["AMD", "INTC"],         "etfs": ["SMH", "SOXX"]},

    # 光通信
    "LITE": {"direct": ["AAOI", "COHR"],  "related": ["CIEN", "FN"],          "etfs": ["SMH"]},
    "AAOI": {"direct": ["LITE", "COHR"],  "related": ["CIEN", "FNSR"],        "etfs": []},
    "COHR": {"direct": ["LITE", "AAOI"],  "related": ["CIEN", "FN"],          "etfs": []},
    "CIEN": {"direct": ["COHR", "LITE"],  "related": ["AAOI", "FN"],          "etfs": []},
    "CRDO": {"direct": ["MRVL", "AVGO"], "related": ["NVDA", "AMD"],          "etfs": ["SMH"]},

    # AI 服务器 / 数据中心
    "SMCI": {"direct": ["DELL", "HPE"],   "related": ["NVDA", "VRT", "ETN"],  "etfs": []},
    "DELL": {"direct": ["SMCI", "HPE"],   "related": ["NVDA", "WDC", "STX"],  "etfs": []},
    "VRT":  {"direct": ["ETN", "PWR"],    "related": ["SMCI", "DELL", "CEG"], "etfs": []},
    "ETN":  {"direct": ["VRT", "PWR"],    "related": ["CEG", "SMCI"],         "etfs": []},

    # 存储 NAND / DRAM
    "MU":   {"direct": ["STX", "WDC"],    "related": ["SNDK", "LRCX", "AMAT"],"etfs": ["SMH"]},

    # 生物医药（保留基础联动）
    # biotech 联动复杂，依赖 LLM 的 related_tickers 字段
}


# 信号定义
SIGNAL_DEFINITIONS = {
    "BUY_ON_VWAP_HOLD": {
        "label":      "✅ 开盘VWAP确认买入",
        "risk_level": "medium",
        "desc_cn":    "事件强、涨幅合理、成交量确认。开盘15分钟后若股价站稳VWAP则买入。",
    },
    "WAIT_FOR_PULLBACK": {
        "label":      "⏳ 等待回踩",
        "risk_level": "high",
        "desc_cn":    "事件利好但盘前涨幅过大，追高风险高。等待回踩至VWAP或关键支撑再介入。",
    },
    "WATCH_ONLY": {
        "label":      "👁 观望确认",
        "risk_level": "medium_high",
        "desc_cn":    "事件质量尚可但大盘环境弱或成交量不足，暂时观望等待确认信号。",
    },
    "WATCH_SYMPATHY": {
        "label":      "🔗 看联动股",
        "risk_level": "medium",
        "desc_cn":    "主线追高风险大，建议关注同板块联动标的，风险收益比更优。",
    },
    "AVOID": {
        "label":      "❌ 不交易",
        "risk_level": "low",
        "desc_cn":    "当前信号质量不足或风险过高，跳过本次机会。",
    },
}


def generate_trade_signal(
    event_score: int,
    market_score: int,
    risk_score: int,
    final_score: int,
    premarket_gap_pct: Optional[float],
    rel_volume: Optional[float],
    qqq_change_pct: Optional[float],
    spy_change_pct: Optional[float],
    ticker: str = "",
    l3_suggested_signal: Optional[str] = None,
) -> dict:
    """
    根据评分和行情数据生成交易信号。

    优先使用 L3 LLM 给出的 suggested_signal（它已经看过行情数据）；
    如果 L3 没给或给的是无效值，则用规则引擎降级决策。

    Returns:
        {
            "signal": str,
            "signal_label": str,
            "risk_level": str,
            "entry_rule": str,
            "stop_loss_rule": str,
            "take_profit_rule": str,
            "position_size": str,
            "reason_cn": str,
            "sympathy_tickers": list,
            "sector_etfs": list,
        }
    """
    valid_signals = set(SIGNAL_DEFINITIONS.keys())

    # 1. 优先使用 L3 LLM 的信号建议
    signal = None
    if l3_suggested_signal and l3_suggested_signal in valid_signals:
        signal = l3_suggested_signal
        logger.debug(f"[Signal] {ticker} 使用L3建议信号: {signal}")

    # 2. 规则引擎降级
    if signal is None:
        signal = _rule_based_signal(
            event_score=event_score,
            final_score=final_score,
            premarket_gap_pct=premarket_gap_pct,
            rel_volume=rel_volume,
            qqq_change_pct=qqq_change_pct,
            spy_change_pct=spy_change_pct,
        )
        logger.debug(f"[Signal] {ticker} 规则引擎信号: {signal}")

    # 3. 生成具体交易规则
    entry, stop, take_profit, position = _generate_trade_rules(
        signal=signal,
        event_score=event_score,
        risk_score=risk_score,
        premarket_gap_pct=premarket_gap_pct,
        rel_volume=rel_volume,
    )

    # 4. 联动股推荐
    sympathy = _get_sympathy_tickers(ticker, signal)

    # 5. 中文原因说明
    reason = _build_reason_cn(
        signal=signal,
        event_score=event_score,
        market_score=market_score,
        risk_score=risk_score,
        premarket_gap_pct=premarket_gap_pct,
        rel_volume=rel_volume,
        qqq_change_pct=qqq_change_pct,
    )

    defn = SIGNAL_DEFINITIONS[signal]
    return {
        "signal":            signal,
        "signal_label":      defn["label"],
        "risk_level":        defn["risk_level"],
        "entry_rule":        entry,
        "stop_loss_rule":    stop,
        "take_profit_rule":  take_profit,
        "position_size":     position,
        "reason_cn":         reason,
        "sympathy_tickers":  sympathy.get("direct", []) + sympathy.get("related", []),
        "sector_etfs":       sympathy.get("etfs", []),
    }


def _rule_based_signal(
    event_score: int,
    final_score: int,
    premarket_gap_pct: Optional[float],
    rel_volume: Optional[float],
    qqq_change_pct: Optional[float],
    spy_change_pct: Optional[float],
) -> str:
    """规则引擎（L3没给信号时的降级决策）

    核心阈值：
        final_score < 40               → AVOID
        final_score < 50               → AVOID（综合质量不足）
        final_score 50–64              → WATCH_ONLY（观望）
        final_score 65–74              → WAIT_FOR_PULLBACK（等待确认）
        final_score ≥ 75 + event ≥ 80 → BUY_ON_VWAP_HOLD（条件满足才买）
    """
    gap = premarket_gap_pct or 0.0
    vol = rel_volume or 1.0
    qqq = qqq_change_pct or 0.0
    spy = spy_change_pct or 0.0
    market_weak = (qqq < -1.0 or spy < -0.8)

    # ── 第一道门：综合分不足直接拒绝 ──────────────────────────
    if final_score < 50 or event_score < 40:
        return "AVOID"

    # ── 第二道门：综合分 50-64 → 只观望 ──────────────────────
    if final_score < 65:
        return "WATCH_ONLY"

    # ── 以下 final_score >= 65 ──────────────────────────────

    # 追高保护：盘前涨幅极大
    if gap > 30:
        return "WATCH_SYMPATHY"
    if gap > 20:
        return "WAIT_FOR_PULLBACK"

    # 大盘极弱，且事件不够强
    if market_weak and event_score < 80:
        return "WATCH_ONLY"

    # BUY 条件：event ≥ 80 + final ≥ 75 + 合理涨幅 + 放量确认
    if (event_score >= 80 and final_score >= 75
            and 2 <= gap <= 15 and vol >= 2.0):
        return "BUY_ON_VWAP_HOLD"

    # event ≥ 80 但涨幅过大或量不足
    if event_score >= 80 and gap > 15:
        return "WAIT_FOR_PULLBACK"
    if event_score >= 80 and vol < 2.0:
        return "WAIT_FOR_PULLBACK"

    # final ≥ 65 但未达 BUY 门槛
    if final_score >= 65:
        return "WAIT_FOR_PULLBACK"

    return "WATCH_ONLY"


def _generate_trade_rules(
    signal: str,
    event_score: int,
    risk_score: int,
    premarket_gap_pct: Optional[float],
    rel_volume: Optional[float],
) -> tuple[str, str, str, str]:
    """生成入场/止损/止盈/仓位规则"""
    gap = premarket_gap_pct or 0.0
    vol = rel_volume

    if signal == "BUY_ON_VWAP_HOLD":
        entry = "开盘15分钟后，若股价站稳VWAP（连续2根1分钟K线收于VWAP上方）则买入"
        stop  = "跌破VWAP或较入场价下跌3%，强制止损"
        take  = "+5%减仓50%，剩余仓位移动止损跟踪；或尾盘前清仓"
        pos   = "medium" if event_score >= 85 else "small"

    elif signal == "WAIT_FOR_PULLBACK":
        pullback_target = f"{abs(gap) * 0.5:.0f}%"
        entry = f"不追盘前/开盘高点；等待回踩盘前涨幅约{pullback_target}或VWAP支撑后再考虑"
        stop  = "回踩后若继续跌破当日低点或VWAP，不进场"
        take  = "回踩买入后目标+5%~+8%，止损跌破回踩低点"
        pos   = "small"  # 回踩买入永远小仓

    elif signal == "WATCH_SYMPATHY":
        entry = "不直接追主线；等开盘后观察联动股是否跟涨，选择涨幅更小/走势更稳的标的"
        stop  = "联动股跌破日内VWAP则离场"
        take  = "以主线走势为参考，主线冲高时联动股可适当减仓"
        pos   = "small"

    elif signal == "WATCH_ONLY":
        entry = "今日不建仓；若收盘前大盘企稳且成交量放大，可考虑隔日复看"
        stop  = "N/A（不交易）"
        take  = "N/A（不交易）"
        pos   = "none"

    else:  # AVOID
        entry = "不交易"
        stop  = "N/A"
        take  = "N/A"
        pos   = "none"

    return entry, stop, take, pos


def _get_sympathy_tickers(ticker: str, signal: str) -> dict:
    """从联动图谱获取相关股票"""
    if signal not in ("WATCH_SYMPATHY", "BUY_ON_VWAP_HOLD", "WAIT_FOR_PULLBACK"):
        return {}
    return SYMPATHY_MAP.get(ticker.upper(), {})


def _build_reason_cn(
    signal: str,
    event_score: int,
    market_score: int,
    risk_score: int,
    premarket_gap_pct: Optional[float],
    rel_volume: Optional[float],
    qqq_change_pct: Optional[float],
) -> str:
    """生成中文原因摘要"""
    parts = []

    if event_score >= 80:
        parts.append(f"事件质量高（分={event_score}）")
    elif event_score >= 60:
        parts.append(f"事件质量中等（分={event_score}）")
    else:
        parts.append(f"事件质量一般（分={event_score}）")

    if premarket_gap_pct is not None:
        if abs(premarket_gap_pct) > 20:
            parts.append(f"盘前涨幅{premarket_gap_pct:+.1f}%（追高风险极大）")
        elif abs(premarket_gap_pct) > 10:
            parts.append(f"盘前涨幅{premarket_gap_pct:+.1f}%（涨幅较大，谨慎追）")
        elif abs(premarket_gap_pct) > 3:
            parts.append(f"盘前涨幅{premarket_gap_pct:+.1f}%（合理区间）")

    if rel_volume is not None:
        if rel_volume >= 3:
            parts.append(f"成交量{rel_volume:.1f}x放量确认")
        elif rel_volume < 1.2:
            parts.append(f"成交量仅{rel_volume:.1f}x（资金参与度低）")

    if qqq_change_pct is not None and qqq_change_pct < -1.0:
        parts.append(f"QQQ跌{abs(qqq_change_pct):.1f}%（大盘压力大）")

    return "；".join(parts) if parts else SIGNAL_DEFINITIONS[signal]["desc_cn"]
