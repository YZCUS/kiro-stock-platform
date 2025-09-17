#!/usr/bin/env python3
"""
Redis 發布訂閱服務單元測試
"""
import asyncio
import pytest
import sys
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock

# 添加項目根目錄到 Python 路徑
sys.path.append('/Users/zhengchy/Documents/projects/kiro-stock-platform/backend')

from services.infrastructure.redis_pubsub import RedisWebSocketBroadcaster


class TestRedisWebSocketBroadcaster:
    """Redis WebSocket 廣播器測試類"""

    def setup_method(self):
        """測試前設置"""
        self.broadcaster = RedisWebSocketBroadcaster()

    @patch('services.infrastructure.redis_pubsub.redis.ConnectionPool')
    @patch('services.infrastructure.redis_pubsub.redis.Redis')
    async def test_connect_success(self, mock_redis_class, mock_pool_class):
        """測試成功連接 Redis"""
        # Mock Redis 連接池和實例
        mock_pool = Mock()
        mock_pool_class.from_url.return_value = mock_pool

        mock_publisher = Mock()
        mock_publisher.ping = AsyncMock()
        mock_subscriber = Mock()
        mock_subscriber.ping = AsyncMock()

        mock_redis_class.side_effect = [mock_publisher, mock_subscriber]

        # 執行測試
        await self.broadcaster.connect()

        # 驗證結果
        assert self.broadcaster.is_connected is True
        assert self.broadcaster.redis_pool == mock_pool
        assert self.broadcaster.publisher == mock_publisher
        assert self.broadcaster.subscriber == mock_subscriber

        mock_publisher.ping.assert_called_once()
        mock_subscriber.ping.assert_called_once()

    @patch('services.infrastructure.redis_pubsub.redis.ConnectionPool')
    async def test_connect_failure(self, mock_pool_class):
        """測試 Redis 連接失敗"""
        # Mock 連接失敗
        mock_pool_class.from_url.side_effect = Exception("連接失敗")

        # 執行測試並期待異常
        with pytest.raises(Exception, match="連接失敗"):
            await self.broadcaster.connect()

        # 驗證結果
        assert self.broadcaster.is_connected is False

    async def test_disconnect_success(self):
        """測試成功斷開 Redis 連接"""
        # Mock 連接物件
        mock_publisher = Mock()
        mock_publisher.close = AsyncMock()
        mock_subscriber = Mock()
        mock_subscriber.close = AsyncMock()
        mock_pool = Mock()
        mock_pool.disconnect = AsyncMock()

        self.broadcaster.publisher = mock_publisher
        self.broadcaster.subscriber = mock_subscriber
        self.broadcaster.redis_pool = mock_pool
        self.broadcaster.is_connected = True

        # 執行測試
        await self.broadcaster.disconnect()

        # 驗證結果
        mock_publisher.close.assert_called_once()
        mock_subscriber.close.assert_called_once()
        mock_pool.disconnect.assert_called_once()
        assert self.broadcaster.is_connected is False

    async def test_disconnect_with_none_objects(self):
        """測試斷開連接時物件為 None"""
        # 設置物件為 None
        self.broadcaster.publisher = None
        self.broadcaster.subscriber = None
        self.broadcaster.redis_pool = None

        # 執行測試 - 不應該拋出異常
        await self.broadcaster.disconnect()

        # 驗證結果
        assert self.broadcaster.is_connected is False

    async def test_publish_message_success(self):
        """測試成功發布消息"""
        # Mock 發布者
        mock_publisher = Mock()
        mock_publisher.publish = AsyncMock(return_value=1)  # 1 個訂閱者收到消息
        self.broadcaster.publisher = mock_publisher
        self.broadcaster.is_connected = True

        # 準備測試數據
        channel = "stock_updates"
        message = {"type": "price_update", "stock_id": 2330, "price": 500.0}

        # 執行測試
        result = await self.broadcaster.publish_message(channel, message)

        # 驗證結果
        assert result == 1
        mock_publisher.publish.assert_called_once_with(
            channel, json.dumps(message, ensure_ascii=False)
        )

    async def test_publish_message_not_connected(self):
        """測試未連接時發布消息"""
        # 設置未連接狀態
        self.broadcaster.is_connected = False

        # 執行測試
        result = await self.broadcaster.publish_message("test_channel", {"test": "data"})

        # 驗證結果
        assert result == 0

    async def test_publish_message_failure(self):
        """測試發布消息失敗"""
        # Mock 發布者拋出異常
        mock_publisher = Mock()
        mock_publisher.publish = AsyncMock(side_effect=Exception("發布失敗"))
        self.broadcaster.publisher = mock_publisher
        self.broadcaster.is_connected = True

        # 執行測試
        result = await self.broadcaster.publish_message("test_channel", {"test": "data"})

        # 驗證結果
        assert result == 0

    async def test_subscribe_to_channel_success(self):
        """測試成功訂閱頻道"""
        # Mock 訂閱者
        mock_subscriber = Mock()
        mock_pubsub = Mock()
        mock_pubsub.subscribe = AsyncMock()
        mock_subscriber.pubsub.return_value = mock_pubsub

        self.broadcaster.subscriber = mock_subscriber
        self.broadcaster.is_connected = True

        # 執行測試
        channel = "stock_updates"
        result = await self.broadcaster.subscribe_to_channel(channel)

        # 驗證結果
        assert result is True
        assert channel in self.broadcaster.subscriptions
        mock_pubsub.subscribe.assert_called_once_with(channel)

    async def test_subscribe_to_channel_not_connected(self):
        """測試未連接時訂閱頻道"""
        # 設置未連接狀態
        self.broadcaster.is_connected = False

        # 執行測試
        result = await self.broadcaster.subscribe_to_channel("test_channel")

        # 驗證結果
        assert result is False

    async def test_unsubscribe_from_channel_success(self):
        """測試成功取消訂閱頻道"""
        # 先設置訂閱狀態
        channel = "stock_updates"
        self.broadcaster.subscriptions.add(channel)

        # Mock 訂閱者
        mock_subscriber = Mock()
        mock_pubsub = Mock()
        mock_pubsub.unsubscribe = AsyncMock()
        mock_subscriber.pubsub.return_value = mock_pubsub

        self.broadcaster.subscriber = mock_subscriber
        self.broadcaster.is_connected = True

        # 執行測試
        result = await self.broadcaster.unsubscribe_from_channel(channel)

        # 驗證結果
        assert result is True
        assert channel not in self.broadcaster.subscriptions
        mock_pubsub.unsubscribe.assert_called_once_with(channel)

    async def test_unsubscribe_from_channel_not_subscribed(self):
        """測試取消訂閱未訂閱的頻道"""
        # 設置連接但未訂閱
        self.broadcaster.is_connected = True

        # 執行測試
        result = await self.broadcaster.unsubscribe_from_channel("nonexistent_channel")

        # 驗證結果
        assert result is False

    async def test_publish_stock_update_success(self):
        """測試成功發布股票更新"""
        # Mock 發布方法
        self.broadcaster.publish_message = AsyncMock(return_value=1)

        # 準備測試數據
        stock_id = 2330
        update_data = {
            "price": 500.0,
            "volume": 1000000,
            "change": 5.0
        }

        # 執行測試
        result = await self.broadcaster.publish_stock_update(stock_id, update_data)

        # 驗證結果
        assert result == 1
        self.broadcaster.publish_message.assert_called_once()

        # 檢查發布的消息格式
        call_args = self.broadcaster.publish_message.call_args
        channel, message = call_args[0]
        assert channel == f"stock_updates_{stock_id}"
        assert message["type"] == "stock_update"
        assert message["stock_id"] == stock_id
        assert message["data"] == update_data

    async def test_publish_global_signal_success(self):
        """測試成功發布全域信號"""
        # Mock 發布方法
        self.broadcaster.publish_message = AsyncMock(return_value=3)

        # 準備測試數據
        signal_data = {
            "signal_type": "MARKET_OPEN",
            "message": "市場開盤",
            "timestamp": "2024-01-01T09:00:00"
        }

        # 執行測試
        result = await self.broadcaster.publish_global_signal(signal_data)

        # 驗證結果
        assert result == 3
        self.broadcaster.publish_message.assert_called_once()

        # 檢查發布的消息格式
        call_args = self.broadcaster.publish_message.call_args
        channel, message = call_args[0]
        assert channel == "global_signals"
        assert message["type"] == "global_signal"
        assert message["data"] == signal_data

    async def test_publish_trading_signal_success(self):
        """測試成功發布交易信號"""
        # Mock 發布方法
        self.broadcaster.publish_message = AsyncMock(return_value=2)

        # 準備測試數據
        stock_id = 2330
        signal_data = {
            "signal_type": "BUY",
            "confidence": 0.85,
            "price": 500.0,
            "description": "黃金交叉形成"
        }

        # 執行測試
        result = await self.broadcaster.publish_trading_signal(stock_id, signal_data)

        # 驗證結果
        assert result == 2
        # 應該發布兩次：一次到股票特定頻道，一次到全域頻道
        assert self.broadcaster.publish_message.call_count == 2

    async def test_get_subscriber_count_success(self):
        """測試成功取得訂閱者數量"""
        # Mock 發布者
        mock_publisher = Mock()
        mock_publisher.pubsub_numsub = AsyncMock(return_value=[("test_channel", 5)])
        self.broadcaster.publisher = mock_publisher
        self.broadcaster.is_connected = True

        # 執行測試
        count = await self.broadcaster.get_subscriber_count("test_channel")

        # 驗證結果
        assert count == 5
        mock_publisher.pubsub_numsub.assert_called_once_with("test_channel")

    async def test_get_subscriber_count_not_connected(self):
        """測試未連接時取得訂閱者數量"""
        # 設置未連接狀態
        self.broadcaster.is_connected = False

        # 執行測試
        count = await self.broadcaster.get_subscriber_count("test_channel")

        # 驗證結果
        assert count == 0

    async def test_get_active_channels_success(self):
        """測試成功取得活躍頻道清單"""
        # Mock 發布者
        mock_publisher = Mock()
        mock_publisher.pubsub_channels = AsyncMock(return_value=["channel1", "channel2", "channel3"])
        self.broadcaster.publisher = mock_publisher
        self.broadcaster.is_connected = True

        # 執行測試
        channels = await self.broadcaster.get_active_channels()

        # 驗證結果
        assert len(channels) == 3
        assert "channel1" in channels
        assert "channel2" in channels
        assert "channel3" in channels

    async def test_get_broadcast_stats_success(self):
        """測試成功取得廣播統計"""
        # Mock 相關方法
        self.broadcaster.get_active_channels = AsyncMock(return_value=["ch1", "ch2"])
        self.broadcaster.get_subscriber_count = AsyncMock(side_effect=[3, 5])

        # 執行測試
        stats = await self.broadcaster.get_broadcast_stats()

        # 驗證結果
        assert stats["total_channels"] == 2
        assert stats["total_subscribers"] == 8
        assert len(stats["channel_details"]) == 2
        assert stats["channel_details"]["ch1"] == 3
        assert stats["channel_details"]["ch2"] == 5

    def test_is_connected_property(self):
        """測試連接狀態屬性"""
        # 初始狀態應該是未連接
        assert self.broadcaster.is_connected is False

        # 設置為已連接
        self.broadcaster.is_connected = True
        assert self.broadcaster.is_connected is True

    def test_get_subscriptions_list(self):
        """測試取得訂閱清單"""
        # 添加一些訂閱
        self.broadcaster.subscriptions.add("channel1")
        self.broadcaster.subscriptions.add("channel2")

        # 執行測試
        subscriptions = list(self.broadcaster.subscriptions)

        # 驗證結果
        assert len(subscriptions) == 2
        assert "channel1" in subscriptions
        assert "channel2" in subscriptions

    async def test_cleanup_expired_subscriptions_success(self):
        """測試清理過期訂閱"""
        # 設置一些訂閱
        self.broadcaster.subscriptions.add("active_channel")
        self.broadcaster.subscriptions.add("inactive_channel")

        # Mock 取得訂閱者數量
        async def mock_get_count(channel):
            if channel == "active_channel":
                return 5  # 有訂閱者
            return 0  # 無訂閱者

        self.broadcaster.get_subscriber_count = AsyncMock(side_effect=mock_get_count)
        self.broadcaster.unsubscribe_from_channel = AsyncMock(return_value=True)

        # 執行測試
        cleaned_count = await self.broadcaster.cleanup_expired_subscriptions()

        # 驗證結果
        assert cleaned_count == 1
        self.broadcaster.unsubscribe_from_channel.assert_called_once_with("inactive_channel")


