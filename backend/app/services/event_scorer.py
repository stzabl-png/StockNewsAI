"""
事件评分器 — 将 LLM 分析结果量化为数值分数

独立于 LLM 的规则评分层，结合以下维度：
1. 事件类型基础分（不同事件本身的稀缺性和影响力）
2. 情感/置信度加成
3. 行情确认加成/惩罚（成交量、大盘环境）
4. 风险惩罚（追高风险）

最终输出：
- event_score:   事件本身质量分（0-100）
- market_score:  行情确认分（0-100）
- risk_score:    风险分（0-100，越高越危险）
- final_score:   综合分（加权）
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── 事件类型基础分 ────────────────────────────────────────────────────────────
# 基于事件稀缺性、历史平均波动幅度、可交易性综合定义
EVENT_BASE_SCORES: dict[str, int] = {
    # 财报类（最常见的催化剂）
    "earnings_beat_guidance_raise":    90,
    "earnings_beat":                   75,
    "earnings_miss":                   70,   # 负面事件也有波动价值
    "guidance_raise":                  70,
    "guidance_cut":                    72,

    # AI / 数据中心（当前最强主题）
    "ai_datacenter_order":             85,
    "ai_partnership_major":            72,
    "ai_product_launch":               65,
    "vague_ai_news":                   20,

    # 半导体 / 供应链
    "supply_chain_tightness":          68,
    "inventory_cycle_turn":            65,
    "price_increase":                  70,
    "price_cut":                       65,

    # 生物医药（原有逻辑保留）
    "phase3_success":                  85,
    "phase3_failure":                  80,
    "phase2_data":                     75,
    "fda_approval":                    85,
    "fda_rejection":                   78,
    "clinical_hold":                   72,
    "mna_takeover_30pct":              82,

    # 企业行动
    "mna_rumor":                       55,
    "mna_takeover":                    78,
    "buyback_major":                   50,
    "dividend_initiation":             40,
    "spin_off":                        55,

    # 监管 / 政策
    "government_contract":             72,
    "defense_award":                   68,
    "tariff_impact":                   60,
    "regulatory_approval":             70,
    "regulatory_rejection":            68,

    # 分析师行动
    "analyst_upgrade_major":           50,
    "analyst_downgrade_major":         45,
    "analyst_upgrade":                 38,
    "analyst_downgrade":               35,

    # 内部行为
    "insider_buying_large":            52,
    "short_squeeze":                   60,

    # 合作协议
    "major_partnership":               65,
    "general_partnership":             30,

    # 其他
    "product_launch":                  50,
    "product_recall":                  60,
    "sec_filing_unusual":              45,
    "general":                         15,
}

# LLM 事件分类 → 本模块 key 的映射（兼容现有 category 字段）
CATEGORY_MAPPING: dict[str, str] = {
    # 原有生物医药 category
    "phase3_data":          "phase3_success",
    "phase2_data":          "phase2_data",
    "fda_decision":         "fda_approval",
    "merger_acquisition":   "mna_takeover",
    "safety_event":         "clinical_hold",
    "trial_design_change":  "phase2_data",
    "regulatory_change":    "regulatory_approval",
    "dose_response":        "phase2_data",
    "partnership":          "general_partnership",
    "analyst_rating":       "analyst_upgrade",
    # 未来扩展的全市场 category
    "earnings_beat":        "earnings_beat",
    "earnings_miss":        "earnings_miss",
    "guidance_raise":       "guidance_raise",
    "guidance_cut":         "guidance_cut",
}


def get_event_base_score(category: str) -> int:
    """根据事件类型获取基础分，未知类型返回 20"""
    mapped = CATEGORY_MAPPING.get(category, category)
    return EVENT_BASE_SCORES.get(mapped, 20)


def calculate_event_score(
    category: str,
    sentiment: str,
    confidence: float,
    impact_level: str,
    event_strength: Optional[str] = None,
    l3_composite_score: Optional[int] = None,
) -> int:
    """
    计算事件质量分（0-100）。
    优先使用 L3 的 composite_score（它已经是全框架评估的结果）；
    L3 不可用时用规则计算。
    """
    # 如果 L3 已经给出了 composite_score，以它为主要依据
    if l3_composite_score is not None:
        base = l3_composite_score
        # 轻微调整：高置信度加分，低置信度减分
        if confidence >= 0.9:
            base = min(100, base + 3)
        elif confidence < 0.6:
            base = max(0, base - 5)
        return base

    # 规则计算路径
    base = get_event_base_score(category)

    # 情感方向（利空也可能有高价值，bearish 不减分）
    if sentiment == "neutral":
        base = max(0, base - 15)

    # 置信度调整（0.5 是中性点）
    confidence_adj = round((confidence - 0.5) * 20)
    base += confidence_adj

    # impact_level 调整
    if impact_level == "high":
        base = min(100, base + 8)
    elif impact_level == "low":
        base = max(0, base - 10)

    # event_strength 调整
    if event_strength == "strong":
        base = min(100, base + 5)
    elif event_strength == "weak":
        base = max(0, base - 8)

    return max(0, min(100, base))


def calculate_market_score(
    rel_volume: Optional[float],
    spy_change_pct: Optional[float],
    qqq_change_pct: Optional[float],
    prev_5d_return: Optional[float],
) -> int:
    """
    行情确认分（0-100）。
    衡量市场环境是否有利于事件驱动行情。
    """
    score = 50  # 基准分

    # 成交量确认（最重要，权重最高）
    if rel_volume is not None:
        if rel_volume >= 5:
            score += 25
        elif rel_volume >= 3:
            score += 15
        elif rel_volume >= 1.5:
            score += 5
        elif rel_volume < 0.8:
            score -= 15  # 明显缩量

    # 大盘环境
    avg_benchmark = None
    if spy_change_pct is not None and qqq_change_pct is not None:
        avg_benchmark = (spy_change_pct + qqq_change_pct) / 2
    elif spy_change_pct is not None:
        avg_benchmark = spy_change_pct
    elif qqq_change_pct is not None:
        avg_benchmark = qqq_change_pct

    if avg_benchmark is not None:
        if avg_benchmark > 1.0:
            score += 15   # 大盘强，利好事件驱动
        elif avg_benchmark > 0.3:
            score += 5
        elif avg_benchmark < -1.0:
            score -= 20   # 大盘大跌，风险偏好极低
        elif avg_benchmark < -0.5:
            score -= 10

    # 近5日涨幅（提前炒作惩罚）
    if prev_5d_return is not None:
        if prev_5d_return > 30:
            score -= 20   # 已大涨，获利盘压力重
        elif prev_5d_return > 15:
            score -= 10
        elif prev_5d_return < -15:
            score += 10   # 超卖，反弹空间大

    return max(0, min(100, score))


def calculate_risk_score(
    premarket_gap_pct: Optional[float],
    rel_volume: Optional[float],
    event_score: int,
) -> int:
    """
    风险分（0-100，越高代表交易风险越大）。
    主要由盘前涨幅驱动：涨太多就是追高风险。
    """
    risk = 30  # 基准风险

    # 盘前涨幅是最主要的风险因子
    if premarket_gap_pct is not None:
        abs_gap = abs(premarket_gap_pct)
        if abs_gap > 30:
            risk += 45
        elif abs_gap > 20:
            risk += 35
        elif abs_gap > 10:
            risk += 20
        elif abs_gap > 5:
            risk += 8
        elif abs_gap < 1:
            risk -= 10  # 平开，风险低

    # 高成交量 + 事件质量好 → 相对安全
    if rel_volume is not None and rel_volume >= 3 and event_score >= 75:
        risk -= 10

    return max(0, min(100, risk))


def calculate_final_score(
    event_score: int,
    market_score: int,
    risk_score: int,
) -> int:
    """
    综合评分 = 事件质量 * 0.5 + 行情确认 * 0.3 - 风险 * 0.2
    范围 0-100
    """
    raw = (event_score * 0.5) + (market_score * 0.3) - (risk_score * 0.2)
    return max(0, min(100, round(raw)))


def score_analysis(
    category: str,
    sentiment: str,
    confidence: float,
    impact_level: str,
    event_strength: Optional[str] = None,
    l3_composite_score: Optional[int] = None,
    market_context: Optional[dict] = None,
) -> dict:
    """
    主入口：对一条新闻分析生成全套评分。

    Args:
        category:           事件类型（来自L1）
        sentiment:          情感（bullish/bearish/neutral）
        confidence:         置信度（0-1）
        impact_level:       影响级别（high/medium/low）
        event_strength:     事件强度（strong/intermediate/weak）
        l3_composite_score: L3给出的综合分（优先使用）
        market_context:     行情上下文字典（来自market_context.py）

    Returns:
        {
            "event_score": int,
            "market_score": int,
            "risk_score": int,
            "final_score": int,
        }
    """
    ctx = market_context or {}

    event_score = calculate_event_score(
        category=category,
        sentiment=sentiment,
        confidence=confidence,
        impact_level=impact_level,
        event_strength=event_strength,
        l3_composite_score=l3_composite_score,
    )

    market_score = calculate_market_score(
        rel_volume=ctx.get("rel_volume"),
        spy_change_pct=ctx.get("spy_change_pct"),
        qqq_change_pct=ctx.get("qqq_change_pct"),
        prev_5d_return=ctx.get("prev_5d_return"),
    )

    risk_score = calculate_risk_score(
        premarket_gap_pct=ctx.get("premarket_gap_pct"),
        rel_volume=ctx.get("rel_volume"),
        event_score=event_score,
    )

    final_score = calculate_final_score(event_score, market_score, risk_score)

    logger.debug(
        f"[Scorer] event={event_score} market={market_score} "
        f"risk={risk_score} final={final_score} "
        f"(cat={category} sentiment={sentiment})"
    )

    return {
        "event_score":  event_score,
        "market_score": market_score,
        "risk_score":   risk_score,
        "final_score":  final_score,
    }
