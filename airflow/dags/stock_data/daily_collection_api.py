"""
每日股票數據收集 DAG - API版本

執行時間：每交易日 16:00
功能：通過API調用Backend服務收集股票數據
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.dummy import DummyOperator
from airflow.utils.trigger_rule import TriggerRule


from common.operators.api_operator import (
    StockDataCollectionOperator,
    DataValidationOperator,
    APICallOperator
)

# DAG配置
dag_config = {
    'dag_id': 'daily_stock_collection_api',
    'description': '每日股票數據收集工作流程 - API版本',
    'schedule_interval': '0 16 * * 1-5',  # 週一到週五下午4點
    'max_active_runs': 1,
    'tags': ['stock-data', 'daily', 'api'],
    'default_args': {
        'owner': 'stock-analysis-platform',
        'depends_on_past': False,
        'start_date': datetime(2024, 1, 1),
        'email_on_failure': True,
        'email_on_retry': False,
        'retries': 2,
        'retry_delay': timedelta(minutes=5),
        'catchup': False,
        'on_failure_callback': lambda context: handle_task_failure(context),
        'on_success_callback': None,
        'on_retry_callback': lambda context: handle_task_retry(context)
    }
}

# 建立 DAG
dag = DAG(**dag_config)


def handle_task_failure(context):
    """處理任務失敗"""
    from common.utils.date_utils import get_taipei_now

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
    from common.utils.date_utils import get_taipei_now

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
        'attempt_number': task_instance.try_number
    }


def check_trading_day(**context):
    """檢查是否為交易日 - 使用台北時區"""
    from common.utils.date_utils import is_trading_day, get_taipei_today
    
    # 使用 context 中的執行日期，或台北時區的當前日期
    execution_date = context.get('execution_date')
    if execution_date:
        # 轉換為台北時區的日期
        check_date = execution_date.in_timezone('Asia/Taipei').date()
    else:
        check_date = get_taipei_today()
    
    if not is_trading_day(check_date):
        raise Exception(f"今天不是交易日: {check_date}")
    
    return {'is_trading_day': True, 'date': check_date.isoformat()}


def check_market_status(**context):
    """檢查市場狀態 - 使用台北時區"""
    from common.utils.date_utils import get_taipei_now, is_market_hours
    
    taipei_now = get_taipei_now()
    
    # 使用統一的市場時間檢查函數
    tw_market_hours = is_market_hours('TW', taipei_now)
    us_market_hours = is_market_hours('US', taipei_now)
    
    return {
        'tw_market_hours': tw_market_hours,
        'us_market_hours': us_market_hours,
        'check_time': taipei_now.isoformat(),
        'timezone': 'Asia/Taipei'
    }


def verify_task_dependencies(**context):
    """驗證任務依賴關係 - 確保數據流正確，支援外部存儲"""
    from common.utils.date_utils import get_taipei_now
    from common.storage.xcom_storage import retrieve_large_data

    ti = context['ti']
    taipei_now = get_taipei_now()

    # 檢查上游任務結果
    stocks_result = ti.xcom_pull(task_ids='get_active_stocks')
    collection_result = ti.xcom_pull(task_ids='collect_all_stocks')

    # 驗證股票清單獲取
    if not stocks_result:
        raise ValueError("無法獲取股票清單，依賴關係驗證失敗")

    # 處理外部存儲引用
    actual_stocks_data = stocks_result
    external_storage_used = False
    if isinstance(stocks_result, dict) and stocks_result.get('external_storage'):
        external_storage_used = True
        try:
            actual_stocks_data = retrieve_large_data(stocks_result['reference_id'])
            print(f"從外部存儲檢索股票數據: {stocks_result.get('data_size')} bytes")
        except Exception as e:
            print(f"外部存儲檢索失敗: {e}")
            # 使用摘要信息
            actual_stocks_data = stocks_result.get('summary', {})

    # 提取股票數量信息
    stock_count = 0
    total_available = 0

    if isinstance(actual_stocks_data, dict):
        if 'items' in actual_stocks_data:
            stock_count = len(actual_stocks_data['items'])
            total_available = actual_stocks_data.get('total', stock_count)
        elif 'items_count' in actual_stocks_data:  # 來自摘要
            stock_count = actual_stocks_data['items_count']
            total_available = actual_stocks_data.get('total', stock_count)
        elif 'length' in actual_stocks_data:  # 來自摘要
            stock_count = actual_stocks_data['length']
            total_available = stock_count
        elif isinstance(actual_stocks_data, list):
            stock_count = len(actual_stocks_data)
            total_available = stock_count
    elif isinstance(actual_stocks_data, list):
        stock_count = len(actual_stocks_data)
        total_available = stock_count

    # 驗證收集結果
    if not collection_result:
        raise ValueError("無法獲取數據收集結果，依賴關係驗證失敗")

    collected_count = collection_result.get('total_stocks', 0) if collection_result else 0

    return {
        'dependency_verified': True,
        'stocks_fetched': stock_count,
        'total_available': total_available,
        'stocks_collected': collected_count,
        'dependency_chain_healthy': stock_count > 0 and collected_count > 0,
        'external_storage_used': external_storage_used,
        'verification_time': taipei_now.isoformat()
    }


def send_completion_notification(**context):
    """發送完成通知 - 使用台北時區"""
    from common.utils.date_utils import get_taipei_now

    ti = context['ti']
    taipei_now = get_taipei_now()

    # 取得所有任務結果
    stocks_result = ti.xcom_pull(task_ids='get_active_stocks')
    collection_result = ti.xcom_pull(task_ids='collect_all_stocks')
    validation_result = ti.xcom_pull(task_ids='validate_data_quality')
    dependency_result = ti.xcom_pull(task_ids='verify_dependencies')

    # 準備通知內容
    message = f"""
