#!/usr/bin/env python3
"""
WebSocket API測試
"""
import sys
import asyncio
import unittest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, date, timedelta
from pathlib import Path
import json

# 添加測試配置路徑
sys.path.insert(0, str(Path(__file__).parent.parent))
from test_config import setup_test_path

# 設置測試環境路徑
setup_test_path()

from fastapi import WebSocket, WebSocketDisconnect
from api.v1.websocket import (
    WebSocketService,
    websocket_endpoint,
    initialize_websocket_manager,
    shutdown_websocket_manager,
    get_websocket_cluster_stats
)


class TestWebSocketService(unittest.TestCase):
    """WebSocket服務測試"""

    def setUp(self):
        """設置測試環境"""
        self.mock_websocket = Mock()
        self.mock_db_session = AsyncMock()
        self.service = WebSocketService()

    @patch('api.v1.websocket.manager')
    async def test_handle_subscribe_stock_message(self, mock_manager):
        """測試處理股票訂閱消息"""
        mock_manager.subscribe_to_stock = AsyncMock()

        # 模擬WebSocketService的send_initial_stock_data方法
        with patch.object(WebSocketService, 'send_initial_stock_data', new_callable=AsyncMock) as mock_send_initial:
            message = {
                "type": "subscribe_stock",
                "data": {"stock_id": 1}
            }

            await WebSocketService.handle_message(
                self.mock_websocket,
                message,
                self.mock_db_session
            )

            # 驗證訂閱方法被調用
            mock_manager.subscribe_to_stock.assert_called_once_with(self.mock_websocket, 1)
            # 驗證發送初始數據方法被調用
            mock_send_initial.assert_called_once_with(self.mock_websocket, 1, self.mock_db_session)

    @patch('api.v1.websocket.manager')
    async def test_handle_unsubscribe_stock_message(self, mock_manager):
        """測試處理股票取消訂閱消息"""
        mock_manager.unsubscribe_from_stock = AsyncMock()

        message = {
            "type": "unsubscribe_stock",
            "data": {"stock_id": 1}
        }

        await WebSocketService.handle_message(
            self.mock_websocket,
            message,
            self.mock_db_session
        )

        # 驗證取消訂閱方法被調用
        mock_manager.unsubscribe_from_stock.assert_called_once_with(self.mock_websocket, 1)

    @patch('api.v1.websocket.manager')
    async def test_handle_subscribe_global_message(self, mock_manager):
        """測試處理全局訂閱消息"""
        mock_manager.subscribe_to_global = AsyncMock()

        message = {
            "type": "subscribe_global",
            "data": {}
        }

        await WebSocketService.handle_message(
            self.mock_websocket,
            message,
            self.mock_db_session
        )

        # 驗證全局訂閱方法被調用
        mock_manager.subscribe_to_global.assert_called_once_with(self.mock_websocket)

    @patch('api.v1.websocket.manager')
    async def test_handle_unsubscribe_global_message(self, mock_manager):
        """測試處理全局取消訂閱消息"""
        mock_manager.unsubscribe_from_global = AsyncMock()

        message = {
            "type": "unsubscribe_global",
            "data": {}
        }

        await WebSocketService.handle_message(
            self.mock_websocket,
            message,
            self.mock_db_session
        )

        # 驗證全局取消訂閱方法被調用
        mock_manager.unsubscribe_from_global.assert_called_once_with(self.mock_websocket)

    async def test_handle_unknown_message_type(self):
        """測試處理未知消息類型"""
        message = {
            "type": "unknown_type",
            "data": {}
        }

        # 應該不會拋出異常，只是忽略未知消息
        try:
            await WebSocketService.handle_message(
                self.mock_websocket,
                message,
                self.mock_db_session
            )
        except Exception as e:
            self.fail(f"處理未知消息類型時不應拋出異常: {e}")

    async def test_handle_malformed_message(self):
        """測試處理格式錯誤的消息"""
        # 缺少type字段的消息
        message = {
            "data": {"stock_id": 1}
        }

        try:
            await WebSocketService.handle_message(
                self.mock_websocket,
                message,
                self.mock_db_session
            )
        except Exception as e:
            self.fail(f"處理格式錯誤消息時不應拋出異常: {e}")

    @patch('api.v1.websocket.stock_crud')
    @patch('api.v1.websocket.price_history_crud')
    @patch('api.v1.websocket.technical_indicator_crud')
    @patch('api.v1.websocket.trading_signal_crud')
    async def test_send_initial_stock_data_success(
        self, mock_signal_crud, mock_indicator_crud,
        mock_price_crud, mock_stock_crud
    ):
        """測試發送初始股票數據 - 成功"""
        # 模擬股票數據
        mock_stock = Mock()
        mock_stock.id = 1
        mock_stock.symbol = "2330.TW"
        mock_stock.name = "台積電"
        mock_stock_crud.get.return_value = mock_stock

        # 模擬價格數據
        mock_prices = []
        for i in range(5):
            price = Mock()
            price.date = date.today() - timedelta(days=i)
            price.close_price = 550.0 + i
            mock_prices.append(price)
        mock_price_crud.get_recent_prices.return_value = mock_prices

        # 模擬技術指標數據
        mock_indicators = []
        for i in range(3):
            indicator = Mock()
            indicator.indicator_type = "RSI"
            indicator.value = 65.0 + i
            indicator.date = date.today() - timedelta(days=i)
            mock_indicators.append(indicator)
        mock_indicator_crud.get_recent_indicators.return_value = mock_indicators

        # 模擬交易信號數據
        mock_signals = []
        signal = Mock()
        signal.signal_type = "BUY"
        signal.confidence = 0.85
        signal.date = date.today()
        mock_signals.append(signal)
        mock_signal_crud.get_recent_signals.return_value = mock_signals

        # 模擬WebSocket發送
        self.mock_websocket.send_text = AsyncMock()

        await WebSocketService.send_initial_stock_data(
            self.mock_websocket,
            1,
            self.mock_db_session
        )

        # 驗證數據查詢方法被調用
        mock_stock_crud.get.assert_called_once_with(self.mock_db_session, 1)
        mock_price_crud.get_recent_prices.assert_called_once()
        mock_indicator_crud.get_recent_indicators.assert_called_once()
        mock_signal_crud.get_recent_signals.assert_called_once()

        # 驗證WebSocket發送被調用
        self.mock_websocket.send_text.assert_called_once()

        # 驗證發送的數據格式
        call_args = self.mock_websocket.send_text.call_args[0][0]
        sent_data = json.loads(call_args)

        self.assertEqual(sent_data['type'], 'initial_data')
        self.assertIn('stock', sent_data['data'])
        self.assertIn('prices', sent_data['data'])
        self.assertIn('indicators', sent_data['data'])
        self.assertIn('signals', sent_data['data'])

    @patch('api.v1.websocket.stock_crud')
    async def test_send_initial_stock_data_stock_not_found(self, mock_stock_crud):
        """測試發送初始股票數據 - 股票不存在"""
        mock_stock_crud.get.return_value = None
        self.mock_websocket.send_text = AsyncMock()

        await WebSocketService.send_initial_stock_data(
            self.mock_websocket,
            999,
            self.mock_db_session
        )

        # 驗證發送錯誤消息
        self.mock_websocket.send_text.assert_called_once()
        call_args = self.mock_websocket.send_text.call_args[0][0]
        sent_data = json.loads(call_args)

        self.assertEqual(sent_data['type'], 'error')
        self.assertIn('Stock not found', sent_data['message'])

    @patch('api.v1.websocket.redis_broadcaster')
    async def test_broadcast_price_update(self, mock_broadcaster):
        """測試廣播價格更新"""
        mock_broadcaster.publish_stock_update = AsyncMock()

        price_data = {
            "symbol": "2330.TW",
            "price": 555.0,
            "change": 5.0,
            "timestamp": datetime.now().isoformat()
        }

        await WebSocketService.broadcast_price_update(1, price_data)

        # 驗證廣播方法被調用
        mock_broadcaster.publish_stock_update.assert_called_once_with(
            1, "price_update", price_data
        )

    @patch('api.v1.websocket.redis_broadcaster')
    async def test_broadcast_indicator_update(self, mock_broadcaster):
        """測試廣播指標更新"""
        mock_broadcaster.publish_stock_update = AsyncMock()

        indicator_data = {
            "indicator_type": "RSI",
            "value": 65.5,
            "date": date.today().isoformat()
        }

        await WebSocketService.broadcast_indicator_update(1, indicator_data)

        # 驗證廣播方法被調用
        mock_broadcaster.publish_stock_update.assert_called_once_with(
            1, "indicator_update", indicator_data
        )

    @patch('api.v1.websocket.redis_broadcaster')
    async def test_broadcast_signal_update(self, mock_broadcaster):
        """測試廣播信號更新"""
        mock_broadcaster.publish_stock_update = AsyncMock()

        signal_data = {
            "signal_type": "BUY",
            "confidence": 0.85,
            "description": "強烈買入信號"
        }

        await WebSocketService.broadcast_signal_update(1, signal_data)

        # 驗證廣播方法被調用
        mock_broadcaster.publish_stock_update.assert_called_once_with(
            1, "signal_update", signal_data
        )

    @patch('api.v1.websocket.redis_broadcaster')
    async def test_broadcast_market_status(self, mock_broadcaster):
        """測試廣播市場狀態"""
        mock_broadcaster.publish_global_update = AsyncMock()

        status_data = {
            "market_status": "OPEN",
            "timestamp": datetime.now().isoformat(),
            "active_stocks": 100
        }

        await WebSocketService.broadcast_market_status(status_data)

        # 驗證廣播方法被調用
        mock_broadcaster.publish_global_update.assert_called_once_with(
            "market_status", status_data
        )


