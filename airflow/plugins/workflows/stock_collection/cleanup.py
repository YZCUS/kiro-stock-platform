"""
Airflow DAG 清理模塊

處理外部存儲數據清理
"""


def cleanup_external_storage(**context):
    """清理外部存儲數據"""
    from plugins.common.date_utils import get_taipei_now
    from plugins.services.storage_service import cleanup_large_data, get_storage_manager

    ti = context['ti']
    taipei_now = get_taipei_now()

    # 獲取本次DAG執行中使用的所有外部存儲引用
    references_to_cleanup = []

    # 檢查各個任務的XCom結果，但只處理實際執行成功的任務
    task_ids = ['try_main_collection', 'execute_fallback_collection']

    for task_id in task_ids:
        try:
            # 獲取任務實例以檢查執行狀態
            dag_run = context.get('dag_run')
            if not dag_run:
                print(f"無法獲取 DAG run 信息，跳過任務 {task_id}")
                continue

            task_instance = dag_run.get_task_instance(task_id)
            if not task_instance:
                print(f"無法獲取任務實例 {task_id}")
                continue

            # 只處理成功執行的任務，跳過 skipped、failed 或其他狀態
            task_state = task_instance.state
            print(f"任務 {task_id} 狀態: {task_state}")

            if task_state != 'success':
                print(f"跳過任務 {task_id}（狀態: {task_state}），不進行外部存儲清理")
                continue

            # 拉取當前執行的 XCom 數據，不包含歷史數據
            result = ti.xcom_pull(task_ids=task_id, include_prior_dates=False)

            if not result:
                print(f"任務 {task_id} 無 XCom 數據")
                continue

            if not isinstance(result, dict):
                print(f"任務 {task_id} XCom 數據格式無效: {type(result)}")
                continue

            print(f"處理任務 {task_id} 的外部存儲引用")

            # 檢查任務結果是否包含外部存儲引用
            if result.get('external_storage'):
                ref_id = result.get('reference_id')
                if ref_id:
                    references_to_cleanup.append(ref_id)
                    print(f"標記清理外部存儲引用: {ref_id} (來自任務: {task_id})")

            # 檢查嵌套的 original_result 中的外部存儲引用
            original_result = result.get('original_result')
            if isinstance(original_result, dict) and original_result.get('external_storage'):
                ref_id = original_result.get('reference_id')
                if ref_id:
                    references_to_cleanup.append(ref_id)
                    print(f"標記清理外部存儲引用: {ref_id} (來自任務: {task_id} 的原始結果)")

        except Exception as e:
            print(f"檢查任務 {task_id} 的外部存儲引用時出錯: {e}")
            # 繼續處理其他任務，不讓單個任務的錯誤影響整體清理

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
