#!/usr/bin/env python3
"""
技術指標同步和更新服務測試
"""
import sys
import asyncio
import unittest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, date, timedelta
from pathlib import Path

# 添加測試配置路徑
sys.path.insert(0, str(Path(__file__).parent.parent))
from test_config import setup_test_path

# 設置測試環境路徑
setup_test_path()

from services.infrastructure.sync import (
    IndicatorSyncService,
    SyncSchedule,
    SyncStatus,
    indicator_sync_service
)
from services.analysis.technical_analysis import IndicatorType


class TestSyncSchedule(unittest.TestCase):
    """同步排程測試"""

    def test_create_sync_schedule(self):
        """測試建立同步排程"""
        stock_ids = [1, 2, 3]
        indicator_types = ["RSI", "SMA_20"]
        schedule = SyncSchedule(
            stock_ids=stock_ids,
            indicator_types=indicator_types,
            sync_frequency='daily',
            last_sync=None,
            next_sync=datetime(2024, 1, 15, 16, 30),
            enabled=True
        )

        self.assertEqual(schedule.stock_ids, stock_ids)
        self.assertEqual(schedule.indicator_types, indicator_types)
        self.assertEqual(schedule.sync_frequency, 'daily')
        self.assertIsNone(schedule.last_sync)
        self.assertTrue(schedule.enabled)


class TestSyncStatus(unittest.TestCase):
    """同步狀態測試"""

    def test_create_sync_status(self):
        """測試建立同步狀態"""
        status = SyncStatus(
            is_running=True,
            current_stock_id=123,
            progress_percentage=45.5,
            start_time=datetime.now(),
            estimated_completion=datetime.now() + timedelta(minutes=10),
            last_error="Some error"
        )

        self.assertTrue(status.is_running)
        self.assertEqual(status.current_stock_id, 123)
        self.assertEqual(status.progress_percentage, 45.5)
        self.assertEqual(status.last_error, "Some error")