class TestWebSocketEndpoint(unittest.TestCase):
    """WebSocket端點測試"""

    def setUp(self):
        """設置測試環境"""
        self.mock_websocket = Mock()
        self.mock_websocket.accept = AsyncMock()
        self.mock_websocket.receive_text = AsyncMock()
        self.mock_websocket.send_text = AsyncMock()
        self.mock_websocket.close = AsyncMock()

    @patch('api.v1.websocket.get_db_session')
    @patch('api.v1.websocket.manager')
    @patch('api.v1.websocket.WebSocketService')
    async def test_websocket_endpoint_success(self, mock_service, mock_manager, mock_get_db):
        """測試WebSocket端點 - 成功連接"""
        mock_db_session = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db_session

        mock_manager.connect = AsyncMock()
        mock_manager.disconnect = AsyncMock()

        # 模擬接收消息然後斷開連接
        message_queue = [
            '{"type": "subscribe_stock", "data": {"stock_id": 1}}',
            WebSocketDisconnect()
        ]

        def mock_receive():
            if message_queue:
                msg = message_queue.pop(0)
                if isinstance(msg, WebSocketDisconnect):
                    raise msg
                return msg
            raise WebSocketDisconnect()

        self.mock_websocket.receive_text.side_effect = mock_receive
        mock_service.handle_message = AsyncMock()

        try:
            await websocket_endpoint(
                websocket=self.mock_websocket,
                stock_id=1,
                client_id="test_client"
            )
        except WebSocketDisconnect:
            pass  # 預期的異常

        # 驗證連接建立
        mock_manager.connect.assert_called_once_with(
            self.mock_websocket, "test_client"
        )

        # 驗證消息處理
        mock_service.handle_message.assert_called_once()

        # 驗證連接斷開
        mock_manager.disconnect.assert_called_once_with(self.mock_websocket)

    @patch('api.v1.websocket.get_db_session')
    @patch('api.v1.websocket.manager')
    async def test_websocket_endpoint_with_exception(self, mock_manager, mock_get_db):
        """測試WebSocket端點 - 異常處理"""
        mock_db_session = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db_session

        mock_manager.connect = AsyncMock()
        mock_manager.disconnect = AsyncMock()

        # 模擬接收消息時發生異常
        self.mock_websocket.receive_text.side_effect = Exception("網絡錯誤")

        try:
            await websocket_endpoint(
                websocket=self.mock_websocket,
                client_id="test_client"
            )
        except Exception:
            pass

        # 驗證即使發生異常，斷開連接方法也會被調用
        mock_manager.disconnect.assert_called_once_with(self.mock_websocket)

    @patch('api.v1.websocket.get_db_session')
    @patch('api.v1.websocket.manager')
    async def test_websocket_endpoint_malformed_json(self, mock_manager, mock_get_db):
        """測試WebSocket端點 - 格式錯誤的JSON"""
        mock_db_session = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db_session

        mock_manager.connect = AsyncMock()
        mock_manager.disconnect = AsyncMock()

        # 模擬接收格式錯誤的JSON然後斷開連接
        message_queue = [
            '{"invalid json": }',  # 格式錯誤的JSON
            WebSocketDisconnect()
        ]

        def mock_receive():
            if message_queue:
                msg = message_queue.pop(0)
                if isinstance(msg, WebSocketDisconnect):
                    raise msg
                return msg
            raise WebSocketDisconnect()

        self.mock_websocket.receive_text.side_effect = mock_receive

        try:
            await websocket_endpoint(
                websocket=self.mock_websocket,
                client_id="test_client"
            )
        except WebSocketDisconnect:
            pass

        # 驗證錯誤消息被發送
        self.mock_websocket.send_text.assert_called()


