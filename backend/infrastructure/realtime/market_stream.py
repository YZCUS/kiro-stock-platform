"""Realtime market stream service for quote and 5m bar fanout."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from random import Random
from typing import Awaitable, Callable, Dict, Optional, Set

import redis.asyncio as redis
import websockets
from fastapi import WebSocket
from sqlalchemy import select

from app.settings import Settings, get_settings
from core.database import AsyncSessionLocal
from domain.market_data.realtime import MarketTradeEvent, RealtimeBar, RealtimeQuote
from domain.models.stock import Stock
from domain.services.intraday_signal_service import IntradaySignalEngine
from infrastructure.persistence.market_data_bar_repository import MarketDataBarRepository

logger = logging.getLogger(__name__)

TradeCallback = Callable[[MarketTradeEvent], Awaitable[None]]


class MarketStreamProvider:
    """Upstream realtime market stream provider contract."""

    def __init__(self) -> None:
        self._handlers: list[TradeCallback] = []

    def add_trade_handler(self, handler: TradeCallback) -> None:
        self._handlers.append(handler)

    async def start(self) -> None:
        raise NotImplementedError

    async def stop(self) -> None:
        raise NotImplementedError

    async def subscribe(self, market: str, symbol: str) -> None:
        raise NotImplementedError

    async def unsubscribe(self, market: str, symbol: str) -> None:
        raise NotImplementedError

    async def health(self) -> dict:
        raise NotImplementedError

    async def _emit_trade(self, event: MarketTradeEvent) -> None:
        for handler in list(self._handlers):
            await handler(event)


class MockMarketStreamProvider(MarketStreamProvider):
    """Deterministic local stream used when Finnhub streaming is unavailable."""

    def __init__(self) -> None:
        super().__init__()
        self._subscriptions: Set[tuple[str, str]] = set()
        self._prices: Dict[tuple[str, str], float] = {}
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._random = Random(42)

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def subscribe(self, market: str, symbol: str) -> None:
        key = (market.upper(), symbol.upper())
        self._subscriptions.add(key)
        self._prices.setdefault(key, 100.0 + len(self._prices) * 7.5)
        await self.start()

    async def unsubscribe(self, market: str, symbol: str) -> None:
        self._subscriptions.discard((market.upper(), symbol.upper()))

    async def health(self) -> dict:
        return {
            "provider": "mock",
            "connected": self._running,
            "subscriptions": len(self._subscriptions),
        }

    async def _run(self) -> None:
        while self._running:
            now = datetime.now(timezone.utc)
            for market, symbol in list(self._subscriptions):
                previous = self._prices[(market, symbol)]
                drift = self._random.uniform(-0.15, 0.15)
                next_price = max(0.01, round(previous + drift, 4))
                self._prices[(market, symbol)] = next_price
                await self._emit_trade(
                    MarketTradeEvent(
                        market=market,
                        symbol=symbol,
                        price=next_price,
                        volume=self._random.randint(10, 500),
                        timestamp=now,
                        source="mock_stream",
                    )
                )
            await asyncio.sleep(2)


class FinnhubMarketStreamProvider(MarketStreamProvider):
    """Finnhub websocket trade stream provider.

    Finnhub websocket trades use:
    wss://ws.finnhub.io?token=TOKEN
    subscribe: {"type": "subscribe", "symbol": "AAPL"}
    data: {"type": "trade", "data": [{"s": "AAPL", "p": 1.23, "v": 100, "t": 171...}]}
    """

    def __init__(self, api_key: str, ws_url: str = "wss://ws.finnhub.io") -> None:
        super().__init__()
        self.api_key = api_key
        self.ws_url = ws_url.rstrip("/")
        self._subscriptions: Set[tuple[str, str]] = set()
        self._socket = None
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._connected = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._running = False
        if self._socket:
            await self._socket.close()
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def subscribe(self, market: str, symbol: str) -> None:
        key = (market.upper(), symbol.upper())
        self._subscriptions.add(key)
        await self.start()
        if self._connected:
            await self._send({"type": "subscribe", "symbol": key[1]})

    async def unsubscribe(self, market: str, symbol: str) -> None:
        key = (market.upper(), symbol.upper())
        self._subscriptions.discard(key)
        if self._connected:
            await self._send({"type": "unsubscribe", "symbol": key[1]})

    async def health(self) -> dict:
        return {
            "provider": "finnhub",
            "connected": self._connected,
            "subscriptions": len(self._subscriptions),
        }

    async def _run(self) -> None:
        retry_seconds = 1
        while self._running:
            try:
                url = f"{self.ws_url}?token={self.api_key}"
                async with websockets.connect(url, ping_interval=20) as websocket:
                    self._socket = websocket
                    self._connected = True
                    retry_seconds = 1
                    for _, symbol in list(self._subscriptions):
                        await self._send({"type": "subscribe", "symbol": symbol})

                    async for raw_message in websocket:
                        await self._handle_message(raw_message)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.warning("Finnhub stream disconnected: %s", exc)
            finally:
                self._connected = False
                self._socket = None

            if self._running:
                await asyncio.sleep(retry_seconds)
                retry_seconds = min(retry_seconds * 2, 30)

    async def _send(self, message: dict) -> None:
        if not self._socket:
            return
        await self._socket.send(json.dumps(message))

    async def _handle_message(self, raw_message: str) -> None:
        try:
            payload = json.loads(raw_message)
        except json.JSONDecodeError:
            return

        if payload.get("type") != "trade":
            return

        for trade in payload.get("data") or []:
            symbol = str(trade.get("s") or "").upper()
            if not symbol:
                continue
            subscription = next(
                (
                    (market, subscribed_symbol)
                    for market, subscribed_symbol in self._subscriptions
                    if subscribed_symbol == symbol
                ),
                None,
            )
            if subscription is None:
                continue

            price = _float_or_none(trade.get("p"))
            if price is None or price <= 0:
                continue

            timestamp = _finnhub_timestamp_to_datetime(trade.get("t"))
            await self._emit_trade(
                MarketTradeEvent(
                    market=subscription[0],
                    symbol=symbol,
                    price=price,
                    volume=int(_float_or_none(trade.get("v")) or 0),
                    timestamp=timestamp,
                    source="finnhub_stream",
                )
            )


class RealtimeMarketCache:
    """Redis-backed latest quote/current bar cache with memory fallback."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._redis: Optional[redis.Redis] = None
        self._memory: Dict[str, dict] = {}

    async def connect(self) -> None:
        if self._redis is not None:
            return
        try:
            auth_part = (
                f":{self.settings.redis.password}@"
                if self.settings.redis.password
                else ""
            )
            redis_url = (
                f"redis://{auth_part}{self.settings.redis.host}:"
                f"{self.settings.redis.port}/{self.settings.redis.db}"
            )
            self._redis = redis.Redis.from_url(
                redis_url, encoding="utf-8", decode_responses=True
            )
            await self._redis.ping()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Realtime cache using memory fallback: %s", exc)
            self._redis = None

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.close()
            self._redis = None

    async def set_json(self, key: str, value: dict, ttl_seconds: int = 300) -> None:
        self._memory[key] = value
        if self._redis is None:
            return
        await self._redis.setex(key, ttl_seconds, json.dumps(value))

    async def get_json(self, key: str) -> Optional[dict]:
        if self._redis is not None:
            value = await self._redis.get(key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return None
        return self._memory.get(key)


class FiveMinuteBarAggregator:
    """Build current/finalized 5m candles from realtime trade events."""

    def __init__(self) -> None:
        self._current_bars: Dict[tuple[str, str], RealtimeBar] = {}

    def apply_trade(
        self, event: MarketTradeEvent
    ) -> tuple[Optional[RealtimeBar], RealtimeBar]:
        key = (event.market, event.symbol)
        bucket_start = _floor_to_interval(event.timestamp, minutes=5)
        current = self._current_bars.get(key)

        if current is None:
            next_bar = self._new_bar(event, bucket_start)
            self._current_bars[key] = next_bar
            return None, next_bar

        if current.bucket_start != bucket_start:
            finalized = replace(current, is_final=True)
            next_bar = self._new_bar(event, bucket_start)
            self._current_bars[key] = next_bar
            return finalized, next_bar

        next_bar = replace(
            current,
            high=max(current.high, event.price),
            low=min(current.low, event.price),
            close=event.price,
            volume=current.volume + event.volume,
            is_final=False,
        )
        self._current_bars[key] = next_bar
        return None, next_bar

    def snapshot(self, market: str, symbol: str) -> Optional[RealtimeBar]:
        return self._current_bars.get((market.upper(), symbol.upper()))

    def _new_bar(self, event: MarketTradeEvent, bucket_start: datetime) -> RealtimeBar:
        return RealtimeBar(
            market=event.market,
            symbol=event.symbol,
            interval="5m",
            bucket_start=bucket_start,
            open=event.price,
            high=event.price,
            low=event.price,
            close=event.price,
            volume=event.volume,
            source=event.source,
            is_final=False,
        )


class MarketStreamService:
    """Frontend websocket fanout for realtime quote and 5m bar updates."""

    def __init__(
        self,
        provider: MarketStreamProvider,
        cache: RealtimeMarketCache,
    ) -> None:
        self.provider = provider
        self.cache = cache
        self.aggregator = FiveMinuteBarAggregator()
        self.signal_engine = IntradaySignalEngine()
        self.connections: Dict[WebSocket, dict] = {}
        self.subscribers: Dict[tuple[str, str], Set[WebSocket]] = {}
        self._stock_cache: Dict[tuple[str, str], dict] = {}
        self._seeded_symbols: Set[tuple[str, str]] = set()
        self.provider.add_trade_handler(self._handle_trade)

    async def initialize(self) -> None:
        await self.cache.connect()

    async def shutdown(self) -> None:
        await self.provider.stop()
        await self.cache.close()
        for websocket in list(self.connections):
            await self.disconnect(websocket)

    async def connect(self, websocket: WebSocket, client_id: Optional[str]) -> None:
        await websocket.accept()
        self.connections[websocket] = {
            "client_id": client_id or f"market_client_{id(websocket)}",
            "subscriptions": set(),
        }
        await self._send(
            websocket,
            {
                "type": "welcome",
                "message": "Market stream connected",
                "client_id": self.connections[websocket]["client_id"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        info = self.connections.pop(websocket, None)
        if not info:
            return
        for key in list(info["subscriptions"]):
            await self._unsubscribe_key(websocket, key)

    async def handle_message(self, websocket: WebSocket, message: dict) -> None:
        message_type = message.get("type")
        if message_type == "subscribe_symbol":
            await self.subscribe_symbol(
                websocket,
                market=str(message.get("market") or "US"),
                symbol=str(message.get("symbol") or ""),
                intervals=set(message.get("intervals") or ["quote", "5m"]),
            )
            return
        if message_type == "unsubscribe_symbol":
            await self.unsubscribe_symbol(
                websocket,
                market=str(message.get("market") or "US"),
                symbol=str(message.get("symbol") or ""),
            )
            return
        if message_type == "ping":
            await self._send(
                websocket,
                {"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()},
            )
            return
        await self._send(websocket, {"type": "error", "message": "Unknown message type"})

    async def subscribe_symbol(
        self,
        websocket: WebSocket,
        market: str,
        symbol: str,
        intervals: Set[str],
    ) -> None:
        market = market.upper()
        symbol = symbol.upper().strip()
        if not symbol:
            await self._send(websocket, {"type": "error", "message": "symbol is required"})
            return

        key = (market, symbol)
        first_subscriber = key not in self.subscribers
        self.subscribers.setdefault(key, set()).add(websocket)
        self.connections[websocket]["subscriptions"].add(key)

        if first_subscriber:
            await self._seed_intraday_history(market, symbol)
            await self.provider.subscribe(market, symbol)

        await self._send(
            websocket,
            {
                "type": "subscribed",
                "market": market,
                "symbol": symbol,
                "intervals": sorted(intervals),
            },
        )
        await self._send_cached_snapshot(websocket, market, symbol)

    async def unsubscribe_symbol(
        self,
        websocket: WebSocket,
        market: str,
        symbol: str,
    ) -> None:
        await self._unsubscribe_key(websocket, (market.upper(), symbol.upper().strip()))

    async def health(self) -> dict:
        provider_health = await self.provider.health()
        return {
            "connections": len(self.connections),
            "active_symbols": len(self.subscribers),
            "provider": provider_health,
        }

    async def _unsubscribe_key(
        self, websocket: WebSocket, key: tuple[str, str]
    ) -> None:
        subscribers = self.subscribers.get(key)
        if subscribers:
            subscribers.discard(websocket)
            if not subscribers:
                self.subscribers.pop(key, None)
                await self.provider.unsubscribe(*key)

        info = self.connections.get(websocket)
        if info:
            info["subscriptions"].discard(key)

    async def _handle_trade(self, event: MarketTradeEvent) -> None:
        quote = RealtimeQuote(
            market=event.market,
            symbol=event.symbol,
            price=event.price,
            volume=event.volume,
            timestamp=event.timestamp,
            source=event.source,
        )
        finalized_bar, current_bar = self.aggregator.apply_trade(event)

        await self.cache.set_json(
            self._quote_key(event.market, event.symbol),
            quote.to_message_data(),
            ttl_seconds=120,
        )
        await self.cache.set_json(
            self._bar_key(event.market, event.symbol),
            current_bar.to_message_data(),
            ttl_seconds=600,
        )

        await self._broadcast(
            (event.market, event.symbol),
            {
                "type": "quote_update",
                "market": event.market,
                "symbol": event.symbol,
                "data": quote.to_message_data(),
            },
        )
        await self._broadcast(
            (event.market, event.symbol),
            {
                "type": "bar_update",
                "market": event.market,
                "symbol": event.symbol,
                "interval": "5m",
                "data": current_bar.to_message_data(),
            },
        )

        if finalized_bar is not None:
            await self._persist_finalized_bar(finalized_bar)
            await self._broadcast(
                (event.market, event.symbol),
                {
                    "type": "bar_update",
                    "market": event.market,
                    "symbol": event.symbol,
                    "interval": "5m",
                    "data": finalized_bar.to_message_data(),
                },
            )

        await self._publish_intraday_signals(current_bar)

    async def _persist_finalized_bar(self, bar: RealtimeBar) -> None:
        stock = await self._get_stock_snapshot(bar.market, bar.symbol)
        if stock is None or AsyncSessionLocal is None:
            return

        async with AsyncSessionLocal() as db:
            await MarketDataBarRepository().upsert_batch(
                db,
                [
                    {
                        "stock_id": stock["id"],
                        "symbol": stock["symbol"],
                        "market": stock["market"],
                        "timeframe": "5m",
                        "timestamp": bar.bucket_start,
                        "open_price": Decimal(str(bar.open)),
                        "high_price": Decimal(str(bar.high)),
                        "low_price": Decimal(str(bar.low)),
                        "close_price": Decimal(str(bar.close)),
                        "volume": bar.volume,
                        "source": bar.source,
                        "source_type": "source",
                        "is_adjusted": False,
                        "generated_from_timeframe": None,
                        "quality_status": "complete",
                    }
                ],
            )

    async def _publish_intraday_signals(self, bar: RealtimeBar) -> None:
        stock = await self._get_stock_snapshot(bar.market, bar.symbol)
        signals = self.signal_engine.evaluate(bar)
        for signal in signals:
            payload = signal.to_payload(
                stock_id=stock["id"] if stock else None,
                symbol=bar.symbol,
                stock_name=stock["name"] if stock else None,
            )
            await self._broadcast(
                (bar.market, bar.symbol),
                {
                    "type": "signal_update",
                    "market": bar.market,
                    "symbol": bar.symbol,
                    "interval": "5m",
                    "data": payload,
                },
            )

    async def _seed_intraday_history(self, market: str, symbol: str) -> None:
        key = (market.upper(), symbol.upper())
        if key in self._seeded_symbols or AsyncSessionLocal is None:
            return

        self._seeded_symbols.add(key)
        stock = await self._get_stock_snapshot(market, symbol)
        if stock is None:
            return

        async with AsyncSessionLocal() as db:
            bars = await MarketDataBarRepository().get_bars(
                db,
                stock_id=stock["id"],
                timeframe="5m",
                limit=80,
                ascending=True,
            )

        self.signal_engine.seed(
            market,
            symbol,
            [
                RealtimeBar(
                    market=bar.market,
                    symbol=bar.symbol,
                    interval="5m",
                    bucket_start=bar.timestamp,
                    open=float(bar.open_price),
                    high=float(bar.high_price),
                    low=float(bar.low_price),
                    close=float(bar.close_price),
                    volume=int(bar.volume),
                    source=bar.source,
                    is_final=True,
                )
                for bar in bars
            ],
        )

    async def _get_stock_snapshot(
        self,
        market: str,
        symbol: str,
    ) -> Optional[dict]:
        key = (market.upper(), symbol.upper())
        if key in self._stock_cache:
            return self._stock_cache[key]
        if AsyncSessionLocal is None:
            return None

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Stock).where(Stock.symbol == key[1], Stock.market == key[0])
            )
            stock = result.scalar_one_or_none()

        if stock is None:
            return None

        snapshot = {
            "id": stock.id,
            "symbol": stock.symbol,
            "market": stock.market,
            "name": stock.name,
        }
        self._stock_cache[key] = snapshot
        return snapshot

    async def _send_cached_snapshot(
        self, websocket: WebSocket, market: str, symbol: str
    ) -> None:
        quote = await self.cache.get_json(self._quote_key(market, symbol))
        if quote:
            await self._send(
                websocket,
                {
                    "type": "quote_update",
                    "market": market,
                    "symbol": symbol,
                    "data": quote,
                },
            )

        bar = await self.cache.get_json(self._bar_key(market, symbol))
        if not bar:
            snapshot = self.aggregator.snapshot(market, symbol)
            bar = snapshot.to_message_data() if snapshot else None
        if bar:
            await self._send(
                websocket,
                {
                    "type": "bar_update",
                    "market": market,
                    "symbol": symbol,
                    "interval": "5m",
                    "data": bar,
                },
            )

    async def _broadcast(self, key: tuple[str, str], message: dict) -> None:
        for websocket in list(self.subscribers.get(key) or []):
            await self._send(websocket, message)

    async def _send(self, websocket: WebSocket, message: dict) -> None:
        try:
            await websocket.send_json(message)
        except Exception:  # noqa: BLE001
            await self.disconnect(websocket)

    def _quote_key(self, market: str, symbol: str) -> str:
        return f"quote:{market.upper()}:{symbol.upper()}"

    def _bar_key(self, market: str, symbol: str) -> str:
        return f"bar:5m:{market.upper()}:{symbol.upper()}:current"


def create_market_stream_service(
    settings: Optional[Settings] = None,
) -> MarketStreamService:
    settings = settings or get_settings()
    provider: MarketStreamProvider
    api_key = settings.external_api.finnhub_api_key
    ws_url = getattr(settings.external_api, "finnhub_ws_url", "wss://ws.finnhub.io")

    if api_key:
        provider = FinnhubMarketStreamProvider(api_key=api_key, ws_url=ws_url)
    else:
        provider = MockMarketStreamProvider()

    return MarketStreamService(provider=provider, cache=RealtimeMarketCache(settings))


def _floor_to_interval(timestamp: datetime, minutes: int) -> datetime:
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    timestamp = timestamp.astimezone(timezone.utc)
    minute = timestamp.minute - (timestamp.minute % minutes)
    return timestamp.replace(minute=minute, second=0, microsecond=0)


def _finnhub_timestamp_to_datetime(value) -> datetime:
    try:
        timestamp_ms = int(value)
    except (TypeError, ValueError):
        return datetime.now(timezone.utc)
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)


def _float_or_none(value) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
