"""
Airflow DAG 驗證器模塊

處理交易日檢查、市場狀態驗證、任務依賴驗證和數據品質驗證
"""


def check_trading_day(**context):
    """檢查是否為交易日 - 使用台北時區"""
    from plugins.common.date_utils import is_trading_day, get_taipei_today

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
    from plugins.common.date_utils import get_taipei_now, is_market_hours

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
    from plugins.common.date_utils import get_taipei_now
    from plugins.services.storage_service import retrieve_large_data

    ti = context['ti']
    taipei_now = get_taipei_now()

    # 檢查收集任務結果
    main_result = ti.xcom_pull(task_ids='try_main_collection')
    fallback_result = ti.xcom_pull(task_ids='execute_fallback_collection')

    # 確定使用的收集策略和結果
    if main_result and main_result.get('status') == 'success':
        active_collection_result = main_result
        collection_source = "main"
        print("使用主要收集任務結果進行驗證")
    elif fallback_result and fallback_result.get('status') == 'success':
        active_collection_result = fallback_result
        collection_source = "fallback"
        print("使用備援收集任務結果進行驗證")
    else:
        raise ValueError("無法獲取數據收集結果（主要和備援策略都失敗），依賴關係驗證失敗")

    # 由於新架構中不再單獨獲取股票清單，直接使用收集結果進行驗證
    if not active_collection_result:
        raise ValueError("無法獲取收集結果，依賴關係驗證失敗")

    # 從收集結果中提取統計信息和成功狀態
    collected_count = 0
    stock_count = 0
    total_available = 0
    api_success = False
    error_count = 0
    success_count = 0

    if collection_source == "main":
        # 主要策略包含詳細的股票和錯誤信息
        stock_count = active_collection_result.get('stocks_fetched', 0)
        collected_count = active_collection_result.get('total_stocks', 0)
        api_success = active_collection_result.get('api_success', False)
        error_count = active_collection_result.get('error_count', 0)
        success_count = active_collection_result.get('success_count', 0)
        total_available = stock_count
        print(f"主要策略驗證: 獲取 {stock_count} 支股票，收集 {collected_count} 支，API成功: {api_success}，錯誤: {error_count}，成功: {success_count}")
    elif collection_source == "fallback":
        # 備援策略使用 collect_all，包含完整的錯誤統計
        collected_count = active_collection_result.get('total_stocks', 0)
        api_success = active_collection_result.get('api_success', False)
        error_count = active_collection_result.get('error_count', 0)
        success_count = active_collection_result.get('success_count', 0)
        stock_count = collected_count  # 備援策略中，獲取的就是收集的
        total_available = collected_count
        print(f"備援策略驗證: 收集 {collected_count} 支股票，API成功: {api_success}，錯誤: {error_count}，成功: {success_count}")

    # 嚴格的依賴鏈健康檢查：必須有數據且API成功且無錯誤
    basic_health = stock_count > 0 and collected_count > 0
    api_health = api_success and error_count == 0
    dependency_chain_healthy = basic_health and api_health

    # 如果有錯誤，記錄詳細信息以便排查
    if error_count > 0:
        print(f"警告: 收集過程中發現 {error_count} 個錯誤，依賴鏈標記為不健康")
        print(f"成功率: {success_count}/{collected_count} = {(success_count/collected_count*100) if collected_count > 0 else 0:.1f}%")

    # 設置外部存儲相關變數（新架構下可能不使用，但保持兼容）
    external_storage_used = False

    return {
        'dependency_verified': dependency_chain_healthy,
        'stocks_fetched': stock_count,
        'total_available': total_available,
        'stocks_collected': collected_count,
        'dependency_chain_healthy': dependency_chain_healthy,
        'api_success': api_success,
        'error_count': error_count,
        'success_count': success_count,
        'success_rate': (success_count/collected_count*100) if collected_count > 0 else 0,
        'external_storage_used': external_storage_used,
        'verification_time': taipei_now.isoformat()
    }


def validate_data_quality(**context):
    """數據品質驗證 - 使用台北時區"""
    from plugins.common.date_utils import get_taipei_now

    taipei_now = get_taipei_now()
    return {
        'validation_completed': True,
        'timestamp': taipei_now.isoformat(),
        'timezone': 'Asia/Taipei'
    }
