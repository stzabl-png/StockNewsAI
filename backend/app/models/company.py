"""
Watchlist 公司模型
- 存储关注的生物医药公司信息
- 支持优先级、FDA 跟踪、临床试验跟踪等配置
"""
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), unique=True, index=True, comment="股票代码")
    name: Mapped[str] = mapped_column(String(200), comment="公司名称")
    sector: Mapped[str] = mapped_column(String(100), default="Biotechnology", comment="所属板块")
    therapeutic_area: Mapped[str] = mapped_column(
        String(200), default="", comment="治疗领域（如: Oncology, Immunology）"
    )
    priority: Mapped[str] = mapped_column(
        String(10), default="medium", comment="优先级: high / medium"
    )
    track_fda: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否跟踪 FDA 审批")
    track_trials: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否跟踪临床试验")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    notes: Mapped[str] = mapped_column(Text, default="", comment="备注")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    news_items = relationship("News", back_populates="company", lazy="selectin")
    trials = relationship("ClinicalTrial", back_populates="company", lazy="selectin")
    catalysts = relationship("Catalyst", back_populates="company", lazy="selectin")

    def __repr__(self):
        return f"<Company {self.ticker} ({self.name})>"
