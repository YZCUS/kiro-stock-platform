"""
Price alert monitoring DAG.

Checks active user alerts against canonical local prices, with the backend
falling back to external quote data only when local prices are unavailable.
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


def check_price_alerts():
    response = requests.post(
        f"{BACKEND_API_URL.rstrip('/')}/internal/price-alerts/check",
        headers={"X-Internal-Token": INTERNAL_API_TOKEN},
        timeout=120,
    )
    response.raise_for_status()
    result = response.json()
    return {
        "checked": int(result.get("checked") or 0),
        "triggered": int(result.get("triggered") or 0),
        "skipped": int(result.get("skipped") or 0),
    }


dag = DAG(
    dag_id="price_alert_monitoring",
    description="Check active price alerts",
    schedule="*/5 * * * *",
    max_active_runs=1,
    catchup=False,
    tags=["alerts", "market-data"],
    default_args={
        "owner": "stock-analysis-platform",
        "depends_on_past": False,
        "start_date": datetime(2024, 1, 1),
        "email_on_failure": True,
        "email_on_retry": False,
        "retries": 1,
        "retry_delay": timedelta(minutes=2),
    },
)


check_alerts_task = PythonOperator(
    task_id="check_price_alerts",
    python_callable=check_price_alerts,
    dag=dag,
)
