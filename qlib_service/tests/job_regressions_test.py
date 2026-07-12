from datetime import date
from types import SimpleNamespace

import pytest

from app.jobs.prediction_job import PredictionJob
from app.jobs.training_job import TrainingJob
from app.schemas import DailyPredictionRequest, TrainModelRequest
from app.db import make_async_engine_kwargs


def _prediction_request(**overrides):
    values = {
        "market": "US",
        "prediction_date": date(2026, 7, 10),
        "universe": "active_us",
        "model_name": "lightgbm_alpha158",
        "feature_set": "alpha158",
        "horizon": "1d",
        "lookback_days": 60,
    }
    values.update(overrides)
    return DailyPredictionRequest(**values)


def _training_request(**overrides):
    values = {
        "market": "US",
        "universe": "active_us",
        "model_name": "lightgbm_alpha158",
        "feature_set": "alpha158",
        "horizon": "1d",
        "train_start": date(2023, 1, 1),
        "train_end": date(2024, 12, 31),
        "valid_start": date(2025, 1, 1),
        "valid_end": date(2025, 6, 30),
        "test_start": date(2025, 7, 1),
        "test_end": date(2026, 7, 10),
        "lookback_days": 60,
    }
    values.update(overrides)
    return TrainModelRequest(**values)


def test_prediction_run_id_is_deterministic_for_airflow_retries():
    job = PredictionJob(SimpleNamespace())
    request = _prediction_request()

    assert job._build_run_id(request) == job._build_run_id(request)
    assert job._build_run_id(request) != job._build_run_id(
        _prediction_request(prediction_date=date(2026, 7, 11))
    )
    assert len(job._build_run_id(request)) <= 64


def test_prediction_run_id_changes_when_production_model_changes():
    job = PredictionJob(SimpleNamespace())
    request = _prediction_request()

    first = job._build_run_id(request, training_run_id="train-run-a")
    retry = job._build_run_id(request, training_run_id="train-run-a")
    promoted = job._build_run_id(request, training_run_id="train-run-b")

    assert first == retry
    assert first != promoted


def test_training_run_id_is_deterministic_for_airflow_retries():
    job = TrainingJob(SimpleNamespace())
    request = _training_request()

    assert job._build_run_id(request) == job._build_run_id(request)
    assert job._build_run_id(request) != job._build_run_id(
        _training_request(lookback_days=80)
    )
    assert len(job._build_run_id(request)) <= 64


def test_qlib_database_pool_is_bounded_per_worker():
    kwargs = make_async_engine_kwargs(
        "postgresql://user:pass@postgres:5432/app",
        pool_size=2,
        max_overflow=1,
    )

    assert kwargs["pool_size"] == 2
    assert kwargs["max_overflow"] == 1


class EmptyMappings:
    def all(self):
        return []


class EmptyResult:
    def mappings(self):
        return EmptyMappings()


class CapturingSession:
    def __init__(self):
        self.sql = ""
        self.params = None

    async def execute(self, statement, params=None):
        self.sql = str(statement)
        self.params = params
        return EmptyResult()


@pytest.mark.asyncio
async def test_prediction_query_limits_history_and_deduplicates_daily_sources():
    session = CapturingSession()
    job = PredictionJob(SimpleNamespace(max_universe_size=500))

    with pytest.raises(ValueError, match="No US daily market data"):
        await job._load_price_rows(session, _prediction_request())

    assert "ROW_NUMBER() OVER" in session.sql
    assert "canonical_rank = 1" in session.sql
    assert "history_rank <= :lookback_days" in session.sql
    assert session.params["limit"] == 500
    assert session.params["lookback_days"] == 60


@pytest.mark.asyncio
async def test_training_query_is_bounded_and_deduplicates_daily_sources():
    session = CapturingSession()
    job = TrainingJob(SimpleNamespace(max_universe_size=500))

    with pytest.raises(ValueError, match="No US daily market data"):
        await job._load_price_rows(session, _training_request())

    assert "ROW_NUMBER() OVER" in session.sql
    assert "canonical_rank = 1" in session.sql
    assert "BETWEEN :history_start AND :test_end" in session.sql
    assert session.params["history_start"] < _training_request().train_start
    assert session.params["limit"] == 500
