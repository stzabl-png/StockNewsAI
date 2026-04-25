"""
板块体系模型 — sectors / sub_sectors / concepts
"""
from sqlalchemy import String, Text, Integer, Boolean, Float, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Sector(Base):
    __tablename__ = "sectors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    gics_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    etf_ticker: Mapped[str | None] = mapped_column(String(10), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self):
        return f"<Sector {self.id}: {self.name_en}>"


class SubSector(Base):
    __tablename__ = "sub_sectors"

    id: Mapped[int] = mapped_column(primary_key=True)
    sector_id: Mapped[int] = mapped_column(ForeignKey("sectors.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    name_en: Mapped[str] = mapped_column(String(100), nullable=False)


class Concept(Base):
    __tablename__ = "concepts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    keywords: Mapped[list | None] = mapped_column(ARRAY(Text()), nullable=True)
    related_tickers: Mapped[list | None] = mapped_column(ARRAY(String(10)), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")
