#!/usr/bin/env python3
"""
存储监控和通知系统测试
测试增强的外部存储监控、健康检查和警示功能
"""
import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta


class TestNotificationManager:
    """通知管理器测试"""

    def test_notification_manager_initialization(self):
        """测试通知管理器初始化"""
        from airflow.plugins.utils.notification_manager import NotificationManager

        manager = NotificationManager()

        assert hasattr(manager, 'email_config')
        assert hasattr(manager, 'slack_config')
        assert hasattr(manager, 'webhook_config')
        assert hasattr(manager, 'default_channels')

    @patch('requests.post')
    def test_slack_notification_success(self, mock_post):
        """测试 Slack 通知成功发送"""
        from airflow.plugins.utils.notification_manager import NotificationManager, NotificationLevel

        # 模拟成功响应
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        manager = NotificationManager()
        manager.slack_config['webhook_url'] = 'https://test.slack.com/webhook'

        result = manager._send_slack({
            'level': 'error',
            'title': 'Test Alert',
            'message': 'Test message',
            'timestamp': datetime.now().isoformat(),
            'context': {'test': 'data'}
        })

        assert result is True
        mock_post.assert_called_once()

    def test_storage_failure_alert(self):
        """测试存储失败警报"""
        from airflow.plugins.utils.notification_manager import NotificationManager

        manager = NotificationManager()

        # 使用 Mock 替换发送方法
        manager._send_log = Mock(return_value=True)
        manager._send_email = Mock(return_value=True)

        result = manager.send_storage_failure_alert(
            operation='store',
            reference_id='test_ref_123',
            error='Redis connection timeout',
            context={'task_id': 'test_task'}
        )

        assert 'log' in result
        # 由于默认配置包含邮件通知，应该调用邮件发送
        manager._send_log.assert_called_once()

    def test_notification_level_routing(self):
        """测试通知级别路由"""
        from airflow.plugins.utils.notification_manager import NotificationManager, NotificationLevel

        manager = NotificationManager()

        # 检查默认路由配置
        info_channels = manager.default_channels[NotificationLevel.INFO]
        warning_channels = manager.default_channels[NotificationLevel.WARNING]
        error_channels = manager.default_channels[NotificationLevel.ERROR]
        critical_channels = manager.default_channels[NotificationLevel.CRITICAL]

        assert len(info_channels) == 1  # 只有日志
        assert len(warning_channels) >= 2  # 日志 + 邮件
        assert len(error_channels) >= 3  # 日志 + 邮件 + Slack
        assert len(critical_channels) >= 4  # 所有渠道


