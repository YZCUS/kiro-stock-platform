"""
Airflow DAG 驗證器模塊

處理交易日檢查、市場狀態驗證、任務依賴驗證和數據品質驗證
"""


def _get_trading_day_status(market, session_date):
    """Ask the backend calendar so Airflow and validation use one rule set."""
    import os
    import requests

    backend_url = os.getenv("BACKEND_API_URL", "http://backend:8000/api/v1")
    internal_token = os.getenv("INTERNAL_API_TOKEN", "dev-internal-token")
    response = requests.get(
        f"{backend_url.rstrip('/')}/stocks/market-data/trading-day",
        params={"market": market, "session_date": session_date.isoformat()},
        headers={"X-Internal-Token": internal_token},
        timeout=10,
    )
    response.raise_for_status()
    result = response.json()
    if "is_trading_day" not in result or "previous_trading_day" not in result:
        raise ValueError(f"Invalid trading-day response: {result}")
    return result


def check_trading_day_tw(**context):
    """檢查是否為台股交易日 - 使用台北時區，返回分支決策而不拋出異常

    邏輯：
    1. 如果今天是交易日 → 執行數據收集
    2. 如果今天不是交易日 → 檢查最近交易日的數據是否存在
       - 如果數據不存在 → 補抓最近交易日的數據
       - 如果數據存在 → 跳過收集
    """
    from datetime import date
    from plugins.common.date_utils import context_interval_date
    import os
    import requests

    check_date = context_interval_date(context, "Asia/Taipei")

    trading_status = _get_trading_day_status("TW", check_date)
    trading_day = bool(trading_status["is_trading_day"])

    # 將結果推送到 XCom 供後續任務使用
    context["ti"].xcom_push(key="is_trading_day", value=trading_day)
    context["ti"].xcom_push(key="check_date", value=check_date.isoformat())
    context["ti"].xcom_push(key="market", value="TW")

    if trading_day:
        print(f"✓ 今天是台股交易日: {check_date}，繼續執行數據收集")
        return "check_market_status"  # 繼續下一步
    else:
        # 今天不是交易日，檢查最近交易日的數據
        last_trading_day = date.fromisoformat(trading_status["previous_trading_day"])
        print(f"✗ 今天不是台股交易日: {check_date}")
        print(f"ℹ 最近的交易日: {last_trading_day}")

        # 檢查最近交易日的數據是否存在
        try:
            backend_url = os.getenv("BACKEND_API_URL", "http://backend:8000/api/v1")

            # 查詢是否有該日期的台股價格數據
            response = requests.get(
                f"{backend_url}/stocks/prices/data-exists",
                params={
                    "date": last_trading_day.isoformat(),
                    "market": "TW",
                    "min_coverage": 0.9,
                },
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                has_data = data.get("has_data", False)
                stock_count = data.get("stock_count", 0)

                if has_data and stock_count > 0:
                    print(
                        f"✓ 最近交易日 {last_trading_day} 已有 {stock_count} 筆台股價格數據，跳過收集"
                    )
                    return "skip_collection"
                else:
                    print(f"✗ 最近交易日 {last_trading_day} 沒有台股價格數據，需要補抓")
                    # 將最近交易日推送到 XCom，供收集任務使用
                    context["ti"].xcom_push(
                        key="collection_date", value=last_trading_day.isoformat()
                    )
                    return "check_market_status"  # 執行數據收集
            else:
                print(
                    f"⚠ 無法檢查數據狀態 (HTTP {response.status_code})，為安全起見執行數據收集"
                )
                context["ti"].xcom_push(
                    key="collection_date", value=last_trading_day.isoformat()
                )
                return "check_market_status"

        except Exception as e:
            print(f"⚠ 檢查數據時發生錯誤: {e}，為安全起見執行數據收集")
            context["ti"].xcom_push(
                key="collection_date", value=last_trading_day.isoformat()
            )
            return "check_market_status"


def check_trading_day_us(**context):
    """檢查是否為美股交易日 - 使用美東時區，返回分支決策而不拋出異常

    邏輯：
    1. 如果今天是美股交易日 → 執行數據收集
    2. 如果今天不是交易日 → 檢查最近交易日的數據是否存在
       - 如果數據不存在 → 補抓最近交易日的數據
       - 如果數據存在 → 跳過收集

    注意：美股交易日檢查使用美東時區，週一到週五為交易日（不含美國聯邦假日）
    """
    from datetime import date
    from plugins.common.date_utils import context_interval_date
    import os
    import requests

    us_check_date = context_interval_date(context, "America/New_York")

    trading_status = _get_trading_day_status("US", us_check_date)
    is_weekday = bool(trading_status["is_trading_day"])

    # 將結果推送到 XCom 供後續任務使用
    context["ti"].xcom_push(key="is_trading_day", value=is_weekday)
    context["ti"].xcom_push(key="check_date", value=us_check_date.isoformat())
    context["ti"].xcom_push(key="market", value="US")

    if is_weekday:
        print(f"✓ 美東 {us_check_date} 是美股交易日，繼續執行數據收集")
        return "check_market_status"  # 繼續下一步
    else:
        # 今天不是交易日，檢查最近交易日的數據
        last_us_trading_day = date.fromisoformat(trading_status["previous_trading_day"])

        print(f"✗ 美東 {us_check_date} 不是美股交易日")
        print(f"ℹ 最近的美股交易日: {last_us_trading_day}")

        # 檢查最近交易日的數據是否存在
        try:
            backend_url = os.getenv("BACKEND_API_URL", "http://backend:8000/api/v1")

            # 查詢是否有該日期的美股價格數據
            response = requests.get(
                f"{backend_url}/stocks/prices/data-exists",
                params={
                    "date": last_us_trading_day.isoformat(),
                    "market": "US",
                    "min_coverage": 0.9,
                },
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                has_data = data.get("has_data", False)
                stock_count = data.get("stock_count", 0)

                if has_data and stock_count > 0:
                    print(
                        f"✓ 最近交易日 {last_us_trading_day} 已有 {stock_count} 筆美股價格數據，跳過收集"
                    )
                    return "skip_collection"
                else:
                    print(
                        f"✗ 最近交易日 {last_us_trading_day} 沒有美股價格數據，需要補抓"
                    )
                    # 將最近交易日推送到 XCom，供收集任務使用
                    context["ti"].xcom_push(
                        key="collection_date", value=last_us_trading_day.isoformat()
                    )
                    return "check_market_status"  # 執行數據收集
            else:
                print(
                    f"⚠ 無法檢查數據狀態 (HTTP {response.status_code})，為安全起見執行數據收集"
                )
                context["ti"].xcom_push(
                    key="collection_date", value=last_us_trading_day.isoformat()
                )
                return "check_market_status"

        except Exception as e:
            print(f"⚠ 檢查數據時發生錯誤: {e}，為安全起見執行數據收集")
            context["ti"].xcom_push(
                key="collection_date", value=last_us_trading_day.isoformat()
            )
            return "check_market_status"


def check_trading_day(**context):
    """檢查是否為交易日 - 使用台北時區，返回分支決策而不拋出異常

    邏輯：
    1. 如果今天是交易日 → 執行數據收集
    2. 如果今天不是交易日 → 檢查最近交易日的數據是否存在
       - 如果數據不存在 → 補抓最近交易日的數據
       - 如果數據存在 → 跳過收集
    """
    from plugins.common.date_utils import (
        context_interval_date,
        get_last_trading_day,
        is_trading_day,
    )
    import os
    import requests

    check_date = context_interval_date(context, "Asia/Taipei")

    trading_day = is_trading_day(check_date)

    # 將結果推送到 XCom 供後續任務使用
    context["ti"].xcom_push(key="is_trading_day", value=trading_day)
    context["ti"].xcom_push(key="check_date", value=check_date.isoformat())

    if trading_day:
        print(f"✓ 今天是交易日: {check_date}，繼續執行數據收集")
        return "check_market_status"  # 繼續下一步
    else:
        # 今天不是交易日，檢查最近交易日的數據
        last_trading_day = get_last_trading_day(check_date)
        print(f"✗ 今天不是交易日: {check_date}")
        print(f"ℹ 最近的交易日: {last_trading_day}")

        # 檢查最近交易日的數據是否存在
        try:
            backend_url = os.getenv("BACKEND_API_URL", "http://backend:8000/api/v1")

            # 查詢是否有該日期的價格數據
            response = requests.get(
                f"{backend_url}/stocks/prices/data-exists",
                params={"date": last_trading_day.isoformat()},
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                has_data = data.get("has_data", False)
                stock_count = data.get("stock_count", 0)

                if has_data and stock_count > 0:
                    print(
                        f"✓ 最近交易日 {last_trading_day} 已有 {stock_count} 筆價格數據，跳過收集"
                    )
                    return "skip_collection"
                else:
                    print(f"✗ 最近交易日 {last_trading_day} 沒有價格數據，需要補抓")
                    # 將最近交易日推送到 XCom，供收集任務使用
                    context["ti"].xcom_push(
                        key="collection_date", value=last_trading_day.isoformat()
                    )
                    return "check_market_status"  # 執行數據收集
            else:
                print(
                    f"⚠ 無法檢查數據狀態 (HTTP {response.status_code})，為安全起見執行數據收集"
                )
                context["ti"].xcom_push(
                    key="collection_date", value=last_trading_day.isoformat()
                )
                return "check_market_status"

        except Exception as e:
            print(f"⚠ 檢查數據時發生錯誤: {e}，為安全起見執行數據收集")
            context["ti"].xcom_push(
                key="collection_date", value=last_trading_day.isoformat()
            )
            return "check_market_status"


def check_market_status(**context):
    """檢查市場狀態 - 使用台北時區"""
    from plugins.common.date_utils import get_taipei_now, is_market_hours

    taipei_now = get_taipei_now()

    # 使用統一的市場時間檢查函數
    tw_market_hours = is_market_hours("TW", taipei_now)
    us_market_hours = is_market_hours("US", taipei_now)

    return {
        "tw_market_hours": tw_market_hours,
        "us_market_hours": us_market_hours,
        "check_time": taipei_now.isoformat(),
        "timezone": "Asia/Taipei",
    }


def verify_task_dependencies(**context):
    """驗證任務依賴關係 - 確保數據流正確，支援外部存儲"""
    from plugins.common.date_utils import get_taipei_now
    from plugins.services.storage_service import retrieve_large_data

    ti = context["ti"]
    taipei_now = get_taipei_now()

    # 檢查收集任務結果
    main_result = ti.xcom_pull(task_ids="try_main_collection")
    fallback_result = ti.xcom_pull(task_ids="execute_fallback_collection")

    # 確定使用的收集策略和結果
    if main_result and main_result.get("status") == "success":
        active_collection_result = main_result
        collection_source = "main"
        print("使用主要收集任務結果進行驗證")
    elif fallback_result and fallback_result.get("status") == "success":
        active_collection_result = fallback_result
        collection_source = "fallback"
        print("使用備援收集任務結果進行驗證")
    else:
        raise ValueError(
            "無法獲取數據收集結果（主要和備援策略都失敗），依賴關係驗證失敗"
        )

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
        stock_count = active_collection_result.get("stocks_fetched", 0)
        collected_count = active_collection_result.get("total_stocks", 0)
        api_success = active_collection_result.get("api_success", False)
        error_count = active_collection_result.get("error_count", 0)
        success_count = active_collection_result.get("success_count", 0)
        total_available = stock_count
        print(
            f"主要策略驗證: 獲取 {stock_count} 支股票，收集 {collected_count} 支，API成功: {api_success}，錯誤: {error_count}，成功: {success_count}"
        )
    elif collection_source == "fallback":
        # 備援策略使用 collect_all，包含完整的錯誤統計
        collected_count = active_collection_result.get("total_stocks", 0)
        api_success = active_collection_result.get("api_success", False)
        error_count = active_collection_result.get("error_count", 0)
        success_count = active_collection_result.get("success_count", 0)
        stock_count = collected_count  # 備援策略中，獲取的就是收集的
        total_available = collected_count
        print(
            f"備援策略驗證: 收集 {collected_count} 支股票，API成功: {api_success}，錯誤: {error_count}，成功: {success_count}"
        )

    # 嚴格的依賴鏈健康檢查：必須有數據且API成功且無錯誤
    basic_health = stock_count > 0 and collected_count > 0
    api_health = api_success and error_count == 0
    dependency_chain_healthy = basic_health and api_health

    # 如果有錯誤，記錄詳細信息以便排查
    if error_count > 0:
        print(f"警告: 收集過程中發現 {error_count} 個錯誤，依賴鏈標記為不健康")
        print(
            f"成功率: {success_count}/{collected_count} = {(success_count/collected_count*100) if collected_count > 0 else 0:.1f}%"
        )

    # 設置外部存儲相關變數（新架構下可能不使用，但保持兼容）
    external_storage_used = False

    result = {
        "dependency_verified": dependency_chain_healthy,
        "stocks_fetched": stock_count,
        "total_available": total_available,
        "stocks_collected": collected_count,
        "dependency_chain_healthy": dependency_chain_healthy,
        "api_success": api_success,
        "error_count": error_count,
        "success_count": success_count,
        "success_rate": (
            (success_count / collected_count * 100) if collected_count > 0 else 0
        ),
        "external_storage_used": external_storage_used,
        "verification_time": taipei_now.isoformat(),
    }
    if not dependency_chain_healthy:
        raise ValueError(
            "Collection dependency chain is unhealthy: "
            f"api_success={api_success}, collected={collected_count}, "
            f"errors={error_count}"
        )
    return result


def validate_data_quality(**context):
    """Fail the DAG unless the canonical market-data pipeline is complete."""
    from plugins.common.date_utils import get_taipei_now
    from plugins.services.storage_service import retrieve_large_data

    taipei_now = get_taipei_now()
    pipeline_result = context["ti"].xcom_pull(task_ids="run_market_data_pipeline")
    if isinstance(pipeline_result, dict) and pipeline_result.get("external_storage"):
        pipeline_result = retrieve_large_data(pipeline_result["reference_id"])
    if not isinstance(pipeline_result, dict):
        raise ValueError("Market-data pipeline returned no validation result")

    reports = pipeline_result.get("reports") or []
    incomplete = [report for report in reports if not report.get("is_complete", False)]
    if (
        not pipeline_result.get("success", False)
        or not pipeline_result.get("validation_success", False)
        or not reports
        or incomplete
    ):
        raise ValueError(
            "Market-data quality validation failed: "
            f"success={pipeline_result.get('success')}, "
            f"reports={len(reports)}, incomplete={len(incomplete)}"
        )
    return {
        "validation_completed": True,
        "reports_checked": len(reports),
        "incomplete_reports": 0,
        "timestamp": taipei_now.isoformat(),
        "timezone": "Asia/Taipei",
    }
