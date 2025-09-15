"""
Redis Pub/Sub WebSocket 廣播服務
"""
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import redis.asyncio as redis
from core.config import settings

logger = logging.getLogger(__name__)


class RedisWebSocketBroadcaster:
    """基於Redis Pub/Sub的WebSocket廣播器"""

    def __init__(self):
        self.redis_pool = None
        self.subscriber = None
        self.publisher = None
        self.subscriptions: Set[str] = set()
        self.is_connected = False

    async def connect(self):
        """連接到Redis"""
        try:
            # 建立Redis連接池
            self.redis_pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20
            )

            # 建立發布者和訂閱者連接
            self.publisher = redis.Redis(connection_pool=self.redis_pool)
            self.subscriber = redis.Redis(connection_pool=self.redis_pool)

            # 測試連接
            await self.publisher.ping()
            await self.subscriber.ping()

            self.is_connected = True
            logger.info("Redis WebSocket broadcaster 連接成功")

        except Exception as e:
            logger.error(f"Redis 連接失敗: {e}")
            self.is_connected = False
            raise

    async def disconnect(self):
        """斷開Redis連接"""
        try:
            if self.publisher:
                await self.publisher.close()
            if self.subscriber:
                await self.subscriber.close()
            if self.redis_pool:
                await self.redis_pool.disconnect()

            self.is_connected = False
            logger.info("Redis WebSocket broadcaster 已斷開連接")

        except Exception as e:
            logger.error(f"Redis 斷開連接失敗: {e}")

    async def publish_message(self, channel: str, message: dict):
        """發布消息到指定頻道"""
        if not self.is_connected:
            logger.warning("Redis 未連接，無法發布消息")
            return

        try:
            message_data = {
                "timestamp": datetime.now().isoformat(),
                "data": message
            }

            await self.publisher.publish(
                channel,
                json.dumps(message_data, ensure_ascii=False)
            )

            logger.debug(f"消息已發布到頻道 {channel}: {message}")

        except Exception as e:
            logger.error(f"發布消息失敗: {e}")

    async def publish_stock_update(self, stock_id: int, update_type: str, data: dict):
        """發布股票更新消息"""
        channel = f"stock_updates:{stock_id}"
        message = {
            "type": update_type,
            "stock_id": stock_id,
            "data": data
        }
        await self.publish_message(channel, message)

    async def publish_global_update(self, update_type: str, data: dict):
        """發布全局更新消息"""
        channel = "global_updates"
        message = {
            "type": update_type,
            "data": data
        }
        await self.publish_message(channel, message)

    async def publish_price_update(self, stock_id: int, price_data: dict):
        """發布價格更新"""
        await self.publish_stock_update(stock_id, "price_update", price_data)

    async def publish_indicator_update(self, stock_id: int, indicator_data: dict):
        """發布技術指標更新"""
        await self.publish_stock_update(stock_id, "indicator_update", indicator_data)

    async def publish_signal_update(self, stock_id: int, signal_data: dict):
        """發布交易信號更新"""
        await self.publish_stock_update(stock_id, "signal_update", signal_data)

    async def publish_market_status(self, status_data: dict):
        """發布市場狀態更新"""
        await self.publish_global_update("market_status", status_data)

    async def subscribe_to_channels(self, channels: List[str], callback):
        """訂閱頻道並處理消息"""
        if not self.is_connected:
            logger.warning("Redis 未連接，無法訂閱頻道")
            return

        try:
            # 建立PubSub實例
            pubsub = self.subscriber.pubsub()

            # 訂閱頻道
            for channel in channels:
                await pubsub.subscribe(channel)
                self.subscriptions.add(channel)

            logger.info(f"已訂閱頻道: {channels}")

            # 處理消息
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        # 解析消息
                        channel = message["channel"]
                        data = json.loads(message["data"])

                        # 調用回調函數
                        await callback(channel, data)

                    except json.JSONDecodeError as e:
                        logger.error(f"解析消息失敗: {e}")
                    except Exception as e:
                        logger.error(f"處理消息回調失敗: {e}")

        except Exception as e:
            logger.error(f"訂閱頻道失敗: {e}")

    async def unsubscribe_from_channels(self, channels: List[str]):
        """取消訂閱頻道"""
        if not self.is_connected:
            return

        try:
            pubsub = self.subscriber.pubsub()
            for channel in channels:
                await pubsub.unsubscribe(channel)
                self.subscriptions.discard(channel)

            logger.info(f"已取消訂閱頻道: {channels}")

        except Exception as e:
            logger.error(f"取消訂閱失敗: {e}")

    async def get_active_subscriptions(self) -> List[str]:
        """取得活躍訂閱"""
        return list(self.subscriptions)

    async def get_channel_subscriber_count(self, channel: str) -> int:
        """取得頻道訂閱者數量"""
        if not self.is_connected:
            return 0

        try:
            # 使用 PUBSUB NUMSUB 命令取得訂閱者數量
            result = await self.publisher.execute_command("PUBSUB", "NUMSUB", channel)
            if result and len(result) >= 2:
                return result[1]
            return 0

        except Exception as e:
            logger.error(f"取得頻道訂閱者數量失敗: {e}")
            return 0

    async def health_check(self) -> dict:
        """健康檢查"""
        try:
            if not self.is_connected:
                return {"status": "disconnected", "error": "Redis not connected"}

            # 測試連接
            await self.publisher.ping()
            await self.subscriber.ping()

            return {
                "status": "healthy",
                "connected": True,
                "active_subscriptions": len(self.subscriptions),
                "subscriptions": list(self.subscriptions)
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "connected": False
            }


# 全局廣播器實例
redis_broadcaster = RedisWebSocketBroadcaster()


async def init_redis_broadcaster():
    """初始化Redis廣播器"""
    await redis_broadcaster.connect()


async def shutdown_redis_broadcaster():
    """關閉Redis廣播器"""
    await redis_broadcaster.disconnect()