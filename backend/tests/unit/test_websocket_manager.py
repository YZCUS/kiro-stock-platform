#!/usr/bin/env python3
"""
WebSocket 管理器單元測試
"""
import asyncio
import pytest
import sys
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime

# 添加項目根目錄到 Python 路徑
sys.path.append('/Users/zhengchy/Documents/projects/kiro-stock-platform/backend')

from services.infrastructure.websocket_manager import EnhancedConnectionManager


class TestEnhancedConnectionManager:
    """WebSocket 連接管理器測試類"""

    def setup_method(self):
        """測試前設置"""
        self.manager = EnhancedConnectionManager()
        self.mock_websocket = Mock()
        self.mock_websocket.accept = AsyncMock()
        self.mock_websocket.close = AsyncMock()
        self.mock_websocket.send_text = AsyncMock()
        self.mock_websocket.send_json = AsyncMock()

    @patch('services.infrastructure.websocket_manager.redis_broadcaster')
    async def test_initialize_success(self, mock_broadcaster):
        """測試成功初始化管理器"""
        # Mock Redis 廣播器
        mock_broadcaster.is_connected = True
        mock_broadcaster.connect = AsyncMock()

        # Mock 私有方法
        self.manager._start_redis_subscription = AsyncMock()

        # 執行測試
        await self.manager.initialize()

        # 驗證結果
        self.manager._start_redis_subscription.assert_called_once()
        assert self.manager.worker_id.startswith("worker_")

    @patch('services.infrastructure.websocket_manager.redis_broadcaster')
    async def test_initialize_redis_not_connected(self, mock_broadcaster):
        """測試 Redis 未連接時的初始化"""
        # Mock Redis 廣播器未連接
        mock_broadcaster.is_connected = False
        mock_broadcaster.connect = AsyncMock()

        # Mock 私有方法
        self.manager._start_redis_subscription = AsyncMock()

        # 執行測試
        await self.manager.initialize()

        # 驗證結果
        mock_broadcaster.connect.assert_called_once()
        self.manager._start_redis_subscription.assert_called_once()

    async def test_connect_websocket_success(self):
        """測試成功建立 WebSocket 連接"""
        client_id = "test_client_123"

        # 執行測試
        await self.manager.connect(self.mock_websocket, client_id)

        # 驗證結果
        self.mock_websocket.accept.assert_called_once()
        assert self.mock_websocket in self.manager.active_connections

        connection_info = self.manager.active_connections[self.mock_websocket]
        assert connection_info["client_id"] == client_id
        assert connection_info["worker_id"] == self.manager.worker_id
        assert isinstance(connection_info["stock_ids"], set)
        assert isinstance(connection_info["connected_at"], datetime)
        assert connection_info["is_global_subscriber"] is False

    async def test_connect_websocket_auto_client_id(self):
        """測試自動生成客戶端 ID"""
        # 執行測試 - 不提供 client_id
        await self.manager.connect(self.mock_websocket)

        # 驗證結果
        connection_info = self.manager.active_connections[self.mock_websocket]
        assert connection_info["client_id"].startswith("client_")

    async def test_disconnect_websocket_success(self):
        """測試成功斷開 WebSocket 連接"""
        # 先建立連接
        await self.manager.connect(self.mock_websocket, "test_client")

        # Mock 清理方法
        self.manager._cleanup_connection = AsyncMock()

        # 執行測試
        await self.manager.disconnect(self.mock_websocket)

        # 驗證結果
        self.manager._cleanup_connection.assert_called_once_with(self.mock_websocket)

    async def test_subscribe_to_stock_success(self):
        """測試成功訂閱股票"""
        # 先建立連接
        await self.manager.connect(self.mock_websocket, "test_client")

        # Mock Redis 相關方法
        self.manager._ensure_redis_subscription = AsyncMock()

        # 執行測試
        stock_id = 2330
        await self.manager.subscribe_to_stock(self.mock_websocket, stock_id)

        # 驗證結果
        assert stock_id in self.manager.stock_subscriptions
        assert self.mock_websocket in self.manager.stock_subscriptions[stock_id]

        connection_info = self.manager.active_connections[self.mock_websocket]
        assert stock_id in connection_info["stock_ids"]

    async def test_subscribe_to_stock_connection_not_found(self):
        """測試訂閱股票但連接不存在"""
        # 執行測試並期待異常
        with pytest.raises(ValueError, match="WebSocket連接不存在"):
            await self.manager.subscribe_to_stock(self.mock_websocket, 2330)

    async def test_unsubscribe_from_stock_success(self):
        """測試成功取消訂閱股票"""
        # 先建立連接和訂閱
        await self.manager.connect(self.mock_websocket, "test_client")
        stock_id = 2330

        # 手動設置訂閱狀態
        self.manager.stock_subscriptions[stock_id] = {self.mock_websocket}
        self.manager.active_connections[self.mock_websocket]["stock_ids"].add(stock_id)

        # 執行測試
        await self.manager.unsubscribe_from_stock(self.mock_websocket, stock_id)

        # 驗證結果
        assert stock_id not in self.manager.active_connections[self.mock_websocket]["stock_ids"]
        assert self.mock_websocket not in self.manager.stock_subscriptions.get(stock_id, set())

    async def test_subscribe_to_global_success(self):
        """測試成功訂閱全域信號"""
        # 先建立連接
        await self.manager.connect(self.mock_websocket, "test_client")

        # Mock Redis 相關方法
        self.manager._ensure_redis_subscription = AsyncMock()

        # 執行測試
        await self.manager.subscribe_to_global(self.mock_websocket)

        # 驗證結果
        assert self.mock_websocket in self.manager.global_subscriptions

        connection_info = self.manager.active_connections[self.mock_websocket]
        assert connection_info["is_global_subscriber"] is True

    async def test_unsubscribe_from_global_success(self):
        """測試成功取消訂閱全域信號"""
        # 先建立連接和訂閱
        await self.manager.connect(self.mock_websocket, "test_client")
        self.manager.global_subscriptions.add(self.mock_websocket)
        self.manager.active_connections[self.mock_websocket]["is_global_subscriber"] = True

        # 執行測試
        await self.manager.unsubscribe_from_global(self.mock_websocket)

        # 驗證結果
        assert self.mock_websocket not in self.manager.global_subscriptions
        assert self.manager.active_connections[self.mock_websocket]["is_global_subscriber"] is False

    async def test_broadcast_to_stock_subscribers_success(self):
        """測試向股票訂閱者廣播"""
        # 設置多個連接
        mock_ws1 = Mock()
        mock_ws1.send_json = AsyncMock()
        mock_ws2 = Mock()
        mock_ws2.send_json = AsyncMock()

        # 建立連接
        await self.manager.connect(mock_ws1, "client1")
        await self.manager.connect(mock_ws2, "client2")

        # 設置訂閱
        stock_id = 2330
        self.manager.stock_subscriptions[stock_id] = {mock_ws1, mock_ws2}

        # 準備測試數據
        message = {"type": "price_update", "stock_id": stock_id, "price": 500.0}

        # 執行測試
        await self.manager.broadcast_to_stock_subscribers(stock_id, message)

        # 驗證結果
        mock_ws1.send_json.assert_called_once_with(message)
        mock_ws2.send_json.assert_called_once_with(message)

    async def test_broadcast_to_global_subscribers_success(self):
        """測試向全域訂閱者廣播"""
        # 設置多個全域訂閱者
        mock_ws1 = Mock()
        mock_ws1.send_json = AsyncMock()
        mock_ws2 = Mock()
        mock_ws2.send_json = AsyncMock()

        # 建立連接
        await self.manager.connect(mock_ws1, "client1")
        await self.manager.connect(mock_ws2, "client2")

        # 設置全域訂閱
        self.manager.global_subscriptions = {mock_ws1, mock_ws2}

        # 準備測試數據
        message = {"type": "global_signal", "message": "市場開盤"}

        # 執行測試
        await self.manager.broadcast_to_global_subscribers(message)

        # 驗證結果
        mock_ws1.send_json.assert_called_once_with(message)
        mock_ws2.send_json.assert_called_once_with(message)

    async def test_get_connection_stats_success(self):
        """測試取得連接統計"""
        # 建立測試連接
        await self.manager.connect(self.mock_websocket, "test_client")

        # 設置訂閱
        stock_id = 2330
        self.manager.stock_subscriptions[stock_id] = {self.mock_websocket}
        self.manager.global_subscriptions.add(self.mock_websocket)

        # 執行測試
        stats = self.manager.get_connection_stats()

        # 驗證結果
        assert stats["total_connections"] == 1
        assert stats["stock_subscriptions"] == 1
        assert stats["global_subscriptions"] == 1
        assert stats["worker_id"] == self.manager.worker_id

    async def test_send_message_to_client_success(self):
        """測試向特定客戶端發送消息"""
        # 建立連接
        client_id = "test_client"
        await self.manager.connect(self.mock_websocket, client_id)

        # 準備測試數據
        message = {"type": "notification", "content": "測試消息"}

        # 執行測試
        result = await self.manager.send_message_to_client(client_id, message)

        # 驗證結果
        assert result is True
        self.mock_websocket.send_json.assert_called_once_with(message)

    async def test_send_message_to_client_not_found(self):
        """測試向不存在的客戶端發送消息"""
        # 準備測試數據
        message = {"type": "notification", "content": "測試消息"}

        # 執行測試
        result = await self.manager.send_message_to_client("nonexistent_client", message)

        # 驗證結果
        assert result is False

    async def test_cleanup_connection_success(self):
        """測試清理連接"""
        # 建立連接和訂閱
        await self.manager.connect(self.mock_websocket, "test_client")
        stock_id = 2330
        self.manager.stock_subscriptions[stock_id] = {self.mock_websocket}
        self.manager.global_subscriptions.add(self.mock_websocket)

        # 執行測試
        await self.manager._cleanup_connection(self.mock_websocket)

        # 驗證結果
        assert self.mock_websocket not in self.manager.active_connections
        assert self.mock_websocket not in self.manager.global_subscriptions
        assert stock_id not in self.manager.stock_subscriptions or \
               self.mock_websocket not in self.manager.stock_subscriptions[stock_id]

    async def test_handle_websocket_error_connection_exists(self):
        """測試處理 WebSocket 錯誤 - 連接存在"""
        # 建立連接
        await self.manager.connect(self.mock_websocket, "test_client")

        # Mock 清理方法
        self.manager._cleanup_connection = AsyncMock()

        # 執行測試
        error = Exception("WebSocket error")
        await self.manager._handle_websocket_error(self.mock_websocket, error)

        # 驗證結果
        self.manager._cleanup_connection.assert_called_once_with(self.mock_websocket)

    async def test_handle_websocket_error_connection_not_exists(self):
        """測試處理 WebSocket 錯誤 - 連接不存在"""
        # Mock 清理方法
        self.manager._cleanup_connection = AsyncMock()

        # 執行測試
        error = Exception("WebSocket error")
        await self.manager._handle_websocket_error(self.mock_websocket, error)

        # 驗證結果 - 不應該調用清理
        self.manager._cleanup_connection.assert_not_called()

    async def test_shutdown_success(self):
        """測試成功關閉管理器"""
        # 建立連接
        await self.manager.connect(self.mock_websocket, "test_client")

        # Mock pubsub 任務
        self.manager.pubsub_task = Mock()
        self.manager.pubsub_task.done.return_value = False
        self.manager.pubsub_task.cancel = Mock()
        self.manager.pubsub_task.__await__ = AsyncMock().__await__

        # Mock 清理方法
        self.manager._cleanup_connection = AsyncMock()

        # 執行測試
        await self.manager.shutdown()

        # 驗證結果
        self.manager.pubsub_task.cancel.assert_called_once()
        self.manager._cleanup_connection.assert_called_once_with(self.mock_websocket)

    async def test_is_client_connected_true(self):
        """測試檢查客戶端連接狀態 - 已連接"""
        # 建立連接
        client_id = "test_client"
        await self.manager.connect(self.mock_websocket, client_id)

        # 執行測試
        result = self.manager.is_client_connected(client_id)

        # 驗證結果
        assert result is True

    async def test_is_client_connected_false(self):
        """測試檢查客戶端連接狀態 - 未連接"""
        # 執行測試
        result = self.manager.is_client_connected("nonexistent_client")

        # 驗證結果
        assert result is False

    async def test_get_connected_clients_success(self):
        """測試取得已連接客戶端清單"""
        # 建立多個連接
        mock_ws1 = Mock()
        mock_ws1.accept = AsyncMock()
        mock_ws2 = Mock()
        mock_ws2.accept = AsyncMock()

        await self.manager.connect(mock_ws1, "client1")
        await self.manager.connect(mock_ws2, "client2")

        # 執行測試
        clients = self.manager.get_connected_clients()

        # 驗證結果
        assert len(clients) == 2
        client_ids = [client["client_id"] for client in clients]
        assert "client1" in client_ids
        assert "client2" in client_ids


