"""
Storage monitoring 報告生成模塊
"""


def generate_storage_report(**context):
    """生成存儲狀態報告"""
    from plugins.common.date_utils import get_taipei_now
    from plugins.services.monitoring_service import get_storage_dashboard

    try:
        taipei_now = get_taipei_now()
        print(f"生成存儲報告 - {taipei_now.format('YYYY-MM-DD HH:mm:ss')} (台北時間)")

        dashboard = get_storage_dashboard()

        # 獲取各種數據
        health_report = dashboard.get_comprehensive_health_report()
        performance_metrics = dashboard.get_performance_metrics(days=1)  # 最近1天
        alerts = dashboard.generate_alerts()

        # 生成報告
        report = {
            'report_timestamp': taipei_now.isoformat(),
            'health_summary': {
                'is_healthy': health_report.is_healthy,
                'total_items': health_report.total_items,
                'total_size_mb': health_report.total_size_mb,
                'issues_count': len(health_report.issues)
            },
            'performance_summary': {
                'total_operations': performance_metrics.get('summary', {}).get('total_operations', 0),
                'success_rate_percent': performance_metrics.get('summary', {}).get('success_rate_percent', 0),
                'failure_rate_percent': performance_metrics.get('summary', {}).get('failure_rate_percent', 0)
            },
            'alerts_summary': {
                'total_alerts': len(alerts),
                'critical_alerts': len([a for a in alerts if a.level == 'critical']),
                'warning_alerts': len([a for a in alerts if a.level == 'warning'])
            }
        }

        print(f"存儲報告生成完成:")
        print(f"  - 健康狀態: {'健康' if health_report.is_healthy else '有問題'}")
        print(f"  - 存儲項目: {health_report.total_items}")
        print(f"  - 成功率: {performance_metrics.get('summary', {}).get('success_rate_percent', 0):.1f}%")
        print(f"  - 警報數量: {len(alerts)}")

        return report

    except Exception as e:
        print(f"生成存儲報告失敗: {e}")
        raise
