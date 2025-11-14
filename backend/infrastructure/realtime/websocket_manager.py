"""
WebSocket manager - Infrastructure Layer
"""

from typing import Dict, Any, Optional, Set
from fastapi import WebSocket
import asyncio


class IWebSocketManager:
    async def connect(
        self, websocket: WebSocket, client_id: Optional[str] = None
    ) -> None:
        raise NotImplementedError

    async def disconnect(self, websocket: WebSocket) -> None:
        raise NotImplementedError

    async def send_personal_message(self, message: dict, websocket: WebSocket) -> None:
        raise NotImplementedError

    async def broadcast_stock_update(self, stock_id: int, message: dict) -> None:
        raise NotImplementedError

    async def broadcast_global_update(self, message: dict) -> None:
        raise NotImplementedError

    def get_connection_stats(self) -> Dict[str, Any]:
        raise NotImplementedError

    async def get_cluster_stats(self) -> Dict[str, Any]:
        raise NotImplementedError

    async def initialize(self) -> None:
        raise NotImplementedError

    async def shutdown(self) -> None:
        raise NotImplementedError


class SimpleWebSocketManager(IWebSocketManager):
    def __init__(self):
        self.active_connections: Dict[WebSocket, Dict[str, Any]] = {}

    async def initialize(self) -> None:
        return None

    async def shutdown(self) -> None:
        return None

    async def connect(
        self, websocket: WebSocket, client_id: Optional[str] = None
    ) -> None:
        await websocket.accept()
        self.active_connections[websocket] = {
            "client_id": client_id or f"client_{id(websocket)}",
        }

    async def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.pop(websocket, None)

    async def send_personal_message(self, message: dict, websocket: WebSocket) -> None:
        await websocket.send_json(message)

    async def broadcast_stock_update(self, stock_id: int, message: dict) -> None:
        await self.broadcast_global_update(message)

    async def broadcast_global_update(self, message: dict) -> None:
        for websocket in list(self.active_connections.keys()):
            try:
                await websocket.send_json(message)
            except Exception:
                await self.disconnect(websocket)

    def get_connection_stats(self) -> Dict[str, Any]:
        return {
            "total_connections": len(self.active_connections),
        }

    async def get_cluster_stats(self) -> Dict[str, Any]:
        return self.get_connection_stats()


