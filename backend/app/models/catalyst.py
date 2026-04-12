"""
催化剂日历模型
- PDUFA 审批日期
- 临床试验 PCD 到期
- 财报发布日期
- AdCom 会议日期
- 支持多级提醒标记（90d / 30d / 7d / 3d / 1d / 当天）
"""
from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Text, DateTime, Date, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Catalyst(Base):
    __tablename__ = "catalysts"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(
        String(50), comment="事件类型: pdufa / pcd / earnings / adcom / other"
    )
    title: Mapped[str] = mapped_column(String(500), comment="事件标题")
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="事件描述"
    )
    event_date: Mapped[date] = mapped_column(Date, index=True, comment="事件日期")
    importance: Mapped[str] = mapped_column(
        String(20), default="medium", comment="重要性: high / medium / low"
    )

    # 提醒标记 — 记录是否已推送过该级别提醒
    reminded_90d: Mapped[bool] = mapped_column(Boolean, default=False)
    reminded_30d: Mapped[bool] = mapped_column(Boolean, default=False)
    reminded_7d: Mapped[bool] = mapped_column(Boolean, default=False)
    reminded_3d: Mapped[bool] = mapped_column(Boolean, default=False)
    reminded_1d: Mapped[bool] = mapped_column(Boolean, default=False)
    reminded_0d: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    company = relationship("Company", back_populates="catalysts")

    def __repr__(self):
        return f"<Catalyst {self.event_type}: {self.title[:40]} @ {self.event_date}>"
