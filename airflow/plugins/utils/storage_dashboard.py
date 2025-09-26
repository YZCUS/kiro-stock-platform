"""
存储管理仪表板工具
提供存储状态监控、健康检查和管理功能
"""
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from ..storage.xcom_storage import get_storage_manager
from .notification_manager import get_notification_manager, NotificationLevel
from .date_utils import get_taipei_now


logger = logging.getLogger(__name__)


@dataclass
class StorageHealthReport:
    """存储健康报告"""
    is_healthy: bool
    total_items: int
    total_size_mb: float
    redis_connected: bool
    consecutive_failures: int
    expired_items: int
    response_time_ms: float
    issues: List[str]
    recommendations: List[str]
    timestamp: str


@dataclass
class StorageAlert:
    """存储警报"""
    level: str
    title: str
    message: str
    context: Dict[str, Any]
    timestamp: str


class StorageDashboard:
    """存储管理仪表板"""

    def __init__(self):
        """初始化仪表板"""
        self.storage_manager = get_storage_manager()
        self.notification_manager = get_notification_manager()

        # 配置阈值
        self.size_warning_threshold_mb = float(os.getenv('STORAGE_WARNING_THRESHOLD_MB', 500))
        self.size_critical_threshold_mb = float(os.getenv('STORAGE_CRITICAL_THRESHOLD_MB', 1000))
        self.failure_warning_threshold = int(os.getenv('FAILURE_WARNING_THRESHOLD', 3))
        self.response_time_warning_ms = float(os.getenv('RESPONSE_TIME_WARNING_MS', 1000))

    def get_comprehensive_health_report(self) -> StorageHealthReport:
        """
        获取综合健康报告

        Returns:
            StorageHealthReport: 健康报告
        """
        issues = []
        recommendations = []

        try:
            # 获取基础统计信息
            stats = self.storage_manager.get_storage_stats()
            health_data = self.storage_manager.check_redis_health()

            # 检查 Redis 连接
            redis_connected = health_data.get('is_healthy', False)
            if not redis_connected:
                issues.append(f"Redis connection failed: {health_data.get('error', 'Unknown error')}")
                recommendations.append("Check Redis server status and network connectivity")

            # 检查存储大小
            total_size_mb = stats.get('total_size_mb', 0)
            if total_size_mb > self.size_critical_threshold_mb:
                issues.append(f"Storage size ({total_size_mb} MB) exceeds critical threshold")
                recommendations.append("Consider cleaning up old data or increasing storage capacity")
            elif total_size_mb > self.size_warning_threshold_mb:
                issues.append(f"Storage size ({total_size_mb} MB) exceeds warning threshold")
                recommendations.append("Monitor storage usage and plan for cleanup")

            # 检查连续失败次数
            consecutive_failures = stats.get('consecutive_failures', 0)
            if consecutive_failures > self.failure_warning_threshold:
                issues.append(f"High number of consecutive failures: {consecutive_failures}")
                recommendations.append("Investigate Redis connectivity and performance issues")

            # 检查响应时间
            response_time_ms = health_data.get('response_time_seconds', 0) * 1000
            if response_time_ms > self.response_time_warning_ms:
                issues.append(f"High Redis response time: {response_time_ms:.2f} ms")
                recommendations.append("Check Redis server performance and network latency")

            # 检查过期项目
            expired_items = stats.get('expired_items', 0)
            total_items = stats.get('total_items', 0)
            if expired_items > 0:
                expired_ratio = expired_items / max(total_items, 1)
                if expired_ratio > 0.1:  # 超过10%的项目过期
                    issues.append(f"High ratio of expired items: {expired_items}/{total_items}")
                    recommendations.append("Run cleanup process to remove expired data")

            # 确定整体健康状态
            is_healthy = redis_connected and len(issues) == 0

            return StorageHealthReport(
                is_healthy=is_healthy,
                total_items=total_items,
                total_size_mb=total_size_mb,
                redis_connected=redis_connected,
                consecutive_failures=consecutive_failures,
                expired_items=expired_items,
                response_time_ms=response_time_ms,
                issues=issues,
                recommendations=recommendations,
                timestamp=get_taipei_now().isoformat()
            )

        except Exception as e:
            logger.error(f"生成健康报告失败: {e}")
            return StorageHealthReport(
                is_healthy=False,
                total_items=0,
                total_size_mb=0,
                redis_connected=False,
                consecutive_failures=999,
                expired_items=0,
                response_time_ms=0,
                issues=[f"Failed to generate health report: {str(e)}"],
                recommendations=["Check storage manager configuration and Redis connectivity"],
                timestamp=get_taipei_now().isoformat()
            )

    def get_performance_metrics(self, days: int = 7) -> Dict[str, Any]:
        """
        获取性能指标

        Args:
            days: 查询天数

        Returns:
            Dict: 性能指标
        """
        try:
            metrics = self.storage_manager.get_metrics_summary(days)

            # 添加计算字段
            total_operations = sum(metrics.get('operations', {}).values())
            total_failures = sum(metrics.get('failures', {}).values())
            success_rate = ((total_operations - total_failures) / max(total_operations, 1)) * 100

            metrics['summary'] = {
                'total_operations': total_operations,
                'total_failures': total_failures,
                'success_rate_percent': round(success_rate, 2),
                'failure_rate_percent': round((total_failures / max(total_operations, 1)) * 100, 2)
            }

            return metrics

        except Exception as e:
            logger.error(f"获取性能指标失败: {e}")
            return {'error': str(e)}

    def get_storage_trends(self, days: int = 30) -> Dict[str, Any]:
        """
        获取存储趋势分析

        Args:
            days: 分析天数

        Returns:
            Dict: 趋势分析数据
        """
        try:
            trends = {
                'period_days': days,
                'daily_storage': [],
                'daily_operations': [],
                'growth_rate': 0,
                'prediction': {}
            }

            # 这里可以扩展为更详细的趋势分析
            # 目前提供基础框架
            current_stats = self.storage_manager.get_storage_stats()
            trends['current_snapshot'] = {
                'total_items': current_stats.get('total_items', 0),
                'total_size_mb': current_stats.get('total_size_mb', 0),
                'timestamp': get_taipei_now().isoformat()
            }

            return trends

        except Exception as e:
            logger.error(f"获取存储趋势失败: {e}")
            return {'error': str(e)}

    def run_automated_maintenance(self) -> Dict[str, Any]:
        """
        运行自动化维护任务

        Returns:
            Dict: 维护结果
        """
        maintenance_results = {
            'timestamp': get_taipei_now().isoformat(),
            'tasks_completed': [],
            'tasks_failed': [],
            'summary': {}
        }

        try:
            # 清理过期数据
            logger.info("开始清理过期数据...")
            expired_count = self.storage_manager.cleanup_expired_data()
            maintenance_results['tasks_completed'].append({
                'task': 'cleanup_expired_data',
                'result': f"Cleaned {expired_count} expired items"
            })

            # 清理旧指标
            logger.info("开始清理过期指标...")
            metrics_cleaned = self.storage_manager.cleanup_metrics(older_than_days=30)
            maintenance_results['tasks_completed'].append({
                'task': 'cleanup_metrics',
                'result': f"Cleaned {metrics_cleaned} old metric entries"
            })

            # 健康检查
            logger.info("执行健康检查...")
            health_report = self.get_comprehensive_health_report()
            maintenance_results['tasks_completed'].append({
                'task': 'health_check',
                'result': f"Health status: {'Healthy' if health_report.is_healthy else 'Issues detected'}"
            })

            # 生成维护摘要
            maintenance_results['summary'] = {
                'total_tasks': len(maintenance_results['tasks_completed']),
                'failed_tasks': len(maintenance_results['tasks_failed']),
                'expired_items_cleaned': expired_count,
                'metrics_cleaned': metrics_cleaned,
                'overall_health': health_report.is_healthy
            }

            # 发送维护完成通知
            if self.notification_manager:
                self.notification_manager.send_notification(
                    message=f"Storage maintenance completed. Cleaned {expired_count} expired items and {metrics_cleaned} old metrics.",
                    level=NotificationLevel.INFO,
                    title="Storage Maintenance Completed",
                    context=maintenance_results['summary']
                )

            logger.info("自动化维护任务完成")

        except Exception as e:
            error_msg = f"维护任务失败: {str(e)}"
            logger.error(error_msg)
            maintenance_results['tasks_failed'].append({
                'task': 'automated_maintenance',
                'error': error_msg
            })

            # 发送维护失败通知
            if self.notification_manager:
                self.notification_manager.send_notification(
                    message=f"Storage maintenance failed: {str(e)}",
                    level=NotificationLevel.ERROR,
                    title="Storage Maintenance Failed",
                    context={'error': str(e)}
                )

        return maintenance_results

    def generate_alerts(self) -> List[StorageAlert]:
        """
        生成当前存储警报

        Returns:
            List[StorageAlert]: 警报列表
        """
        alerts = []

        try:
            health_report = self.get_comprehensive_health_report()

            # 为每个问题生成警报
            for issue in health_report.issues:
                level = "critical" if "critical" in issue.lower() else "warning"
                alert = StorageAlert(
                    level=level,
                    title=f"Storage {level.title()} Alert",
                    message=issue,
                    context={
                        'total_items': health_report.total_items,
                        'total_size_mb': health_report.total_size_mb,
                        'redis_connected': health_report.redis_connected
                    },
                    timestamp=get_taipei_now().isoformat()
                )
                alerts.append(alert)

            # 如果没有问题，生成正常状态警报
            if not health_report.issues and health_report.is_healthy:
                alert = StorageAlert(
                    level="info",
                    title="Storage Status Normal",
                    message="All storage systems are operating normally",
                    context={
                        'total_items': health_report.total_items,
                        'total_size_mb': health_report.total_size_mb,
                        'response_time_ms': health_report.response_time_ms
                    },
                    timestamp=get_taipei_now().isoformat()
                )
                alerts.append(alert)

        except Exception as e:
            logger.error(f"生成警报失败: {e}")
            alert = StorageAlert(
                level="error",
                title="Alert Generation Failed",
                message=f"Failed to generate storage alerts: {str(e)}",
                context={'error': str(e)},
                timestamp=get_taipei_now().isoformat()
            )
            alerts.append(alert)

        return alerts

    def export_dashboard_data(self, include_metrics: bool = True) -> Dict[str, Any]:
        """
        导出仪表板数据

        Args:
            include_metrics: 是否包含详细指标

        Returns:
            Dict: 仪表板数据
        """
        try:
            dashboard_data = {
                'export_timestamp': get_taipei_now().isoformat(),
                'health_report': self.get_comprehensive_health_report().__dict__,
                'storage_stats': self.storage_manager.get_storage_stats(),
                'alerts': [alert.__dict__ for alert in self.generate_alerts()]
            }

            if include_metrics:
                dashboard_data['performance_metrics'] = self.get_performance_metrics()
                dashboard_data['storage_trends'] = self.get_storage_trends()

            return dashboard_data

        except Exception as e:
            logger.error(f"导出仪表板数据失败: {e}")
            return {
                'export_timestamp': get_taipei_now().isoformat(),
                'error': str(e)
            }


# 全局实例
_dashboard = None


def get_storage_dashboard() -> StorageDashboard:
    """获取全局存储仪表板实例"""
    global _dashboard
    if _dashboard is None:
        _dashboard = StorageDashboard()
    return _dashboard


def run_health_check() -> StorageHealthReport:
    """
    运行存储健康检查的便捷函数

    Returns:
        StorageHealthReport: 健康报告
    """
    dashboard = get_storage_dashboard()
    return dashboard.get_comprehensive_health_report()


def run_maintenance() -> Dict[str, Any]:
    """
    运行存储维护的便捷函数

    Returns:
        Dict: 维护结果
    """
    dashboard = get_storage_dashboard()
    return dashboard.run_automated_maintenance()


def export_storage_status() -> Dict[str, Any]:
    """
    导出存储状态的便捷函数

    Returns:
        Dict: 存储状态数据
    """
    dashboard = get_storage_dashboard()
    return dashboard.export_dashboard_data()