class TestEnhancedStorageManager:
    """增强存储管理器测试"""

    @patch('redis.from_url')
    def test_storage_manager_health_check(self, mock_redis):
        """测试存储管理器健康检查"""
        from airflow.plugins.storage.xcom_storage import XComStorageManager

        # 模拟 Redis 客户端
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.info.return_value = {
            'redis_version': '6.2.0',
            'used_memory_human': '1.2M',
            'connected_clients': 5,
            'total_commands_processed': 1000,
            'uptime_in_seconds': 3600
        }
        mock_redis.return_value = mock_client

        manager = XComStorageManager()
        health_data = manager.check_redis_health()

        assert health_data['is_healthy'] is True
        assert 'redis_version' in health_data
        assert 'response_time_seconds' in health_data
        assert manager.consecutive_failures == 0

    @patch('redis.from_url')
    def test_storage_manager_health_check_failure(self, mock_redis):
        """测试存储管理器健康检查失败"""
        from airflow.plugins.storage.xcom_storage import XComStorageManager

        # 模拟 Redis 连接失败
        mock_client = Mock()
        mock_client.ping.side_effect = Exception("Connection refused")
        mock_redis.return_value = mock_client

        manager = XComStorageManager()
        health_data = manager.check_redis_health()

        assert health_data['is_healthy'] is False
        assert 'Connection refused' in health_data['error']
        assert manager.consecutive_failures > 0

    @patch('redis.from_url')
    def test_performance_monitoring(self, mock_redis):
        """测试性能监控"""
        from airflow.plugins.storage.xcom_storage import XComStorageManager

        # 模拟 Redis 客户端
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.setex.return_value = True
        mock_client.lpush.return_value = 1
        mock_client.expire.return_value = True
        mock_client.ltrim.return_value = True
        mock_redis.return_value = mock_client

        manager = XComStorageManager()

        # 测试性能监控上下文管理器
        start_time = time.time()
        try:
            with manager._performance_monitor('test_operation', 'test_ref'):
                time.sleep(0.01)  # 模拟操作时间
                pass  # 成功操作
        except Exception:
            pass

        # 验证监控记录被调用
        assert mock_client.lpush.called

    @patch('redis.from_url')
    def test_storage_with_monitoring(self, mock_redis):
        """测试带监控的存储操作"""
        from airflow.plugins.storage.xcom_storage import XComStorageManager

        # 模拟 Redis 客户端
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.setex.return_value = True
        mock_client.lpush.return_value = 1
        mock_client.expire.return_value = True
        mock_client.ltrim.return_value = True
        mock_redis.return_value = mock_client

        manager = XComStorageManager()
        manager.enable_monitoring = True

        # 存储测试数据
        test_data = {'test': 'data', 'items': [1, 2, 3]}
        ref_id = manager.store_data(test_data, 'test_ref_123')

        assert ref_id == 'test_ref_123'
        # 验证 Redis 操作被调用
        mock_client.setex.assert_called()
        # 验证监控指标被记录
        mock_client.lpush.assert_called()

    @patch('redis.from_url')
    def test_metrics_summary(self, mock_redis):
        """测试指标汇总"""
        from airflow.plugins.storage.xcom_storage import XComStorageManager

        # 模拟 Redis 客户端和数据
        mock_client = Mock()
        mock_client.ping.return_value = True

        # 模拟指标数据
        mock_metrics = [
            json.dumps({
                'type': 'operation_performance',
                'data': {
                    'operation': 'store',
                    'duration_seconds': 0.1,
                    'success': True
                }
            }).encode('utf-8'),
            json.dumps({
                'type': 'store_success',
                'data': {
                    'reference_id': 'test_123',
                    'data_size': 1024
                }
            }).encode('utf-8')
        ]

        mock_client.lrange.return_value = mock_metrics
        mock_redis.return_value = mock_client

        manager = XComStorageManager()
        manager.enable_monitoring = True

        summary = manager.get_metrics_summary(days=1)

        assert 'operations' in summary
        assert 'performance' in summary
        assert 'data_volume' in summary


