#!/usr/bin/env python3
"""
技術指標存儲和快取整合服務測試
"""
import sys
import asyncio
import unittest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, date, timedelta
from dataclasses import asdict
from pathlib import Path

# 添加測試配置路徑
sys.path.insert(0, str(Path(__file__).parent.parent))
from test_config import setup_test_path

# 設置測試環境路徑
setup_test_path()

from services.infrastructure.storage import (
    IndicatorStorageService,
    StorageResult,
    SyncResult,
    indicator_storage_service
)
from services.analysis.technical_analysis import IndicatorType


class TestStorageResult(unittest.TestCase):
    """存儲結果測試"""

    def test_create_storage_result(self):
        """測試建立存儲結果"""
        result = StorageResult(
            success=True,
            indicators_stored=50,
            indicators_cached=30,
            errors=["Error 1"],
            execution_time_seconds=15.5
        )

        self.assertTrue(result.success)
        self.assertEqual(result.indicators_stored, 50)
        self.assertEqual(result.indicators_cached, 30)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.execution_time_seconds, 15.5)


class TestSyncResult(unittest.TestCase):
    """同步結果測試"""

    def test_create_sync_result(self):
        """測試建立同步結果"""
        result = SyncResult(
            success=True,
            stocks_processed=10,
            indicators_updated=100,
            cache_refreshed=50,
            errors=[]
        )

        self.assertTrue(result.success)
        self.assertEqual(result.stocks_processed, 10)
        self.assertEqual(result.indicators_updated, 100)
        self.assertEqual(result.cache_refreshed, 50)
        self.assertEqual(len(result.errors), 0)


