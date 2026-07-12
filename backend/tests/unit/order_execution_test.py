"""
Order execution queue and API contract tests.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from sqlalchemy.dialects import postgresql

from api.routers.v1 import trading
from domain.brokers import (
    BrokerConnectionError,
    BrokerOrderRejected,
    BrokerOrderResult,
    BrokerOrderStatus,
)
from domain.execution import OrderExecutionCommand, OrderQueueFailureDisposition
from domain.models.order_intent import BrokerOrder, OrderEvent, OrderExecution
from domain.models.transaction import Transaction
from domain.models.user_portfolio import UserPortfolio
from domain.services.order_intent_service import (
    OrderExecutionClaimBusy,
    OrderExecutionNotExecutable,
    OrderExecutionReconciliationRequired,
    OrderExecutionRetryable,
    OrderIntentService,
)
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
        "execution_dispatched_at": None,
        "execution_dispatch_claim_token": None,
        "execution_dispatch_claimed_at": None,
        "execution_attempt_count": 0,
        "execution_claim_token": None,
        "execution_claimed_at": None,
        "execution_lease_expires_at": None,
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

    def scalars(self):
        return self


class FakeQuery:
    def __init__(self, value=None):
        self.value = value

    def filter(self, *args, **kwargs):
        return self

    def with_for_update(self):
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
        self.rollbacks = 0
        self.statements = []

    async def execute(self, query):
        self.statements.append(query)
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

    async def rollback(self):
        self.rollbacks += 1

    async def refresh(self, obj):
        return None

    async def run_sync(self, fn):
        return fn(FakeSyncSession(self.added))


class FakeRedis:
    def __init__(self):
        self.groups = set()
        self.streams = {}
        self.stream_sequences = {}
        self.acked = []
        self.claim_response = ("0-0", [], [])
        self.claimed = []
        self.read_calls = []
        self.fail_next_xadd = False
        self.xadd_calls = []
        self.deleted = []
        self.eval_calls = []

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

    def xadd(self, name, fields, maxlen=None, approximate=False):
        if self.fail_next_xadd:
            self.fail_next_xadd = False
            raise RuntimeError("xadd unavailable")
        self.xadd_calls.append((name, maxlen, approximate))
        stream = self.streams.setdefault(name, [])
        self.stream_sequences[name] = self.stream_sequences.get(name, 0) + 1
        message_id = f"{self.stream_sequences[name]}-0"
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

    def xdel(self, name, message_id):
        self.deleted.append((name, message_id))
        stream = self.streams.setdefault(name, [])
        self.streams[name] = [item for item in stream if item[0] != message_id]
        return 1

    def eval(self, script, numkeys, *args):
        self.eval_calls.append((script, numkeys, args))
        stream_name = args[0]
        consumer_group = args[1]
        message_id = args[2]
        if "order_execution_replace_and_ack" in script:
            field_args = args[3:]
            fields = dict(zip(field_args[::2], field_args[1::2]))
            self.xadd(stream_name, fields)
        self.xack(stream_name, consumer_group, message_id)
        self.xdel(stream_name, message_id)
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
    assert redis_client.deleted == [("orders", "1-0")]
    assert redis_client.xadd_calls == [("orders", None, False)]


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
    disposition = await queue.fail(dequeued, RuntimeError("broker offline"))
    retry = await queue.dequeue(timeout=0)

    assert disposition is OrderQueueFailureDisposition.REQUEUED
    assert redis_client.acked == [("orders", "workers", "1-0")]
    assert redis_client.deleted == [("orders", "1-0")]
    assert "order_execution_replace_and_ack" in redis_client.eval_calls[0][0]
    assert retry.attempt == 2
    assert retry.metadata["last_error"] == "broker offline"


@pytest.mark.asyncio
async def test_redis_stream_execution_queue_does_not_ack_when_retry_write_fails():
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
        idempotency_key="idem-retry-window",
    )

    await queue.enqueue(command)
    dequeued = await queue.dequeue(timeout=0)
    redis_client.fail_next_xadd = True

    with pytest.raises(RuntimeError, match="xadd unavailable"):
        await queue.fail(dequeued, RuntimeError("broker offline"))

    assert redis_client.acked == []
    assert redis_client.deleted == []


@pytest.mark.asyncio
async def test_redis_stream_execution_queue_quarantines_without_executable_redelivery():
    redis_client = FakeRedis()
    queue = RedisStreamOrderExecutionQueue(
        redis_client=redis_client,
        stream_name="orders",
        consumer_group="workers",
        consumer_name="worker-1",
    )
    command = OrderExecutionCommand(
        order_intent_id=8,
        user_id=uuid4(),
        idempotency_key="idem-quarantine",
    )

    await queue.enqueue(command)
    dequeued = await queue.dequeue(timeout=0)
    await queue.quarantine(
        dequeued,
        OrderExecutionReconciliationRequired(
            "local ledger unavailable",
            broker_order_ref="broker-q-8",
        ),
    )
    quarantined = await queue.dequeue(timeout=0)

    assert quarantined.order_intent_id == command.order_intent_id
    assert quarantined.attempt == command.attempt
    assert quarantined.metadata["reconciliation_required"] is True
    assert quarantined.metadata["reconciliation_error"] == "local ledger unavailable"
    assert quarantined.metadata["broker_order_ref"] == "broker-q-8"
    assert redis_client.acked == [("orders", "workers", "1-0")]
    assert redis_client.deleted == [("orders", "1-0")]


@pytest.mark.asyncio
async def test_queue_order_intent_is_recoverable_after_queue_write_failure():
    user_id = uuid4()
    intent = make_intent(
        id=11,
        user_id=user_id,
        status="RISK_APPROVED",
        metadata_json={"source": "unit"},
    )
    db = FakeAsyncSession(execute_results=[intent], stock=None)

    class FailOnceQueue:
        def __init__(self):
            self.commands = []
            self.fail = True
            self.db = None
            self.commit_counts_at_enqueue = []

        async def enqueue(self, command):
            self.commit_counts_at_enqueue.append(self.db.commits)
            if self.fail:
                self.fail = False
                raise RuntimeError("redis unavailable")
            self.commands.append(command)

    queue = FailOnceQueue()
    service = OrderIntentService()

    accepted_intent, command, _ = await service.queue_order_intent(
        db=db,
        user_id=user_id,
        intent_id=intent.id,
        risk_engine=object(),
        execution_queue=queue,
        settings=object(),
    )

    assert accepted_intent is intent
    assert command.order_intent_id == intent.id
    assert queue.commands == []
    assert intent.status == "QUEUED_FOR_EXECUTION"
    assert intent.execution_dispatched_at is None

    failed_recovery_db = FakeAsyncSession(
        execute_results=[[intent], intent], stock=None
    )
    queue.db = failed_recovery_db
    failed_recovery = await service.recover_queued_order_intents(
        db=failed_recovery_db,
        execution_queue=queue,
    )

    assert failed_recovery == []
    assert intent.metadata_json["execution_enqueue_error"] == "redis unavailable"

    recovery_db = FakeAsyncSession(execute_results=[[intent], intent], stock=None)
    queue.db = recovery_db
    recovered = await service.recover_queued_order_intents(
        db=recovery_db,
        execution_queue=queue,
    )

    assert recovered == queue.commands
    assert recovered[0].order_intent_id == intent.id
    assert intent.execution_dispatched_at is not None
    assert "execution_enqueued_at" in intent.metadata_json
    assert "execution_enqueue_error" not in intent.metadata_json
    assert queue.commit_counts_at_enqueue == [1, 1]


@pytest.mark.asyncio
async def test_queue_order_intent_uses_locked_db_acceptance_without_sync_publish():
    user_id = uuid4()
    intent = make_intent(
        id=12,
        user_id=user_id,
        status="RISK_APPROVED",
        metadata_json={},
    )
    db = FakeAsyncSession(execute_results=[intent], stock=None)

    class ExplodingQueue:
        async def enqueue(self, command):
            raise AssertionError("queue publish must be decoupled from DB acceptance")

    intent_result, command, risk_result = await OrderIntentService().queue_order_intent(
        db=db,
        user_id=user_id,
        intent_id=intent.id,
        risk_engine=object(),
        execution_queue=ExplodingQueue(),
        settings=object(),
    )

    initial_sql = str(db.statements[0].compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE" in initial_sql
    assert intent_result is intent
    assert command.order_intent_id == intent.id
    assert risk_result is None


@pytest.mark.asyncio
async def test_dispatch_recovery_selects_unpublished_or_stale_outbox_rows():
    class CapturingSession:
        def __init__(self):
            self.statement = None
            self.rolled_back = False

        async def execute(self, statement):
            self.statement = statement
            return FakeScalarResult([])

        async def rollback(self):
            self.rolled_back = True

    class RecordingQueue:
        def __init__(self):
            self.commands = []

        async def enqueue(self, command):
            self.commands.append(command)

    db = CapturingSession()
    queue = RecordingQueue()

    recovered = await OrderIntentService().recover_queued_order_intents(
        db=db,
        execution_queue=queue,
        grace_seconds=0,
    )

    sql = str(
        db.statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert "order_intents.execution_dispatched_at IS NULL" in sql
    assert "order_intents.execution_dispatched_at <=" in sql
    assert "order_intents.execution_dispatch_claim_token IS NULL" in sql
    assert "FOR UPDATE SKIP LOCKED" in sql
    assert recovered == []
    assert queue.commands == []
    assert db.rolled_back is True


@pytest.mark.asyncio
async def test_stale_dispatched_order_is_republished_after_redis_loss_window():
    stale_dispatched_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    intent = make_intent(
        status="QUEUED_FOR_EXECUTION",
        execution_dispatched_at=stale_dispatched_at,
    )
    db = FakeAsyncSession(execute_results=[[intent], intent], stock=None)
    queue = InMemoryOrderExecutionQueue()

    recovered = await OrderIntentService().recover_queued_order_intents(
        db=db,
        execution_queue=queue,
        stale_dispatched_seconds=300,
    )

    assert len(recovered) == 1
    assert recovered[0].order_intent_id == intent.id
    assert intent.execution_dispatched_at > stale_dispatched_at
    assert await queue.dequeue(timeout=0) == recovered[0]


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
    disposition = await queue.fail(dequeued, RuntimeError("broker rejected"))

    assert disposition is OrderQueueFailureDisposition.DEAD_LETTERED
    dead_message = redis_client.streams["orders_dead"][0][1]
    assert dead_message["attempt"] == "2"
    assert dead_message["failed_attempts"] == "2"
    assert "dead_lettered_at" in dead_message
    assert redis_client.xadd_calls[-1] == ("orders_dead", 10000, True)
    assert redis_client.acked == []
    assert await queue.dequeue(timeout=0) is None


@pytest.mark.asyncio
async def test_execution_lookup_locks_intent_until_broker_result_is_committed():
    intent = make_intent(status="QUEUED_FOR_EXECUTION")

    class CapturingSession:
        def __init__(self):
            self.statement = None

        async def execute(self, statement):
            self.statement = statement
            return FakeScalarResult(intent)

    db = CapturingSession()
    loaded = await OrderIntentService().get_user_order_intent(
        db,
        intent.user_id,
        intent.id,
        for_update=True,
    )

    sql = str(db.statement.compile(dialect=postgresql.dialect()))
    assert loaded is intent
    assert "FOR UPDATE" in sql
    assert db.statement.get_execution_options()["populate_existing"] is True


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
async def test_order_execution_worker_scans_and_processes_stale_queued_intent():
    command = OrderExecutionCommand(
        order_intent_id=5,
        user_id=uuid4(),
        idempotency_key="idem-recovered",
    )
    intent = SimpleNamespace(id=5)
    broker_order = SimpleNamespace(id=9)
    queue = InMemoryOrderExecutionQueue()

    class RecoveringService:
        def __init__(self):
            self.recovery_calls = 0

        async def recover_queued_order_intents(self, db, execution_queue):
            self.recovery_calls += 1
            await execution_queue.enqueue(command)
            return [command]

        async def execute_order_intent(self, **kwargs):
            return intent, broker_order

    service = RecoveringService()
    worker = OrderExecutionWorker(order_intent_service=service)

    result = await worker.process_next(
        db=object(),
        execution_queue=queue,
        broker=object(),
        settings=object(),
        timeout=0,
    )

    assert result == (intent, broker_order)
    assert service.recovery_calls == 1


@pytest.mark.asyncio
async def test_order_execution_worker_scans_outbox_even_with_stream_backlog():
    existing = OrderExecutionCommand(
        order_intent_id=5,
        user_id=uuid4(),
        idempotency_key="idem-existing",
    )
    recovered = OrderExecutionCommand(
        order_intent_id=6,
        user_id=uuid4(),
        idempotency_key="idem-outbox",
    )
    queue = InMemoryOrderExecutionQueue()
    await queue.enqueue(existing)

    class RecoveringService:
        def __init__(self):
            self.recovery_calls = 0

        async def recover_queued_order_intents(self, db, execution_queue):
            self.recovery_calls += 1
            await execution_queue.enqueue(recovered)
            return [recovered]

        async def execute_order_intent(self, **kwargs):
            return SimpleNamespace(id=5), SimpleNamespace(id=9)

    service = RecoveringService()
    worker = OrderExecutionWorker(order_intent_service=service)

    await worker.process_next(
        db=object(),
        execution_queue=queue,
        broker=object(),
        settings=object(),
        timeout=0,
    )

    assert service.recovery_calls == 1
    assert queue.size == 1
    assert await queue.dequeue(timeout=0) == recovered


@pytest.mark.asyncio
async def test_order_execution_worker_recovers_submitting_intent_across_attempts():
    user_id = uuid4()
    intent = make_intent(
        id=42,
        user_id=user_id,
        status="QUEUED_FOR_EXECUTION",
        client_order_id="client-retry-42",
    )
    stock = SimpleNamespace(id=1, symbol="AAPL", market="US")
    db = FakeAsyncSession(
        execute_results=[
            [],
            [],
            intent,
            None,
            [],
            intent,
            intent,
            None,
            [],
            intent,
        ],
        stock=stock,
    )
    settings = SimpleNamespace(
        broker=SimpleNamespace(
            provider="paper",
            mode="paper",
            default_account_ref="paper",
        )
    )

    class RecoveringBroker:
        supports_idempotent_submission = True

        def __init__(self):
            self.requests = []

        async def place_order(self, request):
            self.requests.append(request)
            if len(self.requests) == 1:
                raise BrokerConnectionError("response lost")
            return BrokerOrderResult(
                broker_order_ref="broker-order-42",
                status=BrokerOrderStatus.ACCEPTED,
                submitted_quantity=request.quantity,
                submitted_at=datetime(2026, 1, 3, tzinfo=timezone.utc),
                raw_payload={"client_order_id": request.client_order_id},
            )

    redis_client = FakeRedis()
    queue = RedisStreamOrderExecutionQueue(
        redis_client=redis_client,
        stream_name="orders",
        consumer_group="workers",
        consumer_name="worker-1",
    )
    await queue.enqueue(OrderExecutionCommand.from_intent(intent))
    broker = RecoveringBroker()
    worker = OrderExecutionWorker()

    with pytest.raises(BrokerConnectionError, match="response lost"):
        await worker.process_next(db, queue, broker, settings)

    assert db.rollbacks >= 1
    retry_fields = redis_client.streams["orders"][0][1]
    assert retry_fields["attempt"] == "2"

    updated_intent, broker_order = await worker.process_next(
        db, queue, broker, settings
    )

    assert updated_intent.status == "SUBMITTED"
    assert broker_order.broker_order_ref == "broker-order-42"
    assert [request.client_order_id for request in broker.requests] == [
        "client-retry-42",
        "client-retry-42",
    ]


@pytest.mark.asyncio
async def test_order_execution_worker_acks_terminal_broker_error_without_retry():
    command = OrderExecutionCommand(
        order_intent_id=5,
        user_id=uuid4(),
        idempotency_key="idem-terminal",
    )

    class StubQueue:
        def __init__(self):
            self.acked = []
            self.failed = []

        async def dequeue(self, timeout=0):
            return command

        async def ack(self, item):
            self.acked.append(item)

        async def fail(self, item, error):
            self.failed.append((item, error))

    class RejectingService:
        async def execute_order_intent(self, **kwargs):
            raise BrokerOrderRejected("order rejected")

    queue = StubQueue()
    worker = OrderExecutionWorker(order_intent_service=RejectingService())

    with pytest.raises(BrokerOrderRejected, match="order rejected"):
        await worker.process_next(object(), queue, object(), object())

    assert queue.acked == [command]
    assert queue.failed == []


@pytest.mark.asyncio
async def test_order_execution_worker_marks_ambiguous_order_for_review_at_dlq():
    command = OrderExecutionCommand(
        order_intent_id=5,
        user_id=uuid4(),
        idempotency_key="idem-exhausted",
        attempt=3,
    )

    class StubQueue:
        def __init__(self):
            self.failed = []
            self.acked = []

        async def dequeue(self, timeout=0):
            return command

        async def fail(self, item, error):
            self.failed.append((item, error))
            return OrderQueueFailureDisposition.DEAD_LETTERED

        async def ack(self, item):
            self.acked.append(item)

    class FailingService:
        def __init__(self):
            self.reviewed = []

        async def execute_order_intent(self, **kwargs):
            raise BrokerConnectionError("broker response lost")

        async def mark_execution_reconciliation_required(
            self, db, user_id, intent_id, error
        ):
            self.reviewed.append((user_id, intent_id, str(error)))

    queue = StubQueue()
    service = FailingService()
    worker = OrderExecutionWorker(order_intent_service=service)

    with pytest.raises(BrokerConnectionError, match="response lost"):
        await worker.process_next(object(), queue, object(), object())

    assert service.reviewed == [
        (command.user_id, command.order_intent_id, "broker response lost")
    ]
    assert queue.failed[0][0] == command
    assert queue.acked == [command]


@pytest.mark.asyncio
async def test_order_execution_worker_quarantines_post_broker_ref_if_db_fence_fails():
    command = OrderExecutionCommand(
        order_intent_id=5,
        user_id=uuid4(),
        idempotency_key="idem-fence-failure",
        attempt=3,
    )

    class StubQueue:
        def __init__(self):
            self.acked = []
            self.quarantined = []

        async def dequeue(self, timeout=0):
            return command

        async def fail(self, item, error):
            return OrderQueueFailureDisposition.DEAD_LETTERED

        async def ack(self, item):
            self.acked.append(item)

        async def quarantine(self, item, error):
            self.quarantined.append((item, error))

    class FailingFenceService:
        async def execute_order_intent(self, **kwargs):
            raise OrderExecutionReconciliationRequired(
                "local ledger failed",
                broker_order_ref="broker-fence-5",
            )

        async def mark_execution_reconciliation_required(self, **kwargs):
            raise RuntimeError("database unavailable")

    queue = StubQueue()
    worker = OrderExecutionWorker(order_intent_service=FailingFenceService())

    with pytest.raises(RuntimeError, match="database unavailable"):
        await worker.process_next(object(), queue, object(), object())

    assert queue.acked == []
    assert queue.quarantined[0][0] == command
    assert queue.quarantined[0][1].broker_order_ref == "broker-fence-5"


@pytest.mark.asyncio
async def test_order_execution_worker_does_not_retry_post_broker_ledger_failure():
    command = OrderExecutionCommand(
        order_intent_id=5,
        user_id=uuid4(),
        idempotency_key="idem-ledger-failure",
    )

    class StubQueue:
        def __init__(self):
            self.acked = []
            self.failed = []

        async def dequeue(self, timeout=0):
            return command

        async def ack(self, item):
            self.acked.append(item)

        async def fail(self, item, error):
            self.failed.append((item, error))

    class ReconciliationService:
        def __init__(self):
            self.reviewed = []

        async def execute_order_intent(self, **kwargs):
            raise OrderExecutionReconciliationRequired(
                "local ledger failed", broker_order_ref="broker-5"
            )

        async def mark_execution_reconciliation_required(self, **kwargs):
            self.reviewed.append(kwargs["intent_id"])

    queue = StubQueue()
    service = ReconciliationService()
    worker = OrderExecutionWorker(order_intent_service=service)

    with pytest.raises(OrderExecutionReconciliationRequired):
        await worker.process_next(object(), queue, object(), object())

    assert service.reviewed == [command.order_intent_id]
    assert queue.acked == [command]
    assert queue.failed == []


@pytest.mark.asyncio
async def test_reconciliation_marker_redelivery_never_calls_broker_execution():
    command = OrderExecutionCommand(
        order_intent_id=5,
        user_id=uuid4(),
        idempotency_key="idem-reconciliation-redelivery",
        metadata={
            "reconciliation_required": True,
            "reconciliation_error": "broker may have accepted order",
            "broker_order_ref": "broker-redelivery-5",
        },
    )

    class StubQueue:
        def __init__(self):
            self.acked = []

        async def dequeue(self, timeout=0):
            return command

        async def ack(self, item):
            self.acked.append(item)

    class ReconciliationService:
        def __init__(self):
            self.execution_calls = 0
            self.reviewed = []

        async def execute_order_intent(self, **kwargs):
            self.execution_calls += 1
            raise AssertionError("reconciliation marker reached broker path")

        async def mark_execution_reconciliation_required(self, **kwargs):
            self.reviewed.append(
                (kwargs["intent_id"], kwargs["error"].broker_order_ref)
            )

    queue = StubQueue()
    service = ReconciliationService()
    worker = OrderExecutionWorker(order_intent_service=service)

    result = await worker.process_next(object(), queue, object(), object())

    assert result is None
    assert service.execution_calls == 0
    assert service.reviewed == [(command.order_intent_id, "broker-redelivery-5")]
    assert queue.acked == [command]


@pytest.mark.asyncio
async def test_order_execution_worker_acks_duplicate_after_intent_is_finalized():
    command = OrderExecutionCommand(
        order_intent_id=5,
        user_id=uuid4(),
        idempotency_key="idem-finalized-duplicate",
    )

    class StubQueue:
        def __init__(self):
            self.acked = []
            self.failed = []

        async def dequeue(self, timeout=0):
            return command

        async def ack(self, item):
            self.acked.append(item)

        async def fail(self, item, error):
            self.failed.append((item, error))

    class FinalizedService:
        async def execute_order_intent(self, **kwargs):
            raise OrderExecutionNotExecutable("FILLED")

    queue = StubQueue()
    worker = OrderExecutionWorker(order_intent_service=FinalizedService())
    db = FakeAsyncSession(execute_results=[], stock=None)

    result = await worker.process_next(db, queue, object(), object())

    assert result is None
    assert db.rollbacks == 1
    assert queue.acked == [command]
    assert queue.failed == []


@pytest.mark.asyncio
async def test_active_execution_lease_defers_redelivery_without_broker_call():
    intent = make_intent(
        status="SUBMITTING",
        execution_claim_token="active-claim",
        execution_claimed_at=datetime.now(timezone.utc),
        execution_lease_expires_at=datetime.now(timezone.utc) + timedelta(minutes=2),
        execution_attempt_count=1,
    )
    db = FakeAsyncSession(execute_results=[intent], stock=None)

    class NeverBroker:
        async def place_order(self, request):
            raise AssertionError("active lease must fence broker redelivery")

    with pytest.raises(OrderExecutionClaimBusy):
        await OrderIntentService().execute_order_intent(
            db=db,
            user_id=intent.user_id,
            intent_id=intent.id,
            broker=NeverBroker(),
            settings=object(),
        )

    assert intent.status == "SUBMITTING"
    assert db.commits == 0


@pytest.mark.asyncio
async def test_expired_execution_lease_requires_review_without_broker_call():
    intent = make_intent(
        status="SUBMITTING",
        execution_claim_token="crashed-claim",
        execution_claimed_at=datetime.now(timezone.utc) - timedelta(minutes=3),
        execution_lease_expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        execution_attempt_count=1,
    )
    db = FakeAsyncSession(execute_results=[intent], stock=None)

    class NeverBroker:
        def __init__(self):
            self.calls = 0

        async def place_order(self, request):
            self.calls += 1
            raise AssertionError("expired ambiguous lease must not resubmit")

    broker = NeverBroker()
    with pytest.raises(OrderExecutionNotExecutable):
        await OrderIntentService().execute_order_intent(
            db=db,
            user_id=intent.user_id,
            intent_id=intent.id,
            broker=broker,
            settings=object(),
        )

    assert broker.calls == 0
    assert intent.status == "REQUIRES_REVIEW"
    assert intent.execution_claim_token is None
    assert db.commits == 1


@pytest.mark.asyncio
async def test_expired_lease_sweeper_fences_order_without_redis_delivery():
    intent = make_intent(
        status="SUBMITTING",
        execution_claim_token="lost-stream-claim",
        execution_claimed_at=datetime.now(timezone.utc) - timedelta(minutes=3),
        execution_lease_expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        execution_attempt_count=1,
    )
    db = FakeAsyncSession(execute_results=[[intent]], stock=None)

    reconciled = await OrderIntentService().reconcile_expired_execution_leases(db=db)

    sql = str(db.statements[0].compile(dialect=postgresql.dialect()))
    assert "execution_lease_expires_at" in sql
    assert "FOR UPDATE SKIP LOCKED" in sql
    assert reconciled == [intent.id]
    assert intent.status == "REQUIRES_REVIEW"
    assert intent.execution_claim_token is None


@pytest.mark.asyncio
async def test_non_idempotent_broker_ambiguity_is_not_automatically_retried():
    user_id = uuid4()
    intent = make_intent(
        id=41,
        user_id=user_id,
        status="QUEUED_FOR_EXECUTION",
        client_order_id="stable-client-41",
    )
    stock = SimpleNamespace(id=1, symbol="AAPL", market="US")
    db = FakeAsyncSession(
        execute_results=[intent, None, [], intent],
        stock=stock,
    )
    settings = SimpleNamespace(
        broker=SimpleNamespace(
            default_account_ref="paper",
            provider="paper",
            mode="paper",
        ),
        order_execution_queue=SimpleNamespace(
            max_attempts=3,
            pending_idle_ms=60000,
        ),
    )

    class AmbiguousBroker:
        def __init__(self):
            self.requests = []

        async def place_order(self, request):
            self.requests.append(request)
            raise BrokerConnectionError("response lost")

    broker = AmbiguousBroker()
    with pytest.raises(OrderExecutionReconciliationRequired):
        await OrderIntentService().execute_order_intent(
            db=db,
            user_id=user_id,
            intent_id=intent.id,
            broker=broker,
            settings=settings,
        )

    assert len(broker.requests) == 1
    assert broker.requests[0].client_order_id == "stable-client-41"
    assert intent.execution_attempt_count == 1
    assert intent.status == "REQUIRES_REVIEW"
    assert intent.execution_claim_token is None


@pytest.mark.asyncio
async def test_order_execution_service_requires_review_after_broker_reply_db_failure():
    user_id = uuid4()
    intent = make_intent(
        id=42,
        user_id=user_id,
        status="QUEUED_FOR_EXECUTION",
        client_order_id="client-ledger-42",
    )
    stock = SimpleNamespace(id=1, symbol="AAPL", market="US")

    class CommitFailSession(FakeAsyncSession):
        async def commit(self):
            self.commits += 1
            if self.commits == 2:
                raise RuntimeError("database unavailable")

    class AcceptedBroker:
        def __init__(self):
            self.requests = []

        async def place_order(self, request):
            self.requests.append(request)
            return BrokerOrderResult(
                broker_order_ref="broker-ledger-42",
                status=BrokerOrderStatus.ACCEPTED,
                submitted_quantity=request.quantity,
                submitted_at=datetime(2026, 1, 3, tzinfo=timezone.utc),
                raw_payload={"client_order_id": request.client_order_id},
            )

    db = CommitFailSession(
        execute_results=[intent, None, [], intent],
        stock=stock,
    )
    broker = AcceptedBroker()
    settings = SimpleNamespace(
        broker=SimpleNamespace(
            default_account_ref="paper",
            provider="paper",
            mode="paper",
        ),
        order_execution_queue=SimpleNamespace(max_attempts=3),
    )

    with pytest.raises(
        OrderExecutionReconciliationRequired,
        match="local order ledger",
    ) as exc_info:
        await OrderIntentService().execute_order_intent(
            db=db,
            user_id=user_id,
            intent_id=intent.id,
            broker=broker,
            settings=settings,
        )

    assert exc_info.value.broker_order_ref == "broker-ledger-42"
    assert len(broker.requests) == 1
    assert db.rollbacks == 1


@pytest.mark.asyncio
async def test_reconciliation_state_persists_external_broker_order_reference():
    intent = make_intent(
        status="SUBMITTING",
        metadata_json={},
        execution_claim_token="claim-with-broker-ref",
    )
    db = FakeAsyncSession(execute_results=[intent], stock=None)
    error = OrderExecutionReconciliationRequired(
        "local ledger failed",
        broker_order_ref="broker-persisted-42",
    )

    updated = await OrderIntentService().mark_execution_reconciliation_required(
        db=db,
        user_id=intent.user_id,
        intent_id=intent.id,
        error=error,
    )

    assert updated.status == "REQUIRES_REVIEW"
    assert (
        updated.metadata_json["execution_reconciliation_broker_order_ref"]
        == "broker-persisted-42"
    )
    assert updated.execution_claim_token is None


@pytest.mark.asyncio
async def test_order_execution_attempt_budget_is_durable_per_intent():
    user_id = uuid4()
    intent = make_intent(
        id=43,
        user_id=user_id,
        status="QUEUED_FOR_EXECUTION",
        client_order_id="client-budget-43",
    )
    stock = SimpleNamespace(id=1, symbol="AAPL", market="US")
    db = FakeAsyncSession(
        execute_results=[
            intent,
            None,
            [],
            intent,
            intent,
            None,
            [],
            intent,
            intent,
            None,
            [],
            intent,
            intent,
        ],
        stock=stock,
    )
    settings = SimpleNamespace(
        broker=SimpleNamespace(
            default_account_ref="paper",
            provider="paper",
            mode="paper",
        ),
        order_execution_queue=SimpleNamespace(max_attempts=3),
    )

    class OfflineBroker:
        supports_idempotent_submission = True

        def __init__(self):
            self.requests = []

        async def place_order(self, request):
            self.requests.append(request)
            raise BrokerConnectionError("broker offline")

    broker = OfflineBroker()
    service = OrderIntentService()
    observed_attempts = []

    for _ in range(3):
        with pytest.raises(OrderExecutionRetryable) as exc_info:
            await service.execute_order_intent(
                db=db,
                user_id=user_id,
                intent_id=intent.id,
                broker=broker,
                settings=settings,
            )
        observed_attempts.append(exc_info.value.attempt_count)

    assert observed_attempts == [1, 2, 3]
    assert intent.execution_attempt_count == 3
    assert intent.status == "REQUIRES_REVIEW"

    with pytest.raises(OrderExecutionNotExecutable):
        await service.execute_order_intent(
            db=db,
            user_id=user_id,
            intent_id=intent.id,
            broker=broker,
            settings=settings,
        )

    assert len(broker.requests) == 3


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
            intent,
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