class TestStorageDashboard:
    """存储仪表板测试"""

    def test_dashboard_initialization(self):
        """测试仪表板初始化"""
        from airflow.plugins.utils.storage_dashboard import StorageDashboard

        dashboard = StorageDashboard()

        assert hasattr(dashboard, 'storage_manager')
        assert hasattr(dashboard, 'notification_manager')
        assert hasattr(dashboard, 'size_warning_threshold_mb')
        assert hasattr(dashboard, 'size_critical_threshold_mb')

    @patch('airflow.plugins.storage.xcom_storage.get_storage_manager')
    def test_comprehensive_health_report(self, mock_get_storage_manager):
        """测试综合健康报告"""
        from airflow.plugins.utils.storage_dashboard import StorageDashboard

        # 模拟存储管理器
        mock_manager = Mock()
        mock_manager.get_storage_stats.return_value = {
            'total_items': 100,
            'total_size_mb': 250.5,
            'redis_connected': True,
            'consecutive_failures': 0,
            'expired_items': 5
        }
        mock_manager.check_redis_health.return_value = {
            'is_healthy': True,
            'response_time_seconds': 0.05,
            'error': None
        }
        mock_get_storage_manager.return_value = mock_manager

        dashboard = StorageDashboard()
        health_report = dashboard.get_comprehensive_health_report()

        assert health_report.is_healthy is True
        assert health_report.total_items == 100
        assert health_report.total_size_mb == 250.5
        assert health_report.redis_connected is True
        assert len(health_report.issues) == 0

    @patch('airflow.plugins.storage.xcom_storage.get_storage_manager')
    def test_health_report_with_issues(self, mock_get_storage_manager):
        """测试带问题的健康报告"""
        from airflow.plugins.utils.storage_dashboard import StorageDashboard

        # 模拟存储管理器有问题
        mock_manager = Mock()
        mock_manager.get_storage_stats.return_value = {
            'total_items': 100,
            'total_size_mb': 1500.0,  # 超过严重阈值
            'redis_connected': True,
            'consecutive_failures': 5,  # 高失败次数
            'expired_items': 0
        }
        mock_manager.check_redis_health.return_value = {
            'is_healthy': True,
            'response_time_seconds': 2.0,  # 高响应时间
            'error': None
        }
        mock_get_storage_manager.return_value = mock_manager

        dashboard = StorageDashboard()
        dashboard.size_critical_threshold_mb = 1000
        dashboard.failure_warning_threshold = 3
        dashboard.response_time_warning_ms = 1000

        health_report = dashboard.get_comprehensive_health_report()

        assert health_report.is_healthy is False
        assert len(health_report.issues) >= 3  # 大小、失败次数、响应时间
        assert len(health_report.recommendations) >= 3

    @patch('airflow.plugins.storage.xcom_storage.get_storage_manager')
    def test_automated_maintenance(self, mock_get_storage_manager):
        """测试自动化维护"""
        from airflow.plugins.utils.storage_dashboard import StorageDashboard

        # 模拟存储管理器
        mock_manager = Mock()
        mock_manager.cleanup_expired_data.return_value = 10
        mock_manager.cleanup_metrics.return_value = 5
        mock_manager.get_storage_stats.return_value = {
            'total_items': 90,
            'total_size_mb': 200.0,
            'redis_connected': True,
            'consecutive_failures': 0,
            'expired_items': 0
        }
        mock_manager.check_redis_health.return_value = {
            'is_healthy': True,
            'response_time_seconds': 0.05,
            'error': None
        }
        mock_get_storage_manager.return_value = mock_manager

        dashboard = StorageDashboard()
        dashboard.notification_manager = Mock()  # 模拟通知管理器

        maintenance_result = dashboard.run_automated_maintenance()

        assert maintenance_result['summary']['expired_items_cleaned'] == 10
        assert maintenance_result['summary']['metrics_cleaned'] == 5
        assert len(maintenance_result['tasks_completed']) >= 3
        assert len(maintenance_result['tasks_failed']) == 0

    def test_generate_alerts(self):
        """测试警报生成"""
        from airflow.plugins.utils.storage_dashboard import StorageDashboard, StorageHealthReport

        dashboard = StorageDashboard()

        # 模拟健康报告方法
        dashboard.get_comprehensive_health_report = Mock(return_value=StorageHealthReport(
            is_healthy=False,
            total_items=100,
            total_size_mb=1200.0,
            redis_connected=True,
            consecutive_failures=2,
            expired_items=10,
            response_time_ms=500.0,
            issues=['Storage size exceeds critical threshold', 'High number of expired items'],
            recommendations=['Clean up old data', 'Run cleanup process'],
            timestamp=datetime.now().isoformat()
        ))

        alerts = dashboard.generate_alerts()

        assert len(alerts) >= 2  # 至少有两个问题
        assert any(alert.level == 'critical' for alert in alerts)
        assert all(hasattr(alert, 'title') for alert in alerts)
        assert all(hasattr(alert, 'message') for alert in alerts)