class TestIndicatorStorageService(unittest.TestCase):
    """技術指標存儲服務測試"""

    def setUp(self):
        """設置測試環境"""
        self.service = IndicatorStorageService()
        self.mock_db_session = AsyncMock()

    def test_service_initialization(self):
        """測試服務初始化"""
        self.assertEqual(self.service.batch_size, 100)
        self.assertEqual(self.service.cache_expire_seconds, 1800)
        self.assertEqual(self.service.max_concurrent_stocks, 5)

    @patch('services.infrastructure.storage.stock_crud')
    async def test_calculate_and_store_indicators_stock_not_found(self, mock_stock_crud):
        """測試計算和存儲指標 - 股票不存在"""
        # 模擬股票不存在
        mock_stock_crud.get.return_value = None

        result = await self.service.calculate_and_store_indicators(
            self.mock_db_session,
            stock_id=999,
            indicators=[IndicatorType.RSI],
            days=30
        )

        self.assertFalse(result.success)
        self.assertEqual(result.indicators_stored, 0)
        self.assertEqual(result.indicators_cached, 0)
        self.assertIn("找不到股票 ID: 999", result.errors)

    @patch('services.infrastructure.storage.indicator_cache_service')
    @patch('services.infrastructure.storage.technical_analysis_service')
    @patch('services.infrastructure.storage.stock_crud')
    async def test_calculate_and_store_indicators_with_cache_hit(
        self, mock_stock_crud, mock_technical_analysis_service, mock_indicator_cache_service
    ):
        """測試計算和存儲指標 - 快取命中"""
        # 模擬股票存在
        mock_stock = Mock()
        mock_stock.symbol = "2330"
        mock_stock_crud.get.return_value = mock_stock

        # 模擬快取命中
        mock_cached_data = [{"indicator": "RSI", "value": 65.5}]
        mock_indicator_cache_service.get_stock_indicators_from_cache.return_value = mock_cached_data

        result = await self.service.calculate_and_store_indicators(
            self.mock_db_session,
            stock_id=1,
            indicators=[IndicatorType.RSI],
            days=30,
            enable_cache=True,
            force_recalculate=False
        )

        self.assertTrue(result.success)
        self.assertEqual(result.indicators_stored, 0)  # 沒有計算新指標
        self.assertEqual(result.indicators_cached, 1)  # 使用快取數據

        # 驗證不會調用技術分析服務
        mock_technical_analysis_service.calculate_stock_indicators.assert_not_called()

    @patch('services.infrastructure.storage.indicator_cache_service')
    @patch('services.infrastructure.storage.technical_indicator_crud')
    @patch('services.infrastructure.storage.technical_analysis_service')
    @patch('services.infrastructure.storage.stock_crud')
    async def test_calculate_and_store_indicators_success(
        self, mock_stock_crud, mock_technical_analysis_service,
        mock_technical_indicator_crud, mock_indicator_cache_service
    ):
        """測試計算和存儲指標 - 成功"""
        # 模擬股票存在
        mock_stock = Mock()
        mock_stock.symbol = "2330"
        mock_stock_crud.get.return_value = mock_stock

        # 模擬無快取數據
        mock_indicator_cache_service.get_stock_indicators_from_cache.return_value = None

        # 模擬技術分析結果
        mock_analysis_result = Mock()
        mock_analysis_result.indicators_successful = 5
        mock_analysis_result.errors = []
        mock_technical_analysis_service.calculate_stock_indicators.return_value = mock_analysis_result

        # 模擬存儲的指標數據
        mock_stored_indicators = [Mock() for _ in range(5)]
        mock_technical_indicator_crud.get_stock_indicators_by_date_range.return_value = mock_stored_indicators

        # 模擬快取操作
        mock_indicator_cache_service.cache_indicators_batch.return_value = 5

        result = await self.service.calculate_and_store_indicators(
            self.mock_db_session,
            stock_id=1,
            indicators=[IndicatorType.RSI, IndicatorType.SMA_20],
            days=30,
            enable_cache=True,
            force_recalculate=False
        )

        self.assertTrue(result.success)
        self.assertEqual(result.indicators_stored, 5)
        self.assertEqual(result.indicators_cached, 5)
        self.assertEqual(len(result.errors), 0)

        # 驗證技術分析服務被調用
        mock_technical_analysis_service.calculate_stock_indicators.assert_called_once()

        # 驗證快取操作被調用
        mock_indicator_cache_service.cache_indicators_batch.assert_called_once()

    @patch('services.infrastructure.storage.indicator_cache_service')
    @patch('services.infrastructure.storage.technical_analysis_service')
    @patch('services.infrastructure.storage.stock_crud')
    async def test_calculate_and_store_indicators_with_cache_error(
        self, mock_stock_crud, mock_technical_analysis_service, mock_indicator_cache_service
    ):
        """測試計算和存儲指標 - 快取錯誤"""
        # 模擬股票存在
        mock_stock = Mock()
        mock_stock.symbol = "2330"
        mock_stock_crud.get.return_value = mock_stock

        # 模擬無快取數據
        mock_indicator_cache_service.get_stock_indicators_from_cache.return_value = None

        # 模擬技術分析成功
        mock_analysis_result = Mock()
        mock_analysis_result.indicators_successful = 3
        mock_analysis_result.errors = []
        mock_technical_analysis_service.calculate_stock_indicators.return_value = mock_analysis_result

        # 模擬快取操作失敗
        mock_indicator_cache_service.cache_indicators_batch.side_effect = Exception("Cache error")

        result = await self.service.calculate_and_store_indicators(
            self.mock_db_session,
            stock_id=1,
            indicators=[IndicatorType.RSI],
            days=30,
            enable_cache=True
        )

        self.assertTrue(result.success)  # 技術分析成功
        self.assertEqual(result.indicators_stored, 3)
        self.assertEqual(result.indicators_cached, 0)  # 快取失敗
        self.assertIn("快取指標時發生錯誤", str(result.errors))

    async def test_batch_calculate_and_store_empty_list(self):
        """測試批次計算和存儲 - 空列表"""
        results = await self.service.batch_calculate_and_store(
            self.mock_db_session,
            stock_ids=[],
            indicators=[IndicatorType.RSI],
            days=30
        )

        self.assertEqual(len(results), 0)

    @patch('services.infrastructure.storage.IndicatorStorageService.calculate_and_store_indicators')
    async def test_batch_calculate_and_store_success(self, mock_calculate_and_store):
        """測試批次計算和存儲 - 成功"""
        # 模擬單個股票計算結果
        mock_result = StorageResult(
            success=True,
            indicators_stored=5,
            indicators_cached=3,
            errors=[],
            execution_time_seconds=2.5
        )
        mock_calculate_and_store.return_value = mock_result

        stock_ids = [1, 2, 3]
        results = await self.service.batch_calculate_and_store(
            self.mock_db_session,
            stock_ids=stock_ids,
            indicators=[IndicatorType.RSI, IndicatorType.SMA_20],
            days=30
        )

        self.assertEqual(len(results), 3)
        self.assertTrue(all(r.success for r in results))

        # 驗證每個股票都被處理
        self.assertEqual(mock_calculate_and_store.call_count, 3)

    @patch('services.infrastructure.storage.IndicatorStorageService.calculate_and_store_indicators')
    async def test_batch_calculate_and_store_with_exception(self, mock_calculate_and_store):
        """測試批次計算和存儲 - 包含異常"""
        # 模擬第二個股票拋出異常
        def side_effect(*args, **kwargs):
            stock_id = kwargs.get('stock_id')
            if stock_id == 2:
                raise Exception("Database connection error")
            return StorageResult(
                success=True,
                indicators_stored=5,
                indicators_cached=3,
                errors=[],
                execution_time_seconds=2.5
            )

        mock_calculate_and_store.side_effect = side_effect

        stock_ids = [1, 2, 3]
        results = await self.service.batch_calculate_and_store(
            self.mock_db_session,
            stock_ids=stock_ids,
            indicators=[IndicatorType.RSI],
            days=30
        )

        self.assertEqual(len(results), 3)

        # 第一個和第三個成功，第二個失敗
        self.assertTrue(results[0].success)
        self.assertFalse(results[1].success)
        self.assertTrue(results[2].success)

        self.assertIn("Database connection error", results[1].errors)

    @patch('services.infrastructure.storage.indicator_cache_service')
    async def test_get_indicators_with_cache(self, mock_indicator_cache_service):
        """測試取得指標數據（使用快取）"""
        mock_data = {"RSI": [{"date": "2024-01-15", "value": 65.5}]}
        mock_indicator_cache_service.get_or_calculate_indicators.return_value = mock_data

        result = await self.service.get_indicators_with_cache(
            self.mock_db_session,
            stock_id=1,
            indicator_types=["RSI"],
            days=30,
            force_refresh=False
        )

        self.assertEqual(result, mock_data)
        mock_indicator_cache_service.get_or_calculate_indicators.assert_called_once_with(
            self.mock_db_session,
            stock_id=1,
            indicator_types=["RSI"],
            days=30,
            force_refresh=False
        )

    @patch('services.infrastructure.storage.indicator_cache_service')
    @patch('services.infrastructure.storage.technical_indicator_crud')
    @patch('services.infrastructure.storage.stock_crud')
    async def test_sync_indicators_with_cache_success(
        self, mock_stock_crud, mock_technical_indicator_crud, mock_indicator_cache_service
    ):
        """測試同步指標數據和快取 - 成功"""
        # 模擬股票列表
        mock_stocks = []
        for i in range(3):
            stock = Mock()
            stock.id = i + 1
            mock_stocks.append(stock)
        mock_stock_crud.get_multi.return_value = mock_stocks

        # 模擬沒有最新指標
        mock_technical_indicator_crud.get_latest_indicators.return_value = []

        # 模擬計算存儲結果
        mock_storage_result = StorageResult(
            success=True,
            indicators_stored=5,
            indicators_cached=3,
            errors=[],
            execution_time_seconds=2.0
        )

        with patch.object(self.service, 'calculate_and_store_indicators', return_value=mock_storage_result):
            result = await self.service.sync_indicators_with_cache(
                self.mock_db_session,
                stock_ids=[1, 2, 3],
                indicator_types=["RSI"],
                sync_days=7
            )

        self.assertTrue(result.success)
        self.assertEqual(result.stocks_processed, 3)
        self.assertEqual(result.indicators_updated, 15)  # 3 stocks * 5 indicators
        self.assertEqual(result.cache_refreshed, 9)      # 3 stocks * 3 cached

    @patch('services.infrastructure.storage.indicator_cache_service')
    @patch('services.infrastructure.storage.technical_indicator_crud')
    @patch('services.infrastructure.storage.stock_crud')
    async def test_sync_indicators_with_cache_only_refresh(
        self, mock_stock_crud, mock_technical_indicator_crud, mock_indicator_cache_service
    ):
        """測試同步指標數據和快取 - 只刷新快取"""
        # 模擬股票存在
        mock_stock = Mock()
        mock_stock.id = 1
        mock_stock_crud.get.return_value = mock_stock
        mock_stock_crud.get_multi.return_value = [mock_stock]

        # 模擬已有最新指標
        mock_indicator = Mock()
        mock_indicator.date = date.today()
        mock_technical_indicator_crud.get_latest_indicators.return_value = [mock_indicator]

        # 模擬快取刷新成功
        mock_cache_result = {'success': True, 'cached_count': 5}
        mock_indicator_cache_service.refresh_stock_cache.return_value = mock_cache_result

        result = await self.service.sync_indicators_with_cache(
            self.mock_db_session,
            stock_ids=[1],
            indicator_types=["RSI"],
            sync_days=7
        )

        self.assertTrue(result.success)
        self.assertEqual(result.stocks_processed, 1)
        self.assertEqual(result.indicators_updated, 0)  # 沒有更新指標
        self.assertEqual(result.cache_refreshed, 5)     # 只刷新快取

    @patch('services.infrastructure.storage.technical_indicator_crud')
    @patch('services.infrastructure.storage.stock_crud')
    async def test_cleanup_old_data(self, mock_stock_crud, mock_technical_indicator_crud):
        """測試清理舊數據"""
        # 模擬股票列表
        mock_stocks = []
        for i in range(5):
            stock = Mock()
            stock.id = i + 1
            mock_stocks.append(stock)
        mock_stock_crud.get_multi.return_value = mock_stocks

        # 模擬刪除操作
        mock_technical_indicator_crud.delete_old_indicators.return_value = 10

        result = await self.service.cleanup_old_data(
            self.mock_db_session,
            keep_days=365,
            stock_ids=[1, 2, 3]
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['deleted_count'], 30)  # 3 stocks * 10 deleted each
        self.assertEqual(result['stocks_processed'], 3)

        # 驗證刪除操作被正確調用
        self.assertEqual(mock_technical_indicator_crud.delete_old_indicators.call_count, 3)

    @patch('services.infrastructure.storage.indicator_cache_service')
    async def test_get_storage_statistics(self, mock_indicator_cache_service):
        """測試取得存儲統計資訊"""
        # 模擬資料庫查詢結果
        mock_row = Mock()
        mock_row.total_indicators = 1000
        mock_row.total_stocks = 50
        mock_row.total_indicator_types = 8
        mock_row.latest_date = date(2024, 1, 15)
        mock_row.earliest_date = date(2023, 1, 1)

        mock_result = Mock()
        mock_result.first.return_value = mock_row
        self.mock_db_session.execute.return_value = mock_result

        # 模擬快取統計
        mock_cache_stats = Mock()
        mock_cache_stats.hit_count = 500
        mock_cache_stats.miss_count = 100
        mock_cache_stats.hit_rate = 0.83
        mock_cache_stats.total_keys = 200
        mock_cache_stats.cache_size_mb = 50.5
        mock_indicator_cache_service.get_cache_statistics.return_value = mock_cache_stats

        result = await self.service.get_storage_statistics(self.mock_db_session)

        self.assertEqual(result['database']['total_indicators'], 1000)
        self.assertEqual(result['database']['total_stocks'], 50)
        self.assertEqual(result['cache']['hit_count'], 500)
        self.assertEqual(result['cache']['hit_rate'], 0.83)

    @patch('services.infrastructure.storage.technical_indicator_crud')
    @patch('services.infrastructure.storage.stock_crud')
    async def test_validate_data_integrity_success(self, mock_stock_crud, mock_technical_indicator_crud):
        """測試驗證數據完整性 - 成功"""
        # 模擬股票存在
        mock_stock = Mock()
        mock_stock.symbol = "2330"
        mock_stock_crud.get.return_value = mock_stock

        # 模擬指標數據（30天完整數據）
        mock_indicators = []
        base_date = date.today() - timedelta(days=29)
        for i in range(30):
            indicator = Mock()
            indicator.indicator_type = "RSI"
            indicator.date = base_date + timedelta(days=i)
            indicator.value = "65.5"
            mock_indicators.append(indicator)

        mock_technical_indicator_crud.get_stock_indicators_by_date_range.return_value = mock_indicators

        result = await self.service.validate_data_integrity(
            self.mock_db_session,
            stock_id=1,
            days=30
        )

        self.assertTrue(result['success'])
        integrity_report = result['integrity_report']
        self.assertEqual(integrity_report['stock_symbol'], "2330")
        self.assertEqual(integrity_report['overall_health'], 'good')
        self.assertEqual(integrity_report['indicator_types']['RSI']['health_status'], 'good')

    @patch('services.infrastructure.storage.technical_indicator_crud')
    @patch('services.infrastructure.storage.stock_crud')
    async def test_validate_data_integrity_with_missing_data(self, mock_stock_crud, mock_technical_indicator_crud):
        """測試驗證數據完整性 - 缺失數據"""
        # 模擬股票存在
        mock_stock = Mock()
        mock_stock.symbol = "2330"
        mock_stock_crud.get.return_value = mock_stock

        # 模擬指標數據（只有15天數據，缺失很多）
        mock_indicators = []
        base_date = date.today() - timedelta(days=29)
        for i in range(0, 30, 2):  # 只有偶數天的數據
            indicator = Mock()
            indicator.indicator_type = "RSI"
            indicator.date = base_date + timedelta(days=i)
            indicator.value = "65.5"
            mock_indicators.append(indicator)

        mock_technical_indicator_crud.get_stock_indicators_by_date_range.return_value = mock_indicators

        result = await self.service.validate_data_integrity(
            self.mock_db_session,
            stock_id=1,
            days=30
        )

        self.assertTrue(result['success'])
        integrity_report = result['integrity_report']
        self.assertEqual(integrity_report['overall_health'], 'poor')  # 超過10%缺失
        self.assertEqual(integrity_report['indicator_types']['RSI']['health_status'], 'poor')
        self.assertEqual(integrity_report['indicator_types']['RSI']['missing_dates'], 15)

    @patch('services.infrastructure.storage.stock_crud')
    async def test_validate_data_integrity_stock_not_found(self, mock_stock_crud):
        """測試驗證數據完整性 - 股票不存在"""
        mock_stock_crud.get.return_value = None

        result = await self.service.validate_data_integrity(
            self.mock_db_session,
            stock_id=999,
            days=30
        )

        self.assertFalse(result['success'])
        self.assertIn("找不到股票 ID: 999", result['error'])


