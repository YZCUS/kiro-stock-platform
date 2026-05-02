"""
Provider-specific stock symbol mappings.
"""

from sqlalchemy import Boolean, Column, ForeignKey, Index, JSON, String, UniqueConstraint
from sqlalchemy.orm import relationship

from domain.models.base import BaseModel, TimestampMixin


class StockSymbolMapping(BaseModel, TimestampMixin):
    """Maps an internal stock to provider-specific symbols."""

    __tablename__ = "stock_symbol_mappings"

    stock_id = Column(
        ForeignKey("stocks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider = Column(String(50), nullable=False, index=True)
    provider_symbol = Column(String(64), nullable=False, index=True)
    exchange_code = Column(String(32), nullable=True, index=True)
    currency = Column(String(10), nullable=True)
    is_primary = Column(Boolean, nullable=False, default=True)
    metadata_json = Column(JSON, nullable=True)

    stock = relationship("Stock", back_populates="symbol_mappings")

    __table_args__ = (
        UniqueConstraint(
            "stock_id",
            "provider",
            name="uq_stock_symbol_mappings_stock_provider",
        ),
        UniqueConstraint(
            "provider",
            "provider_symbol",
            name="uq_stock_symbol_mappings_provider_symbol",
        ),
        Index("ix_stock_symbol_mappings_lookup", "provider", "provider_symbol"),
        {"comment": "Provider-specific stock symbol mapping table"},
    )
