"""Focused regression tests for async Redis cache and WebSocket Pub/Sub."""

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app import dependencies
from domain.market_data.realtime import MarketTradeEvent
from infrastructure.cache.redis_cache_service import RedisCacheService
from infrastructure.realtime.market_stream import MarketStreamService
from infrastructure.realtime.redis_pubsub import RedisWebSocketBroadcaster
from infrastructure.realtime.websocket_manager import RedisBackedWebSocketManager


class FakeAsyncRedis:
    def __init__(self):
        self.values = {"cache:one": '{"value": 1}'}
        self.fail_gets = 0
        self.scan_calls = []
        self.unlink_calls = []

    async def get(self, key):
        if self.fail_gets:
            self.fail_gets -= 1
            raise ConnectionError("redis unavailable")
        return self.values.get(key)

    async def scan(self, cursor=0, match=None, count=None):
        self.scan_calls.append((cursor, match, count))
        if cursor == 0:
            return 7, ["cache:one", "cache:two"]
        return 0, ["cache:three"]

    async def unlink(self, *keys):
        self.unlink_calls.append(keys)
        return len(keys)


@pytest.mark.asyncio
async def test_async_cache_recovers_after_transient_redis_failure():
    redis_client = FakeAsyncRedis()
    redis_client.fail_gets = 1
    cache = RedisCacheService(redis_client, SimpleNamespace(default_ttl=300))

    assert await cache.get("cache:one") is None
    assert await cache.get("cache:one") == {"value": 1}


@pytest.mark.asyncio
async def test_clear_pattern_uses_incremental_scan_and_unlink():
    redis_client = FakeAsyncRedis()
    cache = RedisCacheService(redis_client, SimpleNamespace(default_ttl=300))

    deleted = await cache.clear_pattern("cache:*")

    assert deleted == 3
    assert redis_client.scan_calls == [
        (0, "cache:*", 500),
        (7, "cache:*", 500),
    ]
    assert redis_client.unlink_calls == [
        ("cache:one", "cache:two"),
        ("cache:three",),
    ]


def test_cache_singleton_can_recover_after_initial_client_failure(monkeypatch):
    monkeypatch.setattr(dependencies, "_cache_service_singleton", None)
    settings = SimpleNamespace(redis=SimpleNamespace(default_ttl=300))

    unavailable = dependencies.get_cache_service(settings, None)
    redis_client = FakeAsyncRedis()
    recovered = dependencies.get_cache_service(settings, redis_client)

    assert unavailable.is_connected is False
    assert dependencies._cache_service_singleton is recovered
    assert recovered.redis_client is redis_client


class FakePubSub:
    def __init__(self, messages):
        self.messages = messages
        self.subscribed = []
        self.psubscribed = []
        self.closed = False

    async def subscribe(self, *channels):
        self.subscribed.extend(channels)

    async def psubscribe(self, *patterns):
        self.psubscribed.extend(patterns)

    async def listen(self):
        for message in self.messages:
            yield message

    async def aclose(self):
        self.closed = True


@pytest.mark.asyncio
async def test_redis_broadcaster_uses_pattern_subscription_and_pmessage_channel():
    pubsub = FakePubSub(
        [
            {
                "type": "pmessage",
                "pattern": "stock_updates:*",
                "channel": "stock_updates:42",
                "data": '{"data": {"price": 101}}',
            },
            {
                "type": "message",
                "channel": "global_updates",
                "data": '{"data": {"market": "open"}}',
            },
        ]
    )
    broadcaster = RedisWebSocketBroadcaster()
    broadcaster.is_connected = True
    broadcaster.subscriber = SimpleNamespace(pubsub=lambda: pubsub)
    received = []

    async def callback(channel, payload):
        received.append((channel, payload))

    await broadcaster.subscribe_to_channels(
        ["global_updates", "stock_updates:*"], callback
    )

    assert pubsub.subscribed == ["global_updates"]
    assert pubsub.psubscribed == ["stock_updates:*"]
    assert received == [
        ("stock_updates:42", {"data": {"price": 101}}),
        ("global_updates", {"data": {"market": "open"}}),
    ]
    assert pubsub.closed is True


