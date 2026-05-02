from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class DailyPredictionRequest(BaseModel):
    market: str = "US"
    prediction_date: date
    universe: str = "active_us"
    model_name: str = "lightgbm_alpha158"
    feature_set: str = "alpha158"
    horizon: str = "1d"
    lookback_days: int = Field(60, ge=10, le=500)
    limit: Optional[int] = Field(None, ge=1, le=5000)


class JobResponse(BaseModel):
    run_id: str
    status: str
    prediction_count: int = 0
    artifact_uri: Optional[str] = None
    message: Optional[str] = None
