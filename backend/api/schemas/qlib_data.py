"""
Qlib data readiness schemas.
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel


class QlibCoverageSummary(BaseModel):
    market: str
    active_stocks: int
    stocks_with_daily_bars: int
    rows: int
    min_date: Optional[date] = None
    max_date: Optional[date] = None
    min_bars: int
    median_bars: float
    max_bars: int
    adjusted_rows: int


class QlibReadinessResponse(BaseModel):
    market: str
    ready: bool
    min_stocks_required: int
    min_bars_required: int
    coverage: QlibCoverageSummary
    issues: list[str]
    recommendations: list[str]


class QlibModelOptionResponse(BaseModel):
    name: str
    label: str
    model_type: str
    feature_set: str
    horizon: str
    min_lookback_days: int
    description: str
    portfolio_strategy: str
    status: str
    config_uri: Optional[str] = None


class QlibModelOptionsResponse(BaseModel):
    models: list[QlibModelOptionResponse]
