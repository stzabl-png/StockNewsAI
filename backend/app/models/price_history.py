"""
日线价格历史表 — 用于趋势分析（MA、RS、HH/HL、成交量确认）
"""
from datetime import date
from sqlalchemy import Column, Integer, String, Float, Date, UniqueConstraint, Index
from app.models.base import Base


class PriceHistory(Base):
    __tablename__ = "price_history"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    ticker      = Column(String(20), nullable=False, index=True)
    date        = Column(Date, nullable=False)

    # OHLCV
    open        = Column(Float)
    high        = Column(Float)
    low         = Column(Float)
    close       = Column(Float, nullable=False)
    volume      = Column(Float)          # 当日成交量
    vwap        = Column(Float)          # 当日VWAP（Polygon提供）

    # 预计算指标（每日更新时填入）
    ma20        = Column(Float)
    ma50        = Column(Float)
    ma200       = Column(Float)
    avg_vol20   = Column(Float)          # 20日平均成交量
    rel_vol     = Column(Float)          # 当日成交量 / avg_vol20

    __table_args__ = (
        UniqueConstraint("ticker", "date", name="uq_price_history_ticker_date"),
        Index("ix_price_history_ticker_date", "ticker", "date"),
    )