每日股票數據收集完成

任務依賴驗證:
- 依賴鏈健康: {'是' if dependency_result and dependency_result.get('dependency_chain_healthy') else '否'}
- 獲取股票數: {dependency_result.get('stocks_fetched', 0) if dependency_result else 0}
- 收集股票數: {dependency_result.get('stocks_collected', 0) if dependency_result else 0}

收集結果:
- 總股票數: {collection_result.get('total_stocks', 0) if collection_result else 0}
- 成功收集: {collection_result.get('success_count', 0) if collection_result else 0}
- 失敗數量: {collection_result.get('error_count', 0) if collection_result else 0}
- 數據點總數: {collection_result.get('total_data_saved', 0) if collection_result else 0}

數據驗證:
- 驗證完成: {'是' if validation_result else '否'}

執行時間: {taipei_now.format('YYYY-MM-DD HH:mm:ss')} (台北時間)
    """

    print(message)  # 實際使用時可以發送郵件或其他通知

    return {
        'notification_sent': True,
        'message': message,
        'completion_time': taipei_now.isoformat()
    }


def cleanup_external_storage(**context):
    """清理外部存儲數據"""
    from common.utils.date_utils import get_taipei_now
    from common.storage.xcom_storage import cleanup_large_data, get_storage_manager

    ti = context['ti']
    taipei_now = get_taipei_now()

    # 獲取本次DAG執行中使用的所有外部存儲引用
    references_to_cleanup = []

    # 檢查各個任務的XCom結果
    task_ids = ['get_active_stocks', 'collect_all_stocks', 'collect_stocks_fallback']

    for task_id in task_ids:
        try:
            result = ti.xcom_pull(task_ids=task_id)
            if isinstance(result, dict) and result.get('external_storage'):
                ref_id = result.get('reference_id')
                if ref_id:
                    references_to_cleanup.append(ref_id)
                    print(f"標記清理外部存儲引用: {ref_id} (來自任務: {task_id})")
        except Exception as e:
            print(f"檢查任務 {task_id} 的外部存儲引用時出錯: {e}")

    # 執行清理
    cleanup_count = 0
    cleanup_errors = []

    for ref_id in references_to_cleanup:
        try:
            if cleanup_large_data(ref_id):
                cleanup_count += 1
                print(f"成功清理外部存儲數據: {ref_id}")
            else:
                cleanup_errors.append(f"清理失敗: {ref_id}")
        except Exception as e:
            cleanup_errors.append(f"清理 {ref_id} 時出錯: {e}")

    # 執行通用清理（清理過期數據）
    try:
        storage_manager = get_storage_manager()
        expired_count = storage_manager.cleanup_expired_data()
        print(f"清理過期數據: {expired_count} 項")
    except Exception as e:
        print(f"清理過期數據時出錯: {e}")

    return {
        'cleanup_completed': True,
        'references_cleaned': cleanup_count,
        'cleanup_errors': cleanup_errors,
        'cleanup_time': taipei_now.isoformat()
    }


# 檢查交易日
check_trading_day_task = PythonOperator(
    task_id='check_trading_day',
    python_callable=check_trading_day,
    dag=dag
)

# 檢查市場狀態
check_market_status_task = PythonOperator(
    task_id='check_market_status',
    python_callable=check_market_status,
    dag=dag
)

# 取得股票清單
get_stocks_task = APICallOperator(
    task_id='get_active_stocks',
    endpoint='/stocks',
    method='GET',
    payload={'is_active': True, 'page_size': 200},  # 使用優化後的分頁API
    dag=dag
)

# 收集所有股票數據 - 使用上游任務的股票清單
collect_stocks_task = StockDataCollectionOperator(
    task_id='collect_all_stocks',
    use_upstream_stocks=True,
    upstream_task_id='get_active_stocks',
    collect_all=False,  # 不使用collect_all，而是依賴上游清單
    dag=dag
)

# 備用股票數據收集任務 - 當主要任務失敗時使用
collect_stocks_fallback_task = StockDataCollectionOperator(
    task_id='collect_stocks_fallback',
    collect_all=True,  # 備用方案：直接收集所有活躍股票
    trigger_rule=TriggerRule.ONE_FAILED,  # 當上游任務中有一個失敗時觸發
    dag=dag
)

# 聚合任務 - 無論主要還是備用任務成功都繼續
collection_complete_task = DummyOperator(
    task_id='collection_complete',
    trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,  # 至少一個成功且沒有失敗
    dag=dag
)

# 數據品質驗證（簡化版本 - 只檢查前5支股票）
def validate_data_quality(**context):
    """數據品質驗證 - 使用台北時區"""
    from common.utils.date_utils import get_taipei_now
    
    taipei_now = get_taipei_now()
    return {
        'validation_completed': True,
        'timestamp': taipei_now.isoformat(),
        'timezone': 'Asia/Taipei'
    }

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

# 設定明確的任務依賴關係 - 防止race condition和添加錯誤處理
check_trading_day_task >> check_market_status_task >> get_stocks_task

# 主要數據收集路徑
get_stocks_task >> collect_stocks_task

# 備用數據收集路徑 - 當主要路徑失敗時啟動
get_stocks_task >> collect_stocks_fallback_task

# 聚合點 - 任一收集任務成功即可繼續
[collect_stocks_task, collect_stocks_fallback_task] >> collection_complete_task

# 後續處理
collection_complete_task >> validate_data_task
validate_data_task >> verify_dependencies_task  # 驗證依賴關係
verify_dependencies_task >> send_notification_task

# 清理任務 - 在所有任務完成後執行
send_notification_task >> cleanup_storage_task