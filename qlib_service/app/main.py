from fastapi import Depends, FastAPI, Header, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.jobs.model_version_job import ModelVersionJob
from app.jobs.prediction_job import PredictionJob
from app.jobs.training_job import TrainingJob
from app.qlib.run_experiment import list_model_configs
from app.schemas import (
    DailyPredictionRequest,
    JobResponse,
    ModelVersionResponse,
    PromoteModelRequest,
    PruneModelVersionsRequest,
    PruneModelVersionsResponse,
    QlibModelListResponse,
    RollbackModelRequest,
    TrainModelRequest,
)
from app.settings import Settings, get_settings


app = FastAPI(title="Qlib Prediction Service")


def require_internal_token(
    x_internal_token: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    if settings.internal_token and x_internal_token != settings.internal_token:
        raise HTTPException(status_code=401, detail="invalid internal token")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post(
    "/internal/jobs/daily-prediction",
    response_model=JobResponse,
    dependencies=[Depends(require_internal_token)],
)
async def run_daily_prediction(
    request: DailyPredictionRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> JobResponse:
    return await PredictionJob(settings).run(db, request)


@app.post(
    "/internal/jobs/train-model",
    response_model=JobResponse,
    dependencies=[Depends(require_internal_token)],
)
async def train_model(
    request: TrainModelRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> JobResponse:
    return await TrainingJob(settings).run(db, request)


@app.post(
    "/internal/model-runs/{run_id}/promote",
    response_model=ModelVersionResponse,
    dependencies=[Depends(require_internal_token)],
)
async def promote_model_run(
    run_id: str,
    request: PromoteModelRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ModelVersionResponse:
    try:
        return await ModelVersionJob(settings).promote_run(db, run_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(
    "/internal/model-runs/rollback",
    response_model=ModelVersionResponse,
    dependencies=[Depends(require_internal_token)],
)
async def rollback_model_run(
    request: RollbackModelRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ModelVersionResponse:
    try:
        return await ModelVersionJob(settings).rollback(db, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(
    "/internal/model-runs/prune",
    response_model=PruneModelVersionsResponse,
    dependencies=[Depends(require_internal_token)],
)
async def prune_model_runs(
    request: PruneModelVersionsRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PruneModelVersionsResponse:
    try:
        return await ModelVersionJob(settings).prune_versions(db, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get(
    "/internal/models",
    response_model=QlibModelListResponse,
    dependencies=[Depends(require_internal_token)],
)
async def get_models() -> QlibModelListResponse:
    return QlibModelListResponse(
        models=[model_config.as_dict() for model_config in list_model_configs()]
    )


@app.get(
    "/internal/jobs/{run_id}",
    response_model=JobResponse,
    dependencies=[Depends(require_internal_token)],
)
async def get_job(
    run_id: str,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    result = await db.execute(
        text(
            """
            SELECT run_id, status, artifact_uri, error_message
            FROM qlib_model_runs
            WHERE run_id = :run_id
            """
        ),
        {"run_id": run_id},
    )
    row = result.mappings().one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="run not found")

    count_result = await db.execute(
        text("SELECT COUNT(*) FROM qlib_predictions WHERE run_id = :run_id"),
        {"run_id": run_id},
    )
    return JobResponse(
        run_id=row["run_id"],
        status=row["status"],
        artifact_uri=row["artifact_uri"],
        prediction_count=int(count_result.scalar_one()),
        message=row["error_message"],
    )
