# Qlib Prediction Service

The Qlib prediction integration is intentionally isolated from the FastAPI
backend. Airflow triggers the service, the service reads market data from the
shared database, and successful inference runs write results back to dedicated
Qlib tables.

## Local Services

Start the service with the `qlib` profile:

```bash
docker compose --profile qlib up qlib-prediction-service
```

The service listens on `http://localhost:8090` locally and on
`http://qlib-prediction-service:8090` inside Docker Compose.

## Database Boundary

The service reads:

- `stocks`
- `market_data_bars`

The service writes:

- `qlib_model_runs`
- `qlib_predictions`
- `qlib_backtest_results`

Backend strategy code should only consume successful inference runs:

```text
qlib_model_runs.mode = 'infer'
qlib_model_runs.status = 'succeeded'
```

## Airflow

`airflow/dags/qlib_daily_prediction.py` triggers:

```text
POST /internal/jobs/daily-prediction
```

The internal token is read from `QLIB_INTERNAL_TOKEN`; local default is
`dev-qlib-token`.

## Current MVP Boundary

The service currently uses a deterministic bootstrap momentum scorer while the
Qlib experiment runner is wired in. The swap point is:

```text
qlib_service/app/qlib/run_experiment.py
```

Replacing that implementation with `pyqlib`/`qrun` output parsing should not
change the backend, Airflow, or database contract.
