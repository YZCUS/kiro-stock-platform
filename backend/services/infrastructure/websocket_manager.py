"""
增強版 WebSocket 連接管理器 - 支援多Worker環境
"""
import json
import asyncio
import logging
from typing import Dict, List, Set, Optional, Any
from datetime import datetime
from fastapi import WebSocket
from services.infrastructure.redis_pubsub import redis_broadcaster

logger = logging.getLogger(__name__)


class EnhancedConnectionManager:
    """增強版WebSocket連接管理器 - 支援Redis Pub/Sub"""

    def __init__(self):
        # 本地連接管理（僅當前Worker）
        self.active_connections: Dict[WebSocket, Dict[str, Any]] = {}
        self.stock_subscriptions: Dict[int, Set[WebSocket]] = {}
        self.global_subscriptions: Set[WebSocket] = set()

        # Redis相關
        self.worker_id = f"worker_{id(self)}"
        self.redis_subscriptions: Set[str] = set()
        self.pubsub_task: Optional[asyncio.Task] = None

    async def initialize(self):
        """初始化管理器"""
        try:
            # 確保Redis廣播器已連接
            if not redis_broadcaster.is_connected:
                await redis_broadcaster.connect()

            # 啟動Redis訂閱任務
            await self._start_redis_subscription()

            logger.info(f"WebSocket管理器初始化完成 - Worker ID: {self.worker_id}")

        except Exception as e:
            logger.error(f"WebSocket管理器初始化失敗: {e}")
            raise

    async def shutdown(self):
        """關閉管理器"""
        try:
            # 停止Redis訂閱任務
            if self.pubsub_task and not self.pubsub_task.done():
                self.pubsub_task.cancel()
                try:
                    await self.pubsub_task
                except asyncio.CancelledError:
                    pass

            # 清理所有連接
            for websocket in list(self.active_connections.keys()):
                await self._cleanup_connection(websocket)

            logger.info(f"WebSocket管理器已關閉 - Worker ID: {self.worker_id}")

        except Exception as e:
            logger.error(f"WebSocket管理器關閉失敗: {e}")

    async def connect(self, websocket: WebSocket, client_id: str = None):
        """建立連接"""
        await websocket.accept()

        client_id = client_id or f"client_{id(websocket)}"
        self.active_connections[websocket] = {
            "client_id": client_id,
            "worker_id": self.worker_id,
            "stock_ids": set(),
            "connected_at": datetime.now(),
            "is_global_subscriber": False
        }

        logger.info(f"WebSocket連接建立: {client_id} (Worker: {self.worker_id})")

    async def disconnect(self, websocket: WebSocket):
        """斷開連接"""
        await self._cleanup_connection(websocket)

    async def _cleanup_connection(self, websocket: WebSocket):
        """清理連接"""
        if websocket not in self.active_connections:
            return

        connection_info = self.active_connections[websocket]

        # 從股票訂閱中移除
        for stock_id in connection_info["stock_ids"]:
            if stock_id in self.stock_subscriptions:
                self.stock_subscriptions[stock_id].discard(websocket)
                if not self.stock_subscriptions[stock_id]:
                    del self.stock_subscriptions[stock_id]
                    # 如果沒有本地訂閱者，取消Redis訂閱
                    await self._unsubscribe_redis_channel(f"stock_updates:{stock_id}")

        # 從全局訂閱中移除
        if connection_info["is_global_subscriber"]:
            self.global_subscriptions.discard(websocket)
            # 如果沒有本地全局訂閱者，取消Redis全局訂閱
            if not self.global_subscriptions:
                await self._unsubscribe_redis_channel("global_updates")

        # 移除連接記錄
        del self.active_connections[websocket]

        logger.info(f"WebSocket連接已清理: {connection_info['client_id']}")

    async def subscribe_to_stock(self, websocket: WebSocket, stock_id: int):
        """訂閱股票更新"""
        if websocket not in self.active_connections:
            return

        # 添加到本地訂閱
        self.active_connections[websocket]["stock_ids"].add(stock_id)

        if stock_id not in self.stock_subscriptions:
            self.stock_subscriptions[stock_id] = set()

        # 如果是第一個訂閱者，需要訂閱Redis頻道
        was_empty = len(self.stock_subscriptions[stock_id]) == 0
        self.stock_subscriptions[stock_id].add(websocket)

        if was_empty:
            await self._subscribe_redis_channel(f"stock_updates:{stock_id}")

        logger.info(f"客戶端訂閱股票: {stock_id} (Worker: {self.worker_id})")

    async def unsubscribe_from_stock(self, websocket: WebSocket, stock_id: int):
        """取消訂閱股票"""
        if websocket not in self.active_connections:
            return

        self.active_connections[websocket]["stock_ids"].discard(stock_id)

        if stock_id in self.stock_subscriptions:
            self.stock_subscriptions[stock_id].discard(websocket)
            if not self.stock_subscriptions[stock_id]:
                del self.stock_subscriptions[stock_id]
                # 如果沒有本地訂閱者，取消Redis訂閱
                await self._unsubscribe_redis_channel(f"stock_updates:{stock_id}")

        logger.info(f"客戶端取消訂閱股票: {stock_id} (Worker: {self.worker_id})")

    async def subscribe_to_global(self, websocket: WebSocket):
        """訂閱全局更新"""
        if websocket not in self.active_connections:
            return

        # 如果是第一個全局訂閱者，需要訂閱Redis頻道
        was_empty = len(self.global_subscriptions) == 0
        self.global_subscriptions.add(websocket)
        self.active_connections[websocket]["is_global_subscriber"] = True

        if was_empty:
            await self._subscribe_redis_channel("global_updates")

        logger.info(f"客戶端訂閱全局更新 (Worker: {self.worker_id})")

    async def unsubscribe_from_global(self, websocket: WebSocket):
        """取消全局訂閱"""
        if websocket not in self.active_connections:
            return

        self.global_subscriptions.discard(websocket)
        self.active_connections[websocket]["is_global_subscriber"] = False

        # 如果沒有本地全局訂閱者，取消Redis訂閱
        if not self.global_subscriptions:
            await self._unsubscribe_redis_channel("global_updates")

        logger.info(f"客戶端取消全局訂閱 (Worker: {self.worker_id})")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """發送個人消息"""
        try:
            await websocket.send_text(json.dumps(message, ensure_ascii=False))
        except Exception as e:
            logger.error(f"發送個人消息失敗: {e}")
            await self._cleanup_connection(websocket)

    async def broadcast_to_stock_subscribers(self, message: dict, stock_id: int):
        """向股票訂閱者廣播消息 - 通過Redis"""
        await redis_broadcaster.publish_stock_update(
            stock_id, message.get("type", "update"), message.get("data", {})
        )

    async def broadcast_global(self, message: dict):
        """全局廣播 - 通過Redis"""
        await redis_broadcaster.publish_global_update(
            message.get("type", "update"), message.get("data", {})
        )

    async def _subscribe_redis_channel(self, channel: str):
        """訂閱Redis頻道"""
        if channel not in self.redis_subscriptions:
            self.redis_subscriptions.add(channel)
            logger.debug(f"Worker {self.worker_id} 訂閱Redis頻道: {channel}")

    async def _unsubscribe_redis_channel(self, channel: str):
        """取消訂閱Redis頻道"""
        if channel in self.redis_subscriptions:
            self.redis_subscriptions.discard(channel)
            logger.debug(f"Worker {self.worker_id} 取消訂閱Redis頻道: {channel}")

    async def _start_redis_subscription(self):
        """啟動Redis訂閱任務"""
        try:
            # 訂閱所有可能的頻道模式
            channels = ["global_updates", "stock_updates:*"]

            self.pubsub_task = asyncio.create_task(
                redis_broadcaster.subscribe_to_channels(
                    channels, self._handle_redis_message
                )
            )

            logger.info(f"Redis訂閱任務已啟動 (Worker: {self.worker_id})")

        except Exception as e:
            logger.error(f"啟動Redis訂閱任務失敗: {e}")

    async def _handle_redis_message(self, channel: str, message_data: dict):
        """處理來自Redis的消息"""
        try:
            message = message_data.get("data", {})
            message_type = message.get("type", "unknown")

            # 格式化消息
            formatted_message = {
                "type": message_type,
                "data": message.get("data", {}),
                "timestamp": message_data.get("timestamp", datetime.now().isoformat())
            }

            if channel == "global_updates":
                # 全局更新 - 廣播給所有全局訂閱者
                await self._broadcast_to_local_global_subscribers(formatted_message)

            elif channel.startswith("stock_updates:"):
                # 股票更新 - 廣播給特定股票的訂閱者
                try:
                    stock_id = int(channel.split(":")[-1])
                    await self._broadcast_to_local_stock_subscribers(formatted_message, stock_id)
                except ValueError:
                    logger.error(f"無效的股票更新頻道: {channel}")

        except Exception as e:
            logger.error(f"處理Redis消息失敗 (頻道: {channel}): {e}")

    async def _broadcast_to_local_global_subscribers(self, message: dict):
        """廣播給本地全局訂閱者"""
        disconnected_clients = []

        for websocket in self.global_subscriptions.copy():
            try:
                await websocket.send_text(json.dumps(message, ensure_ascii=False))
            except Exception as e:
                logger.error(f"廣播全局消息失敗: {e}")
                disconnected_clients.append(websocket)

        # 清理斷開的連接
        for websocket in disconnected_clients:
            await self._cleanup_connection(websocket)

    async def _broadcast_to_local_stock_subscribers(self, message: dict, stock_id: int):
        """廣播給本地股票訂閱者"""
        if stock_id not in self.stock_subscriptions:
            return

        disconnected_clients = []

        for websocket in self.stock_subscriptions[stock_id].copy():
            try:
                await websocket.send_text(json.dumps(message, ensure_ascii=False))
            except Exception as e:
                logger.error(f"廣播股票消息失敗 (股票ID: {stock_id}): {e}")
                disconnected_clients.append(websocket)

        # 清理斷開的連接
        for websocket in disconnected_clients:
            await self._cleanup_connection(websocket)

    def get_connection_stats(self) -> dict:
        """取得連接統計"""
        return {
            "worker_id": self.worker_id,
            "total_connections": len(self.active_connections),
            "stock_subscriptions": len(self.stock_subscriptions),
            "global_subscriptions": len(self.global_subscriptions),
            "subscribed_stocks": list(self.stock_subscriptions.keys()),
            "redis_subscriptions": list(self.redis_subscriptions)
        }

    async def get_cluster_stats(self) -> dict:
        """取得集群統計（通過Redis）"""
        try:
            stats = self.get_connection_stats()

            # 取得Redis健康狀態
            redis_health = await redis_broadcaster.health_check()

            # 取得各頻道訂閱者數量
            channel_stats = {}
            for channel in self.redis_subscriptions:
                count = await redis_broadcaster.get_channel_subscriber_count(channel)
                channel_stats[channel] = count

            return {
                "local_worker": stats,
                "redis_health": redis_health,
                "channel_subscriber_counts": channel_stats,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"取得集群統計失敗: {e}")
            return {
                "local_worker": self.get_connection_stats(),
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# 全局管理器實例
enhanced_manager = EnhancedConnectionManager()