class TestIndicatorSyncService(unittest.TestCase):
    """技術指標同步服務測試"""

    def setUp(self):
        """設置測試環境"""
        self.service = IndicatorSyncService()

    def test_service_initialization(self):
        """測試服務初始化"""
        self.assertFalse(self.service.sync_status.is_running)
        self.assertIsNone(self.service.sync_status.current_stock_id)
        self.assertEqual(self.service.sync_status.progress_percentage, 0.0)
        self.assertEqual(len(self.service.sync_schedules), 0)
        self.assertEqual(len(self.service.default_indicators), 9)

    async def test_create_sync_schedule_success(self):
        """測試建立同步排程 - 成功"""
        stock_ids = [1, 2, 3]
        indicator_types = ["RSI", "SMA_20"]

        result = await self.service.create_sync_schedule(
            schedule_name="test_schedule",
            stock_ids=stock_ids,
            indicator_types=indicator_types,
            sync_frequency='daily'
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['schedule_name'], "test_schedule")
        self.assertEqual(result['stock_count'], 3)
        self.assertEqual(result['indicator_count'], 2)
        self.assertIn("test_schedule", self.service.sync_schedules)

        schedule = self.service.sync_schedules["test_schedule"]
        self.assertEqual(schedule.stock_ids, stock_ids)
        self.assertEqual(schedule.indicator_types, indicator_types)
        self.assertEqual(schedule.sync_frequency, 'daily')
        self.assertTrue(schedule.enabled)

    async def test_create_sync_schedule_with_default_indicators(self):
        """測試建立同步排程 - 使用默認指標"""
        stock_ids = [1, 2]

        result = await self.service.create_sync_schedule(
            schedule_name="default_indicators_schedule",
            stock_ids=stock_ids,
            sync_frequency='hourly'
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['indicator_count'], 9)  # 默認指標數量

        schedule = self.service.sync_schedules["default_indicators_schedule"]
        self.assertEqual(len(schedule.indicator_types), 9)

    def test_calculate_next_sync_time_daily(self):
        """測試計算下次同步時間 - 每日"""
        next_sync = self.service._calculate_next_sync_time('daily')

        self.assertIsNotNone(next_sync)
        self.assertEqual(next_sync.hour, 16)
        self.assertEqual(next_sync.minute, 30)

        # 如果現在是16:30之前，應該是今天；否則是明天
        now = datetime.now()
        today_1630 = now.replace(hour=16, minute=30, second=0, microsecond=0)

        if now <= today_1630:
            self.assertEqual(next_sync.date(), now.date())
        else:
            self.assertEqual(next_sync.date(), now.date() + timedelta(days=1))

    def test_calculate_next_sync_time_hourly(self):
        """測試計算下次同步時間 - 每小時"""
        next_sync = self.service._calculate_next_sync_time('hourly')

        self.assertIsNotNone(next_sync)
        self.assertEqual(next_sync.minute, 0)
        self.assertEqual(next_sync.second, 0)

        # 應該是下一個小時
        now = datetime.now()
        expected_hour = (now.hour + 1) % 24
        if next_sync.date() == now.date():
            self.assertEqual(next_sync.hour, expected_hour)

    def test_calculate_next_sync_time_manual(self):
        """測試計算下次同步時間 - 手動"""
        next_sync = self.service._calculate_next_sync_time('manual')
        self.assertIsNone(next_sync)

    def test_calculate_next_sync_time_unknown(self):
        """測試計算下次同步時間 - 未知頻率"""
        next_sync = self.service._calculate_next_sync_time('unknown_frequency')
        self.assertIsNone(next_sync)

    async def test_execute_sync_schedule_already_running(self):
        """測試執行同步排程 - 已在運行中"""
        self.service.sync_status.is_running = True

        result = await self.service.execute_sync_schedule("any_schedule")

        self.assertFalse(result['success'])
        self.assertIn("同步正在進行中", result['error'])

    async def test_execute_sync_schedule_not_found(self):
        """測試執行同步排程 - 排程不存在"""
        result = await self.service.execute_sync_schedule("nonexistent_schedule")

        self.assertFalse(result['success'])
        self.assertIn("找不到同步排程", result['error'])

    async def test_execute_sync_schedule_disabled(self):
        """測試執行同步排程 - 排程已停用"""
        schedule = SyncSchedule(
            stock_ids=[1, 2],
            indicator_types=["RSI"],
            sync_frequency='daily',
            last_sync=None,
            next_sync=datetime.now() - timedelta(hours=1),
            enabled=False
        )
        self.service.sync_schedules["disabled_schedule"] = schedule

        result = await self.service.execute_sync_schedule("disabled_schedule")

        self.assertFalse(result['success'])
        self.assertIn("已停用", result['error'])

    async def test_execute_sync_schedule_not_time_yet(self):
        """測試執行同步排程 - 尚未到同步時間"""
        future_time = datetime.now() + timedelta(hours=1)
        schedule = SyncSchedule(
            stock_ids=[1, 2],
            indicator_types=["RSI"],
            sync_frequency='daily',
            last_sync=None,
            next_sync=future_time,
            enabled=True
        )
        self.service.sync_schedules["future_schedule"] = schedule

        result = await self.service.execute_sync_schedule("future_schedule")

        self.assertFalse(result['success'])
        self.assertIn("尚未到同步時間", result['error'])

    @patch('services.infrastructure.sync.get_db')
    @patch('services.infrastructure.sync.indicator_storage_service')
    async def test_execute_sync_schedule_success(self, mock_indicator_storage_service, mock_get_db):
        """測試執行同步排程 - 成功"""
        # 模擬資料庫會話
        mock_db_session = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db_session

        # 模擬同步結果
        from services.infrastructure.storage import SyncResult
        mock_sync_result = SyncResult(
            success=True,
            stocks_processed=2,
            indicators_updated=10,
            cache_refreshed=5,
            errors=[]
        )
        mock_indicator_storage_service.sync_indicators_with_cache.return_value = mock_sync_result

        # 建立排程
        schedule = SyncSchedule(
            stock_ids=[1, 2],
            indicator_types=["RSI"],
            sync_frequency='daily',
            last_sync=None,
            next_sync=datetime.now() - timedelta(minutes=1),
            enabled=True
        )
        self.service.sync_schedules["success_schedule"] = schedule

        result = await self.service.execute_sync_schedule("success_schedule", force_sync=True)

        self.assertTrue(result['success'])
        self.assertEqual(result['stocks_processed'], 2)
        self.assertEqual(result['indicators_updated'], 10)
        self.assertEqual(result['cache_refreshed'], 5)

        # 驗證排程狀態更新
        updated_schedule = self.service.sync_schedules["success_schedule"]
        self.assertIsNotNone(updated_schedule.last_sync)
        self.assertIsNotNone(updated_schedule.next_sync)

        # 驗證同步狀態重置
        self.assertFalse(self.service.sync_status.is_running)
        self.assertEqual(self.service.sync_status.progress_percentage, 100.0)

    @patch('services.infrastructure.sync.get_db')
    @patch('services.infrastructure.sync.stock_crud')
    @patch('services.infrastructure.sync.indicator_storage_service')
    async def test_sync_single_stock_success(self, mock_indicator_storage_service, mock_stock_crud, mock_get_db):
        """測試同步單支股票 - 成功"""
        # 模擬資料庫會話
        mock_db_session = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db_session

        # 模擬股票存在
        mock_stock = Mock()
        mock_stock.symbol = "2330"
        mock_stock_crud.get.return_value = mock_stock

        # 模擬存儲結果
        from services.infrastructure.storage import StorageResult
        mock_storage_result = StorageResult(
            success=True,
            indicators_stored=5,
            indicators_cached=3,
            errors=[],
            execution_time_seconds=2.5
        )
        mock_indicator_storage_service.calculate_and_store_indicators.return_value = mock_storage_result

        result = await self.service.sync_single_stock(
            stock_id=1,
            indicator_types=["RSI", "SMA_20"],
            force_recalculate=True
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['stock_symbol'], "2330")
        self.assertEqual(result['indicators_stored'], 5)
        self.assertEqual(result['indicators_cached'], 3)
        self.assertEqual(result['execution_time'], 2.5)

    @patch('services.infrastructure.sync.get_db')
    @patch('services.infrastructure.sync.stock_crud')
    async def test_sync_single_stock_not_found(self, mock_stock_crud, mock_get_db):
        """測試同步單支股票 - 股票不存在"""
        # 模擬資料庫會話
        mock_db_session = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db_session

        # 模擬股票不存在
        mock_stock_crud.get.return_value = None

        result = await self.service.sync_single_stock(stock_id=999)

        self.assertFalse(result['success'])
        self.assertIn("找不到股票 ID: 999", result['error'])

    @patch('services.infrastructure.sync.get_db')
    @patch('services.infrastructure.sync.technical_indicator_crud')
    @patch('services.infrastructure.sync.stock_crud')
    @patch('services.infrastructure.sync.indicator_storage_service')
    async def test_sync_missing_indicators_success(
        self, mock_indicator_storage_service, mock_stock_crud,
        mock_technical_indicator_crud, mock_get_db
    ):
        """測試同步缺失指標 - 成功"""
        # 模擬資料庫會話
        mock_db_session = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db_session

        # 模擬股票列表
        mock_stocks = []
        for i in range(5):
            stock = Mock()
            stock.id = i + 1
            stock.symbol = f"STOCK_{i+1}"
            mock_stocks.append(stock)
        mock_stock_crud.get_multi.return_value = mock_stocks

        # 模擬前3支股票缺失數據，後2支有最新數據
        def mock_get_indicators(db_session, stock_id, start_date, end_date):
            if stock_id <= 3:
                return []  # 缺失數據
            else:
                # 有最新數據
                indicator = Mock()
                indicator.date = date.today()
                return [indicator]

        mock_technical_indicator_crud.get_stock_indicators_by_date_range.side_effect = mock_get_indicators

        # 模擬批次同步結果
        from services.infrastructure.storage import StorageResult
        mock_storage_results = []
        for i in range(3):  # 只有前3支股票需要同步
            result = StorageResult(
                success=True,
                indicators_stored=5,
                indicators_cached=3,
                errors=[],
                execution_time_seconds=2.0
            )
            mock_storage_results.append(result)

        mock_indicator_storage_service.batch_calculate_and_store.return_value = mock_storage_results

        result = await self.service.sync_missing_indicators(days_back=7, max_stocks=5)

        self.assertTrue(result['success'])
        self.assertEqual(result['stocks_checked'], 5)
        self.assertEqual(result['missing_stocks'], 3)
        self.assertEqual(result['successful_syncs'], 3)
        self.assertEqual(result['total_indicators_stored'], 15)  # 3 stocks * 5 indicators
        self.assertEqual(result['total_indicators_cached'], 9)   # 3 stocks * 3 cached

    @patch('services.infrastructure.sync.get_db')
    @patch('services.infrastructure.sync.technical_indicator_crud')
    @patch('services.infrastructure.sync.stock_crud')
    async def test_sync_missing_indicators_all_up_to_date(
        self, mock_stock_crud, mock_technical_indicator_crud, mock_get_db
    ):
        """測試同步缺失指標 - 所有數據都是最新的"""
        # 模擬資料庫會話
        mock_db_session = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db_session

        # 模擬股票列表
        mock_stocks = [Mock(id=1)]
        mock_stock_crud.get_multi.return_value = mock_stocks

        # 模擬有最新數據
        mock_indicator = Mock()
        mock_indicator.date = date.today()
        mock_technical_indicator_crud.get_stock_indicators_by_date_range.return_value = [mock_indicator]

        result = await self.service.sync_missing_indicators()

        self.assertTrue(result['success'])
        self.assertIn("所有股票的指標數據都是最新的", result['message'])
        self.assertEqual(result['missing_stocks'], 0)

    @patch('services.infrastructure.sync.get_db')
    @patch('services.infrastructure.sync.indicator_cache_service')
    async def test_refresh_cache_for_active_stocks_success(self, mock_indicator_cache_service, mock_get_db):
        """測試為活躍股票刷新快取 - 成功"""
        # 模擬資料庫會話
        mock_db_session = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db_session

        # 模擬活躍股票查詢結果
        mock_row1 = Mock()
        mock_row1.stock_id = 1
        mock_row2 = Mock()
        mock_row2.stock_id = 2

        mock_result = Mock()
        mock_result.fetchall.return_value = [mock_row1, mock_row2]
        mock_db_session.execute.return_value = mock_result

        # 模擬快取刷新成功
        mock_cache_result = {'success': True, 'cached_count': 5}
        mock_indicator_cache_service.refresh_stock_cache.return_value = mock_cache_result

        result = await self.service.refresh_cache_for_active_stocks(max_stocks=10)

        self.assertTrue(result['success'])
        self.assertEqual(result['refreshed_stocks'], 2)
        self.assertEqual(result['total_active_stocks'], 2)
        self.assertEqual(len(result['errors']), 0)

    @patch('services.infrastructure.sync.get_db')
    async def test_refresh_cache_for_active_stocks_no_active(self, mock_get_db):
        """測試為活躍股票刷新快取 - 沒有活躍股票"""
        # 模擬資料庫會話
        mock_db_session = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db_session

        # 模擬沒有活躍股票
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_db_session.execute.return_value = mock_result

        result = await self.service.refresh_cache_for_active_stocks()

        self.assertTrue(result['success'])
        self.assertIn("沒有找到活躍股票", result['message'])
        self.assertEqual(result['refreshed_stocks'], 0)

    async def test_get_sync_status(self):
        """測試取得同步狀態"""
        # 設置同步狀態
        self.service.sync_status.is_running = True
        self.service.sync_status.current_stock_id = 123
        self.service.sync_status.progress_percentage = 75.5
        self.service.sync_status.start_time = datetime(2024, 1, 15, 10, 30)
        self.service.sync_status.last_error = "Some error"

        # 添加一些排程
        schedule1 = SyncSchedule(
            stock_ids=[1, 2],
            indicator_types=["RSI"],
            sync_frequency='daily',
            last_sync=None,
            next_sync=None,
            enabled=True
        )
        schedule2 = SyncSchedule(
            stock_ids=[3, 4],
            indicator_types=["SMA_20"],
            sync_frequency='hourly',
            last_sync=None,
            next_sync=None,
            enabled=False
        )
        self.service.sync_schedules["schedule1"] = schedule1
        self.service.sync_schedules["schedule2"] = schedule2

        status = await self.service.get_sync_status()

        self.assertTrue(status['is_running'])
        self.assertEqual(status['current_stock_id'], 123)
        self.assertEqual(status['progress_percentage'], 75.5)
        self.assertEqual(status['start_time'], "2024-01-15T10:30:00")
        self.assertEqual(status['last_error'], "Some error")
        self.assertEqual(status['active_schedules'], 1)  # 只有一個啟用的排程

    async def test_get_sync_schedules(self):
        """測試取得所有同步排程"""
        # 添加排程
        schedule1 = SyncSchedule(
            stock_ids=[1, 2, 3],
            indicator_types=["RSI", "SMA_20"],
            sync_frequency='daily',
            last_sync=datetime(2024, 1, 14, 16, 30),
            next_sync=datetime(2024, 1, 15, 16, 30),
            enabled=True
        )
        schedule2 = SyncSchedule(
            stock_ids=[4, 5],
            indicator_types=["MACD"],
            sync_frequency='hourly',
            last_sync=None,
            next_sync=None,
            enabled=False
        )
        self.service.sync_schedules["daily_schedule"] = schedule1
        self.service.sync_schedules["hourly_schedule"] = schedule2

        schedules = await self.service.get_sync_schedules()

        self.assertEqual(len(schedules), 2)

        daily_info = schedules["daily_schedule"]
        self.assertEqual(daily_info['stock_count'], 3)
        self.assertEqual(daily_info['indicator_count'], 2)
        self.assertEqual(daily_info['sync_frequency'], 'daily')
        self.assertTrue(daily_info['enabled'])

        hourly_info = schedules["hourly_schedule"]
        self.assertEqual(hourly_info['stock_count'], 2)
        self.assertEqual(hourly_info['indicator_count'], 1)
        self.assertFalse(hourly_info['enabled'])

    async def test_enable_schedule_success(self):
        """測試啟用同步排程 - 成功"""
        schedule = SyncSchedule(
            stock_ids=[1, 2],
            indicator_types=["RSI"],
            sync_frequency='daily',
            last_sync=None,
            next_sync=None,
            enabled=False
        )
        self.service.sync_schedules["test_schedule"] = schedule

        result = await self.service.enable_schedule("test_schedule")

        self.assertTrue(result['success'])
        self.assertIn("已啟用", result['message'])
        self.assertTrue(self.service.sync_schedules["test_schedule"].enabled)
        self.assertIsNotNone(self.service.sync_schedules["test_schedule"].next_sync)

    async def test_enable_schedule_not_found(self):
        """測試啟用同步排程 - 排程不存在"""
        result = await self.service.enable_schedule("nonexistent_schedule")

        self.assertFalse(result['success'])
        self.assertIn("找不到同步排程", result['error'])

    async def test_disable_schedule_success(self):
        """測試停用同步排程 - 成功"""
        schedule = SyncSchedule(
            stock_ids=[1, 2],
            indicator_types=["RSI"],
            sync_frequency='daily',
            last_sync=None,
            next_sync=datetime.now(),
            enabled=True
        )
        self.service.sync_schedules["test_schedule"] = schedule

        result = await self.service.disable_schedule("test_schedule")

        self.assertTrue(result['success'])
        self.assertIn("已停用", result['message'])
        self.assertFalse(self.service.sync_schedules["test_schedule"].enabled)
        self.assertIsNone(self.service.sync_schedules["test_schedule"].next_sync)

    async def test_delete_schedule_success(self):
        """測試刪除同步排程 - 成功"""
        schedule = SyncSchedule(
            stock_ids=[1, 2],
            indicator_types=["RSI"],
            sync_frequency='daily',
            last_sync=None,
            next_sync=None,
            enabled=True
        )
        self.service.sync_schedules["test_schedule"] = schedule

        result = await self.service.delete_schedule("test_schedule")

        self.assertTrue(result['success'])
        self.assertIn("已刪除", result['message'])
        self.assertNotIn("test_schedule", self.service.sync_schedules)

    async def test_delete_schedule_not_found(self):
        """測試刪除同步排程 - 排程不存在"""
        result = await self.service.delete_schedule("nonexistent_schedule")

        self.assertFalse(result['success'])
        self.assertIn("找不到同步排程", result['error'])

    @patch.object(IndicatorSyncService, 'execute_sync_schedule')
    async def test_run_scheduled_sync_check(self, mock_execute_sync_schedule):
        """測試執行排程同步檢查"""
        # 模擬執行結果
        mock_execute_sync_schedule.return_value = {'success': True}

        # 添加需要執行的排程
        past_time = datetime.now() - timedelta(minutes=1)
        schedule = SyncSchedule(
            stock_ids=[1, 2],
            indicator_types=["RSI"],
            sync_frequency='daily',
            last_sync=None,
            next_sync=past_time,
            enabled=True
        )
        self.service.sync_schedules["ready_schedule"] = schedule
        self.service.sync_status.is_running = False

        await self.service.run_scheduled_sync_check()

        # 驗證排程被執行
        mock_execute_sync_schedule.assert_called_once_with("ready_schedule")


