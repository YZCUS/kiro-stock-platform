"""
Multi-timeframe market data bar model.
"""

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from domain.models.base import BaseModel, TimestampMixin


class MarketDataBar(BaseModel, TimestampMixin):
    """Normalized OHLCV bar for source and derived timeframes."""

    __tablename__ = "market_data_bars"

    stock_id = Column(
        Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    symbol = Column(String(30), nullable=False, index=True)
    market = Column(String(10), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    open_price = Column(Numeric(20, 8), nullable=False)
    high_price = Column(Numeric(20, 8), nullable=False)
    low_price = Column(Numeric(20, 8), nullable=False)
    close_price = Column(Numeric(20, 8), nullable=False)
    volume = Column(BigInteger, nullable=False, default=0)
    source = Column(String(50), nullable=False, default="unknown", index=True)
    source_type = Column(String(20), nullable=False, default="source")
    is_adjusted = Column(Boolean, nullable=False, default=False)
    generated_from_timeframe = Column(String(10), nullable=True)
    quality_status = Column(String(20), nullable=False, default="complete", index=True)

    stock = relationship("Stock", back_populates="market_data_bars")

    __table_args__ = (
        CheckConstraint(
            "timeframe IN ('1m', '5m', '15m', '30m', '1h', '1d', '1w')",
            name="ck_market_data_bars_timeframe",
        ),
        CheckConstraint(
            "source_type IN ('source', 'derived')",
            name="ck_market_data_bars_source_type",
        ),
        CheckConstraint(
            "quality_status IN ('complete', 'partial', 'backfilled', 'corrected', 'missing')",
            name="ck_market_data_bars_quality_status",
        ),
        CheckConstraint("open_price > 0", name="ck_market_data_bars_open_positive"),
        CheckConstraint("high_price > 0", name="ck_market_data_bars_high_positive"),
        CheckConstraint("low_price > 0", name="ck_market_data_bars_low_positive"),
        CheckConstraint("close_price > 0", name="ck_market_data_bars_close_positive"),
        CheckConstraint("volume >= 0", name="ck_market_data_bars_volume_nonnegative"),
        CheckConstraint(
            "high_price >= open_price AND high_price >= low_price AND high_price >= close_price",
            name="ck_market_data_bars_high_is_max",
        ),
        CheckConstraint(
            "low_price <= open_price AND low_price <= high_price AND low_price <= close_price",
            name="ck_market_data_bars_low_is_min",
        ),
        UniqueConstraint(
            "stock_id",
            "timeframe",
            "timestamp",
            "source",
            "is_adjusted",
            name="uq_market_data_bars_stock_time_source_adjusted",
        ),
        Index("ix_market_data_bars_lookup", "stock_id", "timeframe", "timestamp"),
        Index("ix_market_data_bars_freshness", "timeframe", "quality_status", "timestamp"),
        {"comment": "Multi-timeframe source and derived OHLCV bars"},
    )
