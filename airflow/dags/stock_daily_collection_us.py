"""
每日美股數據收集 DAG - API版本（模塊化重構）

執行時間：每交易日台北時間 05:00 (UTC 21:00 前一天)
         對應美東時間 17:00 (收盤後 1 小時，確保 Yahoo Finance 數據已更新)
功能：通過API調用Backend服務收集美股數據
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.trigger_rule import TriggerRule

# Import workflow functions from plugins
from plugins.workflows.stock_collection import (
    # Callbacks
    handle_task_failure,
    handle_task_retry,
    # Validators
    check_trading_day_us,
    check_market_status,
    verify_task_dependencies,
    validate_data_quality,
    # Collection workflows
    decide_collection_strategy,
    try_main_collection_workflow_us,
    decide_next_step,
    execute_fallback_collection_us,
    # Notifications
    send_completion_notification,
    # Cleanup
    cleanup_external_storage,
)

# DAG配置
dag_config = {
    'dag_id': 'daily_stock_collection_us_api',
    'description': '每日美股數據收集工作流程 - API版本',
    'schedule_interval': '0 21 * * 1-5',  # UTC 週一到週五 21:00 = 台北時間週二到週六 05:00
    'max_active_runs': 1,
    'catchup': False,  # 移至 DAG 層級，避免補跑歷史排程
    'tags': ['stock-data', 'daily', 'api', 'us-market'],
    'default_args': {
        'owner': 'stock-analysis-platform',
        'depends_on_past': False,
        'start_date': datetime(2024, 1, 1),
        'email_on_failure': True,
        'email_on_retry': False,
        'retries': 2,
        'retry_delay': timedelta(minutes=5),
        'on_failure_callback': lambda context: handle_task_failure(context),
        'on_success_callback': None,
        'on_retry_callback': lambda context: handle_task_retry(context)
    }
}

# 建立 DAG
dag = DAG(**dag_config)

# ========== 任務定義 ==========

# 檢查美股交易日（使用分支決策）
check_trading_day_task = BranchPythonOperator(
    task_id='check_trading_day_us',
    python_callable=check_trading_day_us,
    dag=dag
)

# 非交易日跳過任務
skip_collection_task = EmptyOperator(
    task_id='skip_collection',
    dag=dag
)

# 檢查市場狀態
check_market_status_task = PythonOperator(
    task_id='check_market_status',
    python_callable=check_market_status,
    dag=dag
)

# 分支決策：選擇收集策略
branch_task = BranchPythonOperator(
    task_id='decide_collection_strategy',
    python_callable=decide_collection_strategy,
    dag=dag
)

# 主要收集任務 - 美股
try_main_collection_task = PythonOperator(
    task_id='try_main_collection',
    python_callable=try_main_collection_workflow_us,
    dag=dag
)

# 根據主要收集結果決定下一步
next_step_branch = BranchPythonOperator(
    task_id='decide_next_step',
    python_callable=decide_next_step,
    dag=dag
)

# 成功標記任務（當主要流程成功時）
collection_success_task = EmptyOperator(
    task_id='collection_success',
    dag=dag
)

# 備援收集任務 - 美股
fallback_collection_task = PythonOperator(
    task_id='execute_fallback_collection',
    python_callable=execute_fallback_collection_us,
    dag=dag
)

# 聚合任務 - 匯合主要成功路徑和備援成功路徑
collection_complete_task = EmptyOperator(
    task_id='collection_complete',
    trigger_rule=TriggerRule.NONE_FAILED_OR_SKIPPED,  # 只要執行的路徑成功即可
    dag=dag
)

# 數據品質驗證
validate_data_task = PythonOperator(
    task_id='validate_data_quality',
    python_callable=validate_data_quality,
    dag=dag
)

# 驗證任務依賴關係
verify_dependencies_task = PythonOperator(
    task_id='verify_dependencies',
    python_callable=verify_task_dependencies,
    dag=dag
)

# 發送完成通知
send_notification_task = PythonOperator(
    task_id='send_completion_notification',
    python_callable=send_completion_notification,
    dag=dag
)

# 清理外部存儲
cleanup_storage_task = PythonOperator(
    task_id='cleanup_external_storage',
    python_callable=cleanup_external_storage,
    trigger_rule=TriggerRule.ALL_DONE,  # 無論成功失敗都執行清理
    dag=dag
)

# ========== 任務依賴關係 ==========

# 第一層分支：檢查是否為美股交易日
check_trading_day_task >> [check_market_status_task, skip_collection_task]

# 交易日流程：檢查市場狀態後進入收集策略分支
check_market_status_task >> branch_task

# 分支路徑：總是先嘗試主要收集
branch_task >> try_main_collection_task

# 根據主要收集結果決定下一步
try_main_collection_task >> next_step_branch

# 分支選擇：成功則直接進入後續，失敗則執行備援
next_step_branch >> collection_success_task  # 主要成功路徑
next_step_branch >> fallback_collection_task  # 備援路徑

# 匯合點：單一成功路徑繼續
[collection_success_task, fallback_collection_task] >> collection_complete_task

# 後續處理
collection_complete_task >> validate_data_task
validate_data_task >> verify_dependencies_task
verify_dependencies_task >> send_notification_task
send_notification_task >> cleanup_storage_task