class TestAPIOperatorIntegration:
    """API 操作器集成测试"""

    @patch('airflow.plugins.storage.xcom_storage.store_large_data')
    @patch('airflow.plugins.utils.notification_manager.get_notification_manager')
    @patch('requests.get')
    def test_api_operator_storage_failure_notification(self, mock_get, mock_get_notification, mock_store):
        """测试 API 操作器存储失败通知"""
        from airflow.plugins.operators.api_operator import APICallOperator

        # 模拟 API 响应
        mock_response = Mock()
        mock_response.json.return_value = {'large_data': 'x' * 100000}  # 大数据
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # 模拟存储失败
        mock_store.side_effect = Exception("Redis connection failed")

        # 模拟通知管理器
        mock_notification_manager = Mock()
        mock_notification_manager.send_storage_failure_alert.return_value = {'email': True}
        mock_get_notification.return_value = mock_notification_manager

        operator = APICallOperator(
            task_id='test_task',
            endpoint='/test',
            method='GET',
            use_external_storage=True,
            max_xcom_size=1000  # 小阈值确保触发外部存储
        )

        # 模拟 Airflow context
        context = {
            'task_instance': Mock(task_id='test_task', dag_id='test_dag')
        }

        # 执行操作，应该回退到直接返回
        result = operator.execute(context)

        # 验证通知被发送
        mock_notification_manager.send_storage_failure_alert.assert_called_once()

        # 验证回退行为（直接返回数据）
        assert result == {'large_data': 'x' * 100000}

    @patch('airflow.plugins.storage.xcom_storage.retrieve_large_data')
    @patch('airflow.plugins.utils.notification_manager.get_notification_manager')
    def test_stock_collection_operator_retrieve_failure_notification(self, mock_get_notification, mock_retrieve):
        """测试股票收集操作器检索失败通知"""
        from airflow.plugins.operators.api_operator import StockDataCollectionOperator

        # 模拟检索失败
        mock_retrieve.side_effect = Exception("Data not found in Redis")

        # 模拟通知管理器
        mock_notification_manager = Mock()
        mock_notification_manager.send_storage_failure_alert.return_value = {'email': True}
        mock_get_notification.return_value = mock_notification_manager

        operator = StockDataCollectionOperator(
            task_id='test_task',
            use_upstream_stocks=True,
            upstream_task_id='get_stocks'
        )

        # 模拟 Airflow context
        ti_mock = Mock()
        ti_mock.xcom_pull.return_value = {
            'external_storage': True,
            'reference_id': 'test_ref_123',
            'data_size': 50000
        }
        context = {
            'task_instance': Mock(task_id='test_task', dag_id='test_dag'),
            'ti': ti_mock
        }

        # 执行操作，应该抛出异常
        with pytest.raises(ValueError, match="無法從外部存儲檢索股票清單"):
            operator.execute(context)

        # 验证通知被发送
        mock_notification_manager.send_storage_failure_alert.assert_called_once()


class TestStorageMonitoringDAG:
    """存储监控 DAG 测试"""

    @patch('airflow.plugins.utils.storage_dashboard.run_health_check')
    def test_storage_health_check_task(self, mock_health_check):
        """测试存储健康检查任务"""
        from airflow.dags.storage_monitoring import storage_health_check

        # 模拟健康检查结果
        mock_health_report = Mock()
        mock_health_report.is_healthy = True
        mock_health_report.total_items = 150
        mock_health_report.total_size_mb = 300.5
        mock_health_report.redis_connected = True
        mock_health_report.consecutive_failures = 0
        mock_health_report.response_time_ms = 45.2
        mock_health_report.issues = []
        mock_health_report.recommendations = []
        mock_health_report.timestamp = datetime.now().isoformat()

        mock_health_check.return_value = mock_health_report

        # 执行任务
        result = storage_health_check()

        assert result['health_status'] == 'healthy'
        assert result['total_items'] == 150
        assert result['total_size_mb'] == 300.5
        assert result['redis_connected'] is True
        assert result['issues_count'] == 0

    @patch('airflow.plugins.utils.storage_dashboard.run_maintenance')
    def test_storage_maintenance_task(self, mock_maintenance):
        """测试存储维护任务"""
        from airflow.dags.storage_monitoring import storage_maintenance

        # 模拟维护结果
        mock_maintenance.return_value = {
            'timestamp': datetime.now().isoformat(),
            'tasks_completed': [
                {'task': 'cleanup_expired_data', 'result': 'Cleaned 15 expired items'},
                {'task': 'cleanup_metrics', 'result': 'Cleaned 8 old metric entries'}
            ],
            'tasks_failed': [],
            'summary': {
                'total_tasks': 2,
                'failed_tasks': 0,
                'expired_items_cleaned': 15,
                'metrics_cleaned': 8,
                'overall_health': True
            }
        }

        # 执行任务
        result = storage_maintenance()

        assert result['summary']['total_tasks'] == 2
        assert result['summary']['expired_items_cleaned'] == 15
        assert result['summary']['overall_health'] is True
        assert len(result['tasks_failed']) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])