class RedisBackedWebSocketManager(IWebSocketManager):
    def __init__(self, redis_broadcaster):
        from datetime import datetime

        self.redis_broadcaster = redis_broadcaster
        self.active_connections: Dict[WebSocket, Dict[str, Any]] = {}
        self.stock_subscriptions: Dict[int, Set[WebSocket]] = {}
        self.global_subscriptions: Set[WebSocket] = set()
        self.redis_channels: Set[str] = set()
        self.pubsub_task: Optional[asyncio.Task] = None
        self.worker_id = f"worker_{id(self)}"
        self._now = datetime

    async def initialize(self) -> None:
        if not self.redis_broadcaster.is_connected:
            await self.redis_broadcaster.connect()

        await self._start_subscription()

    async def shutdown(self) -> None:
        if self.pubsub_task and not self.pubsub_task.done():
            self.pubsub_task.cancel()
            try:
                await self.pubsub_task
            except asyncio.CancelledError:
                pass

        for websocket in list(self.active_connections.keys()):
            await self.disconnect(websocket)

    async def connect(
        self, websocket: WebSocket, client_id: Optional[str] = None
    ) -> None:
        await websocket.accept()
        self.active_connections[websocket] = {
            "client_id": client_id or f"client_{id(websocket)}",
            "worker_id": self.worker_id,
            "stock_ids": set(),
            "connected_at": self._now.now(),
            "is_global_subscriber": False,
        }

    async def disconnect(self, websocket: WebSocket) -> None:
        if websocket not in self.active_connections:
            return

        info = self.active_connections.pop(websocket)

        for stock_id in info["stock_ids"]:
            subscribers = self.stock_subscriptions.get(stock_id)
            if not subscribers:
                continue
            subscribers.discard(websocket)
            if not subscribers:
                self.stock_subscriptions.pop(stock_id, None)

        if info["is_global_subscriber"]:
            self.global_subscriptions.discard(websocket)

    async def send_personal_message(self, message: dict, websocket: WebSocket) -> None:
        await websocket.send_json(message)

    async def broadcast_stock_update(self, stock_id: int, message: dict) -> None:
        await self.redis_broadcaster.publish_stock_update(stock_id, message)

    async def broadcast_global_update(self, message: dict) -> None:
        await self.redis_broadcaster.publish_global_update(message)

    async def subscribe_to_stock(self, websocket: WebSocket, stock_id: int) -> None:
        if websocket not in self.active_connections:
            return

        info = self.active_connections[websocket]
        info["stock_ids"].add(stock_id)
        channel = f"stock_updates:{stock_id}"

        subscribers = self.stock_subscriptions.setdefault(stock_id, set())
        if not subscribers:
            await self._subscribe_channel(channel)
        subscribers.add(websocket)

    async def unsubscribe_from_stock(self, websocket: WebSocket, stock_id: int) -> None:
        if websocket not in self.active_connections:
            return

        info = self.active_connections[websocket]
        info["stock_ids"].discard(stock_id)
        channel = f"stock_updates:{stock_id}"

        subscribers = self.stock_subscriptions.get(stock_id)
        if not subscribers:
            return
        subscribers.discard(websocket)
        if not subscribers:
            await self._unsubscribe_channel(channel)
            self.stock_subscriptions.pop(stock_id, None)

    async def subscribe_global(self, websocket: WebSocket) -> None:
        if websocket not in self.active_connections:
            return

        if not self.global_subscriptions:
            await self._subscribe_channel("global_updates")

        self.global_subscriptions.add(websocket)
        self.active_connections[websocket]["is_global_subscriber"] = True

    async def unsubscribe_global(self, websocket: WebSocket) -> None:
        if websocket not in self.active_connections:
            return

        self.global_subscriptions.discard(websocket)
        self.active_connections[websocket]["is_global_subscriber"] = False

        if not self.global_subscriptions:
            await self._unsubscribe_channel("global_updates")

    def get_connection_stats(self) -> Dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "total_connections": len(self.active_connections),
            "stock_subscriptions": len(self.stock_subscriptions),
            "global_subscriptions": len(self.global_subscriptions),
        }

    async def get_cluster_stats(self) -> Dict[str, Any]:
        redis_health = await self.redis_broadcaster.health_check()
        return {
            "local_worker": self.get_connection_stats(),
            "redis_health": redis_health,
        }

    async def _start_subscription(self) -> None:
        channels = ["global_updates", "stock_updates:*"]
        self.pubsub_task = asyncio.create_task(
            self.redis_broadcaster.subscribe_to_channels(channels, self._handle_message)
        )

    async def _subscribe_channel(self, channel: str) -> None:
        self.redis_channels.add(channel)

    async def _unsubscribe_channel(self, channel: str) -> None:
        self.redis_channels.discard(channel)

    async def _handle_message(self, channel: str, message: dict) -> None:
        payload = message.get("data", {})
        if channel == "global_updates":
            await self._broadcast_locally(payload)
            return

        if channel.startswith("stock_updates:"):
            try:
                stock_id = int(channel.split(":")[-1])
            except ValueError:
                return

            await self._broadcast_stock_locally(stock_id, payload)

    async def _broadcast_locally(self, message: dict) -> None:
        for websocket in list(self.global_subscriptions):
            try:
                await websocket.send_json(message)
            except Exception:
                await self.disconnect(websocket)

    async def _broadcast_stock_locally(self, stock_id: int, message: dict) -> None:
        subscribers = self.stock_subscriptions.get(stock_id)
        if not subscribers:
            return

        for websocket in list(subscribers):
            try:
                await websocket.send_json(message)
            except Exception:
                await self.disconnect(websocket)
