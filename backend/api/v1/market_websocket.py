"""Market data websocket endpoint for realtime quote and 5m bar streams."""

from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect

from app.settings import get_settings
from infrastructure.realtime.market_stream import (
    MarketStreamService,
    create_market_stream_service,
)

logger = logging.getLogger(__name__)

_market_stream_service: Optional[MarketStreamService] = None
_market_stream_initialized = False


def get_market_stream_service() -> MarketStreamService:
    global _market_stream_service
    if _market_stream_service is None:
        _market_stream_service = create_market_stream_service(get_settings())
    return _market_stream_service


async def initialize_market_stream_service() -> None:
    global _market_stream_initialized
    if _market_stream_initialized:
        return
    await get_market_stream_service().initialize()
    _market_stream_initialized = True


async def shutdown_market_stream_service() -> None:
    global _market_stream_initialized
    if not _market_stream_initialized:
        return
    await get_market_stream_service().shutdown()
    _market_stream_initialized = False


async def market_stream_stats() -> dict:
    return await get_market_stream_service().health()


async def market_websocket_endpoint(
    websocket: WebSocket,
    client_id: Optional[str] = None,
) -> None:
    service = get_market_stream_service()
    await initialize_market_stream_service()
    await service.connect(websocket, client_id)

    try:
        while True:
            raw_message = await websocket.receive_text()
            try:
                message = json.loads(raw_message)
            except json.JSONDecodeError as exc:
                await websocket.send_json(
                    {"type": "error", "message": f"Invalid JSON: {exc}"}
                )
                continue
            await service.handle_message(websocket, message)
    except WebSocketDisconnect:
        logger.info("Market websocket disconnected: %s", client_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Market websocket error: %s", exc)
    finally:
        await service.disconnect(websocket)