class FakeWebSocket:
    def __init__(self):
        self.messages = []

    async def accept(self):
        return None

    async def send_json(self, message):
        self.messages.append(message)


@pytest.mark.asyncio
async def test_redis_backed_manager_routes_pattern_stock_update_locally():
    class FakeBroadcaster:
        is_connected = True

        async def subscribe_to_channels(self, channels, callback):
            self.channels = channels
            await callback(
                "stock_updates:42",
                {"data": {"type": "price_update", "price": 101}},
            )

    broadcaster = FakeBroadcaster()
    manager = RedisBackedWebSocketManager(broadcaster)
    websocket = FakeWebSocket()
    await manager.connect(websocket)
    await manager.subscribe_to_stock(websocket, 42)

    await manager.initialize()
    await manager.pubsub_task

    assert broadcaster.channels == ["global_updates", "stock_updates:*"]
    assert websocket.messages == [{"type": "price_update", "price": 101}]


class FakeMarketProvider:
    def add_trade_handler(self, handler):
        self.handler = handler

    async def stop(self):
        return None

    async def unsubscribe(self, market, symbol):
        return None


class FakeMarketCache:
    async def set_json(self, key, value, ttl_seconds=300):
        return None


@pytest.mark.asyncio
async def test_finalized_market_bar_is_persisted_before_any_boundary_broadcast(
    monkeypatch,
):
    service = MarketStreamService(FakeMarketProvider(), FakeMarketCache())
    events = []

    async def persist(bar):
        events.append(("persist", bar.bucket_start))
        return True

    async def broadcast(key, message):
        events.append(("broadcast", message["type"], message.get("data", {})))

    async def publish_signals(bar):
        return None

    monkeypatch.setattr(service, "_persist_finalized_bar", persist)
    monkeypatch.setattr(service, "_broadcast", broadcast)
    monkeypatch.setattr(service, "_publish_intraday_signals", publish_signals)

    await service._handle_trade(
        MarketTradeEvent(
            market="US",
            symbol="AAPL",
            price=100,
            volume=10,
            timestamp=datetime(2026, 1, 2, 14, 30, tzinfo=timezone.utc),
            source="test",
        )
    )
    events.clear()

    await service._handle_trade(
        MarketTradeEvent(
            market="US",
            symbol="AAPL",
            price=101,
            volume=5,
            timestamp=datetime(2026, 1, 2, 14, 35, tzinfo=timezone.utc),
            source="test",
        )
    )

    assert events[0][0] == "persist"
    assert events[1][0:2] == ("broadcast", "quote_update")
    assert events[2][0:2] == ("broadcast", "bar_update")
    assert events[2][2]["is_final"] is False
    assert events[3][2]["is_final"] is True


@pytest.mark.asyncio
async def test_market_broadcast_isolates_and_times_out_slow_clients():
    service = MarketStreamService(FakeMarketProvider(), FakeMarketCache())
    service._send_timeout_seconds = 0.1
    key = ("US", "AAPL")
    all_started = asyncio.Event()
    started = 0

    class SlowWebSocket:
        async def send_json(self, message):
            nonlocal started
            started += 1
            if started == 3:
                all_started.set()
            await asyncio.Event().wait()

    websockets = [SlowWebSocket() for _ in range(3)]
    for websocket in websockets:
        service.connections[websocket] = {
            "client_id": str(id(websocket)),
            "subscriptions": {key},
        }
    service.subscribers[key] = set(websockets)

    broadcast_task = asyncio.create_task(
        service._broadcast(key, {"type": "quote_update"})
    )
    await asyncio.wait_for(all_started.wait(), timeout=0.05)
    await asyncio.wait_for(broadcast_task, timeout=0.2)

    assert started == 3
    assert service.connections == {}
    assert key not in service.subscribers
