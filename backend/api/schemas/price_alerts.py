"""
Price alert API schemas.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class PriceAlertCreateRequest(BaseModel):
    stock_id: int = Field(..., gt=0)
    condition: str = Field(..., pattern="^(ABOVE|BELOW)$")
    target_price: float = Field(..., gt=0)
    source_timeframe: str = Field("1d", pattern="^(1m|5m|15m|30m|1h|1d|1w)$")
    expires_at: Optional[datetime] = None

    @field_validator("condition")
    @classmethod
    def normalize_condition(cls, value: str) -> str:
        return value.upper()


class PriceAlertUpdateRequest(BaseModel):
    active: Optional[bool] = None
    target_price: Optional[float] = Field(None, gt=0)
    condition: Optional[str] = Field(None, pattern="^(ABOVE|BELOW)$")
    expires_at: Optional[datetime] = None

    @field_validator("condition")
    @classmethod
    def normalize_condition(cls, value: Optional[str]) -> Optional[str]:
        return value.upper() if value else value


class PriceAlertResponse(BaseModel):
    id: int
    user_id: str
    stock_id: int
    symbol: str
    market: str
    condition: str
    target_price: float
    source_timeframe: str
    active: bool
    triggered: bool
    triggered_at: Optional[datetime] = None
    expires_at: datetime
    last_checked_at: Optional[datetime] = None
    last_price: Optional[float] = None
    last_source: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PriceAlertCheckItem(BaseModel):
    alert_id: int
    stock_id: int
    symbol: str
    condition: str
    target_price: float
    current_price: Optional[float] = None
    source: Optional[str] = None
    triggered: bool


class PriceAlertCheckResponse(BaseModel):
    checked: int
    triggered: int
    skipped: int
    items: list[PriceAlertCheckItem]
