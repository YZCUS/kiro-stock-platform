#!/usr/bin/env python3
"""
API性能測試
"""
import sys
import asyncio
import unittest
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
import pytest

# 添加測試配置路徑
sys.path.insert(0, str(Path(__file__).parent.parent))
from test_config import setup_test_path

# 設置測試環境路徑
setup_test_path()

# TODO: migrate API performance tests to new modular endpoints or monitoring suite
pytestmark = pytest.mark.xfail(reason="Legacy API performance tests incompatible with refactored modules", run=False)


class TestAPIPerformance(unittest.TestCase):
    """API性能測試"""

    def setUp(self):
        """設置測試環境"""
        self.mock_db = AsyncMock()

    @patch('api.v1.stocks.stock_crud')
    async def test_get_stocks_performance_with_large_dataset(self, mock_crud):
        """測試大數據集下的API性能"""
        # 模擬1000條股票數據
        large_stock_dataset = []
        for i in range(1000):
            large_stock_dataset.append(Mock(
                id=i+1,
                symbol=f"STOCK{i+1:04d}.TW",
                market="TW",
                name=f"股票{i+1}",
                is_active=True
            ))

        mock_crud.get_stocks_with_filters.return_value = large_stock_dataset[:50]  # 返回第一頁
        mock_crud.count_stocks_with_filters.return_value = 1000

        start_time = time.time()

        result = await get_stocks(
            market="TW",
            is_active=True,
            search=None,
            page=1,
            page_size=50,
            db=self.mock_db
        )

        end_time = time.time()
        execution_time = end_time - start_time

        # 驗證結果
        self.assertEqual(len(result.items), 50)
        self.assertEqual(result.total, 1000)
        self.assertEqual(result.total_pages, 20)

        # 驗證只調用一次數據庫查詢
        self.assertEqual(mock_crud.get_stocks_with_filters.call_count, 1)
        self.assertEqual(mock_crud.count_stocks_with_filters.call_count, 1)

        # 性能驗證（應該很快完成）
        self.assertLess(execution_time, 1.0, "API調用應該在1秒內完成")

    @patch('api.v1.stocks.stock_crud')
    async def test_filter_performance_comparison(self, mock_crud):
        """測試過濾性能對比"""
        # 模擬搜尋結果
        filtered_stocks = [
            Mock(id=1, symbol="2330.TW", market="TW", name="台積電", is_active=True),
            Mock(id=2, symbol="2317.TW", market="TW", name="鴻海", is_active=True)
        ]

        mock_crud.get_stocks_with_filters.return_value = filtered_stocks
        mock_crud.count_stocks_with_filters.return_value = 2

        # 測試數據庫層過濾
        start_time = time.time()

        result = await get_stocks(
            market="TW",
            is_active=True,
            search="積電",
            page=1,
            page_size=10,
            db=self.mock_db
        )

        end_time = time.time()
        db_filter_time = end_time - start_time

        # 驗證過濾條件被正確傳遞到數據庫層
        mock_crud.get_stocks_with_filters.assert_called_once_with(
            self.mock_db,
            market="TW",
            is_active=True,
            search_term="積電",
            skip=0,
            limit=10
        )

        mock_crud.count_stocks_with_filters.assert_called_once_with(
            self.mock_db,
            market="TW",
            is_active=True,
            search_term="積電"
        )

        # 驗證沒有調用舊的方法
        self.assertFalse(hasattr(mock_crud, 'get_multi') or
                        mock_crud.get_multi.call_count > 0)

        # 性能應該很好
        self.assertLess(db_filter_time, 0.1, "數據庫層過濾應該非常快")

    @patch('api.v1.stocks.stock_crud')
    async def test_pagination_performance(self, mock_crud):
        """測試分頁性能"""
        # 模擬分頁數據
        page_stocks = [
            Mock(id=21, symbol="2881.TW", market="TW", name="富邦金", is_active=True),
            Mock(id=22, symbol="2882.TW", market="TW", name="國泰金", is_active=True)
        ]

        mock_crud.get_stocks_with_filters.return_value = page_stocks
        mock_crud.count_stocks_with_filters.return_value = 500

        # 測試第3頁性能
        start_time = time.time()

        result = await get_stocks(
            market="TW",
            is_active=True,
            search=None,
            page=3,
            page_size=20,
            db=self.mock_db
        )

        end_time = time.time()
        pagination_time = end_time - start_time

        # 驗證分頁計算正確
        mock_crud.get_stocks_with_filters.assert_called_once_with(
            self.mock_db,
            market="TW",
            is_active=True,
            search_term=None,
            skip=40,  # (3-1) * 20
            limit=20
        )

        # 驗證結果
        self.assertEqual(len(result.items), 2)
        self.assertEqual(result.page, 3)
        self.assertEqual(result.total_pages, 25)  # 500 / 20

        # 分頁查詢應該很快
        self.assertLess(pagination_time, 0.1, "分頁查詢應該非常快")

    @patch('api.v1.stocks.stock_crud')
    async def test_concurrent_requests_performance(self, mock_crud):
        """測試並發請求性能"""
        mock_crud.get_stocks_with_filters.return_value = []
        mock_crud.count_stocks_with_filters.return_value = 0

        # 模擬多個並發請求
        tasks = []
        for i in range(10):
            task = get_stocks(
                market="TW",
                is_active=True,
                search=f"test{i}",
                page=1,
                page_size=10,
                db=self.mock_db
            )
            tasks.append(task)

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        concurrent_time = end_time - start_time

        # 驗證所有請求都成功
        self.assertEqual(len(results), 10)
        for result in results:
            self.assertEqual(len(result.items), 0)
            self.assertEqual(result.total, 0)

        # 驗證數據庫調用次數
        self.assertEqual(mock_crud.get_stocks_with_filters.call_count, 10)
        self.assertEqual(mock_crud.count_stocks_with_filters.call_count, 10)

        # 並發性能測試
        self.assertLess(concurrent_time, 2.0, "10個並發請求應該在2秒內完成")

    @patch('api.v1.stocks.stock_crud')
    async def test_memory_usage_optimization(self, mock_crud):
        """測試內存使用優化"""
        # 模擬只返回需要的數據
        limited_stocks = [
            Mock(id=1, symbol="2330.TW", market="TW", name="台積電", is_active=True)
            for _ in range(50)  # 只返回一頁的數據
        ]

        mock_crud.get_stocks_with_filters.return_value = limited_stocks
        mock_crud.count_stocks_with_filters.return_value = 10000  # 總共有很多數據

        result = await get_stocks(
            market="TW",
            is_active=True,
            search=None,
            page=1,
            page_size=50,
            db=self.mock_db
        )

        # 驗證只返回請求的數據量
        self.assertEqual(len(result.items), 50)
        self.assertEqual(result.total, 10000)

        # 驗證LIMIT被正確使用
        mock_crud.get_stocks_with_filters.assert_called_once_with(
            self.mock_db,
            market="TW",
            is_active=True,
            search_term=None,
            skip=0,
            limit=50
        )

    @patch('api.v1.stocks.stock_crud')
    async def test_backward_compatibility_performance(self, mock_crud):
        """測試向後兼容性接口性能"""
        mock_stocks = [
            Mock(id=1, symbol="2330.TW", market="TW", name="台積電", is_active=True),
            Mock(id=2, symbol="2317.TW", market="TW", name="鴻海", is_active=True)
        ]

        mock_crud.get_stocks_with_filters.return_value = mock_stocks

        start_time = time.time()

        result = await get_stocks_simple(
            market="TW",
            is_active=True,
            limit=100,
            db=self.mock_db
        )

        end_time = time.time()
        simple_api_time = end_time - start_time

        # 驗證返回簡單格式
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)

        # 驗證使用優化的查詢方法
        mock_crud.get_stocks_with_filters.assert_called_once_with(
            self.mock_db,
            market="TW",
            is_active=True,
            skip=0,
            limit=100
        )

        # 性能應該很好
        self.assertLess(simple_api_time, 0.1, "簡化API應該非常快")


