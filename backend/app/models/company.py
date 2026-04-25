"""
Watchlist 公司模型 — 扩展支持 SP500 全板块
- GICS 板块分类（gics_sector / gics_sub_sector）
- SP500 排名和市值
- 采集优先级分层（tier: A/B/C）
"""
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, Text, Integer, BigInteger, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), unique=True, index=True, comment="股票代码")
    name: Mapped[str] = mapped_column(String(200), comment="公司名称")

    # ── 旧字段（保持兼容）────────────────────────────────────────────────────
    sector: Mapped[str] = mapped_column(String(100), default="", comment="板块（旧字段，兼容）")
    therapeutic_area: Mapped[str] = mapped_column(
        String(200), default="", comment="治疗领域（医疗类专用）"
    )
    priority: Mapped[str] = mapped_column(
        String(10), default="medium", comment="优先级: high / medium"
    )
    track_fda: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否跟踪 FDA 审批")
    track_trials: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否跟踪临床试验")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    notes: Mapped[str] = mapped_column(Text, default="", comment="备注")

    # ── 板块体系（Phase 2 新增）──────────────────────────────────────────────
    gics_sector: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="GICS 大板块，如 Information Technology"
    )
    gics_sub_sector: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="GICS 细分行业，如 Semiconductors"
    )
    sp500_rank: Mapped[int | None] = mapped_column(
        Integer(), nullable=True, comment="SP500 市值排名"
    )
    market_cap: Mapped[int | None] = mapped_column(
        BigInteger(), nullable=True, comment="市值（美元）"
    )
    tier: Mapped[str] = mapped_column(
        String(1), default="B", comment="采集优先级层: A(30min) / B(2h) / C(4h)"
    )

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
        return f"<Company {self.ticker} ({self.name}) [{self.tier}]>"
