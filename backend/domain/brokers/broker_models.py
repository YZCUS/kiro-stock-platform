"""
交易平台 domain models
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional

from domain.orders import OrderSide, OrderType, TimeInForce


class BrokerProvider(str, Enum):
    PAPER = "paper"
    IBKR = "ibkr"


class BrokerMode(str, Enum):
    PAPER = "paper"
    LIVE = "live"


class BrokerOrderStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class BrokerStatus:
    provider: str
    mode: str
    available: bool
    read_only: bool = True
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BrokerAccountSnapshot:
    account_ref: str
    account_type: Optional[str] = None
    base_currency: str = "USD"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BrokerPosition:
    account_ref: str
    symbol: str
    market: str
    quantity: Decimal
    avg_cost: Optional[Decimal] = None
    market_price: Optional[Decimal] = None
    currency: str = "USD"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BrokerCashBalance:
    account_ref: str
    currency: str
    cash: Decimal
    buying_power: Optional[Decimal] = None
    settled_cash: Optional[Decimal] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BrokerOrderRequest:
    client_order_id: str
    account_ref: Optional[str]
    symbol: str
    market: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    time_in_force: TimeInForce = TimeInForce.DAY
    limit_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BrokerOrderResult:
    broker_order_ref: str
    status: BrokerOrderStatus
    submitted_quantity: Decimal
    filled_quantity: Decimal = Decimal("0")
    avg_fill_price: Optional[Decimal] = None
    submitted_at: Optional[datetime] = None
    raw_payload: Dict[str, Any] = field(default_factory=dict)
