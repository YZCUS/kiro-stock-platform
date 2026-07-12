"""
Daily Qlib prediction orchestration.

This DAG triggers the isolated Qlib prediction service after market data has
been collected. The service writes qlib_model_runs and qlib_predictions back to
the shared database; backend strategies read only successful runs.
"""

from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import os
import pendulum

import requests
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.sensors.external_task import ExternalTaskSensor

from plugins.common.date_utils import context_interval_date

QLIB_API_URL = os.getenv("QLIB_PREDICTION_URL", "http://qlib-prediction-service:8090")
QLIB_INTERNAL_TOKEN = os.getenv("QLIB_INTERNAL_TOKEN", "dev-qlib-token")
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://backend:8000/api/v1")
INTERNAL_API_TOKEN = os.getenv(
    "INTERNAL_API_TOKEN",
    os.getenv("QLIB_INTERNAL_TOKEN", "dev-internal-token"),
)
DEFAULT_MODEL_NAMES = (
    "lightgbm_alpha158,lightgbm_alpha158_5d,"
    "lightgbm_alpha158_20d,lightgbm_alpha158_60d"
)

MODEL_PAYLOAD_CONFIGS = {
    "lightgbm_alpha158": {
        "feature_set": "alpha158",
        "horizon": "1d",
        "lookback_days": 60,
    },
    "lightgbm_alpha158_5d": {
        "feature_set": "alpha158",
        "horizon": "5d",
        "lookback_days": 80,
    },
    "lightgbm_alpha158_20d": {
        "feature_set": "alpha158",
        "horizon": "20d",
        "lookback_days": 120,
    },
    "lightgbm_alpha158_60d": {
        "feature_set": "alpha158",
        "horizon": "60d",
        "lookback_days": 180,
    },
    "xgboost_alpha158": {
        "feature_set": "alpha158",
        "horizon": "1d",
        "lookback_days": 60,
    },
    "xgboost_alpha158_5d": {
        "feature_set": "alpha158",
        "horizon": "5d",
        "lookback_days": 80,
    },
    "xgboost_alpha158_20d": {
        "feature_set": "alpha158",
        "horizon": "20d",
        "lookback_days": 120,
    },
    "xgboost_alpha158_60d": {
        "feature_set": "alpha158",
        "horizon": "60d",
        "lookback_days": 180,
    },
    "catboost_alpha158": {
        "feature_set": "alpha158",
        "horizon": "1d",
        "lookback_days": 60,
    },
    "catboost_alpha158_5d": {
        "feature_set": "alpha158",
        "horizon": "5d",
        "lookback_days": 80,
    },
    "catboost_alpha158_20d": {
        "feature_set": "alpha158",
        "horizon": "20d",
        "lookback_days": 120,
    },
    "catboost_alpha158_60d": {
        "feature_set": "alpha158",
        "horizon": "60d",
        "lookback_days": 180,
    },
    "mlp_alpha360": {
        "feature_set": "alpha360",
        "horizon": "1d",
        "lookback_days": 120,
    },
    "lstm_alpha360": {
        "feature_set": "alpha360",
        "horizon": "1d",
        "lookback_days": 180,
    },
}


def get_enabled_model_names():
    raw_model_names = os.getenv("QLIB_MODEL_NAMES", DEFAULT_MODEL_NAMES)
    model_names = [
        model_name.strip()
        for model_name in raw_model_names.split(",")
        if model_name.strip()
    ]
    if not model_names:
        raise ValueError("QLIB_MODEL_NAMES must enable at least one model")
    invalid_model_names = [
        model_name
        for model_name in model_names
        if model_name not in MODEL_PAYLOAD_CONFIGS
    ]
    if invalid_model_names:
        raise ValueError(
            "Unsupported Qlib model names: " + ", ".join(invalid_model_names)
        )
    return model_names


def build_prediction_payload(**context):
    prediction_date = context_interval_date(context, "America/New_York")
    payloads = []
    for model_name in get_enabled_model_names():
        payloads.append(
            {
                "market": "US",
                "prediction_date": prediction_date.isoformat(),
                "universe": "active_us",
                "model_name": model_name,
                **MODEL_PAYLOAD_CONFIGS[model_name],
            }
        )
    return payloads


