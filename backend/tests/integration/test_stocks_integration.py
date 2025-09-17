#!/usr/bin/env python3
"""
股票API整合測試
"""
import sys
import asyncio
import unittest
from unittest.mock import AsyncMock, patch
from pathlib import Path
from httpx import AsyncClient

# 添加測試配置路徑
sys.path.insert(0, str(Path(__file__).parent.parent))
from test_config import setup_test_path

# 設置測試環境路徑
setup_test_path()

from app.main import app
from core.database import get_db_session


class TestStocksIntegration(unittest.TestCase):
    """股票API整合測試"""

    def setUp(self):
        """設置測試環境"""
        self.mock_db = AsyncMock()

    async def test_stocks_endpoint_integration(self):
        """測試股票端點整合"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('core.database.get_db_session', return_value=self.mock_db):
                with patch('api.v1.stocks.stock_crud') as mock_crud:
                    # 設置mock返回值
                    mock_crud.get_stocks_with_filters.return_value = [
                        type('Stock', (), {
                            'id': 1,
                            'symbol': '2330.TW',
                            'market': 'TW',
                            'name': '台積電',
                            'is_active': True
                        })()
                    ]
                    mock_crud.count_stocks_with_filters.return_value = 1

                    # 測試GET /api/v1/stocks/
                    response = await client.get(
                        "/api/v1/stocks/",
                        params={
                            "market": "TW",
                            "is_active": True,
                            "page": 1,
                            "page_size": 10
                        }
                    )

                    # 驗證響應
                    self.assertEqual(response.status_code, 200)
                    data = response.json()

                    # 驗證響應結構
                    self.assertIn('items', data)
                    self.assertIn('total', data)
                    self.assertIn('page', data)
                    self.assertIn('page_size', data)
                    self.assertIn('total_pages', data)

                    # 驗證數據
                    self.assertEqual(len(data['items']), 1)
                    self.assertEqual(data['total'], 1)
                    self.assertEqual(data['page'], 1)
                    self.assertEqual(data['page_size'], 10)

    async def test_stocks_search_integration(self):
        """測試股票搜尋整合"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('core.database.get_db_session', return_value=self.mock_db):
                with patch('api.v1.stocks.search_stocks') as mock_search:
                    # 設置mock返回值
                    mock_search.return_value = {
                        'items': [
                            {
                                'id': 1,
                                'symbol': '2330.TW',
                                'market': 'TW',
                                'name': '台積電',
                                'is_active': True
                            }
                        ],
                        'total': 1,
                        'page': 1,
                        'page_size': 20,
                        'total_pages': 1
                    }

                    # 測試GET /api/v1/stocks/search
                    response = await client.get(
                        "/api/v1/stocks/search",
                        params={
                            "q": "台積",
                            "market": "TW",
                            "page": 1,
                            "page_size": 20
                        }
                    )

                    # 驗證響應
                    self.assertEqual(response.status_code, 200)
                    data = response.json()

                    # 驗證搜尋結果
                    self.assertEqual(len(data['items']), 1)
                    self.assertEqual(data['items'][0]['name'], '台積電')

    async def test_stocks_simple_endpoint_integration(self):
        """測試簡化股票端點整合"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('core.database.get_db_session', return_value=self.mock_db):
                with patch('api.v1.stocks.get_stocks_simple') as mock_simple:
                    # 設置mock返回值
                    mock_simple.return_value = [
                        {
                            'id': 1,
                            'symbol': '2330.TW',
                            'market': 'TW',
                            'name': '台積電',
                            'is_active': True
                        },
                        {
                            'id': 2,
                            'symbol': '2317.TW',
                            'market': 'TW',
                            'name': '鴻海',
                            'is_active': True
                        }
                    ]

                    # 測試GET /api/v1/stocks/simple
                    response = await client.get(
                        "/api/v1/stocks/simple",
                        params={
                            "market": "TW",
                            "limit": 100
                        }
                    )

                    # 驗證響應
                    self.assertEqual(response.status_code, 200)
                    data = response.json()

                    # 驗證是簡單列表格式
                    self.assertIsInstance(data, list)
                    self.assertEqual(len(data), 2)

    async def test_stocks_pagination_integration(self):
        """測試分頁整合"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('core.database.get_db_session', return_value=self.mock_db):
                with patch('api.v1.stocks.stock_crud') as mock_crud:
                    # 設置mock返回值 - 總共100條記錄
                    mock_crud.count_stocks_with_filters.return_value = 100
                    mock_crud.get_stocks_with_filters.return_value = [
                        type('Stock', (), {
                            'id': i,
                            'symbol': f'STOCK{i:03d}.TW',
                            'market': 'TW',
                            'name': f'股票{i}',
                            'is_active': True
                        })()
                        for i in range(21, 41)  # 第2頁的20條記錄
                    ]

                    # 測試第2頁
                    response = await client.get(
                        "/api/v1/stocks/",
                        params={
                            "market": "TW",
                            "page": 2,
                            "page_size": 20
                        }
                    )

                    # 驗證響應
                    self.assertEqual(response.status_code, 200)
                    data = response.json()

                    # 驗證分頁信息
                    self.assertEqual(data['page'], 2)
                    self.assertEqual(data['page_size'], 20)
                    self.assertEqual(data['total'], 100)
                    self.assertEqual(data['total_pages'], 5)  # 100 / 20
                    self.assertEqual(len(data['items']), 20)

    async def test_stocks_error_handling_integration(self):
        """測試錯誤處理整合"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('core.database.get_db_session', return_value=self.mock_db):
                with patch('api.v1.stocks.stock_crud') as mock_crud:
                    # 模擬數據庫錯誤
                    mock_crud.get_stocks_with_filters.side_effect = Exception("Database error")

                    # 測試錯誤響應
                    response = await client.get(
                        "/api/v1/stocks/",
                        params={"market": "TW"}
                    )

                    # 驗證錯誤響應
                    self.assertEqual(response.status_code, 500)

    async def test_stocks_parameter_validation_integration(self):
        """測試參數驗證整合"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 測試無效的頁碼
            response = await client.get(
                "/api/v1/stocks/",
                params={
                    "page": 0,  # 無效：應該 >= 1
                    "page_size": 10
                }
            )
            self.assertEqual(response.status_code, 422)

            # 測試無效的頁面大小
            response = await client.get(
                "/api/v1/stocks/",
                params={
                    "page": 1,
                    "page_size": 300  # 無效：應該 <= 200
                }
            )
            self.assertEqual(response.status_code, 422)

    async def test_stocks_market_filter_integration(self):
        """測試市場過濾整合"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('core.database.get_db_session', return_value=self.mock_db):
                with patch('api.v1.stocks.stock_crud') as mock_crud:
                    # 設置美股數據
                    mock_crud.get_stocks_with_filters.return_value = [
                        type('Stock', (), {
                            'id': 1,
                            'symbol': 'AAPL',
                            'market': 'US',
                            'name': 'Apple Inc.',
                            'is_active': True
                        })()
                    ]
                    mock_crud.count_stocks_with_filters.return_value = 1

                    # 測試美股過濾
                    response = await client.get(
                        "/api/v1/stocks/",
                        params={"market": "US"}
                    )

                    # 驗證響應
                    self.assertEqual(response.status_code, 200)
                    data = response.json()

                    # 驗證過濾結果
                    self.assertEqual(len(data['items']), 1)
                    self.assertEqual(data['items'][0]['market'], 'US')

                    # 驗證CRUD被正確調用
                    mock_crud.get_stocks_with_filters.assert_called_once()
                    call_kwargs = mock_crud.get_stocks_with_filters.call_args[1]
                    self.assertEqual(call_kwargs['market'], 'US')


class TestStocksPerformanceIntegration(unittest.TestCase):
    """股票API性能整合測試"""

    def setUp(self):
        """設置測試環境"""
        self.mock_db = AsyncMock()

    async def test_concurrent_requests_integration(self):
        """測試並發請求整合"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('core.database.get_db_session', return_value=self.mock_db):
                with patch('api.v1.stocks.stock_crud') as mock_crud:
                    # 設置mock返回值
                    mock_crud.get_stocks_with_filters.return_value = []
                    mock_crud.count_stocks_with_filters.return_value = 0

                    # 創建多個並發請求
                    tasks = []
                    for i in range(5):
                        task = client.get(
                            "/api/v1/stocks/",
                            params={
                                "market": "TW",
                                "search": f"test{i}",
                                "page": 1,
                                "page_size": 10
                            }
                        )
                        tasks.append(task)

                    # 執行並發請求
                    responses = await asyncio.gather(*tasks)

                    # 驗證所有請求都成功
                    for response in responses:
                        self.assertEqual(response.status_code, 200)
                        data = response.json()
                        self.assertEqual(data['total'], 0)
                        self.assertEqual(len(data['items']), 0)

    async def test_large_dataset_pagination_integration(self):
        """測試大數據集分頁整合"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('core.database.get_db_session', return_value=self.mock_db):
                with patch('api.v1.stocks.stock_crud') as mock_crud:
                    # 模擬大數據集
                    mock_crud.count_stocks_with_filters.return_value = 10000
                    mock_crud.get_stocks_with_filters.return_value = [
                        type('Stock', (), {
                            'id': i,
                            'symbol': f'STOCK{i:05d}.TW',
                            'market': 'TW',
                            'name': f'股票{i}',
                            'is_active': True
                        })()
                        for i in range(100)  # 返回100條記錄
                    ]

                    # 測試大頁面大小
                    response = await client.get(
                        "/api/v1/stocks/",
                        params={
                            "market": "TW",
                            "page": 1,
                            "page_size": 100
                        }
                    )

                    # 驗證響應
                    self.assertEqual(response.status_code, 200)
                    data = response.json()

                    # 驗證大數據集處理
                    self.assertEqual(data['total'], 10000)
                    self.assertEqual(data['total_pages'], 100)  # 10000 / 100
                    self.assertEqual(len(data['items']), 100)

                    # 驗證數據庫調用優化
                    self.assertEqual(mock_crud.get_stocks_with_filters.call_count, 1)
                    self.assertEqual(mock_crud.count_stocks_with_filters.call_count, 1)


async def run_all_tests():
    """執行所有測試"""
    print("=" * 60)
    print("股票API整合測試")
    print("=" * 60)

    # 異步測試
    async_test_classes = [
        TestStocksIntegration,
        TestStocksPerformanceIntegration
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

    print("\n🎉 所有股票API整合測試都通過了！")
    return True


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)