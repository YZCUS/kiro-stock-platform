"""
存储监控 DAG
定期监控外部存储健康状态、执行维护任务和发送警报
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.trigger_rule import TriggerRule

from ..plugins.utils.storage_dashboard import get_storage_dashboard, run_health_check, run_maintenance
from ..plugins.utils.notification_manager import get_notification_manager, NotificationLevel


# DAG 配置
dag_config = {
    'dag_id': 'storage_monitoring',
    'description': '外部存储监控和维护工作流程',
    'schedule_interval': '*/30 * * * *',  # 每30分钟运行一次
    'max_active_runs': 1,
    'tags': ['monitoring', 'storage', 'maintenance'],
    'default_args': {
        'owner': 'data-platform',
        'depends_on_past': False,
        'start_date': datetime(2024, 1, 1),
        'email_on_failure': True,
        'email_on_retry': False,
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
        'catchup': False
    }
}

# 创建 DAG
dag = DAG(**dag_config)


def storage_health_check(**context):
    """执行存储健康检查"""
    from ..plugins.utils.date_utils import get_taipei_now

    try:
        taipei_now = get_taipei_now()
        print(f"开始存储健康检查 - {taipei_now.format('YYYY-MM-DD HH:mm:ss')} (台北时间)")

        # 执行健康检查
        health_report = run_health_check()

        # 记录结果
        print(f"健康检查完成:")
        print(f"  - 整体状态: {'健康' if health_report.is_healthy else '有问题'}")
        print(f"  - 存储项目: {health_report.total_items}")
        print(f"  - 总大小: {health_report.total_size_mb} MB")
        print(f"  - Redis连接: {'正常' if health_report.redis_connected else '异常'}")
        print(f"  - 连续失败: {health_report.consecutive_failures}")
        print(f"  - 响应时间: {health_report.response_time_ms:.2f} ms")

        if health_report.issues:
            print(f"  - 发现问题: {len(health_report.issues)}")
            for issue in health_report.issues:
                print(f"    * {issue}")

        if health_report.recommendations:
            print(f"  - 建议: {len(health_report.recommendations)}")
            for rec in health_report.recommendations:
                print(f"    * {rec}")

        # 发送警报（如果需要）
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
        print(f"健康检查失败: {e}")

        # 发送失败通知
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
            print(f"发送健康检查失败通知失败: {notify_error}")

        raise


def storage_maintenance(**context):
    """执行存储维护任务"""
    from ..plugins.utils.date_utils import get_taipei_now

    try:
        taipei_now = get_taipei_now()
        print(f"开始存储维护任务 - {taipei_now.format('YYYY-MM-DD HH:mm:ss')} (台北时间)")

        # 执行维护
        maintenance_result = run_maintenance()

        # 记录结果
        print(f"维护任务完成:")
        print(f"  - 完成任务: {maintenance_result['summary'].get('total_tasks', 0)}")
        print(f"  - 失败任务: {maintenance_result['summary'].get('failed_tasks', 0)}")
        print(f"  - 清理过期项目: {maintenance_result['summary'].get('expired_items_cleaned', 0)}")
        print(f"  - 清理指标数据: {maintenance_result['summary'].get('metrics_cleaned', 0)}")
        print(f"  - 整体健康: {'是' if maintenance_result['summary'].get('overall_health') else '否'}")

        if maintenance_result['tasks_failed']:
            print(f"失败的任务:")
            for failed_task in maintenance_result['tasks_failed']:
                print(f"  - {failed_task['task']}: {failed_task.get('error', 'Unknown error')}")

        return maintenance_result

    except Exception as e:
        print(f"存储维护失败: {e}")
        raise


def generate_storage_report(**context):
    """生成存储状态报告"""
    from ..plugins.utils.date_utils import get_taipei_now

    try:
        taipei_now = get_taipei_now()
        print(f"生成存储报告 - {taipei_now.format('YYYY-MM-DD HH:mm:ss')} (台北时间)")

        dashboard = get_storage_dashboard()

        # 获取各种数据
        health_report = dashboard.get_comprehensive_health_report()
        performance_metrics = dashboard.get_performance_metrics(days=1)  # 最近1天
        alerts = dashboard.generate_alerts()

        # 生成报告
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

        print(f"存储报告生成完成:")
        print(f"  - 健康状态: {'健康' if health_report.is_healthy else '有问题'}")
        print(f"  - 存储项目: {health_report.total_items}")
        print(f"  - 成功率: {performance_metrics.get('summary', {}).get('success_rate_percent', 0):.1f}%")
        print(f"  - 警报数量: {len(alerts)}")

        return report

    except Exception as e:
        print(f"生成存储报告失败: {e}")
        raise


def check_storage_capacity(**context):
    """检查存储容量并发送警报"""
    from ..plugins.utils.date_utils import get_taipei_now

    try:
        taipei_now = get_taipei_now()
        dashboard = get_storage_dashboard()

        # 获取存储统计
        storage_stats = dashboard.storage_manager.get_storage_stats()
        total_size_mb = storage_stats.get('total_size_mb', 0)
        total_items = storage_stats.get('total_items', 0)

        # 检查容量阈值
        warning_threshold = dashboard.size_warning_threshold_mb
        critical_threshold = dashboard.size_critical_threshold_mb

        capacity_status = 'normal'
        if total_size_mb > critical_threshold:
            capacity_status = 'critical'
        elif total_size_mb > warning_threshold:
            capacity_status = 'warning'

        print(f"存储容量检查:")
        print(f"  - 当前大小: {total_size_mb} MB")
        print(f"  - 项目数量: {total_items}")
        print(f"  - 警告阈值: {warning_threshold} MB")
        print(f"  - 严重阈值: {critical_threshold} MB")
        print(f"  - 状态: {capacity_status}")

        # 发送容量警报
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
        print(f"容量检查失败: {e}")
        raise


# 定义任务

# 存储健康检查
health_check_task = PythonOperator(
    task_id='storage_health_check',
    python_callable=storage_health_check,
    dag=dag
)

# 容量检查
capacity_check_task = PythonOperator(
    task_id='check_storage_capacity',
    python_callable=check_storage_capacity,
    dag=dag
)

# 生成报告
report_task = PythonOperator(
    task_id='generate_storage_report',
    python_callable=generate_storage_report,
    dag=dag
)

# 存储维护（每小时执行一次，只在整点运行）
maintenance_task = PythonOperator(
    task_id='storage_maintenance',
    python_callable=storage_maintenance,
    dag=dag,
    # 只在每小时的第一次运行时执行维护
    depends_on_past=False
)

# 汇总任务
summary_task = EmptyOperator(
    task_id='monitoring_complete',
    trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    dag=dag
)

# 设置任务依赖关系
# 并行执行健康检查和容量检查
[health_check_task, capacity_check_task] >> report_task

# 维护任务独立运行，每小时执行一次
# 可以根据需要调整维护频率
maintenance_task

# 所有监控任务完成后执行汇总
[report_task, maintenance_task] >> summary_task