def validate_prediction_result(**context):
    result = context["ti"].xcom_pull(task_ids="trigger_qlib_prediction")
    if not result:
        raise ValueError("Qlib prediction service returned no result")

    results = result if isinstance(result, list) else [result]
    for item in results:
        if item.get("status") != "succeeded":
            raise ValueError(f"Qlib prediction run failed: {item}")
        if int(item.get("prediction_count") or 0) <= 0:
            raise ValueError(f"Qlib prediction run produced no predictions: {item}")
    return result


def trigger_strategy_signal_generation():
    response = requests.post(
        f"{BACKEND_API_URL.rstrip('/')}/internal/strategies/signals/generate",
        headers={"X-Internal-Token": INTERNAL_API_TOKEN},
        timeout=1800,
    )
    response.raise_for_status()
    result = response.json()
    if result.get("errors"):
        raise ValueError(f"Strategy signal generation had errors: {result['errors']}")
    return result


def trigger_composite_score_generation():
    response = requests.post(
        f"{BACKEND_API_URL.rstrip('/')}/internal/strategies/composite-scores/generate",
        headers={"X-Internal-Token": INTERNAL_API_TOKEN},
        timeout=600,
    )
    response.raise_for_status()
    return response.json()


def trigger_qlib_prediction(**context):
    payloads = context["ti"].xcom_pull(task_ids="build_prediction_payload")
    if isinstance(payloads, dict):
        payloads = [payloads]

    def submit(payload):
        response = requests.post(
            f"{QLIB_API_URL.rstrip('/')}/internal/jobs/daily-prediction",
            json=payload,
            headers={"X-Internal-Token": QLIB_INTERNAL_TOKEN},
            timeout=1800,
        )
        response.raise_for_status()
        return response.json()

    max_workers = min(
        len(payloads),
        max(1, int(os.getenv("QLIB_MAX_PARALLEL_MODELS", "2"))),
    )
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(submit, payloads))


dag_config = {
    "dag_id": "qlib_daily_prediction",
    "description": "Run daily Qlib prediction and persist model scores",
    "schedule": "30 23 * * 1-5",
    "max_active_runs": 1,
    "catchup": False,
    "tags": ["qlib", "prediction", "ml"],
    "default_args": {
        "owner": "stock-analysis-platform",
        "depends_on_past": False,
        "start_date": pendulum.datetime(2024, 1, 1, tz="UTC"),
        "email_on_failure": True,
        "email_on_retry": False,
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    },
}

dag = DAG(**dag_config)

start_task = EmptyOperator(task_id="start", dag=dag)

wait_for_collection_task = ExternalTaskSensor(
    task_id="wait_for_us_collection_validation",
    external_dag_id="daily_stock_collection_us_api",
    external_task_id="verify_dependencies",
    execution_delta=timedelta(hours=2, minutes=30),
    allowed_states=["success"],
    skipped_states=["skipped"],
    failed_states=["failed", "upstream_failed"],
    timeout=60 * 60,
    poke_interval=60,
    mode="reschedule",
    dag=dag,
)

build_payload_task = PythonOperator(
    task_id="build_prediction_payload",
    python_callable=build_prediction_payload,
    dag=dag,
)

trigger_prediction_task = PythonOperator(
    task_id="trigger_qlib_prediction",
    python_callable=trigger_qlib_prediction,
    dag=dag,
)

validate_result_task = PythonOperator(
    task_id="validate_prediction_result",
    python_callable=validate_prediction_result,
    dag=dag,
)

trigger_signal_generation_task = PythonOperator(
    task_id="trigger_strategy_signal_generation",
    python_callable=trigger_strategy_signal_generation,
    dag=dag,
)

trigger_composite_scores_task = PythonOperator(
    task_id="trigger_composite_score_generation",
    python_callable=trigger_composite_score_generation,
    dag=dag,
)

complete_task = EmptyOperator(
    task_id="qlib_prediction_complete",
    dag=dag,
)

start_task >> wait_for_collection_task >> build_payload_task >> trigger_prediction_task
trigger_prediction_task >> validate_result_task >> trigger_signal_generation_task
trigger_signal_generation_task >> trigger_composite_scores_task >> complete_task
