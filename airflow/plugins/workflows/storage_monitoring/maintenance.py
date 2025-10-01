"""
Storage monitoring 維護任務模塊
"""


def storage_maintenance(**context):
    """執行存儲維護任務"""
    from plugins.common.date_utils import get_taipei_now
    from plugins.services.monitoring_service import run_maintenance

    try:
        taipei_now = get_taipei_now()
        print(f"開始存儲維護任務 - {taipei_now.format('YYYY-MM-DD HH:mm:ss')} (台北時間)")

        # 執行維護
        maintenance_result = run_maintenance()

        # 記錄結果
        print(f"維護任務完成:")
        print(f"  - 完成任務: {maintenance_result['summary'].get('total_tasks', 0)}")
        print(f"  - 失敗任務: {maintenance_result['summary'].get('failed_tasks', 0)}")
        print(f"  - 清理過期項目: {maintenance_result['summary'].get('expired_items_cleaned', 0)}")
        print(f"  - 清理指標數據: {maintenance_result['summary'].get('metrics_cleaned', 0)}")
        print(f"  - 整體健康: {'是' if maintenance_result['summary'].get('overall_health') else '否'}")

        if maintenance_result['tasks_failed']:
            print(f"失敗的任務:")
            for failed_task in maintenance_result['tasks_failed']:
                print(f"  - {failed_task['task']}: {failed_task.get('error', 'Unknown error')}")

        return maintenance_result

    except Exception as e:
        print(f"存儲維護失敗: {e}")
        raise