async def run_all_tests():
    """執行所有測試"""
    print("開始執行 WebSocket 管理器測試...")

    test_manager = TestEnhancedConnectionManager()

    try:
        test_manager.setup_method()

        await test_manager.test_initialize_success()
        print("✅ 初始化管理器測試 - 通過")

        await test_manager.test_initialize_redis_not_connected()
        print("✅ Redis 未連接初始化測試 - 通過")

        await test_manager.test_connect_websocket_success()
        print("✅ 建立 WebSocket 連接測試 - 通過")

        await test_manager.test_connect_websocket_auto_client_id()
        print("✅ 自動生成客戶端 ID 測試 - 通過")

        await test_manager.test_disconnect_websocket_success()
        print("✅ 斷開 WebSocket 連接測試 - 通過")

        await test_manager.test_subscribe_to_stock_success()
        print("✅ 訂閱股票測試 - 通過")

        await test_manager.test_subscribe_to_stock_connection_not_found()
        print("✅ 訂閱股票連接不存在測試 - 通過")

        await test_manager.test_unsubscribe_from_stock_success()
        print("✅ 取消訂閱股票測試 - 通過")

        await test_manager.test_subscribe_to_global_success()
        print("✅ 訂閱全域信號測試 - 通過")

        await test_manager.test_unsubscribe_from_global_success()
        print("✅ 取消訂閱全域信號測試 - 通過")

        await test_manager.test_broadcast_to_stock_subscribers_success()
        print("✅ 向股票訂閱者廣播測試 - 通過")

        await test_manager.test_broadcast_to_global_subscribers_success()
        print("✅ 向全域訂閱者廣播測試 - 通過")

        await test_manager.test_get_connection_stats_success()
        print("✅ 取得連接統計測試 - 通過")

        await test_manager.test_send_message_to_client_success()
        print("✅ 向客戶端發送消息測試 - 通過")

        await test_manager.test_send_message_to_client_not_found()
        print("✅ 向不存在客戶端發送消息測試 - 通過")

        await test_manager.test_cleanup_connection_success()
        print("✅ 清理連接測試 - 通過")

        await test_manager.test_handle_websocket_error_connection_exists()
        print("✅ 處理 WebSocket 錯誤測試 - 通過")

        await test_manager.test_handle_websocket_error_connection_not_exists()
        print("✅ 處理不存在連接錯誤測試 - 通過")

        await test_manager.test_shutdown_success()
        print("✅ 關閉管理器測試 - 通過")

        await test_manager.test_is_client_connected_true()
        print("✅ 檢查客戶端連接狀態測試 - 通過")

        await test_manager.test_is_client_connected_false()
        print("✅ 檢查客戶端未連接狀態測試 - 通過")

        await test_manager.test_get_connected_clients_success()
        print("✅ 取得已連接客戶端清單測試 - 通過")

    except Exception as e:
        print(f"❌ WebSocket 管理器測試失敗: {str(e)}")
        return False

    print("\n🎉 所有 WebSocket 管理器測試通過！")
    return True


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)