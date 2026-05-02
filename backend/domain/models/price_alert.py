"""
User price alert model.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from domain.models.base import BaseModel, TimestampMixin


def default_price_alert_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=90)


class PriceAlert(BaseModel, TimestampMixin):
    """Price threshold alert owned by a user."""

    __tablename__ = "price_alerts"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stock_id = Column(
        ForeignKey("stocks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    symbol = Column(String(30), nullable=False, index=True)
    market = Column(String(10), nullable=False, index=True)
    condition = Column(String(10), nullable=False)
    target_price = Column(Numeric(20, 8), nullable=False)
    source_timeframe = Column(String(10), nullable=False, default="1d")

    active = Column(Boolean, nullable=False, default=True, index=True)
    triggered = Column(Boolean, nullable=False, default=False, index=True)
    triggered_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=default_price_alert_expiry,
        index=True,
    )
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    last_price = Column(Numeric(20, 8), nullable=True)
    last_source = Column(String(50), nullable=True)

    user = relationship("User", back_populates="price_alerts")
    stock = relationship("Stock", back_populates="price_alerts")

    __table_args__ = (
        CheckConstraint(
            "condition IN ('ABOVE', 'BELOW')",
            name="ck_price_alerts_condition",
        ),
        CheckConstraint("target_price > 0", name="ck_price_alerts_target_positive"),
        CheckConstraint(
            "source_timeframe IN ('1m', '5m', '15m', '30m', '1h', '1d', '1w')",
            name="ck_price_alerts_source_timeframe",
        ),
        Index(
            "ix_price_alerts_active_scan",
            "active",
            "triggered",
            "expires_at",
            "stock_id",
        ),
        {"comment": "User-owned price threshold alerts"},
    )
