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

Training runs use the same table with:

```text
qlib_model_runs.mode = 'train'
qlib_model_runs.status = 'succeeded'
qlib_model_runs.horizon IN ('1d', '5d', '20d', '60d')
qlib_model_runs.artifact_uri = '/app/artifacts/models/.../model.pkl'
qlib_model_runs.stage IN ('candidate', 'production', 'previous', 'archived')
```

New training artifacts start as `candidate`. Daily prediction for CPU-trainable
models only loads a `production` artifact. This prevents a newly trained model
from silently replacing the currently deployed model before evaluation.

## Model Version Management

Promote a successful candidate after evaluation:

```text
POST /internal/model-runs/{run_id}/promote
```

Promotion rules:

- the target run must be `mode='train'`, `status='succeeded'`, and have a
  retained artifact
- existing `production` for the same market/universe/model/feature set becomes
  `previous`
- existing `previous` versions for that same scope become `archived`
- only one `production` version is allowed per
  market/universe/model/feature set/horizon

Rollback promotes the current `previous` version back to `production`:

```text
POST /internal/model-runs/rollback
```

Retention is dry-run by default:

```text
POST /internal/model-runs/prune
```

Recommended initial policy:

- keep `production`
- keep `previous`
- keep the latest `8-12` successful artifacts per model
- archive older candidates
- only delete local artifacts when `delete_artifacts=true` and after confirming
  they are no longer needed

## Airflow

`airflow/dags/qlib_daily_prediction.py` triggers:

```text
POST /internal/jobs/daily-prediction
```

`airflow/dags/qlib_cpu_model_training.py` triggers:

```text
POST /internal/jobs/train-model
```

`airflow/dags/strategy_weekly_evaluation.py` triggers:

```text
POST /internal/strategies/evaluation/run
```

The internal token is read from `QLIB_INTERNAL_TOKEN`; local default is
`dev-qlib-token`.

By default the daily prediction DAG runs the LightGBM CPU profiles across the
supported horizons:

```text
lightgbm_alpha158,lightgbm_alpha158_5d,lightgbm_alpha158_20d,lightgbm_alpha158_60d
```

Override `QLIB_MODEL_NAMES` with a comma-separated list to run a different
subset. Supported values are:

- `lightgbm_alpha158`
- `lightgbm_alpha158_5d`
- `lightgbm_alpha158_20d`
- `lightgbm_alpha158_60d`
- `xgboost_alpha158`
- `xgboost_alpha158_5d`
- `xgboost_alpha158_20d`
- `xgboost_alpha158_60d`
- `catboost_alpha158`
- `catboost_alpha158_5d`
- `catboost_alpha158_20d`
- `catboost_alpha158_60d`
- `mlp_alpha360`
- `lstm_alpha360`

CPU training is currently enabled for:

```text
lightgbm_alpha158,lightgbm_alpha158_5d,lightgbm_alpha158_20d,lightgbm_alpha158_60d
```

Override `QLIB_CPU_MODEL_NAMES` with a comma-separated subset when needed.
XGBoost and CatBoost horizon variants are available in the registry and can be
enabled explicitly. `mlp_alpha360` and `lstm_alpha360` remain listed in the
registry as planned GPU profiles, but they are not accepted by the CPU training
endpoint.

The service exposes the same registry through:

```text
GET /internal/models
```

The backend exposes frontend-safe options through:

```text
GET /api/v1/qlib/models
```

## Current MVP Boundary

The service now supports CPU-trained artifacts for LightGBM, XGBoost, and
CatBoost using alpha-like daily price/volume features. Daily inference loads the
current production artifact for the requested model, market, universe, and
feature set. If no production artifact exists for a CPU-trainable model, the
prediction job fails and the model must be promoted first.

Prediction horizon is part of the model contract. A `20d` model is trained
against 20 trading days of forward return and inference results are written with
`qlib_predictions.horizon = '20d'`. Backend strategy code should match
prediction rows and model runs by horizon instead of treating all predictions as
one-day signals.

## Strategy Evaluation and Composite Scores

The strategy evaluation layer runs outside user request paths. It backtests each
registered strategy over historical daily bars, converts those results into
bounded reliability scores, publishes a weight version, and writes cached stock
composite scores for the UI.

The evaluation service writes:

- `strategy_backtest_runs`
- `strategy_backtest_results`
- `strategy_reliability_scores`
- `strategy_weight_versions`
- `strategy_weights`
- `stock_composite_scores`

Supported signal horizons are `1d`, `5d`, `20d`, and `60d`.
`strategy_signals.signal_horizon` records the intended holding/prediction
period for each generated signal. Composite scoring matches active signals to
weights by `(strategy_type, signal_horizon)`.

The evaluation run now records a strategy research pipeline version and data
coverage on `strategy_backtest_runs.parameters`. Each result also stores
research diagnostics in `strategy_backtest_results.metrics`:

- `data_coverage`: stock count, estimated trading-day coverage, and bars per
  stock.
- `walk_forward`: chronological fold pass rate and fold return dispersion.
- `precision_at_10`, `precision_at_20`, `precision_at_50`: top-confidence hit
  rate.
- `confidence_return_rank_ic`: rank correlation between signal confidence and
  realized forward return.
- `research_status`: gate such as `low_sample`, `unstable_walk_forward`,
  `research_ready`, or `production_candidate`.

Reliability scoring uses these research metrics conservatively. Poor
walk-forward stability, weak top-rank precision, low sample count, or incomplete
data coverage caps the target score even when headline backtest metrics look
good.

`stock_composite_scores` is a cache. User-facing pages should read this table
instead of recomputing all strategy votes during page load.

Dynamic weights are bounded to avoid death-spiral behavior:

- minimum weight per strategy/horizon: `0.05`
- maximum weight per strategy/horizon: `0.45`
- smoothing factor per evaluation: `0.20`

Low-sample strategies are retained with a validation penalty instead of being
dropped completely.

The remaining pyqlib/qrun integration point is:

```text
qlib_service/app/qlib/run_experiment.py
```

Replacing the local feature/training implementation with `pyqlib`/`qrun` output
parsing should not change the backend, Airflow, or database contract.
