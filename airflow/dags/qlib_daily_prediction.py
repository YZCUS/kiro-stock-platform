"""
Daily Qlib prediction orchestration.

This DAG triggers the isolated Qlib prediction service after market data has
been collected. The service writes qlib_model_runs and qlib_predictions back to
the shared database; backend strategies read only successful runs.
"""

from datetime import datetime, timedelta
import os

import requests
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.utils.trigger_rule import TriggerRule


QLIB_API_URL = os.getenv("QLIB_PREDICTION_URL", "http://qlib-prediction-service:8090")
QLIB_INTERNAL_TOKEN = os.getenv("QLIB_INTERNAL_TOKEN", "dev-qlib-token")


def build_prediction_payload(**context):
    logical_date = context["logical_date"].date()
    return {
        "market": "US",
        "prediction_date": logical_date.isoformat(),
        "universe": "active_us",
        "model_name": "lightgbm_alpha158",
        "feature_set": "alpha158",
        "horizon": "1d",
        "lookback_days": 60,
    }


def validate_prediction_result(**context):
    result = context["ti"].xcom_pull(task_ids="trigger_qlib_prediction")
    if not result:
        raise ValueError("Qlib prediction service returned no result")
    if result.get("status") != "succeeded":
        raise ValueError(f"Qlib prediction run failed: {result}")
    if int(result.get("prediction_count") or 0) <= 0:
        raise ValueError(f"Qlib prediction run produced no predictions: {result}")
    return result


def trigger_qlib_prediction(**context):
    payload = context["ti"].xcom_pull(task_ids="build_prediction_payload")
    response = requests.post(
        f"{QLIB_API_URL.rstrip('/')}/internal/jobs/daily-prediction",
        json=payload,
        headers={"X-Internal-Token": QLIB_INTERNAL_TOKEN},
        timeout=1800,
    )
    response.raise_for_status()
    return response.json()


dag_config = {
    "dag_id": "qlib_daily_prediction",
    "description": "Run daily Qlib prediction and persist model scores",
    "schedule_interval": "30 23 * * 1-5",
    "max_active_runs": 1,
    "catchup": False,
    "tags": ["qlib", "prediction", "ml"],
    "default_args": {
        "owner": "stock-analysis-platform",
        "depends_on_past": False,
        "start_date": datetime(2024, 1, 1),
        "email_on_failure": True,
        "email_on_retry": False,
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    },
}

dag = DAG(**dag_config)

start_task = EmptyOperator(task_id="start", dag=dag)

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

complete_task = EmptyOperator(
    task_id="qlib_prediction_complete",
    trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    dag=dag,
)

start_task >> build_payload_task >> trigger_prediction_task
trigger_prediction_task >> validate_result_task >> complete_task
