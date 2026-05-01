"""
交易整合 API schemas
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class OrderIntentCreateRequest(BaseModel):
    """建立下單意圖請求。"""

    stock_id: int = Field(..., description="股票 ID")
    side: str = Field(..., description="BUY 或 SELL")
    order_type: str = Field("MARKET", description="MARKET/LIMIT/STOP/STOP_LIMIT")
    time_in_force: str = Field("DAY", description="DAY/GTC/IOC/FOK")
    quantity: Decimal = Field(..., gt=0, description="數量")
    limit_price: Optional[Decimal] = Field(None, gt=0, description="限價")
    stop_price: Optional[Decimal] = Field(None, gt=0, description="停損觸發價")
    notional: Optional[Decimal] = Field(None, gt=0, description="名目金額")
    strategy_signal_id: Optional[int] = Field(None, description="來源策略信號 ID")
    broker_account_id: Optional[int] = Field(None, description="broker 帳戶 ID")
    source: str = Field("manual", description="manual/strategy/api")
    reason: Optional[str] = Field(None, description="建立原因")
    idempotency_key: Optional[str] = Field(None, description="冪等鍵")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="額外資訊")
    expires_at: Optional[datetime] = Field(None, description="過期時間")


class RiskCheckResponse(BaseModel):
    """風控評估結果。"""

    id: int
    order_intent_id: int
    decision: str
    reason_code: str
    reason_message: Optional[str]
    evaluated_by: str
    evaluated_at: Optional[datetime]
    metadata: Optional[Dict[str, Any]]


class BrokerOrderResponse(BaseModel):
    """Broker 訂單結果。"""

    id: int
    order_intent_id: int
    broker_order_ref: str
    status: str
    submitted_quantity: Decimal
    filled_quantity: Decimal
    avg_fill_price: Optional[Decimal]
    submitted_at: Optional[datetime]
    raw_payload: Optional[Dict[str, Any]]


class OrderExecutionCommandResponse(BaseModel):
    """送單執行命令。"""

    order_intent_id: int
    idempotency_key: str
    attempt: int
    requested_at: datetime
    metadata: Dict[str, Any]


class OrderIntentResponse(BaseModel):
    """下單意圖響應。"""

    id: int
    user_id: str
    stock_id: int
    strategy_signal_id: Optional[int]
    broker_account_id: Optional[int]
    side: str
    order_type: str
    time_in_force: str
    quantity: Decimal
    limit_price: Optional[Decimal]
    stop_price: Optional[Decimal]
    notional: Optional[Decimal]
    status: str
    source: str
    idempotency_key: str
    client_order_id: Optional[str]
    reason: Optional[str]
    metadata: Optional[Dict[str, Any]]
    requested_at: Optional[datetime]
    risk_checked_at: Optional[datetime]
    submitted_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class OrderIntentListResponse(BaseModel):
    """下單意圖列表。"""

    items: List[OrderIntentResponse]
    total: int


class OrderIntentQueuedResponse(BaseModel):
    """下單意圖已排入執行佇列。"""

    order_intent: OrderIntentResponse
    command: OrderExecutionCommandResponse
    risk_check: Optional[RiskCheckResponse] = None


class BrokerStatusResponse(BaseModel):
    """Broker 狀態。"""

    provider: str
    mode: str
    available: bool
    read_only: bool
    message: str
    metadata: Dict[str, Any]
