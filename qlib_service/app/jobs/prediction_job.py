from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.qlib.cpu_training import (
    ModelArtifact,
    load_model_artifact,
    predict_with_artifact,
)
from app.qlib.export_market_data import export_predictions_input_csv
from app.qlib.run_experiment import (
    QlibModelConfig,
    get_model_config,
    score_price_window,
)
from app.schemas import DailyPredictionRequest, JobResponse
from app.settings import Settings


class PredictionJob:
    """Runs daily prediction and persists scores to the shared database."""

    def __init__(self, settings: Settings):
        self.settings = settings

    async def run(
        self, db: AsyncSession, request: DailyPredictionRequest
    ) -> JobResponse:
        model_config = self._validate_request(request)
        run_id = self._build_run_id(request)
        model_run_id = await self._upsert_model_run(
            db, run_id, request, model_config, None, "running"
        )
        try:
            trained_artifact = await self._load_latest_training_artifact(
                db, request, model_config
            )
            price_rows = await self._load_price_rows(db, request)
            artifact_uri = self._export_input_rows(run_id, price_rows)
            predictions = self._build_predictions(
                run_id,
                model_run_id,
                request,
                model_config,
                trained_artifact,
                price_rows,
            )
            await self._replace_predictions(db, run_id, predictions)
            await self._mark_run_succeeded(
                db=db,
                run_id=run_id,
                artifact_uri=artifact_uri,
                prediction_count=len(predictions),
                model_config=model_config,
                trained_artifact=trained_artifact,
            )
            return JobResponse(
                run_id=run_id,
                status="succeeded",
                prediction_count=len(predictions),
                artifact_uri=artifact_uri,
            )
        except Exception as exc:
            await db.rollback()
            await self._mark_run_failed(db, run_id, str(exc))
            raise

    def _validate_request(self, request: DailyPredictionRequest) -> QlibModelConfig:
        model_config = get_model_config(request.model_name)
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
        return model_config

    def _build_run_id(self, request: DailyPredictionRequest) -> str:
        suffix = uuid4().hex[:8]
        return (
            f"qlib-{request.market.lower()}-{request.prediction_date.isoformat()}"
            f"-{request.model_name}-{suffix}"
        )[:64]

    async def _upsert_model_run(
        self,
        db: AsyncSession,
        run_id: str,
        request: DailyPredictionRequest,
        model_config: QlibModelConfig,
        trained_artifact: ModelArtifact | None,
        status: str,
    ) -> int:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            text(
                """
                INSERT INTO qlib_model_runs (
                    run_id, market, universe, model_name, feature_set, mode, status,
                    prediction_date, horizon, metrics, artifact_uri, config_uri,
                    started_at, created_at, updated_at
                )
                VALUES (
                    :run_id, :market, :universe, :model_name, :feature_set, 'infer',
                    :status, :prediction_date, :horizon, CAST(:metrics AS JSON),
                    NULL, :config_uri, :started_at, NOW(), NOW()
                )
                ON CONFLICT (run_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    horizon = EXCLUDED.horizon,
                    metrics = EXCLUDED.metrics,
                    config_uri = EXCLUDED.config_uri,
                    started_at = EXCLUDED.started_at,
                    updated_at = NOW()
                RETURNING id
                """
            ),
            {
                "run_id": run_id,
                "market": request.market,
                "universe": request.universe,
                "model_name": request.model_name,
                "feature_set": request.feature_set,
                "status": status,
                "prediction_date": request.prediction_date,
                "horizon": request.horizon,
                "metrics": json.dumps(
                    self._build_metrics(model_config, trained_artifact)
                ),
                "config_uri": model_config.config_uri,
                "started_at": now,
            },
        )
        await db.commit()
        return int(result.scalar_one())

    async def _load_price_rows(
        self, db: AsyncSession, request: DailyPredictionRequest
    ) -> list[dict]:
        limit = request.limit or self.settings.max_universe_size
        result = await db.execute(
            text(
                """
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
                    b.close_price AS adjusted_close
                FROM stocks s
                JOIN market_data_bars b ON b.stock_id = s.id
                WHERE s.market = :market
                  AND s.is_active = TRUE
                  AND b.timeframe = '1d'
                  AND (
                    CASE
                      WHEN b.market = 'TW' THEN (b.timestamp AT TIME ZONE 'Asia/Taipei')::date
                      ELSE (b.timestamp AT TIME ZONE 'America/New_York')::date
                    END
                  ) <= :prediction_date
                ORDER BY s.symbol ASC, b.timestamp DESC
                """
            ),
            {
                "market": request.market,
                "prediction_date": request.prediction_date,
            },
        )
        rows_by_symbol: dict[str, list[dict]] = {}
        for row in result.mappings().all():
            symbol = row["symbol"]
            if len(rows_by_symbol) >= limit and symbol not in rows_by_symbol:
                continue
            symbol_rows = rows_by_symbol.setdefault(symbol, [])
            if len(symbol_rows) < request.lookback_days:
                symbol_rows.append(dict(row))

        price_rows = []
        for rows in rows_by_symbol.values():
            price_rows.extend(reversed(rows))
        if not price_rows:
            raise ValueError(
                f"No {request.market} daily market data found for "
                f"{request.prediction_date}"
            )
        return price_rows

    def _export_input_rows(self, run_id: str, price_rows: list[dict]) -> str:
        output_path = Path(self.settings.artifact_root) / run_id / "market_data.csv"
        export_predictions_input_csv(price_rows, output_path)
        return str(output_path)

    def _build_predictions(
        self,
        run_id: str,
        model_run_id: int,
        request: DailyPredictionRequest,
        model_config: QlibModelConfig,
        trained_artifact: ModelArtifact | None,
        price_rows: list[dict],
    ) -> list[dict]:
        rows_by_stock: dict[int, list[dict]] = {}
        for row in price_rows:
            rows_by_stock.setdefault(int(row["stock_id"]), []).append(row)

        scored = []
        for rows in rows_by_stock.values():
            closes = [
                float(row["adjusted_close"] or row["close_price"])
                for row in rows
            ]
            if len(closes) < model_config.min_lookback_days:
                continue
            latest = rows[-1]
            scored.append(
                {
                    "model_run_id": model_run_id,
                    "run_id": run_id,
                    "stock_id": int(latest["stock_id"]),
                    "symbol": latest["symbol"],
                    "market": latest["market"],
                    "prediction_date": request.prediction_date,
                    "horizon": request.horizon,
                    "score": self._score_rows(
                        rows,
                        closes,
                        model_config,
                        trained_artifact,
                    ),
                    "model_name": request.model_name,
                    "feature_set": request.feature_set,
                }
            )

        scored.sort(key=lambda item: item["score"], reverse=True)
        total = len(scored)
        if total == 0:
            raise ValueError("Not enough daily market data to produce predictions")

        for index, item in enumerate(scored):
            rank = index + 1
            percentile = 1.0 if total == 1 else 1.0 - (index / (total - 1))
            item["rank"] = rank
            item["percentile"] = percentile
            if percentile >= 0.8:
                item["signal_direction"] = "LONG"
            elif percentile <= 0.2:
                item["signal_direction"] = "SHORT"
            else:
                item["signal_direction"] = "NEUTRAL"
            item["metadata_json"] = {
                "engine": self._engine_name(trained_artifact),
                "model_type": model_config.model_type,
                "model_status": model_config.status,
                "portfolio_strategy": model_config.portfolio_strategy,
                "config_uri": model_config.config_uri,
                "training_run_id": (
                    trained_artifact.run_id if trained_artifact else None
                ),
                "universe": request.universe,
                "lookback_days": request.lookback_days,
            }
        return scored

    def _score_rows(
        self,
        rows: list[dict],
        closes: list[float],
        model_config: QlibModelConfig,
        trained_artifact: ModelArtifact | None,
    ) -> float:
        if trained_artifact is not None:
            return predict_with_artifact(rows, trained_artifact)
        return score_price_window(closes, model_config)

    async def _replace_predictions(
        self, db: AsyncSession, run_id: str, predictions: list[dict]
    ) -> None:
        await db.execute(
            text("DELETE FROM qlib_predictions WHERE run_id = :run_id"),
            {"run_id": run_id},
        )
        for prediction in predictions:
            await db.execute(
                text(
                    """
                    INSERT INTO qlib_predictions (
                        model_run_id, run_id, stock_id, symbol, market,
                        prediction_date, horizon, score, rank, percentile,
                        signal_direction, model_name, feature_set, metadata_json,
                        created_at, updated_at
                    )
                    VALUES (
                        :model_run_id, :run_id, :stock_id, :symbol, :market,
                        :prediction_date, :horizon, :score, :rank, :percentile,
                        :signal_direction, :model_name, :feature_set,
                        CAST(:metadata_json AS JSON), NOW(), NOW()
                    )
                    ON CONFLICT (
                        run_id, stock_id, prediction_date, horizon
                    ) DO UPDATE SET
                        score = EXCLUDED.score,
                        rank = EXCLUDED.rank,
                        percentile = EXCLUDED.percentile,
                        signal_direction = EXCLUDED.signal_direction,
                        metadata_json = EXCLUDED.metadata_json,
                        updated_at = NOW()
                    """
                ),
                {
                    **prediction,
                    "metadata_json": json.dumps(prediction["metadata_json"]),
                },
            )
        await db.commit()

    async def _mark_run_succeeded(
        self,
        db: AsyncSession,
        run_id: str,
        artifact_uri: str,
        prediction_count: int,
        model_config: QlibModelConfig,
        trained_artifact: ModelArtifact | None,
    ) -> None:
        await db.execute(
            text(
                """
                UPDATE qlib_model_runs
                SET status = 'succeeded',
                    artifact_uri = :artifact_uri,
                    metrics = CAST(:metrics AS JSON),
                    finished_at = :finished_at,
                    updated_at = NOW()
                WHERE run_id = :run_id
                """
            ),
            {
                "run_id": run_id,
                "artifact_uri": artifact_uri,
                "metrics": json.dumps(
                    self._build_metrics(
                        model_config,
                        trained_artifact,
                        {"prediction_count": prediction_count},
                    )
                ),
                "finished_at": datetime.now(timezone.utc),
            },
        )
        await db.commit()

    def _build_metrics(
        self,
        model_config: QlibModelConfig,
        trained_artifact: ModelArtifact | None = None,
        extra_metrics: dict | None = None,
    ) -> dict:
        metrics = {
            "engine": self._engine_name(trained_artifact),
            "model_type": model_config.model_type,
            "model_status": model_config.status,
            "feature_set": model_config.feature_set,
            "horizon": model_config.horizon,
            "min_lookback_days": model_config.min_lookback_days,
            "portfolio_strategy": model_config.portfolio_strategy,
            "training_run_id": trained_artifact.run_id if trained_artifact else None,
        }
        if extra_metrics:
            metrics.update(extra_metrics)
        return metrics

    def _engine_name(self, trained_artifact: ModelArtifact | None) -> str:
        if trained_artifact is not None:
            return "cpu_model_artifact"
        return "bootstrap_model_registry"

    async def _load_latest_training_artifact(
        self,
        db: AsyncSession,
        request: DailyPredictionRequest,
        model_config: QlibModelConfig,
    ) -> ModelArtifact | None:
        result = await db.execute(
            text(
                """
                SELECT run_id, artifact_uri
                FROM qlib_model_runs
                WHERE market = :market
                  AND universe = :universe
                  AND model_name = :model_name
                  AND feature_set = :feature_set
                  AND (
                    horizon = :horizon
                    OR (horizon IS NULL AND :horizon = '1d')
                  )
                  AND mode = 'train'
                  AND status = 'succeeded'
                  AND stage = 'production'
                  AND artifact_uri IS NOT NULL
                  AND artifact_deleted_at IS NULL
                  AND train_end <= :prediction_date
                ORDER BY promoted_at DESC NULLS LAST, train_end DESC, finished_at DESC
                LIMIT 1
                """
            ),
            {
                "market": request.market,
                "universe": request.universe,
                "model_name": request.model_name,
                "feature_set": request.feature_set,
                "horizon": request.horizon,
                "prediction_date": request.prediction_date,
            },
        )
        row = result.mappings().one_or_none()
        if row is None:
            if model_config.status == "cpu_trainable":
                raise ValueError(
                    "No production training artifact found for "
                    f"{request.market}/{request.universe}/{request.model_name}. "
                    "Promote a succeeded train run before daily prediction."
                )
            return None

        artifact = load_model_artifact(row["artifact_uri"])
        if artifact.model_name != model_config.name:
            raise ValueError(
                f"Training artifact {row['run_id']} is for {artifact.model_name}, "
                f"not {model_config.name}"
            )
        return artifact

    async def _mark_run_failed(
        self, db: AsyncSession, run_id: str, error_message: str
    ) -> None:
        await db.execute(
            text(
                """
                UPDATE qlib_model_runs
                SET status = 'failed',
                    error_message = :error_message,
                    finished_at = :finished_at,
                    updated_at = NOW()
                WHERE run_id = :run_id
                """
            ),
            {
                "run_id": run_id,
                "error_message": error_message[:4000],
                "finished_at": datetime.now(timezone.utc),
            },
        )
        await db.commit()
