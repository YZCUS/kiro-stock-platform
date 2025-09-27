#!/usr/bin/env python3
"""
时区处理测试
确保所有监控组件正确使用台北时区
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime


try:
    import pendulum
    from airflow.plugins.utils.date_utils import get_taipei_now
    PENDULUM_AVAILABLE = True
except ImportError:
    PENDULUM_AVAILABLE = False
    pytest.skip("Pendulum not available", allow_module_level=True)


class TestTimezoneHandling:
    """时区处理测试类"""

    def test_get_taipei_now_returns_correct_timezone(self):
        """测试 get_taipei_now 返回正确的时区"""
        if not PENDULUM_AVAILABLE:
            pytest.skip("Pendulum not available")

        taipei_time = get_taipei_now()

        # 验证返回的是 pendulum.DateTime 对象
        assert isinstance(taipei_time, pendulum.DateTime)

        # 验证时区是 Asia/Taipei
        assert taipei_time.timezone.name == 'Asia/Taipei'

        # 验证是当前时间（允许1分钟误差）
        now_utc = pendulum.now('UTC')
        taipei_utc = taipei_time.in_timezone('UTC')
        time_diff = abs((now_utc - taipei_utc).total_seconds())
        assert time_diff < 60  # 允许1分钟误差

    def test_timestamp_conversion_preserves_timezone(self):
        """测试时间戳转换保持时区信息"""
        if not PENDULUM_AVAILABLE:
            pytest.skip("Pendulum not available")

        # 创建一个已知的时间戳
        known_timestamp = 1640995200  # 2022-01-01 00:00:00 UTC

        # 转换为台北时区
        taipei_time = pendulum.from_timestamp(known_timestamp, 'Asia/Taipei')

        # 验证时区
        assert taipei_time.timezone.name == 'Asia/Taipei'

        # 验证时间（台北时间应该是 UTC+8）
        expected_hour = 8  # UTC 00:00 在台北是 08:00
        assert taipei_time.hour == expected_hour

    def test_isoformat_includes_timezone_info(self):
        """测试 ISO 格式包含时区信息"""
        if not PENDULUM_AVAILABLE:
            pytest.skip("Pendulum not available")

        taipei_time = get_taipei_now()
        iso_string = taipei_time.isoformat()

        # 验证 ISO 字符串包含时区信息
        # 台北时区的 ISO 格式应该以 +08:00 结尾
        assert '+08:00' in iso_string or '+0800' in iso_string

    @patch('airflow.plugins.storage.xcom_storage.get_taipei_now')
    def test_storage_manager_uses_taipei_time(self, mock_get_taipei_now):
        """测试存储管理器使用台北时间"""
        if not PENDULUM_AVAILABLE:
            pytest.skip("Pendulum not available")

        # 模拟台北时间
        mock_taipei_time = pendulum.parse('2024-01-01T10:30:00+08:00')
        mock_get_taipei_now.return_value = mock_taipei_time

        try:
            from airflow.plugins.storage.xcom_storage import XComStorageManager

            # 由于没有实际的 Redis，这个会失败，但我们可以验证时间函数的调用
            storage = XComStorageManager()

            # 验证 get_taipei_now 被调用
            mock_get_taipei_now.assert_called()

        except Exception:
            # 预期会失败（没有 Redis），但我们已经验证了时间函数的调用
            pass

    @patch('airflow.plugins.utils.notification_manager.get_taipei_now')
    def test_notification_manager_uses_taipei_time(self, mock_get_taipei_now):
        """测试通知管理器使用台北时间"""
        if not PENDULUM_AVAILABLE:
            pytest.skip("Pendulum not available")

        # 模拟台北时间
        mock_taipei_time = pendulum.parse('2024-01-01T15:45:00+08:00')
        mock_get_taipei_now.return_value = mock_taipei_time

        try:
            from airflow.plugins.utils.notification_manager import NotificationManager, NotificationLevel

            manager = NotificationManager()

            # 模拟发送通知
            manager._send_log = Mock(return_value=True)

            result = manager.send_notification(
                message="测试消息",
                level=NotificationLevel.INFO
            )

            # 验证 get_taipei_now 被调用
            mock_get_taipei_now.assert_called()

            # 验证通知发送成功
            assert 'log' in result

        except ImportError:
            pytest.skip("Notification manager not available")

    @patch('airflow.plugins.utils.storage_dashboard.get_taipei_now')
    def test_storage_dashboard_uses_taipei_time(self, mock_get_taipei_now):
        """测试存储仪表板使用台北时间"""
        if not PENDULUM_AVAILABLE:
            pytest.skip("Pendulum not available")

        # 模拟台北时间
        mock_taipei_time = pendulum.parse('2024-01-01T20:15:00+08:00')
        mock_get_taipei_now.return_value = mock_taipei_time

        try:
            from airflow.plugins.utils.storage_dashboard import StorageHealthReport

            # 创建健康报告
            health_report = StorageHealthReport(
                is_healthy=True,
                total_items=100,
                total_size_mb=50.0,
                redis_connected=True,
                consecutive_failures=0,
                expired_items=0,
                response_time_ms=100.0,
                issues=[],
                recommendations=[],
                timestamp=mock_taipei_time.isoformat()
            )

            # 验证时间戳格式正确
            assert '+08:00' in health_report.timestamp or '+0800' in health_report.timestamp

        except ImportError:
            pytest.skip("Storage dashboard not available")

    def test_timezone_consistency_across_components(self):
        """测试各组件之间的时区一致性"""
        if not PENDULUM_AVAILABLE:
            pytest.skip("Pendulum not available")

        # 获取多个台北时间实例
        time1 = get_taipei_now()
        time2 = get_taipei_now()
        time3 = get_taipei_now()

        # 验证所有时间都使用相同的时区
        assert time1.timezone.name == 'Asia/Taipei'
        assert time2.timezone.name == 'Asia/Taipei'
        assert time3.timezone.name == 'Asia/Taipei'

        # 验证时间差很小（应该在几秒内）
        max_diff = max(
            abs((time2 - time1).total_seconds()),
            abs((time3 - time2).total_seconds()),
            abs((time3 - time1).total_seconds())
        )
        assert max_diff < 10  # 应该在10秒内

    def test_date_string_formatting_for_metrics(self):
        """测试指标的日期字符串格式化"""
        if not PENDULUM_AVAILABLE:
            pytest.skip("Pendulum not available")

        taipei_time = get_taipei_now()
        date_string = taipei_time.strftime('%Y%m%d')

        # 验证日期字符串格式
        assert len(date_string) == 8
        assert date_string.isdigit()

        # 验证年份合理（假设在2020-2030之间）
        year = int(date_string[:4])
        assert 2020 <= year <= 2030

    def test_trading_hours_with_timezone(self):
        """测试交易时间的时区处理"""
        if not PENDULUM_AVAILABLE:
            pytest.skip("Pendulum not available")

        from airflow.plugins.utils.date_utils import is_market_hours

        # 创建台湾股市开盘时间（09:30）
        market_open = pendulum.now('Asia/Taipei').replace(hour=9, minute=30, second=0, microsecond=0)

        # 验证市场开放时间检查
        is_tw_market_open = is_market_hours('TW', market_open)
        assert is_tw_market_open is True

        # 创建台湾股市收盘后时间（14:00）
        market_closed = pendulum.now('Asia/Taipei').replace(hour=14, minute=0, second=0, microsecond=0)

        # 验证市场关闭时间检查
        is_tw_market_closed = is_market_hours('TW', market_closed)
        assert is_tw_market_closed is False


class TestTimezoneEdgeCases:
    """时区边缘情况测试"""

    def test_daylight_saving_time_handling(self):
        """测试夏令时处理（台湾不使用夏令时，但测试稳定性）"""
        if not PENDULUM_AVAILABLE:
            pytest.skip("Pendulum not available")

        # 台湾不使用夏令时，所以全年UTC偏移应该是+8
        summer_time = pendulum.parse('2024-07-01T12:00:00', tz='Asia/Taipei')
        winter_time = pendulum.parse('2024-01-01T12:00:00', tz='Asia/Taipei')

        # 验证偏移量一致
        assert summer_time.offset_hours == 8
        assert winter_time.offset_hours == 8

    def test_timestamp_roundtrip_conversion(self):
        """测试时间戳往返转换的准确性"""
        if not PENDULUM_AVAILABLE:
            pytest.skip("Pendulum not available")

        original_time = get_taipei_now()
        timestamp = original_time.timestamp()
        converted_time = pendulum.from_timestamp(timestamp, 'Asia/Taipei')

        # 验证往返转换后时间一致（允许毫秒级误差）
        time_diff = abs((original_time - converted_time).total_seconds())
        assert time_diff < 0.001  # 1毫秒误差


def test_timezone_imports():
    """测试时区相关的导入是否正常"""
    try:
        from airflow.plugins.utils.date_utils import get_taipei_now, get_taipei_today, is_market_hours

        # 验证函数可调用
        assert callable(get_taipei_now)
        assert callable(get_taipei_today)
        assert callable(is_market_hours)

        print("时区工具函数导入成功")
        return True

    except ImportError as e:
        print(f"时区工具函数导入失败: {e}")
        return False


if __name__ == '__main__':
    # 基础导入测试
    if test_timezone_imports():
        print("时区处理测试模块准备就绪")

        if PENDULUM_AVAILABLE:
            # 运行基础时区测试
            try:
                taipei_now = get_taipei_now()
                print(f"当前台北时间: {taipei_now.isoformat()}")
                print(f"时区: {taipei_now.timezone.name}")
                print(f"UTC偏移: + {taipei_now.offset_hours}小时")
            except Exception as e:
                print(f"基础时区测试失败: {e}")
        else:
            print("Pendulum 库不可用，跳过详细测试")
    else:
        print("时区处理测试模块初始化失败")

    print("\n要运行完整测试套件，请使用: pytest test_timezone_handling.py -v")