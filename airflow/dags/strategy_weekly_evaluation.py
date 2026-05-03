"""
Weekly strategy backtest and reliability-weight evaluation.

Runs outside user request paths. The backend writes backtest metrics,
strategy reliability scores, bounded dynamic weights, and current composite
stock scores.
"""

from datetime import datetime, timedelta
import os

import requests
from airflow import DAG
from airflow.operators.python import PythonOperator


BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://backend:8000/api/v1")
INTERNAL_API_TOKEN = os.getenv(
    "INTERNAL_API_TOKEN",
    os.getenv("QLIB_INTERNAL_TOKEN", "dev-internal-token"),
)
DEFAULT_HORIZONS = "1d,5d,20d,60d"


def run_strategy_evaluation(**context):
    horizons = [
        horizon.strip()
        for horizon in os.getenv("STRATEGY_EVALUATION_HORIZONS", DEFAULT_HORIZONS).split(",")
        if horizon.strip()
    ]
    logical_date = context["logical_date"].date()
    start_date = logical_date - timedelta(days=365 * 3)
    params = [
        ("market", "US"),
        ("universe", "active_us"),
        ("start_date", start_date.isoformat()),
        ("end_date", logical_date.isoformat()),
        *[("horizons", horizon) for horizon in horizons],
    ]
    response = requests.post(
        f"{BACKEND_API_URL.rstrip('/')}/internal/strategies/evaluation/run",
        params=params,
        headers={"X-Internal-Token": INTERNAL_API_TOKEN},
        timeout=3600,
    )
    response.raise_for_status()
    return response.json()


dag = DAG(
    dag_id="strategy_weekly_evaluation",
    description="Backtest strategies and publish bounded reliability weights",
    schedule_interval="0 6 * * 6",
    max_active_runs=1,
    catchup=False,
    tags=["strategy", "backtest", "weights"],
    default_args={
        "owner": "stock-analysis-platform",
        "depends_on_past": False,
        "start_date": datetime(2024, 1, 1),
        "email_on_failure": True,
        "email_on_retry": False,
        "retries": 0,
    },
)


run_evaluation_task = PythonOperator(
    task_id="run_strategy_evaluation",
    python_callable=run_strategy_evaluation,
    dag=dag,
)
