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


class TrainModelRequest(BaseModel):
    market: str = "US"
    universe: str = "active_us"
    model_name: str = "lightgbm_alpha158"
    feature_set: str = "alpha158"
    horizon: str = "1d"
    train_start: date
    train_end: date
    valid_start: date
    valid_end: date
    test_start: date
    test_end: date
    lookback_days: int = Field(60, ge=10, le=500)
    limit: Optional[int] = Field(None, ge=1, le=5000)


class JobResponse(BaseModel):
    run_id: str
    status: str
    prediction_count: int = 0
    artifact_uri: Optional[str] = None
    message: Optional[str] = None


class PromoteModelRequest(BaseModel):
    promoted_by: Optional[str] = None
    note: Optional[str] = None


class RollbackModelRequest(BaseModel):
    market: str = "US"
    universe: str = "active_us"
    model_name: str
    feature_set: str = "alpha158"
    promoted_by: Optional[str] = None
    note: Optional[str] = None


class PruneModelVersionsRequest(BaseModel):
    market: Optional[str] = None
    universe: Optional[str] = None
    model_name: Optional[str] = None
    feature_set: Optional[str] = None
    retain_successful_per_model: int = Field(12, ge=2, le=100)
    delete_artifacts: bool = False
    dry_run: bool = True


class ModelVersionResponse(BaseModel):
    run_id: str
    market: str
    universe: str
    model_name: str
    feature_set: str
    status: str
    stage: Optional[str] = None
    artifact_uri: Optional[str] = None
    promoted_at: Optional[str] = None
    promoted_by: Optional[str] = None
    archived_at: Optional[str] = None
    artifact_deleted_at: Optional[str] = None


class PruneModelVersionsResponse(BaseModel):
    dry_run: bool
    archived_run_ids: list[str]
    deleted_artifact_run_ids: list[str]
    retained_run_ids: list[str]


class QlibModelConfigResponse(BaseModel):
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


class QlibModelListResponse(BaseModel):
    models: list[QlibModelConfigResponse]
