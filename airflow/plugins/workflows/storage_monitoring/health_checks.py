"""
Storage monitoring 健康檢查模塊
"""


def storage_health_check(**context):
    """執行存儲健康檢查"""
    from plugins.common.date_utils import get_taipei_now
    from plugins.services.monitoring_service import run_health_check, get_notification_manager
    from plugins.services.notification_service import NotificationLevel

    try:
        taipei_now = get_taipei_now()
        print(f"開始存儲健康檢查 - {taipei_now.format('YYYY-MM-DD HH:mm:ss')} (台北時間)")

        # 執行健康檢查
        health_report = run_health_check()

        # 記錄結果
        print(f"健康檢查完成:")
        print(f"  - 整體狀態: {'健康' if health_report.is_healthy else '有問題'}")
        print(f"  - 存儲項目: {health_report.total_items}")
        print(f"  - 總大小: {health_report.total_size_mb} MB")
        print(f"  - Redis連接: {'正常' if health_report.redis_connected else '異常'}")
        print(f"  - 連續失敗: {health_report.consecutive_failures}")
        print(f"  - 響應時間: {health_report.response_time_ms:.2f} ms")

        if health_report.issues:
            print(f"  - 發現問題: {len(health_report.issues)}")
            for issue in health_report.issues:
                print(f"    * {issue}")

        if health_report.recommendations:
            print(f"  - 建議: {len(health_report.recommendations)}")
            for rec in health_report.recommendations:
                print(f"    * {rec}")

        # 發送警報（如果需要）
        if not health_report.is_healthy:
            notification_manager = get_notification_manager()
            if notification_manager:
                notification_manager.send_notification(
                    message=f"Storage health check detected {len(health_report.issues)} issues",
                    level=NotificationLevel.WARNING,
                    title="Storage Health Alert",
                    context={
                        'issues_count': len(health_report.issues),
                        'total_items': health_report.total_items,
                        'total_size_mb': health_report.total_size_mb,
                        'consecutive_failures': health_report.consecutive_failures
                    }
                )

        return {
            'health_status': 'healthy' if health_report.is_healthy else 'issues_detected',
            'total_items': health_report.total_items,
            'total_size_mb': health_report.total_size_mb,
            'redis_connected': health_report.redis_connected,
            'issues_count': len(health_report.issues),
            'check_timestamp': health_report.timestamp
        }

    except Exception as e:
        print(f"健康檢查失敗: {e}")

        # 發送失敗通知
        try:
            notification_manager = get_notification_manager()
            if notification_manager:
                notification_manager.send_notification(
                    message=f"Storage health check failed: {str(e)}",
                    level=NotificationLevel.ERROR,
                    title="Storage Health Check Failed",
                    context={'error': str(e)}
                )
        except Exception as notify_error:
            print(f"發送健康檢查失敗通知失敗: {notify_error}")

        raise


def check_storage_capacity(**context):
    """檢查存儲容量並發送警報"""
    from plugins.common.date_utils import get_taipei_now
    from plugins.services.monitoring_service import get_storage_dashboard, get_notification_manager
    from plugins.services.notification_service import NotificationLevel

    try:
        taipei_now = get_taipei_now()
        dashboard = get_storage_dashboard()

        # 獲取存儲統計
        storage_stats = dashboard.storage_manager.get_storage_stats()
        total_size_mb = storage_stats.get('total_size_mb', 0)
        total_items = storage_stats.get('total_items', 0)

        # 檢查容量閾值
        warning_threshold = dashboard.size_warning_threshold_mb
        critical_threshold = dashboard.size_critical_threshold_mb

        capacity_status = 'normal'
        if total_size_mb > critical_threshold:
            capacity_status = 'critical'
        elif total_size_mb > warning_threshold:
            capacity_status = 'warning'

        print(f"存儲容量檢查:")
        print(f"  - 當前大小: {total_size_mb} MB")
        print(f"  - 項目數量: {total_items}")
        print(f"  - 警告閾值: {warning_threshold} MB")
        print(f"  - 嚴重閾值: {critical_threshold} MB")
        print(f"  - 狀態: {capacity_status}")

        # 發送容量警報
        if capacity_status != 'normal':
            notification_manager = get_notification_manager()
            if notification_manager:
                level = NotificationLevel.CRITICAL if capacity_status == 'critical' else NotificationLevel.WARNING

                notification_manager.send_notification(
                    message=f"Storage capacity {capacity_status}: {total_size_mb} MB ({total_items} items)",
                    level=level,
                    title=f"Storage Capacity {capacity_status.title()} Alert",
                    context={
                        'current_size_mb': total_size_mb,
                        'total_items': total_items,
                        'warning_threshold_mb': warning_threshold,
                        'critical_threshold_mb': critical_threshold,
                        'capacity_status': capacity_status
                    }
                )

        return {
            'capacity_status': capacity_status,
            'current_size_mb': total_size_mb,
            'total_items': total_items,
            'threshold_warning_mb': warning_threshold,
            'threshold_critical_mb': critical_threshold,
            'check_timestamp': taipei_now.isoformat()
        }

    except Exception as e:
        print(f"容量檢查失敗: {e}")
        raise
