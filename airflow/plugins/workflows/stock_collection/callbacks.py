"""
Airflow DAG 回調函數模塊

處理任務失敗、重試等回調邏輯
"""


def handle_task_failure(context):
    """處理任務失敗"""
    from plugins.common.date_utils import get_taipei_now

    task_instance = context['task_instance']
    dag_run = context['dag_run']
    task_id = task_instance.task_id
    taipei_now = get_taipei_now()

    error_message = f"""
任務失敗通知

DAG: {dag_run.dag_id}
任務: {task_id}
執行日期: {dag_run.execution_date}
失敗時間: {taipei_now.format('YYYY-MM-DD HH:mm:ss')} (台北時間)

錯誤詳情:
{context.get('exception', '未知錯誤')}

影響分析:
- 如果是 get_active_stocks 失敗，會影響整個數據收集流程
- 如果是 collect_all_stocks 失敗，可能是部分股票數據收集有問題
- 建議檢查相關API服務和網路連接

自動重試: {task_instance.max_tries - task_instance.try_number} 次剩餘
    """

    print(error_message)

    # 記錄失敗統計
    return {
        'failure_logged': True,
        'failed_task': task_id,
        'failure_time': taipei_now.isoformat(),
        'retry_count': task_instance.try_number
    }


def handle_task_retry(context):
    """處理任務重試"""
    from plugins.common.date_utils import get_taipei_now

    task_instance = context['task_instance']
    task_id = task_instance.task_id
    taipei_now = get_taipei_now()

    retry_message = f"""
任務重試通知

任務: {task_id}
重試次數: {task_instance.try_number}/{task_instance.max_tries}
重試時間: {taipei_now.format('YYYY-MM-DD HH:mm:ss')} (台北時間)

如果是股票獲取任務重試，將重新獲取最新的股票清單
如果是數據收集任務重試，將重新使用上游任務的股票清單進行收集
    """

    print(retry_message)

    return {
        'retry_logged': True,
        'retried_task': task_id,
        'retry_time': taipei_now.isoformat(),
        'retry_attempt': task_instance.try_number
    }
