"""
訂單意圖 domain models
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class TimeInForce(str, Enum):
    DAY = "DAY"
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"


class OrderIntentStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_RISK_CHECK = "PENDING_RISK_CHECK"
    RISK_APPROVED = "RISK_APPROVED"
    RISK_BLOCKED = "RISK_BLOCKED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class OrderIntentRequest:
    """策略或使用者產生的下單意圖，不代表已送出 broker。"""

    user_id: UUID
    stock_id: int
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    time_in_force: TimeInForce = TimeInForce.DAY
    limit_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    notional: Optional[Decimal] = None
    strategy_signal_id: Optional[int] = None
    broker_account_id: Optional[int] = None
    source: str = "manual"
    reason: Optional[str] = None
    idempotency_key: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    expires_at: Optional[datetime] = None

    def validate(self) -> None:
        if self.quantity <= 0:
            raise ValueError("Order quantity must be greater than 0")
        if self.order_type in {OrderType.LIMIT, OrderType.STOP_LIMIT}:
            if self.limit_price is None or self.limit_price <= 0:
                raise ValueError("Limit orders require a positive limit price")
        if self.order_type in {OrderType.STOP, OrderType.STOP_LIMIT}:
            if self.stop_price is None or self.stop_price <= 0:
                raise ValueError("Stop orders require a positive stop price")
        if self.notional is not None and self.notional <= 0:
            raise ValueError("Order notional must be greater than 0")
