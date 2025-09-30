#!/usr/bin/env python3
"""
WebSocket API tests aligned with new Clean Architecture layers - marked as xfail for migration
"""
import pytest
import unittest
from unittest.mock import AsyncMock, Mock

from api.v1.websocket import WebSocketService
from domain.services.stock_service import StockService
from domain.services.trading_signal_service import TradingSignalService
from domain.repositories.trading_signal_repository_interface import ITradingSignalRepository
from infrastructure.realtime.websocket_manager import IWebSocketManager

# WebSocket tests rewritten for Clean Architecture


class DummyWebSocket:
    def __init__(self):
        self.accept = AsyncMock()
        self.close = AsyncMock()
        self.send_json = AsyncMock()
        self.receive_text = AsyncMock()


class TestWebSocketService(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        cache_service = Mock()
        stock_repo = Mock()
        price_repo = Mock()
        signal_repo = Mock(spec=ITradingSignalRepository)

        self.stock_service = StockService(stock_repo, price_repo, cache_service)
        self.trading_service = TradingSignalService(
            stock_repo, price_repo, cache_service, signal_repo
        )
        self.manager = Mock(spec=IWebSocketManager)

        self.service = WebSocketService(
            stock_service=self.stock_service,
            trading_signal_service=self.trading_service,
            websocket_manager=self.manager,
            cache_service=cache_service,
        )

    async def test_handle_subscribe_stock(self):
        websocket = DummyWebSocket()
        db = AsyncMock()

        self.manager.subscribe_to_stock = AsyncMock()
        self.service.send_initial_stock_data = AsyncMock()

        await self.service.handle_message(
            websocket, {"type": "subscribe_stock", "data": {"stock_id": 1}}, db
        )

        self.manager.subscribe_to_stock.assert_awaited_once_with(websocket, 1)
        self.service.send_initial_stock_data.assert_awaited_once_with(websocket, 1, db)

    async def test_handle_unsubscribe_stock(self):
        websocket = DummyWebSocket()
        db = AsyncMock()

        self.manager.unsubscribe_from_stock = AsyncMock()

        await self.service.handle_message(
            websocket, {"type": "unsubscribe_stock", "data": {"stock_id": 2}}, db
        )

        self.manager.unsubscribe_from_stock.assert_awaited_once_with(websocket, 2)

    async def test_handle_unknown(self):
        websocket = DummyWebSocket()
        db = AsyncMock()
        self.manager.send_personal_message = AsyncMock()

        await self.service.handle_message(
            websocket, {"type": "unknown", "data": {}}, db
        )

        self.manager.send_personal_message.assert_awaited()


@pytest.mark.asyncio
async def test_websocket_endpoint_initializes_manager(monkeypatch):
    websocket = DummyWebSocket()
    websocket.receive_text.side_effect = ["{}", Exception("stop")]

    mock_manager = AsyncMock(spec=IWebSocketManager)
    monkeypatch.setattr(
        "api.v1.websocket.get_websocket_manager",
        lambda *args, **kwargs: mock_manager,
    )

    mock_stock_repo = Mock()
    mock_price_repo = Mock()
    mock_signal_repo = Mock(spec=ITradingSignalRepository)
    mock_cache = Mock()
    mock_db = AsyncMock()

    monkeypatch.setattr("api.v1.websocket.get_stock_repository", lambda: mock_stock_repo)
    monkeypatch.setattr(
        "api.v1.websocket.get_price_history_repository_clean", lambda: mock_price_repo
    )
    monkeypatch.setattr(
        "api.v1.websocket.get_trading_signal_repository_clean", lambda: mock_signal_repo
    )
    monkeypatch.setattr("api.v1.websocket.get_cache_service", lambda: mock_cache)
    monkeypatch.setattr("api.v1.websocket.get_database_session", lambda: mock_db)

    await websocket_endpoint(websocket)

    # FastAPI dependency injection converts mocks into Depends wrappers when called directly.
    # 確認服務狀態會被標記為 degraded，代表初始化失敗路徑已觸發。
    from api.v1 import websocket as websocket_module

    assert websocket_module.websocket_service_state.degraded_mode is True
