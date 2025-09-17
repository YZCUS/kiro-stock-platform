#!/usr/bin/env python3
"""
股票CRUD優化功能測試
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

from models.repositories.crud_stock import stock_crud
from models.domain.stock import Stock


class TestStockCRUDOptimized(unittest.TestCase):
    """股票CRUD優化功能測試"""

    def setUp(self):
        """設置測試環境"""
        self.mock_db = AsyncMock()
        self.mock_result = Mock()
        self.mock_scalars = Mock()

    async def test_get_stocks_with_filters_market_only(self):
        """測試按市場過濾獲取股票"""
        # 模擬數據庫返回
        mock_stocks = [
            Mock(id=1, symbol="2330.TW", market="TW", name="台積電", is_active=True),
            Mock(id=2, symbol="2317.TW", market="TW", name="鴻海", is_active=True)
        ]

        self.mock_scalars.all.return_value = mock_stocks
        self.mock_result.scalars.return_value = self.mock_scalars
        self.mock_db.execute.return_value = self.mock_result

        # 測試調用
        result = await stock_crud.get_stocks_with_filters(
            self.mock_db,
            market="TW",
            skip=0,
            limit=10
        )

        # 驗證結果
        self.assertEqual(len(result), 2)
        self.mock_db.execute.assert_called_once()

        # 驗證SQL查詢包含market過濾條件
        call_args = self.mock_db.execute.call_args[0][0]
        query_str = str(call_args)
        self.assertIn("market", query_str.lower())

    async def test_get_stocks_with_filters_active_status(self):
        """測試按活躍狀態過濾獲取股票"""
        mock_stocks = [
            Mock(id=1, symbol="2330.TW", market="TW", name="台積電", is_active=True)
        ]

        self.mock_scalars.all.return_value = mock_stocks
        self.mock_result.scalars.return_value = self.mock_scalars
        self.mock_db.execute.return_value = self.mock_result

        result = await stock_crud.get_stocks_with_filters(
            self.mock_db,
            is_active=True,
            skip=0,
            limit=10
        )

        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].is_active)

    async def test_get_stocks_with_filters_search_term(self):
        """測試按搜尋關鍵字過濾獲取股票"""
        mock_stocks = [
            Mock(id=1, symbol="2330.TW", market="TW", name="台積電", is_active=True)
        ]

        self.mock_scalars.all.return_value = mock_stocks
        self.mock_result.scalars.return_value = self.mock_scalars
        self.mock_db.execute.return_value = self.mock_result

        result = await stock_crud.get_stocks_with_filters(
            self.mock_db,
            search_term="台積",
            skip=0,
            limit=10
        )

        self.assertEqual(len(result), 1)

        # 驗證查詢包含搜尋條件
        call_args = self.mock_db.execute.call_args[0][0]
        query_str = str(call_args)
        self.assertIn("ilike", query_str.lower())

    async def test_get_stocks_with_filters_combined(self):
        """測試組合過濾條件"""
        mock_stocks = [
            Mock(id=1, symbol="2330.TW", market="TW", name="台積電", is_active=True)
        ]

        self.mock_scalars.all.return_value = mock_stocks
        self.mock_result.scalars.return_value = self.mock_scalars
        self.mock_db.execute.return_value = self.mock_result

        result = await stock_crud.get_stocks_with_filters(
            self.mock_db,
            market="TW",
            is_active=True,
            search_term="台積",
            skip=0,
            limit=10
        )

        self.assertEqual(len(result), 1)

        # 驗證所有條件都被應用
        call_args = self.mock_db.execute.call_args[0][0]
        query_str = str(call_args).lower()
        self.assertIn("market", query_str)
        self.assertIn("is_active", query_str)
        self.assertIn("ilike", query_str)

    async def test_get_stocks_with_filters_pagination(self):
        """測試分頁功能"""
        mock_stocks = [
            Mock(id=3, symbol="2454.TW", market="TW", name="聯發科", is_active=True),
            Mock(id=4, symbol="2881.TW", market="TW", name="富邦金", is_active=True)
        ]

        self.mock_scalars.all.return_value = mock_stocks
        self.mock_result.scalars.return_value = self.mock_scalars
        self.mock_db.execute.return_value = self.mock_result

        # 測試第二頁，每頁2條
        result = await stock_crud.get_stocks_with_filters(
            self.mock_db,
            market="TW",
            skip=2,
            limit=2
        )

        self.assertEqual(len(result), 2)

        # 驗證包含OFFSET和LIMIT
        call_args = self.mock_db.execute.call_args[0][0]
        query_str = str(call_args).lower()
        self.assertIn("offset", query_str)
        self.assertIn("limit", query_str)

    async def test_count_stocks_with_filters_market(self):
        """測試按市場計算股票總數"""
        # 模擬計數結果
        self.mock_result.scalar.return_value = 15
        self.mock_db.execute.return_value = self.mock_result

        result = await stock_crud.count_stocks_with_filters(
            self.mock_db,
            market="TW"
        )

        self.assertEqual(result, 15)

        # 驗證使用COUNT查詢
        call_args = self.mock_db.execute.call_args[0][0]
        query_str = str(call_args).lower()
        self.assertIn("count", query_str)
        self.assertIn("market", query_str)

    async def test_count_stocks_with_filters_search(self):
        """測試按搜尋條件計算股票總數"""
        self.mock_result.scalar.return_value = 5
        self.mock_db.execute.return_value = self.mock_result

        result = await stock_crud.count_stocks_with_filters(
            self.mock_db,
            search_term="科技"
        )

        self.assertEqual(result, 5)

        # 驗證查詢包含搜尋條件
        call_args = self.mock_db.execute.call_args[0][0]
        query_str = str(call_args).lower()
        self.assertIn("count", query_str)
        self.assertIn("ilike", query_str)

    async def test_count_stocks_with_filters_combined(self):
        """測試組合過濾條件計算總數"""
        self.mock_result.scalar.return_value = 3
        self.mock_db.execute.return_value = self.mock_result

        result = await stock_crud.count_stocks_with_filters(
            self.mock_db,
            market="TW",
            is_active=True,
            search_term="金融"
        )

        self.assertEqual(result, 3)

    async def test_search_by_symbol_with_market(self):
        """測試按股票代號搜尋（指定市場）"""
        mock_stocks = [
            Mock(id=1, symbol="2330.TW", market="TW", name="台積電", is_active=True)
        ]

        self.mock_scalars.all.return_value = mock_stocks
        self.mock_result.scalars.return_value = self.mock_scalars
        self.mock_db.execute.return_value = self.mock_result

        result = await stock_crud.search_by_symbol(
            self.mock_db,
            symbol="2330",
            market="TW",
            limit=20
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].symbol, "2330.TW")

    async def test_search_by_symbol_without_market(self):
        """測試按股票代號搜尋（不指定市場）"""
        mock_stocks = [
            Mock(id=1, symbol="2330.TW", market="TW", name="台積電", is_active=True),
            Mock(id=2, symbol="AAPL", market="US", name="Apple", is_active=True)
        ]

        self.mock_scalars.all.return_value = mock_stocks
        self.mock_result.scalars.return_value = self.mock_scalars
        self.mock_db.execute.return_value = self.mock_result

        result = await stock_crud.search_by_symbol(
            self.mock_db,
            symbol="A",
            limit=20
        )

        self.assertEqual(len(result), 2)

    async def test_get_stocks_with_filters_no_conditions(self):
        """測試無過濾條件時的行為"""
        mock_stocks = [
            Mock(id=1, symbol="2330.TW", market="TW", name="台積電", is_active=True),
            Mock(id=2, symbol="AAPL", market="US", name="Apple", is_active=True)
        ]

        self.mock_scalars.all.return_value = mock_stocks
        self.mock_result.scalars.return_value = self.mock_scalars
        self.mock_db.execute.return_value = self.mock_result

        result = await stock_crud.get_stocks_with_filters(
            self.mock_db,
            skip=0,
            limit=10
        )

        self.assertEqual(len(result), 2)

        # 驗證基本查詢結構
        call_args = self.mock_db.execute.call_args[0][0]
        query_str = str(call_args).lower()
        self.assertIn("select", query_str)
        self.assertIn("order by", query_str)

    async def test_get_stocks_with_filters_empty_result(self):
        """測試空結果的處理"""
        self.mock_scalars.all.return_value = []
        self.mock_result.scalars.return_value = self.mock_scalars
        self.mock_db.execute.return_value = self.mock_result

        result = await stock_crud.get_stocks_with_filters(
            self.mock_db,
            market="INVALID",
            skip=0,
            limit=10
        )

        self.assertEqual(len(result), 0)

    async def test_count_stocks_with_filters_zero_count(self):
        """測試零計數的處理"""
        self.mock_result.scalar.return_value = 0
        self.mock_db.execute.return_value = self.mock_result

        result = await stock_crud.count_stocks_with_filters(
            self.mock_db,
            market="INVALID"
        )

        self.assertEqual(result, 0)


class TestStockCRUDCompatibility(unittest.TestCase):
    """股票CRUD向後兼容性測試"""

    def setUp(self):
        """設置測試環境"""
        self.mock_db = AsyncMock()

    async def test_get_by_symbol_and_market_exists(self):
        """測試get_by_symbol_and_market方法存在性"""
        self.assertTrue(hasattr(stock_crud, 'get_by_symbol_and_market'))
        self.assertTrue(callable(getattr(stock_crud, 'get_by_symbol_and_market')))

    async def test_search_by_symbol_exists(self):
        """測試search_by_symbol方法存在性"""
        self.assertTrue(hasattr(stock_crud, 'search_by_symbol'))
        self.assertTrue(callable(getattr(stock_crud, 'search_by_symbol')))


async def run_all_tests():
    """執行所有測試"""
    print("=" * 60)
    print("股票CRUD優化功能測試")
    print("=" * 60)

    # 異步測試
    async_test_classes = [
        TestStockCRUDOptimized,
        TestStockCRUDCompatibility
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

    print("\n🎉 所有股票CRUD優化測試都通過了！")
    return True


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)