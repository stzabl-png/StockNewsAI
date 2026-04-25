"""
新闻记录模型
- 存储从各数据源采集的新闻
- 使用 fingerprint 字段做去重
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, Integer, ForeignKey, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class News(Base):
    __tablename__ = "news"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(500), comment="新闻标题")
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="新闻正文")
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="摘要")
    source: Mapped[str] = mapped_column(
        String(50), comment="数据来源: polygon / finnhub / fda / sec"
    )
    source_url: Mapped[Optional[str]] = mapped_column(
        String(1000), nullable=True, comment="原文链接"
    )
    category: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="事件类型: fda_approval / earnings / merger / policy / product",
    )
    fingerprint: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, comment="新闻指纹 (SHA-256)，用于去重"
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="新闻发布时间"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── 板块/概念标签（Phase 2 新增）────────────────────────────────────────
    sector_id: Mapped[Optional[int]] = mapped_column(
        Integer(),
        ForeignKey("sectors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="所属 GICS 大板块 ID",
    )
    concept_ids: Mapped[Optional[list]] = mapped_column(
        ARRAY(Integer()),
        nullable=True,
        comment="匹配的主题概念 ID 列表",
    )

    # Relationships
    company = relationship("Company", back_populates="news_items")
    analysis = relationship("Analysis", back_populates="news", uselist=False)

    def __repr__(self):
        return f"<News {self.id}: {self.title[:50]}>"