async def run_all_tests():
    """執行所有測試"""
    print("開始執行 Redis 發布訂閱服務測試...")

    test_broadcaster = TestRedisWebSocketBroadcaster()

    try:
        test_broadcaster.setup_method()

        await test_broadcaster.test_connect_success()
        print("✅ 成功連接 Redis 測試 - 通過")

        await test_broadcaster.test_connect_failure()
        print("✅ Redis 連接失敗測試 - 通過")

        await test_broadcaster.test_disconnect_success()
        print("✅ 成功斷開 Redis 連接測試 - 通過")

        await test_broadcaster.test_disconnect_with_none_objects()
        print("✅ 斷開空物件連接測試 - 通過")

        await test_broadcaster.test_publish_message_success()
        print("✅ 成功發布消息測試 - 通過")

        await test_broadcaster.test_publish_message_not_connected()
        print("✅ 未連接發布消息測試 - 通過")

        await test_broadcaster.test_publish_message_failure()
        print("✅ 發布消息失敗測試 - 通過")

        await test_broadcaster.test_subscribe_to_channel_success()
        print("✅ 成功訂閱頻道測試 - 通過")

        await test_broadcaster.test_subscribe_to_channel_not_connected()
        print("✅ 未連接訂閱頻道測試 - 通過")

        await test_broadcaster.test_unsubscribe_from_channel_success()
        print("✅ 成功取消訂閱頻道測試 - 通過")

        await test_broadcaster.test_unsubscribe_from_channel_not_subscribed()
        print("✅ 取消訂閱未訂閱頻道測試 - 通過")

        await test_broadcaster.test_publish_stock_update_success()
        print("✅ 成功發布股票更新測試 - 通過")

        await test_broadcaster.test_publish_global_signal_success()
        print("✅ 成功發布全域信號測試 - 通過")

        await test_broadcaster.test_publish_trading_signal_success()
        print("✅ 成功發布交易信號測試 - 通過")

        await test_broadcaster.test_get_subscriber_count_success()
        print("✅ 成功取得訂閱者數量測試 - 通過")

        await test_broadcaster.test_get_subscriber_count_not_connected()
        print("✅ 未連接取得訂閱者數量測試 - 通過")

        await test_broadcaster.test_get_active_channels_success()
        print("✅ 成功取得活躍頻道清單測試 - 通過")

        await test_broadcaster.test_get_broadcast_stats_success()
        print("✅ 成功取得廣播統計測試 - 通過")

        test_broadcaster.test_is_connected_property()
        print("✅ 連接狀態屬性測試 - 通過")

        test_broadcaster.test_get_subscriptions_list()
        print("✅ 取得訂閱清單測試 - 通過")

        await test_broadcaster.test_cleanup_expired_subscriptions_success()
        print("✅ 清理過期訂閱測試 - 通過")

    except Exception as e:
        print(f"❌ Redis 發布訂閱服務測試失敗: {str(e)}")
        return False

    print("\n🎉 所有 Redis 發布訂閱服務測試通過！")
    return True


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)