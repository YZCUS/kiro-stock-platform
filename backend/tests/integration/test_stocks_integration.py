#!/usr/bin/env python3
"""
股票API整合測試
"""
import sys
import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from pathlib import Path
from httpx import AsyncClient

# 添加測試配置路徑
sys.path.insert(0, str(Path(__file__).parent.parent))
from test_config import setup_test_path

# 設置測試環境路徑
setup_test_path()

from app.main import app
from app.dependencies import get_database_session, get_stock_service


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest_asyncio.fixture
async def async_client(mock_db):
    async def override_db():
        yield mock_db

    app.dependency_overrides[get_database_session] = override_db

    client = AsyncClient(app=app, base_url="http://test")
    try:
        yield client
    finally:
        await client.aclose()
        app.dependency_overrides.clear()

class TestStocksIntegration:
    """股票API整合測試"""

    @pytest.mark.asyncio
    async def test_stocks_endpoint_integration(self, async_client):
        """測試股票端點整合"""
        mock_service = AsyncMock()
        mock_service.get_stock_list.return_value = {
            'items': [
                {
                    'id': 1,
                    'symbol': '2330.TW',
                    'market': 'TW',
                    'name': '台積電',
                    'is_active': True,
                    'created_at': '2024-01-01T00:00:00',
                    'updated_at': '2024-01-02T00:00:00'
                }
            ],
            'total': 1,
            'page': 1,
            'per_page': 10,
            'total_pages': 1
        }
        app.dependency_overrides[get_stock_service] = lambda: mock_service

        try:
            response = await async_client.get(
                "/api/v1/stocks/",
                params={
                    "market": "TW",
                    "is_active": True,
                    "page": 1,
                    "per_page": 10
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data['total'] == 1
            assert len(data['items']) == 1
        finally:
            app.dependency_overrides.pop(get_stock_service, None)

    @pytest.mark.asyncio
    async def test_stocks_search_integration(self, async_client):
        """測試股票搜尋整合"""
        mock_service = AsyncMock()
        mock_service.get_stock_list.return_value = {
            'items': [
                {
                    'id': 1,
                    'symbol': '2330.TW',
                    'market': 'TW',
                    'name': '台積電',
                    'is_active': True,
                    'created_at': '2024-01-01T00:00:00',
                    'updated_at': '2024-01-02T00:00:00'
                }
            ],
            'total': 1,
            'page': 1,
            'per_page': 20,
            'total_pages': 1
        }
        app.dependency_overrides[get_stock_service] = lambda: mock_service

        try:
            response = await async_client.get(
                "/api/v1/stocks/search",
                params={
                    "q": "台積",
                    "market": "TW",
                    "page": 1,
                    "per_page": 20
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data['items']) == 1
            assert data['items'][0]['name'] == '台積電'
        finally:
            app.dependency_overrides.pop(get_stock_service, None)

    @pytest.mark.asyncio
    async def test_stocks_simple_endpoint_integration(self, async_client):
        """測試簡化股票端點整合"""
        mock_service = AsyncMock()
        mock_service.get_stock_list.return_value = {
            'items': [
                {
                    'id': 1,
                    'symbol': '2330.TW',
                    'market': 'TW',
                    'name': '台積電',
                    'is_active': True,
                    'created_at': '2024-01-01T00:00:00',
                    'updated_at': '2024-01-02T00:00:00'
                },
                {
                    'id': 2,
                    'symbol': '2317.TW',
                    'market': 'TW',
                    'name': '鴻海',
                    'is_active': True,
                    'created_at': '2024-01-01T00:00:00',
                    'updated_at': '2024-01-02T00:00:00'
                }
            ],
            'total': 2,
            'page': 1,
            'per_page': 100,
            'total_pages': 1
        }
        app.dependency_overrides[get_stock_service] = lambda: mock_service

        try:
            response = await async_client.get(
                "/api/v1/stocks/simple",
                params={
                    "market": "TW",
                    "limit": 100
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 2
        finally:
            app.dependency_overrides.pop(get_stock_service, None)

    @pytest.mark.asyncio
    async def test_stocks_pagination_integration(self, async_client):
        """測試分頁整合"""
        mock_service = AsyncMock()
        mock_service.get_stock_list.return_value = {
            'items': [
                {
                    'id': i,
                    'symbol': f'STOCK{i:03d}.TW',
                    'market': 'TW',
                    'name': f'股票{i}',
                    'is_active': True,
                    'created_at': '2024-01-01T00:00:00',
                    'updated_at': '2024-01-02T00:00:00'
                }
                for i in range(21, 41)
            ],
            'total': 100,
            'page': 2,
            'per_page': 20,
            'total_pages': 5
        }
        app.dependency_overrides[get_stock_service] = lambda: mock_service

        try:
            response = await async_client.get(
                "/api/v1/stocks/",
                params={
                    "market": "TW",
                    "page": 2,
                    "per_page": 20
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data['page'] == 2
            assert data['per_page'] == 20
            assert data['total'] == 100
            assert data['total_pages'] == 5
            assert len(data['items']) == 20
        finally:
            app.dependency_overrides.pop(get_stock_service, None)

    @pytest.mark.asyncio
    async def test_stocks_error_handling_integration(self, async_client):
        """測試錯誤處理整合"""
        mock_service = AsyncMock()
        mock_service.get_stock_list.side_effect = Exception("Service failure")
        app.dependency_overrides[get_stock_service] = lambda: mock_service

        try:
            response = await async_client.get(
                "/api/v1/stocks/",
                params={"market": "TW"}
            )

            assert response.status_code == 500
        finally:
            app.dependency_overrides.pop(get_stock_service, None)

    @pytest.mark.asyncio
    async def test_stocks_parameter_validation_integration(self):
        """測試參數驗證整合"""
        app.dependency_overrides[get_stock_service] = lambda: AsyncMock()
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/stocks/",
                params={
                    "page": 0,
                    "per_page": 10
                }
            )
            assert response.status_code == 422

            response = await client.get(
                "/api/v1/stocks/",
                params={
                    "page": 1,
                    "per_page": 300
                }
            )
            assert response.status_code == 422
        app.dependency_overrides.pop(get_stock_service, None)

    @pytest.mark.asyncio
    async def test_stocks_market_filter_integration(self, async_client):
        """測試市場過濾整合"""
        mock_service = AsyncMock()
        mock_service.get_stock_list.return_value = {
            'items': [
                {
                    'id': 1,
                    'symbol': 'AAPL',
                    'market': 'US',
                    'name': 'Apple Inc.',
                    'is_active': True,
                    'created_at': '2024-01-01T00:00:00',
                    'updated_at': '2024-01-02T00:00:00'
                }
            ],
            'total': 1,
            'page': 1,
            'per_page': 50,
            'total_pages': 1
        }
        app.dependency_overrides[get_stock_service] = lambda: mock_service

        try:
            response = await async_client.get(
                "/api/v1/stocks/",
                params={"market": "US"}
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data['items']) == 1
            assert data['items'][0]['market'] == 'US'
        finally:
            app.dependency_overrides.pop(get_stock_service, None)


class TestStocksPerformanceIntegration:
    """股票API性能整合測試"""

    @pytest.mark.asyncio
    async def test_concurrent_requests_integration(self, async_client):
        """測試並發請求整合"""
        mock_service = AsyncMock()
        mock_service.get_stock_list.return_value = {
            'items': [],
            'total': 0,
            'page': 1,
            'per_page': 10,
            'total_pages': 0
        }
        app.dependency_overrides[get_stock_service] = lambda: mock_service

        try:
            tasks = [
                async_client.get(
                    "/api/v1/stocks/",
                    params={
                        "market": "TW",
                        "search": f"test{i}",
                        "page": 1,
                        "per_page": 10
                    }
                )
                for i in range(5)
            ]

            responses = await asyncio.gather(*tasks)

            for response in responses:
                assert response.status_code == 200
                data = response.json()
                assert data['total'] == 0
                assert len(data['items']) == 0
        finally:
            app.dependency_overrides.pop(get_stock_service, None)

    @pytest.mark.asyncio
    async def test_large_dataset_pagination_integration(self, async_client):
        """測試大數據集分頁整合"""
        mock_service = AsyncMock()
        mock_service.get_stock_list.return_value = {
            'items': [
                {
                    'id': i,
                    'symbol': f'STOCK{i:05d}.TW',
                    'market': 'TW',
                    'name': f'股票{i}',
                    'is_active': True,
                    'created_at': '2024-01-01T00:00:00',
                    'updated_at': '2024-01-02T00:00:00'
                }
                for i in range(100)
            ],
            'total': 10000,
            'page': 1,
            'per_page': 100,
            'total_pages': 100
        }
        app.dependency_overrides[get_stock_service] = lambda: mock_service

        try:
            response = await async_client.get(
                "/api/v1/stocks/",
                params={
                    "market": "TW",
                    "page": 1,
                    "per_page": 100
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data['total'] == 10000
            assert data['total_pages'] == 100
            assert len(data['items']) == 100
        finally:
            app.dependency_overrides.pop(get_stock_service, None)

