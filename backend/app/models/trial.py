"""
临床试验模型
- 追踪 ClinicalTrials.gov 上的 Phase 2/3 试验
- 检测试验状态变更
- 追踪 Primary Completion Date (PCD) 倒计时
"""
from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Text, DateTime, Date, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ClinicalTrial(Base):
    __tablename__ = "clinical_trials"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    nct_id: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, comment="ClinicalTrials.gov 注册号"
    )
    title: Mapped[str] = mapped_column(String(500), comment="试验标题")
    phase: Mapped[str] = mapped_column(
        String(20), comment="试验阶段: Phase 1 / Phase 2 / Phase 3 / Phase 4"
    )
    status: Mapped[str] = mapped_column(
        String(50),
        comment="试验状态: Recruiting / Active, not recruiting / Completed / Terminated / etc.",
    )
    conditions: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="适应症（逗号分隔）"
    )
    interventions: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="干预措施（药物名称等）"
    )
    primary_completion_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="主要完成日期 (PCD)"
    )
    study_completion_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="研究完成日期"
    )
    enrollment: Mapped[Optional[int]] = mapped_column(
        nullable=True, comment="入组人数"
    )
    previous_status: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="上次记录时的状态（用于变更检测）"
    )
    last_updated: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="ClinicalTrials.gov 上的更新时间"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    company = relationship("Company", back_populates="trials")

    def __repr__(self):
        return f"<ClinicalTrial {self.nct_id}: {self.title[:40]}>"
