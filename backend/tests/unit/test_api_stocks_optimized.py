#!/usr/bin/env python3
"""
股票API優化功能測試
"""
import sys
import asyncio
import unittest
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
from datetime import datetime

# 添加測試配置路徑
sys.path.insert(0, str(Path(__file__).parent.parent))
from test_config import setup_test_path

# 設置測試環境路徑
setup_test_path()

from api.v1.stocks import (
    get_stocks,
    get_stocks_simple,
    search_stocks,
    StockListResponse,
    StockResponse
)


class TestStocksAPIOptimized(unittest.TestCase):
    """股票API優化功能測試"""

    def setUp(self):
        """設置測試環境"""
        self.mock_db = AsyncMock()

        # 模擬股票數據
        self.mock_stocks = [
            Mock(
                id=1,
                symbol="2330.TW",
                market="TW",
                name="台積電",
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            Mock(
                id=2,
                symbol="2317.TW",
                market="TW",
                name="鴻海",
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        ]

    @patch('api.v1.stocks.stock_crud')
    async def test_get_stocks_with_pagination(self, mock_crud):
        """測試分頁式獲取股票清單"""
        # 設置mock返回值
        mock_crud.get_stocks_with_filters.return_value = self.mock_stocks
        mock_crud.count_stocks_with_filters.return_value = 25

        # 測試調用
        result = await get_stocks(
            market="TW",
            is_active=True,
            search=None,
            page=1,
            page_size=10,
            db=self.mock_db
        )

        # 驗證結果結構
        self.assertIsInstance(result, StockListResponse)
        self.assertEqual(len(result.items), 2)
        self.assertEqual(result.total, 25)
        self.assertEqual(result.page, 1)
        self.assertEqual(result.page_size, 10)
        self.assertEqual(result.total_pages, 3)  # 25 / 10 = 3 pages

        # 驗證CRUD方法被正確調用
        mock_crud.get_stocks_with_filters.assert_called_once_with(
            self.mock_db,
            market="TW",
            is_active=True,
            search_term=None,
            skip=0,
            limit=10
        )

        mock_crud.count_stocks_with_filters.assert_called_once_with(
            self.mock_db,
            market="TW",
            is_active=True,
            search_term=None
        )

    @patch('api.v1.stocks.stock_crud')
    async def test_get_stocks_with_search(self, mock_crud):
        """測試搜尋功能"""
        mock_crud.get_stocks_with_filters.return_value = [self.mock_stocks[0]]
        mock_crud.count_stocks_with_filters.return_value = 1

        result = await get_stocks(
            market=None,
            is_active=True,
            search="台積",
            page=1,
            page_size=10,
            db=self.mock_db
        )

        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.total, 1)

        # 驗證搜尋條件被傳遞
        mock_crud.get_stocks_with_filters.assert_called_once_with(
            self.mock_db,
            market=None,
            is_active=True,
            search_term="台積",
            skip=0,
            limit=10
        )

    @patch('api.v1.stocks.stock_crud')
    async def test_get_stocks_second_page(self, mock_crud):
        """測試第二頁數據"""
        mock_crud.get_stocks_with_filters.return_value = self.mock_stocks
        mock_crud.count_stocks_with_filters.return_value = 25

        result = await get_stocks(
            market="TW",
            is_active=True,
            search=None,
            page=2,
            page_size=10,
            db=self.mock_db
        )

        # 驗證分頁計算
        mock_crud.get_stocks_with_filters.assert_called_once_with(
            self.mock_db,
            market="TW",
            is_active=True,
            search_term=None,
            skip=10,  # (page-1) * page_size = (2-1) * 10 = 10
            limit=10
        )

    @patch('api.v1.stocks.stock_crud')
    async def test_get_stocks_us_market(self, mock_crud):
        """測試美股市場過濾"""
        us_stocks = [
            Mock(
                id=3,
                symbol="AAPL",
                market="US",
                name="Apple Inc.",
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        ]

        mock_crud.get_stocks_with_filters.return_value = us_stocks
        mock_crud.count_stocks_with_filters.return_value = 100

        result = await get_stocks(
            market="US",
            is_active=True,
            search=None,
            page=1,
            page_size=50,
            db=self.mock_db
        )

        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0].market, "US")

        # 驗證市場過濾
        mock_crud.get_stocks_with_filters.assert_called_once_with(
            self.mock_db,
            market="US",
            is_active=True,
            search_term=None,
            skip=0,
            limit=50
        )

    @patch('api.v1.stocks.stock_crud')
    async def test_get_stocks_inactive_stocks(self, mock_crud):
        """測試包含非活躍股票"""
        inactive_stocks = [
            Mock(
                id=4,
                symbol="1234.TW",
                market="TW",
                name="下市股票",
                is_active=False,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        ]

        mock_crud.get_stocks_with_filters.return_value = inactive_stocks
        mock_crud.count_stocks_with_filters.return_value = 5

        result = await get_stocks(
            market="TW",
            is_active=False,
            search=None,
            page=1,
            page_size=10,
            db=self.mock_db
        )

        self.assertEqual(len(result.items), 1)
        self.assertFalse(result.items[0].is_active)

    @patch('api.v1.stocks.stock_crud')
    async def test_get_stocks_simple_backward_compatibility(self, mock_crud):
        """測試簡化端點向後兼容性"""
        mock_crud.get_stocks_with_filters.return_value = self.mock_stocks

        result = await get_stocks_simple(
            market="TW",
            is_active=True,
            limit=100,
            db=self.mock_db
        )

        # 驗證返回簡單列表格式
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)

        # 驗證CRUD調用
        mock_crud.get_stocks_with_filters.assert_called_once_with(
            self.mock_db,
            market="TW",
            is_active=True,
            skip=0,
            limit=100
        )

    @patch('api.v1.stocks.stock_crud')
    async def test_search_stocks_functionality(self, mock_crud):
        """測試股票搜尋功能"""
        mock_crud.get_stocks_with_filters.return_value = [self.mock_stocks[0]]
        mock_crud.count_stocks_with_filters.return_value = 1

        result = await search_stocks(
            q="台積",
            market="TW",
            is_active=True,
            page=1,
            page_size=20,
            db=self.mock_db
        )

        self.assertIsInstance(result, StockListResponse)
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.total, 1)

        # 驗證搜尋參數
        mock_crud.get_stocks_with_filters.assert_called_once_with(
            self.mock_db,
            market="TW",
            is_active=True,
            search_term="台積",
            skip=0,
            limit=20
        )

    @patch('api.v1.stocks.stock_crud')
    async def test_search_stocks_cross_market(self, mock_crud):
        """測試跨市場搜尋"""
        cross_market_stocks = [
            self.mock_stocks[0],  # TW stock
            Mock(
                id=5,
                symbol="TSMC",
                market="US",
                name="Taiwan Semiconductor",
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        ]

        mock_crud.get_stocks_with_filters.return_value = cross_market_stocks
        mock_crud.count_stocks_with_filters.return_value = 2

        result = await search_stocks(
            q="TSM",
            market=None,  # 不指定市場
            is_active=True,
            page=1,
            page_size=20,
            db=self.mock_db
        )

        self.assertEqual(len(result.items), 2)

        # 驗證無市場限制
        mock_crud.get_stocks_with_filters.assert_called_once_with(
            self.mock_db,
            market=None,
            is_active=True,
            search_term="TSM",
            skip=0,
            limit=20
        )

    @patch('api.v1.stocks.stock_crud')
    async def test_get_stocks_empty_result(self, mock_crud):
        """測試空結果處理"""
        mock_crud.get_stocks_with_filters.return_value = []
        mock_crud.count_stocks_with_filters.return_value = 0

        result = await get_stocks(
            market="INVALID",
            is_active=True,
            search=None,
            page=1,
            page_size=10,
            db=self.mock_db
        )

        self.assertEqual(len(result.items), 0)
        self.assertEqual(result.total, 0)
        self.assertEqual(result.total_pages, 0)

    @patch('api.v1.stocks.stock_crud')
    async def test_get_stocks_large_page_size(self, mock_crud):
        """測試大頁面大小限制"""
        mock_crud.get_stocks_with_filters.return_value = self.mock_stocks
        mock_crud.count_stocks_with_filters.return_value = 2

        # 測試頁面大小限制在200
        result = await get_stocks(
            market=None,
            is_active=True,
            search=None,
            page=1,
            page_size=200,  # 最大值
            db=self.mock_db
        )

        self.assertEqual(result.page_size, 200)

        mock_crud.get_stocks_with_filters.assert_called_once_with(
            self.mock_db,
            market=None,
            is_active=True,
            search_term=None,
            skip=0,
            limit=200
        )

    @patch('api.v1.stocks.stock_crud')
    async def test_get_stocks_all_parameters(self, mock_crud):
        """測試所有參數組合"""
        mock_crud.get_stocks_with_filters.return_value = [self.mock_stocks[0]]
        mock_crud.count_stocks_with_filters.return_value = 1

        result = await get_stocks(
            market="TW",
            is_active=True,
            search="積電",
            page=2,
            page_size=5,
            db=self.mock_db
        )

        # 驗證所有參數都被正確傳遞
        mock_crud.get_stocks_with_filters.assert_called_once_with(
            self.mock_db,
            market="TW",
            is_active=True,
            search_term="積電",
            skip=5,  # (2-1) * 5
            limit=5
        )

        mock_crud.count_stocks_with_filters.assert_called_once_with(
            self.mock_db,
            market="TW",
            is_active=True,
            search_term="積電"
        )


class TestStocksAPIPerformance(unittest.TestCase):
    """股票API性能測試"""

    def setUp(self):
        """設置測試環境"""
        self.mock_db = AsyncMock()

    @patch('api.v1.stocks.stock_crud')
    async def test_database_calls_optimization(self, mock_crud):
        """測試數據庫調用優化"""
        mock_crud.get_stocks_with_filters.return_value = []
        mock_crud.count_stocks_with_filters.return_value = 0

        await get_stocks(
            market="TW",
            is_active=True,
            search="test",
            page=1,
            page_size=10,
            db=self.mock_db
        )

        # 驗證只有2次數據庫調用：查詢數據 + 計算總數
        self.assertEqual(mock_crud.get_stocks_with_filters.call_count, 1)
        self.assertEqual(mock_crud.count_stocks_with_filters.call_count, 1)

        # 驗證沒有調用舊的低效方法
        self.assertEqual(mock_crud.get_multi.call_count, 0)

    @patch('api.v1.stocks.stock_crud')
    async def test_filter_pushdown_verification(self, mock_crud):
        """驗證過濾條件下推到數據庫層"""
        mock_crud.get_stocks_with_filters.return_value = []
        mock_crud.count_stocks_with_filters.return_value = 0

        await get_stocks(
            market="TW",
            is_active=True,
            search="台積",
            page=1,
            page_size=10,
            db=self.mock_db
        )

        # 驗證所有過濾條件都傳遞給數據庫層
        get_call_args = mock_crud.get_stocks_with_filters.call_args[1]
        count_call_args = mock_crud.count_stocks_with_filters.call_args[1]

        # 檢查get調用參數
        self.assertEqual(get_call_args['market'], "TW")
        self.assertEqual(get_call_args['is_active'], True)
        self.assertEqual(get_call_args['search_term'], "台積")

        # 檢查count調用參數
        self.assertEqual(count_call_args['market'], "TW")
        self.assertEqual(count_call_args['is_active'], True)
        self.assertEqual(count_call_args['search_term'], "台積")


async def run_all_tests():
    """執行所有測試"""
    print("=" * 60)
    print("股票API優化功能測試")
    print("=" * 60)

    # 異步測試
    async_test_classes = [
        TestStocksAPIOptimized,
        TestStocksAPIPerformance
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

    print("\n🎉 所有股票API優化測試都通過了！")
    return True


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)