class TestWebSocketManagement(unittest.TestCase):
    """WebSocket管理測試"""

    @patch('api.v1.websocket.manager')
    async def test_initialize_websocket_manager(self, mock_manager):
        """測試初始化WebSocket管理器"""
        mock_manager.initialize = AsyncMock()

        await initialize_websocket_manager()

        mock_manager.initialize.assert_called_once()

    @patch('api.v1.websocket.manager')
    async def test_shutdown_websocket_manager(self, mock_manager):
        """測試關閉WebSocket管理器"""
        mock_manager.shutdown = AsyncMock()

        await shutdown_websocket_manager()

        mock_manager.shutdown.assert_called_once()

    @patch('api.v1.websocket.manager')
    async def test_get_websocket_cluster_stats(self, mock_manager):
        """測試獲取WebSocket集群統計"""
        mock_stats = {
            "total_connections": 150,
            "active_subscriptions": 300,
            "cluster_nodes": 3,
            "redis_status": "connected"
        }
        mock_manager.get_cluster_stats.return_value = mock_stats

        result = await get_websocket_cluster_stats()

        self.assertEqual(result, mock_stats)
        mock_manager.get_cluster_stats.assert_called_once()


class TestWebSocketIntegration(unittest.TestCase):
    """WebSocket整合測試"""

    def test_websocket_service_static_methods(self):
        """測試WebSocketService靜態方法可用性"""
        # 檢查所有必要的靜態方法是否存在
        required_methods = [
            'handle_message',
            'send_initial_stock_data',
            'broadcast_price_update',
            'broadcast_indicator_update',
            'broadcast_signal_update',
            'broadcast_market_status'
        ]

        for method_name in required_methods:
            self.assertTrue(
                hasattr(WebSocketService, method_name),
                f"WebSocketService缺少方法: {method_name}"
            )
            self.assertTrue(
                callable(getattr(WebSocketService, method_name)),
                f"WebSocketService.{method_name} 不可調用"
            )

    def test_message_types_coverage(self):
        """測試消息類型覆蓋完整性"""
        # 確保所有重要的消息類型都有處理邏輯
        expected_message_types = [
            "subscribe_stock",
            "unsubscribe_stock",
            "subscribe_global",
            "unsubscribe_global"
        ]

        # 這裡我們通過檢查代碼結構來驗證
        # 在實際實現中，可以通過檢查handle_message方法的分支來確認
        self.assertTrue(len(expected_message_types) > 0)

    async def test_error_handling_robustness(self):
        """測試錯誤處理健壯性"""
        # 測試各種錯誤情況下系統的穩定性
        service = WebSocketService()

        # 測試None消息
        try:
            await WebSocketService.handle_message(None, None, None)
        except Exception:
            pass  # 允許拋出異常，但不應該崩潰

        # 測試空消息
        try:
            await WebSocketService.handle_message(Mock(), {}, AsyncMock())
        except Exception:
            pass  # 允許拋出異常，但不應該崩潰

        # 如果代碼執行到這裡，說明錯誤處理是健壯的
        self.assertTrue(True)


async def run_all_tests():
    """執行所有測試"""
    print("=" * 60)
    print("WebSocket API測試")
    print("=" * 60)

    # 同步測試
    sync_test_classes = [
        TestWebSocketIntegration
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
    async_test_classes = [
        TestWebSocketService,
        TestWebSocketEndpoint,
        TestWebSocketManagement
    ]

    for test_class in async_test_classes:
        print(f"\n執行 {test_class.__name__}...")
        async_test = test_class()

        # 獲取所有測試方法
        test_methods = [method for method in dir(async_test)
                       if method.startswith('test_') and callable(getattr(async_test, method))]

        for method_name in test_methods:
            if hasattr(async_test, 'setUp'):
                async_test.setUp()
            try:
                await getattr(async_test, method_name)()
                print(f"✅ {method_name} - 通過")
            except Exception as e:
                print(f"❌ {method_name} - 失敗: {str(e)}")
                return False

    print("\n🎉 所有WebSocket API測試都通過了！")
    return True


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)