"""
事件回测数据模型

存储每条 HIGH 影响新闻发布后的股价表现，用于：
1. 验证 LLM 预测质量（conviction_level vs 实际涨跌）
2. 统计不同事件类型的历史胜率
3. 统计不同信号类型的历史胜率
4. 帮助用户判断 "盘后涨X% 后继续涨的概率"

由 scheduler 在收盘后自动回填。
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, Float, DateTime, Integer, Boolean,
    ForeignKey, JSON, func, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EventOutcome(Base):
    """事件结果跟踪表 — 绑定新闻和后续价格表现"""
    __tablename__ = "event_outcomes"

    id: Mapped[int] = mapped_column(primary_key=True)
    news_id: Mapped[int] = mapped_column(
        ForeignKey("news.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        comment="关联的新闻 ID"
    )
    ticker: Mapped[str] = mapped_column(
        String(10), index=True, comment="股票代码"
    )

    # ── 事件发生时的基准价格 ─────────────────────────────────────────────────
    price_at_news: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="新闻发布时的最近价格（盘后/前一收盘）"
    )
    price_prev_close: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="事件前一交易日收盘价"
    )

    # ── 开盘后各时间节点价格 ─────────────────────────────────────────────────
    price_next_open: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="下一交易日开盘价"
    )
    price_30m_after_open: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="开盘后30分钟价格"
    )
    price_1h_after_open: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="开盘后1小时价格"
    )
    price_close_day1: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="事件后第1个交易日收盘价"
    )
    price_close_day2: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="事件后第2个交易日收盘价"
    )
    price_close_day5: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="事件后第5个交易日收盘价（1周后）"
    )

    # ── 收益率计算（相对prev_close）───────────────────────────────────────────
    gap_pct: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="开盘 gap（相对前收）%"
    )
    return_open: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="开盘价收益率 %"
    )
    return_1h: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="开盘1小时收益率 %"
    )
    return_day1: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="第1日收益率 %"
    )
    return_day2: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="第2日收益率 %"
    )
    return_day5: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="第5日收益率 %（1周后）"
    )
    max_intraday_gain_day1: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="第1日日内最大浮盈 %"
    )
    max_intraday_drawdown_day1: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="第1日日内最大回撤 %"
    )

    # ── 行为标签（方便统计）────────────────────────────────────────────────────
    label_gap_and_fade: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True,
        comment="True=高开低走（gap up 但日内回落超过50%涨幅）"
    )
    label_open_continuation: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True,
        comment="True=开盘后继续涨（日收益率 > gap 的1.2倍）"
    )
    label_profitable_day1: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True,
        comment="True=当日持有盈利（相对prev_close）"
    )
    label_profitable_day5: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True,
        comment="True=持有5日盈利"
    )

    # ── AI 预测 vs 实际对比 ────────────────────────────────────────────────────
    predicted_signal: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True, comment="AI预测信号: BUY_ON_VWAP_HOLD etc."
    )
    predicted_conviction: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True, comment="AI预测置信度: HIGH/MODERATE/LOW_CONVICTION"
    )
    predicted_event_score: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="AI事件评分"
    )
    predicted_final_score: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="AI综合评分"
    )
    event_category: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="事件类型（来自L1）"
    )
    sector_tag: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="板块标签"
    )

    # ── 时间戳 ────────────────────────────────────────────────────────────────
    news_published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="新闻发布时间"
    )
    filled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="价格数据回填时间"
    )
    is_complete: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="True=5日数据已全部回填"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self):
        return f"<EventOutcome ticker={self.ticker} day1={self.return_day1}%>"
