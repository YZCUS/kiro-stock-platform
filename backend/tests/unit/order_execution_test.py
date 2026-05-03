"""
Order execution queue and API contract tests.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from api.routers.v1 import trading
from domain.execution import OrderExecutionCommand
from domain.models.order_intent import BrokerOrder, OrderEvent, OrderExecution
from domain.models.transaction import Transaction
from domain.models.user_portfolio import UserPortfolio
from domain.services.order_intent_service import OrderIntentService
from domain.services.order_execution_worker import OrderExecutionWorker
from infrastructure.brokers.paper_broker import PaperBrokerAdapter
from infrastructure.execution import (
    InMemoryOrderExecutionQueue,
    RedisStreamOrderExecutionQueue,
)


def make_user():
    return SimpleNamespace(id=uuid4())


def make_intent(**overrides):
    data = {
        "id": 10,
        "user_id": uuid4(),
        "stock_id": 1,
        "strategy_signal_id": None,
        "broker_account_id": None,
        "side": "BUY",
        "order_type": "MARKET",
        "time_in_force": "DAY",
        "quantity": Decimal("5"),
        "limit_price": None,
        "stop_price": None,
        "notional": None,
        "status": "DRAFT",
        "source": "manual",
        "idempotency_key": "idem-1",
        "client_order_id": "client-1",
        "reason": "test",
        "metadata_json": {"source": "unit"},
        "requested_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "risk_checked_at": None,
        "submitted_at": None,
        "expires_at": None,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
    }
    data.update(overrides)
    return SimpleNamespace(**data)


class FakeScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def all(self):
        return self.value if isinstance(self.value, list) else []


class FakeQuery:
    def __init__(self, value=None):
        self.value = value

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.value


class FakeSyncSession:
    def __init__(self, added):
        self.added = added

    def query(self, model):
        return FakeQuery(None)

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = len(self.added) + 1
        self.added.append(obj)

    def flush(self):
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = len(self.added) + 1

    def delete(self, obj):
        if obj in self.added:
            self.added.remove(obj)


class FakeAsyncSession:
    def __init__(self, execute_results, stock):
        self.execute_results = list(execute_results)
        self.stock = stock
        self.added = []
        self.commits = 0

    async def execute(self, query):
        return FakeScalarResult(self.execute_results.pop(0))

    async def get(self, model, obj_id):
        return self.stock

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = len(self.added) + 1
        self.added.append(obj)

    async def flush(self):
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = len(self.added) + 1

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj):
        return None

    async def run_sync(self, fn):
        return fn(FakeSyncSession(self.added))


class FakeRedis:
    def __init__(self):
        self.groups = set()
        self.streams = {}
        self.acked = []
        self.claim_response = ("0-0", [], [])
        self.claimed = []
        self.read_calls = []

    def xgroup_create(self, name, groupname, id="0", mkstream=False):
        key = (name, groupname)
        if key in self.groups:
            import redis

            raise redis.exceptions.ResponseError(
                "BUSYGROUP Consumer Group name already exists"
            )
        self.groups.add(key)
        if mkstream:
            self.streams.setdefault(name, [])
        return True

    def xadd(self, name, fields):
        stream = self.streams.setdefault(name, [])
        message_id = f"{len(stream) + 1}-0"
        stream.append((message_id, dict(fields)))
        return message_id

    def xreadgroup(self, groupname, consumername, streams, count=None, block=None):
        self.read_calls.append((groupname, consumername, streams, count, block))
        stream_name = next(iter(streams.keys()))
        stream = self.streams.setdefault(stream_name, [])
        if not stream:
            return []
        message = stream.pop(0)
        return [(stream_name, [message])]

    def xautoclaim(
        self,
        name,
        groupname,
        consumername,
        min_idle_time,
        start_id="0-0",
        count=None,
    ):
        self.claimed.append(
            (name, groupname, consumername, min_idle_time, start_id, count)
        )
        return self.claim_response

    def xack(self, name, groupname, message_id):
        self.acked.append((name, groupname, message_id))
        return 1


@pytest.mark.asyncio
async def test_in_memory_execution_queue_dequeues_commands_fifo():
    queue = InMemoryOrderExecutionQueue()
    first = OrderExecutionCommand(
        order_intent_id=1,
        user_id=uuid4(),
        idempotency_key="idem-1",
    )
    second = OrderExecutionCommand(
        order_intent_id=2,
        user_id=uuid4(),
        idempotency_key="idem-2",
    )

    await queue.enqueue(first)
    await queue.enqueue(second)

    assert queue.size == 2
    assert await queue.dequeue(timeout=0) == first
    assert await queue.dequeue(timeout=0) == second
    assert await queue.dequeue(timeout=0) is None


@pytest.mark.asyncio
async def test_redis_stream_execution_queue_round_trips_command_and_ack():
    redis_client = FakeRedis()
    queue = RedisStreamOrderExecutionQueue(
        redis_client=redis_client,
        stream_name="orders",
        consumer_group="workers",
        consumer_name="worker-1",
    )
    command = OrderExecutionCommand(
        order_intent_id=7,
        user_id=uuid4(),
        idempotency_key="idem-redis",
        metadata={"source": "unit"},
    )

    await queue.enqueue(command)
    dequeued = await queue.dequeue(timeout=0)

    assert dequeued.order_intent_id == command.order_intent_id
    assert dequeued.user_id == command.user_id
    assert dequeued.idempotency_key == command.idempotency_key
    assert dequeued.metadata["source"] == "unit"
    assert dequeued.metadata["_redis_message_id"] == "1-0"

    await queue.ack(dequeued)

    assert redis_client.acked == [("orders", "workers", "1-0")]


@pytest.mark.asyncio
async def test_redis_stream_execution_queue_requeues_failed_command():
    redis_client = FakeRedis()
    queue = RedisStreamOrderExecutionQueue(
        redis_client=redis_client,
        stream_name="orders",
        consumer_group="workers",
        consumer_name="worker-1",
        max_attempts=3,
    )
    command = OrderExecutionCommand(
        order_intent_id=8,
        user_id=uuid4(),
        idempotency_key="idem-retry",
    )

    await queue.enqueue(command)
    dequeued = await queue.dequeue(timeout=0)
    await queue.fail(dequeued, RuntimeError("broker offline"))
    retry = await queue.dequeue(timeout=0)

    assert redis_client.acked == [("orders", "workers", "1-0")]
    assert retry.attempt == 2
    assert retry.metadata["last_error"] == "broker offline"


@pytest.mark.asyncio
async def test_redis_stream_execution_queue_claims_stale_pending_message():
    redis_client = FakeRedis()
    command = OrderExecutionCommand(
        order_intent_id=9,
        user_id=uuid4(),
        idempotency_key="idem-stale",
    )
    redis_client.claim_response = ("0-0", [("9-0", command.to_stream_fields())], [])
    queue = RedisStreamOrderExecutionQueue(
        redis_client=redis_client,
        stream_name="orders",
        consumer_group="workers",
        consumer_name="worker-2",
        pending_idle_ms=1000,
    )

    dequeued = await queue.dequeue(timeout=0)

    assert dequeued.order_intent_id == command.order_intent_id
    assert dequeued.metadata["_redis_message_id"] == "9-0"
    assert redis_client.claimed == [("orders", "workers", "worker-2", 1000, "0-0", 1)]
    assert redis_client.read_calls == []


@pytest.mark.asyncio
async def test_redis_stream_execution_queue_dead_letters_after_max_attempts():
    redis_client = FakeRedis()
    queue = RedisStreamOrderExecutionQueue(
        redis_client=redis_client,
        stream_name="orders",
        consumer_group="workers",
        consumer_name="worker-1",
        dead_letter_stream="orders_dead",
        max_attempts=2,
    )
    command = OrderExecutionCommand(
        order_intent_id=10,
        user_id=uuid4(),
        idempotency_key="idem-dead",
        attempt=2,
    )

    await queue.enqueue(command)
    dequeued = await queue.dequeue(timeout=0)
    await queue.fail(dequeued, RuntimeError("broker rejected"))

    dead_message = redis_client.streams["orders_dead"][0][1]
    assert dead_message["attempt"] == "2"
    assert dead_message["failed_attempts"] == "2"
    assert "dead_lettered_at" in dead_message
    assert await queue.dequeue(timeout=0) is None


@pytest.mark.asyncio
async def test_order_execution_worker_delegates_command_to_service():
    command = OrderExecutionCommand(
        order_intent_id=5,
        user_id=uuid4(),
        idempotency_key="idem-worker",
    )
    intent = SimpleNamespace(id=5)
    broker_order = SimpleNamespace(id=9)

    class StubOrderIntentService:
        async def execute_order_intent(self, db, user_id, intent_id, broker, settings):
            assert user_id == command.user_id
            assert intent_id == command.order_intent_id
            return intent, broker_order

    worker = OrderExecutionWorker(order_intent_service=StubOrderIntentService())

    result = await worker.process_command(
        db=object(),
        command=command,
        broker=object(),
        settings=object(),
    )

    assert result == (intent, broker_order)


@pytest.mark.asyncio
async def test_order_execution_worker_acks_successful_queue_command():
    command = OrderExecutionCommand(
        order_intent_id=5,
        user_id=uuid4(),
        idempotency_key="idem-worker",
    )
    intent = SimpleNamespace(id=5)
    broker_order = SimpleNamespace(id=9)

    class StubQueue:
        def __init__(self):
            self.acked = []
            self.failed = []

        async def dequeue(self, timeout=0):
            return command

        async def ack(self, command):
            self.acked.append(command)

        async def fail(self, command, error):
            self.failed.append((command, error))

    class StubOrderIntentService:
        async def execute_order_intent(self, db, user_id, intent_id, broker, settings):
            return intent, broker_order

    queue = StubQueue()
    worker = OrderExecutionWorker(order_intent_service=StubOrderIntentService())

    result = await worker.process_next(
        db=object(),
        execution_queue=queue,
        broker=object(),
        settings=object(),
    )

    assert result == (intent, broker_order)
    assert queue.acked == [command]
    assert queue.failed == []


@pytest.mark.asyncio
async def test_paper_order_execution_records_fill_transaction_and_position():
    user_id = uuid4()
    intent = make_intent(
        id=42,
        user_id=user_id,
        status="QUEUED_FOR_EXECUTION",
        quantity=Decimal("3"),
        client_order_id="client-paper-42",
    )
    stock = SimpleNamespace(id=1, symbol="AAPL", market="US")
    latest_daily_bar = SimpleNamespace(
        id=100,
        stock_id=1,
        timestamp=datetime(2026, 1, 2, tzinfo=timezone.utc),
        market="US",
        open_price=Decimal("100.00"),
        high_price=Decimal("102.00"),
        low_price=Decimal("99.00"),
        close_price=Decimal("101.25"),
        volume=1000,
    )
    db = FakeAsyncSession(
        execute_results=[
            intent,
            None,
            [(latest_daily_bar, date(2026, 1, 2))],
        ],
        stock=stock,
    )
    settings = SimpleNamespace(
        broker=SimpleNamespace(
            provider="paper",
            mode="paper",
            default_account_ref="paper",
            trading_enabled=True,
            read_only=False,
        ),
        ibkr=SimpleNamespace(read_only=True),
    )

    service = OrderIntentService()

    updated_intent, broker_order = await service.execute_order_intent(
        db=db,
        user_id=user_id,
        intent_id=42,
        broker=PaperBrokerAdapter("paper"),
        settings=settings,
    )

    assert updated_intent.status == "FILLED"
    assert broker_order.status == "FILLED"
    assert broker_order.filled_quantity == Decimal("3")
    assert broker_order.avg_fill_price == Decimal("101.25")
    assert any(isinstance(obj, BrokerOrder) for obj in db.added)
    assert any(isinstance(obj, OrderExecution) for obj in db.added)
    assert any(
        isinstance(obj, OrderEvent) and obj.event_type == "ORDER_FILLED"
        for obj in db.added
    )
    assert any(isinstance(obj, Transaction) for obj in db.added)
    portfolio = next(obj for obj in db.added if isinstance(obj, UserPortfolio))
    assert portfolio.quantity == Decimal("3")
    assert portfolio.avg_cost == Decimal("101.25")


@pytest.mark.asyncio
async def test_submit_order_intent_enqueues_execution_command_response():
    current_user = make_user()
    queued_intent = make_intent(
        user_id=current_user.id,
        status="QUEUED_FOR_EXECUTION",
    )
    command = OrderExecutionCommand.from_intent(queued_intent)
    service = SimpleNamespace(
        queue_order_intent=AsyncMock(return_value=(queued_intent, command, None))
    )
    execution_queue = object()

    response = await trading.submit_order_intent(
        10,
        background_tasks=None,
        db=object(),
        current_user=current_user,
        service=service,
        risk_engine=object(),
        execution_queue=execution_queue,
        settings=object(),
    )

    assert response.order_intent.status == "QUEUED_FOR_EXECUTION"
    assert response.command.order_intent_id == 10
    assert response.command.idempotency_key == "idem-1"
    assert response.risk_check is None
    assert service.queue_order_intent.call_args.args[4] is execution_queue


@pytest.mark.asyncio
async def test_submit_order_intent_maps_queue_failure_to_service_unavailable():
    service = SimpleNamespace(
        queue_order_intent=AsyncMock(side_effect=RuntimeError("queue offline"))
    )

    with pytest.raises(HTTPException) as exc_info:
        await trading.submit_order_intent(
            10,
            background_tasks=None,
            db=object(),
            current_user=make_user(),
            service=service,
            risk_engine=object(),
            execution_queue=object(),
            settings=object(),
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "queue offline"
