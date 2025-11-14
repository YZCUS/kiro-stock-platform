"""
WebSocket 即時數據服務 - 支援多Worker環境
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    get_database_session,
    get_websocket_manager,
)
from domain.services.stock_service import StockService
from domain.services.trading_signal_service import TradingSignalService
from infrastructure.cache.redis_cache_service import ICacheService
from infrastructure.realtime.websocket_manager import IWebSocketManager

logger = logging.getLogger(__name__)


class WebSocketService:
    """WebSocket 服務類"""

    def __init__(
        self,
        stock_service: StockService,
        trading_signal_service: TradingSignalService,
        websocket_manager: IWebSocketManager,
        cache_service: ICacheService,
    ) -> None:
        self.stock_service = stock_service
        self.trading_signal_service = trading_signal_service
        self.manager = websocket_manager
        self.cache = cache_service

    async def handle_message(
        self,
        websocket: WebSocket,
        message: Dict[str, Any],
        db: AsyncSession,
    ) -> None:
        """處理客戶端消息"""
        message_type = message.get("type")
        data = message.get("data", {})

        handlers = {
            "subscribe_stock": self._handle_subscribe_stock,
            "unsubscribe_stock": self._handle_unsubscribe_stock,
            "subscribe_global": self._handle_subscribe_global,
            "unsubscribe_global": self._handle_unsubscribe_global,
            "get_stats": self._handle_get_stats,
            "ping": self._handle_ping,
        }

        handler = handlers.get(message_type)
        if handler:
            await handler(websocket, data, db)
            return

        await self.manager.send_personal_message(
            {"type": "error", "message": f"未知的消息類型: {message_type}"},
            websocket,
        )

    async def send_initial_stock_data(
        self,
        websocket: WebSocket,
        stock_id: int,
        db: AsyncSession = None,  # db 參數變為可選，我們將創建新的 session
    ) -> None:
        """發送初始股票數據"""
        # 創建新的資料庫 session 以確保能看到最新數據
        from core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as fresh_db:
            try:
                stock = await self.stock_service.get_stock_by_id(fresh_db, stock_id)

                # 如果 stock 是 None，可能是事務隔離問題，直接返回錯誤但不中斷連線
                if stock is None:
                    logger.warning(
                        "股票 %s 暫時無法取得（可能正在創建中），跳過初始數據發送",
                        stock_id,
                    )
                    return

            except Exception as exc:  # noqa: BLE001
                # 捕獲所有異常，但不視為致命錯誤
                # 某些情況下（如股票剛創建），可能會暫時無法取得
                logger.warning("無法取得股票 %s: %s，跳過初始數據發送", stock_id, exc)
                return

            price_data = await self.trading_signal_service.get_price_history(
                fresh_db, stock_id=stock_id, limit=100
            )
            indicator_data = await self.trading_signal_service.get_indicator_history(
                fresh_db, stock_id=stock_id, limit=50
            )
            signal_data = await self.trading_signal_service.get_signal_history(
                fresh_db, stock_id=stock_id, limit=10
            )

        await self.manager.send_personal_message(
            {
                "type": "initial_data",
                "data": {
                    "stock": {
                        "id": stock.id,
                        "symbol": stock.symbol,
                        "market": stock.market,
                        "name": stock.name,
                    },
                    "prices": price_data,
                    "indicators": indicator_data,
                    "signals": signal_data,
                    "timestamp": datetime.now().isoformat(),
                },
            },
            websocket,
        )

    async def broadcast_price_update(self, stock_id: int, price_data: dict) -> None:
        await self.manager.broadcast_stock_update(
            stock_id,
            {"type": "price_update", "data": price_data},
        )

    async def broadcast_indicator_update(
        self, stock_id: int, indicator_data: dict
    ) -> None:
        await self.manager.broadcast_stock_update(
            stock_id,
            {"type": "indicator_update", "data": indicator_data},
        )

    async def broadcast_signal_update(self, stock_id: int, signal_data: dict) -> None:
        await self.manager.broadcast_stock_update(
            stock_id,
            {"type": "signal_update", "data": signal_data},
        )

    async def broadcast_market_status(self, status_data: dict) -> None:
        await self.manager.broadcast_global_update(
            {"type": "market_status", "data": status_data}
        )

    async def _handle_subscribe_stock(
        self,
        websocket: WebSocket,
        data: Dict[str, Any],
        db: AsyncSession,
    ) -> None:
        stock_id = data.get("stock_id")
        if not stock_id:
            await self.manager.send_personal_message(
                {"type": "error", "message": "缺少 stock_id"},
                websocket,
            )
            return

        subscribe = getattr(self.manager, "subscribe_to_stock", None)
        if subscribe:
            await subscribe(websocket, stock_id)

        await self.send_initial_stock_data(websocket, stock_id, db)

    async def _handle_unsubscribe_stock(
        self,
        websocket: WebSocket,
        data: Dict[str, Any],
        db: AsyncSession,
    ) -> None:  # noqa: ARG002 - db reserved for interface parity
        stock_id = data.get("stock_id")
        unsubscribe = getattr(self.manager, "unsubscribe_from_stock", None)
        if stock_id and unsubscribe:
            await unsubscribe(websocket, stock_id)

    async def _handle_subscribe_global(
        self,
        websocket: WebSocket,
        data: Dict[str, Any],
        db: AsyncSession,
    ) -> None:  # noqa: ARG002
        subscribe = getattr(self.manager, "subscribe_global", None)
        if subscribe:
            await subscribe(websocket)

    async def _handle_unsubscribe_global(
        self,
        websocket: WebSocket,
        data: Dict[str, Any],
        db: AsyncSession,
    ) -> None:  # noqa: ARG002
        unsubscribe = getattr(self.manager, "unsubscribe_global", None)
        if unsubscribe:
            await unsubscribe(websocket)

    async def _handle_get_stats(
        self,
        websocket: WebSocket,
        data: Dict[str, Any],
        db: AsyncSession,
    ) -> None:  # noqa: ARG002
        stats = self.manager.get_connection_stats()
        await self.manager.send_personal_message(
            {"type": "stats", "data": stats},
            websocket,
        )

    async def _handle_ping(
        self,
        websocket: WebSocket,
        data: Dict[str, Any],
        db: AsyncSession,
    ) -> None:  # noqa: ARG002
        await self.manager.send_personal_message(
            {"type": "pong", "timestamp": datetime.now().isoformat()},
            websocket,
        )


class WebSocketServiceState:
    def __init__(self) -> None:
        self.is_initialized = False
        self.degraded_mode = False
        self.initialization_error: Exception | None = None

    def set_initialized(self, success: bool, error: Exception | None = None) -> None:
        self.is_initialized = success
        self.degraded_mode = not success
        self.initialization_error = error


websocket_service_state = WebSocketServiceState()


async def websocket_endpoint(
    websocket: WebSocket,
    stock_id: Optional[int] = None,
    client_id: Optional[str] = None,
    db: AsyncSession = Depends(get_database_session),
) -> None:
    """
    WebSocket 端點處理函數

    使用全域單例的 WebSocketService，避免為每個連線創建新實例。
    """
    # 從依賴注入容器取得單例服務和管理器
    from app.dependencies import get_websocket_service, get_websocket_manager

    service = get_websocket_service()
    websocket_manager = get_websocket_manager()

    # 檢查服務狀態（初始化已在應用程式啟動時完成）
    if websocket_service_state.degraded_mode:
        logger.warning("WebSocket服務處於降級模式，拒絕新連接: %s", client_id)
        await websocket.close(code=1013, reason="Service temporarily unavailable")
        return

    if not websocket_service_state.is_initialized:
        logger.error("WebSocket 管理器未初始化，拒絕連接: %s", client_id)
        await websocket.close(code=1011, reason="Service not initialized")
        return

    # 建立連接
    await websocket_manager.connect(websocket, client_id)

    if stock_id:
        subscribe = getattr(websocket_manager, "subscribe_to_stock", None)
        if subscribe:
            await subscribe(websocket, stock_id)
        await service.send_initial_stock_data(websocket, stock_id, db)

    connection_stats = websocket_manager.get_connection_stats()
    await websocket_manager.send_personal_message(
        {
            "type": "welcome",
            "message": "WebSocket連接成功",
            "client_id": client_id,
            "worker_id": connection_stats.get("worker_id"),
            "timestamp": datetime.now().isoformat(),
        },
        websocket,
    )

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await service.handle_message(websocket, message, db)
    except WebSocketDisconnect:
        logger.info("WebSocket客戶端正常斷開連接: %s", client_id)
    except json.JSONDecodeError as exc:
        logger.warning("WebSocket收到無效JSON: %s", exc)
        await websocket_manager.send_personal_message(
            {"type": "error", "message": f"JSON格式錯誤: {exc}"},
            websocket,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("WebSocket處理消息時發生未預期錯誤: %s", exc)
        await websocket_manager.send_personal_message(
            {"type": "error", "message": f"處理消息失敗: {exc}"},
            websocket,
        )
    finally:
        await websocket_manager.disconnect(websocket)


async def initialize_websocket_manager() -> bool:
    manager = get_websocket_manager()
    try:
        await manager.initialize()
        websocket_service_state.set_initialized(True)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.exception("初始化 WebSocket 管理器失敗")
        websocket_service_state.set_initialized(False, exc)
        return False


async def shutdown_websocket_manager() -> None:
    manager = get_websocket_manager()
    try:
        await manager.shutdown()
        websocket_service_state.set_initialized(False)
    except Exception as exc:  # noqa: BLE001
        logger.exception("關閉 WebSocket 管理器失敗: %s", exc)


async def health_check_websocket_service() -> Dict[str, Any]:
    manager = get_websocket_manager()
    status = "healthy"
    if websocket_service_state.degraded_mode:
        status = "degraded"

    stats: Dict[str, Any] = {}
    try:
        stats = manager.get_connection_stats()
    except Exception as exc:  # noqa: BLE001
        logger.debug("取得管理器狀態失敗: %s", exc)

    health = {
        "service": "websocket",
        "status": status,
        "initialized": websocket_service_state.is_initialized,
        "degraded_mode": websocket_service_state.degraded_mode,
        "timestamp": datetime.now().isoformat(),
        "connections": stats,
    }

    if websocket_service_state.initialization_error:
        health["error"] = str(websocket_service_state.initialization_error)

    return health


async def get_websocket_cluster_stats() -> Dict[str, Any]:
    manager = get_websocket_manager()
    try:
        return await manager.get_cluster_stats()
    except Exception as exc:  # noqa: BLE001
        logger.exception("取得 WebSocket 集群統計失敗: %s", exc)
        return {"error": str(exc), "timestamp": datetime.now().isoformat()}
