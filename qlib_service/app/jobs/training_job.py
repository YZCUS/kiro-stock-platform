from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.qlib.cpu_training import build_training_dataset, train_cpu_model
from app.qlib.run_experiment import QlibModelConfig, get_model_config
from app.schemas import JobResponse, TrainModelRequest
from app.settings import Settings

CPU_TRAINABLE_MODEL_TYPES = {"lightgbm", "xgboost", "catboost"}


class TrainingJob:
    """Trains CPU model artifacts and records the run in qlib_model_runs."""

    def __init__(self, settings: Settings):
        self.settings = settings

    async def run(self, db: AsyncSession, request: TrainModelRequest) -> JobResponse:
        model_config = self._validate_request(request)
        run_id = self._build_run_id(request)
        claimed = await self._claim_model_run(
            db, run_id, request, model_config, "running"
        )
        if not claimed:
            return await self._existing_job_response(db, run_id)

        try:
            rows_by_stock = await self._load_price_rows(db, request)
            dataset = await asyncio.to_thread(
                build_training_dataset,
                rows_by_stock,
                horizon_days=self._horizon_days(model_config.horizon),
                train_start=request.train_start,
                train_end=request.train_end,
                valid_start=request.valid_start,
                valid_end=request.valid_end,
                test_start=request.test_start,
                test_end=request.test_end,
                lookback_days=request.lookback_days,
            )
            artifact_dir = (
                Path(self.settings.artifact_root)
                / "models"
                / request.model_name
                / run_id
            )
            artifact_uri, metrics = await asyncio.to_thread(
                train_cpu_model,
                run_id=run_id,
                model_config=model_config,
                dataset=dataset,
                artifact_dir=artifact_dir,
                metadata={
                    "run_id": run_id,
                    "market": request.market,
                    "universe": request.universe,
                    "train_start": request.train_start.isoformat(),
                    "train_end": request.train_end.isoformat(),
                    "valid_start": request.valid_start.isoformat(),
                    "valid_end": request.valid_end.isoformat(),
                    "test_start": request.test_start.isoformat(),
                    "test_end": request.test_end.isoformat(),
                    "lookback_days": request.lookback_days,
                    "horizon": request.horizon,
                    "config_uri": model_config.config_uri,
                },
                cpu_threads=self.settings.cpu_threads,
            )
            await self._mark_run_succeeded(
                db=db,
                run_id=run_id,
                artifact_uri=artifact_uri,
                metrics=metrics,
            )
            return JobResponse(
                run_id=run_id,
                status="succeeded",
                artifact_uri=artifact_uri,
                message="cpu training completed",
            )
        except Exception as exc:
            await db.rollback()
            await self._mark_run_failed(db, run_id, str(exc))
            raise

    def _validate_request(self, request: TrainModelRequest) -> QlibModelConfig:
        model_config = get_model_config(request.model_name)
        if model_config.model_type not in CPU_TRAINABLE_MODEL_TYPES:
            raise ValueError(f"Model {request.model_name} is not CPU trainable")
        if request.feature_set != model_config.feature_set:
            raise ValueError(
                f"Model {request.model_name} requires feature_set "
                f"{model_config.feature_set}, got {request.feature_set}"
            )
        if request.horizon != model_config.horizon:
            raise ValueError(
                f"Model {request.model_name} requires horizon "
                f"{model_config.horizon}, got {request.horizon}"
            )
        if request.lookback_days < model_config.min_lookback_days:
            raise ValueError(
                f"Model {request.model_name} requires at least "
                f"{model_config.min_lookback_days} lookback days"
            )
        if not (
            request.train_start
            <= request.train_end
            < request.valid_start
            <= request.valid_end
            < request.test_start
            <= request.test_end
        ):
            raise ValueError("Training, validation, and test ranges must not overlap")
        return model_config

    def _build_run_id(self, request: TrainModelRequest) -> str:
        payload = json.dumps(request.model_dump(mode="json"), sort_keys=True)
        digest = sha256(payload.encode("utf-8")).hexdigest()[:16]
        return (
            f"qlib-train-{request.market.lower()}-"
            f"{request.test_end.isoformat()}-{digest}"
        )

    async def _claim_model_run(
        self,
        db: AsyncSession,
        run_id: str,
        request: TrainModelRequest,
        model_config: QlibModelConfig,
        status: str,
    ) -> bool:
        result = await db.execute(
            text("""
                INSERT INTO qlib_model_runs (
                    run_id, market, universe, model_name, feature_set, mode, status,
                    train_start, train_end, valid_start, valid_end, test_start,
                    test_end, horizon, metrics, config_uri, stage, started_at,
                    created_at, updated_at
                )
                VALUES (
                    :run_id, :market, :universe, :model_name, :feature_set,
                    'train', :status, :train_start, :train_end, :valid_start,
                    :valid_end, :test_start, :test_end, :horizon,
                    CAST(:metrics AS JSON), :config_uri, 'candidate',
                    :started_at, NOW(), NOW()
                )
                ON CONFLICT (run_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    metrics = EXCLUDED.metrics,
                    config_uri = EXCLUDED.config_uri,
                    started_at = EXCLUDED.started_at,
                    finished_at = NULL,
                    error_message = NULL,
                    updated_at = NOW()
                WHERE qlib_model_runs.status = 'failed'
                   OR (
                       qlib_model_runs.status = 'running'
                       AND qlib_model_runs.started_at < NOW() - make_interval(secs => :stale_seconds)
                   )
                RETURNING id
                """),
            {
                "run_id": run_id,
                "market": request.market,
                "universe": request.universe,
                "model_name": request.model_name,
                "feature_set": request.feature_set,
                "status": status,
                "train_start": request.train_start,
                "train_end": request.train_end,
                "valid_start": request.valid_start,
                "valid_end": request.valid_end,
                "test_start": request.test_start,
                "test_end": request.test_end,
                "horizon": request.horizon,
                "metrics": json.dumps(self._initial_metrics(model_config)),
                "config_uri": model_config.config_uri,
                "started_at": datetime.now(timezone.utc),
                "stale_seconds": self.settings.stale_job_seconds,
            },
        )
        await db.commit()
        return result.scalar_one_or_none() is not None

    async def _existing_job_response(
        self, db: AsyncSession, run_id: str
    ) -> JobResponse:
        result = await db.execute(
            text("""
                SELECT status, artifact_uri, error_message
                FROM qlib_model_runs
                WHERE run_id = :run_id
                """),
            {"run_id": run_id},
        )
        row = result.mappings().one()
        return JobResponse(
            run_id=run_id,
            status=row["status"],
            artifact_uri=row["artifact_uri"],
            message=row["error_message"] or "idempotent existing run",
        )

    def _horizon_days(self, horizon: str) -> int:
        if horizon.endswith("d"):
            return max(1, int(horizon[:-1]))
        return 1

    async def _load_price_rows(
        self,
        db: AsyncSession,
        request: TrainModelRequest,
    ) -> dict[int, list[dict[str, Any]]]:
        limit = request.limit or self.settings.max_universe_size
        history_start = request.train_start - timedelta(
            days=max(30, request.lookback_days * 3)
        )
        result = await db.execute(
            text("""
                WITH stock_universe AS (
                    SELECT id, symbol, market
                    FROM stocks
                    WHERE market = :market AND is_active = TRUE
                    ORDER BY symbol
                    LIMIT :limit
                ), canonical_daily AS (
                    SELECT
                        s.id AS stock_id,
                        s.symbol,
                        s.market,
                        b.timestamp,
                        b.open_price,
                        b.high_price,
                        b.low_price,
                        b.close_price,
                        b.volume,
                        b.is_adjusted,
                        b.close_price AS adjusted_close,
                        ROW_NUMBER() OVER (
                            PARTITION BY s.id,
                                CASE
                                  WHEN b.market = 'TW' THEN (b.timestamp AT TIME ZONE 'Asia/Taipei')::date
                                  ELSE (b.timestamp AT TIME ZONE 'America/New_York')::date
                                END
                            ORDER BY b.is_adjusted DESC,
                                     CASE WHEN b.source = 'yahoo_finance' THEN 0 ELSE 1 END,
                                     b.updated_at DESC,
                                     b.id DESC
                        ) AS canonical_rank
                    FROM stock_universe s
                    JOIN market_data_bars b ON b.stock_id = s.id
                    WHERE b.timeframe = '1d'
                      AND (
                        CASE
                          WHEN b.market = 'TW' THEN (b.timestamp AT TIME ZONE 'Asia/Taipei')::date
                          ELSE (b.timestamp AT TIME ZONE 'America/New_York')::date
                        END
                      ) BETWEEN :history_start AND :test_end
                )
                SELECT stock_id, symbol, market, timestamp, open_price,
                       high_price, low_price, close_price, volume,
                       is_adjusted, adjusted_close
                FROM canonical_daily
                WHERE canonical_rank = 1
                ORDER BY symbol ASC, timestamp ASC
                """),
            {
                "market": request.market,
                "limit": limit,
                "history_start": history_start,
                "test_end": request.test_end,
            },
        )

        rows_by_stock: dict[int, list[dict[str, Any]]] = {}
        for row in result.mappings().all():
            stock_id = int(row["stock_id"])
            rows_by_stock.setdefault(stock_id, []).append(dict(row))

        if not rows_by_stock:
            raise ValueError(f"No {request.market} daily market data found")
        return rows_by_stock

    async def _mark_run_succeeded(
        self,
        db: AsyncSession,
        run_id: str,
        artifact_uri: str,
        metrics: dict[str, Any],
    ) -> None:
        await db.execute(
            text("""
                UPDATE qlib_model_runs
                SET status = 'succeeded',
                    artifact_uri = :artifact_uri,
                    metrics = CAST(:metrics AS JSON),
                    finished_at = :finished_at,
                    updated_at = NOW()
                WHERE run_id = :run_id
                """),
            {
                "run_id": run_id,
                "artifact_uri": artifact_uri,
                "metrics": json.dumps(metrics),
                "finished_at": datetime.now(timezone.utc),
            },
        )
        await db.commit()

    async def _mark_run_failed(
        self,
        db: AsyncSession,
        run_id: str,
        error_message: str,
    ) -> None:
        await db.execute(
            text("""
                UPDATE qlib_model_runs
                SET status = 'failed',
                    error_message = :error_message,
                    finished_at = :finished_at,
                    updated_at = NOW()
                WHERE run_id = :run_id
                """),
            {
                "run_id": run_id,
                "error_message": error_message[:4000],
                "finished_at": datetime.now(timezone.utc),
            },
        )
        await db.commit()

    def _initial_metrics(self, model_config: QlibModelConfig) -> dict[str, Any]:
        return {
            "engine": "cpu_model_artifact",
            "model_type": model_config.model_type,
            "model_status": model_config.status,
            "feature_set": model_config.feature_set,
            "horizon": model_config.horizon,
            "min_lookback_days": model_config.min_lookback_days,
            "portfolio_strategy": model_config.portfolio_strategy,
        }