async def run_all_tests():
    """執行所有測試"""
    print("=" * 60)
    print("技術指標存儲服務測試")
    print("=" * 60)

    # 同步測試
    sync_test_classes = [
        TestStorageResult,
        TestSyncResult
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
    print(f"\n執行 TestIndicatorStorageService...")
    async_test = TestIndicatorStorageService()

    async_test_methods = [
        'test_calculate_and_store_indicators_stock_not_found',
        'test_calculate_and_store_indicators_with_cache_hit',
        'test_calculate_and_store_indicators_success',
        'test_calculate_and_store_indicators_with_cache_error',
        'test_batch_calculate_and_store_empty_list',
        'test_batch_calculate_and_store_success',
        'test_batch_calculate_and_store_with_exception',
        'test_get_indicators_with_cache',
        'test_sync_indicators_with_cache_success',
        'test_sync_indicators_with_cache_only_refresh',
        'test_cleanup_old_data',
        'test_get_storage_statistics',
        'test_validate_data_integrity_success',
        'test_validate_data_integrity_with_missing_data',
        'test_validate_data_integrity_stock_not_found'
    ]

    for method_name in async_test_methods:
        async_test.setUp()
        try:
            await getattr(async_test, method_name)()
            print(f"✅ {method_name} - 通過")
        except Exception as e:
            print(f"❌ {method_name} - 失敗: {str(e)}")
            return False

    print("\n🎉 所有存儲服務測試都通過了！")
    return True


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)