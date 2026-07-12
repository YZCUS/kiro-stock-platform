"""
Weekly CPU model training orchestration for Qlib prediction profiles.

This DAG trains CPU-backed model artifacts. Daily prediction jobs then load the
latest successful artifact for the selected model and market.
"""

from datetime import datetime, timedelta
import os
import pendulum

import requests
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator

from plugins.common.date_utils import context_interval_date

QLIB_API_URL = os.getenv("QLIB_PREDICTION_URL", "http://qlib-prediction-service:8090")
QLIB_INTERNAL_TOKEN = os.getenv("QLIB_INTERNAL_TOKEN", "dev-qlib-token")
DEFAULT_CPU_MODEL_NAMES = (
    "lightgbm_alpha158,lightgbm_alpha158_5d,"
    "lightgbm_alpha158_20d,lightgbm_alpha158_60d"
)

CPU_MODEL_PAYLOAD_CONFIGS = {
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
}


def get_enabled_cpu_model_names():
    raw_model_names = os.getenv("QLIB_CPU_MODEL_NAMES", DEFAULT_CPU_MODEL_NAMES)
    model_names = [
        model_name.strip()
        for model_name in raw_model_names.split(",")
        if model_name.strip()
    ]
    if not model_names:
        raise ValueError("QLIB_CPU_MODEL_NAMES must enable at least one model")
    invalid_model_names = [
        model_name
        for model_name in model_names
        if model_name not in CPU_MODEL_PAYLOAD_CONFIGS
    ]
    if invalid_model_names:
        raise ValueError(
            "Unsupported CPU Qlib model names: " + ", ".join(invalid_model_names)
        )
    return model_names


def build_training_payloads(**context):
    test_end = context_interval_date(context, "America/New_York")
    test_start = test_end - timedelta(days=90)
    valid_end = test_start - timedelta(days=1)
    valid_start = valid_end - timedelta(days=90)
    train_end = valid_start - timedelta(days=1)
    train_start = train_end - timedelta(days=720)

    payloads = []
    for model_name in get_enabled_cpu_model_names():
        payloads.append(
            {
                "market": "US",
                "universe": "active_us",
                "model_name": model_name,
                "train_start": train_start.isoformat(),
                "train_end": train_end.isoformat(),
                "valid_start": valid_start.isoformat(),
                "valid_end": valid_end.isoformat(),
                "test_start": test_start.isoformat(),
                "test_end": test_end.isoformat(),
                **CPU_MODEL_PAYLOAD_CONFIGS[model_name],
            }
        )
    return payloads


def trigger_cpu_training(**context):
    payloads = context["ti"].xcom_pull(task_ids="build_training_payloads")
    results = []
    for payload in payloads:
        response = requests.post(
            f"{QLIB_API_URL.rstrip('/')}/internal/jobs/train-model",
            json=payload,
            headers={"X-Internal-Token": QLIB_INTERNAL_TOKEN},
            timeout=3600,
        )
        response.raise_for_status()
        results.append(response.json())
    return results


def validate_training_results(**context):
    results = context["ti"].xcom_pull(task_ids="trigger_cpu_training")
    if not results:
        raise ValueError("Qlib CPU training returned no result")

    for result in results:
        if result.get("status") != "succeeded":
            raise ValueError(f"Qlib CPU training failed: {result}")
        if not result.get("artifact_uri"):
            raise ValueError(f"Qlib CPU training produced no artifact: {result}")
    return results


dag_config = {
    "dag_id": "qlib_cpu_model_training",
    "description": "Train CPU Qlib model artifacts for daily inference",
    "schedule": "0 2 * * 6",
    "max_active_runs": 1,
    "catchup": False,
    "tags": ["qlib", "training", "ml", "cpu"],
    "default_args": {
        "owner": "stock-analysis-platform",
        "depends_on_past": False,
        "start_date": pendulum.datetime(2024, 1, 1, tz="UTC"),
        "email_on_failure": True,
        "email_on_retry": False,
        "retries": 0,
    },
}

dag = DAG(**dag_config)

start_task = EmptyOperator(task_id="start", dag=dag)

build_payloads_task = PythonOperator(
    task_id="build_training_payloads",
    python_callable=build_training_payloads,
    dag=dag,
)

trigger_training_task = PythonOperator(
    task_id="trigger_cpu_training",
    python_callable=trigger_cpu_training,
    dag=dag,
)

validate_results_task = PythonOperator(
    task_id="validate_training_results",
    python_callable=validate_training_results,
    dag=dag,
)

complete_task = EmptyOperator(
    task_id="qlib_cpu_training_complete",
    dag=dag,
)

start_task >> build_payloads_task >> trigger_training_task
trigger_training_task >> validate_results_task >> complete_task
