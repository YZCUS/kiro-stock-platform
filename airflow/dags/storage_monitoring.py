"""
存儲監控 DAG（模塊化重構）

定期監控外部存儲健康狀態、執行維護任務和發送警報
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.trigger_rule import TriggerRule

# Import workflow functions from plugins
from plugins.workflows.storage_monitoring import (
    storage_health_check,
    check_storage_capacity,
    storage_maintenance,
    generate_storage_report,
)

# DAG 配置
dag_config = {
    'dag_id': 'storage_monitoring',
    'description': '外部存儲監控和維護工作流程',
    'schedule_interval': '*/30 * * * *',  # 每30分鐘運行一次
    'max_active_runs': 1,
    'catchup': False,
    'tags': ['monitoring', 'storage', 'maintenance'],
    'default_args': {
        'owner': 'data-platform',
        'depends_on_past': False,
        'start_date': datetime(2024, 1, 1),
        'email_on_failure': True,
        'email_on_retry': False,
        'retries': 1,
        'retry_delay': timedelta(minutes=5)
    }
}

# 創建 DAG
dag = DAG(**dag_config)

# ========== 任務定義 ==========

# 存儲健康檢查
health_check_task = PythonOperator(
    task_id='storage_health_check',
    python_callable=storage_health_check,
    dag=dag
)

# 容量檢查
capacity_check_task = PythonOperator(
    task_id='check_storage_capacity',
    python_callable=check_storage_capacity,
    dag=dag
)

# 生成報告
report_task = PythonOperator(
    task_id='generate_storage_report',
    python_callable=generate_storage_report,
    dag=dag
)

# 存儲維護（每小時執行一次，只在整點運行）
maintenance_task = PythonOperator(
    task_id='storage_maintenance',
    python_callable=storage_maintenance,
    dag=dag,
    depends_on_past=False
)

# 匯總任務
summary_task = EmptyOperator(
    task_id='monitoring_complete',
    trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    dag=dag
)

# ========== 任務依賴關係 ==========

# 並行執行健康檢查和容量檢查
[health_check_task, capacity_check_task] >> report_task

# 維護任務獨立運行
maintenance_task

# 所有監控任務完成後執行匯總
[report_task, maintenance_task] >> summary_task
