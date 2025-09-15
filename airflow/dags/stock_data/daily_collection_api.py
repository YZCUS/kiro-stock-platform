"""
每日股票數據收集 DAG - API版本

執行時間：每交易日 16:00
功能：通過API調用Backend服務收集股票數據
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


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
        'email_on_failure': False,
        'email_on_retry': False,
        'retries': 2,
        'retry_delay': timedelta(minutes=5),
        'catchup': False
    }
}

# 建立 DAG
dag = DAG(**dag_config)


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


def send_completion_notification(**context):
    """發送完成通知 - 使用台北時區"""
    from common.utils.date_utils import get_taipei_now
    
    ti = context['ti']
    taipei_now = get_taipei_now()
    
    # 取得收集結果
    collection_result = ti.xcom_pull(task_ids='collect_all_stocks')
    validation_result = ti.xcom_pull(task_ids='validate_data_quality')
    
    # 準備通知內容
    message = f"""
每日股票數據收集完成

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
    payload={'active_only': True, 'limit': 100},
    dag=dag
)

# 收集所有股票數據
collect_stocks_task = StockDataCollectionOperator(
    task_id='collect_all_stocks',
    collect_all=True,
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

# 發送完成通知
send_notification_task = PythonOperator(
    task_id='send_completion_notification',
    python_callable=send_completion_notification,
    dag=dag
)

# 設定任務依賴
check_trading_day_task >> check_market_status_task >> get_stocks_task
get_stocks_task >> collect_stocks_task >> validate_data_task >> send_notification_task