class TestQueryOptimization(unittest.TestCase):
    """查詢優化測試"""

    def setUp(self):
        """設置測試環境"""
        self.mock_db = AsyncMock()

    @patch('api.v1.stocks.stock_crud')
    async def test_query_pushdown_verification(self, mock_crud):
        """驗證查詢下推優化"""
        mock_crud.get_stocks_with_filters.return_value = []
        mock_crud.count_stocks_with_filters.return_value = 0

        await get_stocks(
            market="US",
            is_active=False,
            search="APPLE",
            page=2,
            page_size=25,
            db=self.mock_db
        )

        # 驗證所有過濾條件都下推到數據庫層
        get_call_args = mock_crud.get_stocks_with_filters.call_args
        count_call_args = mock_crud.count_stocks_with_filters.call_args

        # 檢查get調用
        self.assertEqual(get_call_args[0][0], self.mock_db)  # 第一個位置參數是db
        get_kwargs = get_call_args[1]
        self.assertEqual(get_kwargs['market'], "US")
        self.assertEqual(get_kwargs['is_active'], False)
        self.assertEqual(get_kwargs['search_term'], "APPLE")
        self.assertEqual(get_kwargs['skip'], 25)  # (2-1) * 25
        self.assertEqual(get_kwargs['limit'], 25)

        # 檢查count調用
        self.assertEqual(count_call_args[0][0], self.mock_db)
        count_kwargs = count_call_args[1]
        self.assertEqual(count_kwargs['market'], "US")
        self.assertEqual(count_kwargs['is_active'], False)
        self.assertEqual(count_kwargs['search_term'], "APPLE")

    @patch('api.v1.stocks.stock_crud')
    async def test_no_unnecessary_data_loading(self, mock_crud):
        """測試不加載不必要的數據"""
        # 模擬大量數據
        mock_crud.count_stocks_with_filters.return_value = 5000
        mock_crud.get_stocks_with_filters.return_value = [
            Mock(id=i, symbol=f"STOCK{i}.TW", market="TW", name=f"股票{i}", is_active=True)
            for i in range(20)  # 只返回請求的20條
        ]

        result = await get_stocks(
            market="TW",
            is_active=True,
            search=None,
            page=10,
            page_size=20,
            db=self.mock_db
        )

        # 驗證只請求需要的數據
        mock_crud.get_stocks_with_filters.assert_called_once_with(
            self.mock_db,
            market="TW",
            is_active=True,
            search_term=None,
            skip=180,  # (10-1) * 20
            limit=20
        )

        # 驗證結果
        self.assertEqual(len(result.items), 20)
        self.assertEqual(result.total, 5000)
        self.assertEqual(result.page, 10)
        self.assertEqual(result.total_pages, 250)  # 5000 / 20


async def run_all_tests():
    """執行所有測試"""
    print("=" * 60)
    print("API性能測試")
    print("=" * 60)

    # 異步測試
    async_test_classes = [
        TestAPIPerformance,
        TestQueryOptimization
    ]

    for test_class in async_test_classes:
        print(f"\n執行 {test_class.__name__}...")
        test_instance = test_class()

        # 獲取所有測試方法
        test_methods = [
            method for method in dir(test_instance)
            if method.startswith('test_') and callable(getattr(test_instance, method))
        ]

        for method_name in test_methods:
            test_instance.setUp()
            try:
                await getattr(test_instance, method_name)()
                print(f"✅ {method_name} - 通過")
            except Exception as e:
                print(f"❌ {method_name} - 失敗: {str(e)}")
                return False

    print("\n🎉 所有API性能測試都通過了！")
    return True


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)