async def run_all_tests():
    """執行所有測試"""
    print("=" * 60)
    print("技術指標同步服務測試")
    print("=" * 60)

    # 同步測試
    sync_test_classes = [
        TestSyncSchedule,
        TestSyncStatus
    ]

    for test_class in sync_test_classes:
        print(f"\n執行 {test_class.__name__}...")
        suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)

        if not result.wasSuccessful():
            print(f"❌ {test_class.__name__} 測試失敗")
            return False

    # 異步測試
    print(f"\n執行 TestIndicatorSyncService...")
    async_test = TestIndicatorSyncService()

    async_test_methods = [
        'test_create_sync_schedule_success',
        'test_create_sync_schedule_with_default_indicators',
        'test_execute_sync_schedule_already_running',
        'test_execute_sync_schedule_not_found',
        'test_execute_sync_schedule_disabled',
        'test_execute_sync_schedule_not_time_yet',
        'test_execute_sync_schedule_success',
        'test_sync_single_stock_success',
        'test_sync_single_stock_not_found',
        'test_sync_missing_indicators_success',
        'test_sync_missing_indicators_all_up_to_date',
        'test_refresh_cache_for_active_stocks_success',
        'test_refresh_cache_for_active_stocks_no_active',
        'test_get_sync_status',
        'test_get_sync_schedules',
        'test_enable_schedule_success',
        'test_enable_schedule_not_found',
        'test_disable_schedule_success',
        'test_delete_schedule_success',
        'test_delete_schedule_not_found',
        'test_run_scheduled_sync_check'
    ]

    for method_name in async_test_methods:
        async_test.setUp()
        try:
            await getattr(async_test, method_name)()
            print(f"✅ {method_name} - 通過")
        except Exception as e:
            print(f"❌ {method_name} - 失敗: {str(e)}")
            return False

    print("\n🎉 所有同步服務測試都通過了！")
    return True


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)