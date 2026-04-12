"""
分析结果模型
- 存储 LLM 两级分析的输出
- Level 1: GPT-4o-mini 初筛（分类 + 评级）
- Level 2: Claude Sonnet 深度分析（详细报告）
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, Integer, Float, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    news_id: Mapped[int] = mapped_column(
        ForeignKey("news.id", ondelete="CASCADE"), unique=True, index=True
    )
    level: Mapped[int] = mapped_column(
        Integer, comment="分析级别: 1=GPT-4o-mini 初筛, 2=Claude Sonnet 深度分析"
    )
    sentiment: Mapped[str] = mapped_column(
        String(20), comment="情感判断: bullish / bearish / neutral"
    )
    confidence: Mapped[float] = mapped_column(Float, comment="置信度 0.0-1.0")
    impact_level: Mapped[str] = mapped_column(
        String(20), comment="影响级别: high / medium / low"
    )
    impact_duration: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="影响时长: short_term / medium_term / long_term"
    )
    summary_cn: Mapped[str] = mapped_column(Text, comment="中文摘要")
    detailed_analysis: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="深度分析详情 (Level 2): direct_impact, pipeline_impact, etc.",
    )
    related_tickers: Mapped[Optional[list]] = mapped_column(
        JSON, nullable=True, comment="关联股票代码列表"
    )
    key_dates: Mapped[Optional[list]] = mapped_column(
        JSON, nullable=True, comment="后续需要关注的关键日期"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    news = relationship("News", back_populates="analysis")

    def __repr__(self):
        return f"<Analysis L{self.level} news={self.news_id} {self.sentiment}>"
