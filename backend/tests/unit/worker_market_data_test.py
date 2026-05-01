"""
Worker queue and multi-timeframe market data tests.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from domain.market_data import MarketDataBarDTO
from domain.services.bar_aggregation_service import BarAggregationService
from domain.services.market_calendar_service import MarketCalendarService
from domain.services.market_data_ingestion_service import MarketDataIngestionService
from domain.services.market_data_validation_service import MarketDataValidationService
from domain.strategies.golden_cross_strategy import GoldenCrossStrategy
from domain.workers import StreamTaskCommand
from infrastructure.workers import RedisStreamTaskQueue


class FakeRedis:
    def __init__(self):
        self.groups = set()
        self.streams = {}
        self.acked = []
        self.claim_response = ("0-0", [], [])

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
        stream_name = next(iter(streams.keys()))
        stream = self.streams.setdefault(stream_name, [])
        if not stream:
            return []
        return [(stream_name, [stream.pop(0)])]

    def xautoclaim(
        self,
        name,
        groupname,
        consumername,
        min_idle_time,
        start_id="0-0",
        count=None,
    ):
        return self.claim_response

    def xack(self, name, groupname, message_id):
        self.acked.append((name, groupname, message_id))
        return 1


@pytest.mark.asyncio
async def test_generic_redis_stream_task_queue_round_trips_and_acks():
    redis_client = FakeRedis()
    queue = RedisStreamTaskQueue(
        redis_client=redis_client,
        stream_name="market_data_tasks",
        consumer_group="market_data_workers",
        consumer_name="worker-1",
    )
    command = StreamTaskCommand(
        task_type="collect_bars",
        payload={"stock_id": 1, "timeframe": "5m"},
        idempotency_key="task-1",
    )

    await queue.enqueue(command)
    dequeued = await queue.dequeue(timeout=0)

    assert dequeued.task_type == "collect_bars"
    assert dequeued.payload["timeframe"] == "5m"
    assert dequeued.metadata["_redis_message_id"] == "1-0"

    await queue.ack(dequeued)

    assert redis_client.acked == [("market_data_tasks", "market_data_workers", "1-0")]


@pytest.mark.asyncio
async def test_generic_redis_stream_task_queue_dead_letters_after_retries():
    redis_client = FakeRedis()
    queue = RedisStreamTaskQueue(
        redis_client=redis_client,
        stream_name="strategy_tasks",
        consumer_group="strategy_workers",
        consumer_name="worker-1",
        max_attempts=1,
    )
    command = StreamTaskCommand(
        task_type="run_strategy",
        payload={"stock_id": 1, "strategy_type": "golden_cross"},
        idempotency_key="task-dead",
        attempt=1,
    )

    await queue.enqueue(command)
    dequeued = await queue.dequeue(timeout=0)
    await queue.fail(dequeued, RuntimeError("insufficient data"))

    dead_message = redis_client.streams["strategy_tasks_dead"][0][1]
    assert dead_message["attempt"] == "1"
    assert dead_message["failed_attempts"] == "1"
    assert "dead_lettered_at" in dead_message


def test_bar_aggregation_service_aggregates_5m_to_15m():
    service = BarAggregationService()
    start = datetime(2026, 1, 1, 9, 30, tzinfo=timezone.utc)
    bars = [
        MarketDataBarDTO(
            stock_id=1,
            timeframe="5m",
            timestamp=start + timedelta(minutes=5 * index),
            open_price=Decimal(str(100 + index)),
            high_price=Decimal(str(102 + index)),
            low_price=Decimal(str(99 + index)),
            close_price=Decimal(str(101 + index)),
            volume=1000 + index,
            source="ibkr",
        )
        for index in range(3)
    ]

    aggregated = service.aggregate(bars, target_timeframe="15m")

    assert len(aggregated) == 1
    assert aggregated[0].open_price == Decimal("100")
    assert aggregated[0].high_price == Decimal("104")
    assert aggregated[0].low_price == Decimal("99")
    assert aggregated[0].close_price == Decimal("103")
    assert aggregated[0].volume == 3003
    assert aggregated[0].source_type == "derived"
    assert aggregated[0].generated_from_timeframe == "5m"


def test_bar_aggregation_service_marks_incomplete_bucket_partial():
    service = BarAggregationService()
    start = datetime(2026, 1, 1, 9, 30, tzinfo=timezone.utc)
    bars = [
        MarketDataBarDTO(
            stock_id=1,
            timeframe="5m",
            timestamp=start + timedelta(minutes=5 * index),
            open_price=Decimal("100"),
            high_price=Decimal("101"),
            low_price=Decimal("99"),
            close_price=Decimal("100"),
            volume=100,
            source="ibkr",
        )
        for index in range(2)
    ]

    aggregated = service.aggregate(bars, target_timeframe="15m")

    assert aggregated[0].quality_status == "partial"


def test_bar_aggregation_uses_market_session_boundary_for_expected_count():
    service = BarAggregationService()
    tz = ZoneInfo("Asia/Taipei")
    start = datetime(2026, 1, 5, 13, 0, tzinfo=tz)
    bars = [
        MarketDataBarDTO(
            stock_id=1,
            timeframe="5m",
            timestamp=start + timedelta(minutes=5 * index),
            open_price=Decimal("100"),
            high_price=Decimal("101"),
            low_price=Decimal("99"),
            close_price=Decimal("100"),
            volume=100,
            source="ibkr",
        )
        for index in range(6)
    ]

    aggregated = service.aggregate(
        bars,
        target_timeframe="1h",
        market="TW",
    )

    assert len(aggregated) == 1
    assert aggregated[0].quality_status == "complete"


def test_bar_aggregation_marks_missing_source_bucket_partial_with_market_calendar():
    service = BarAggregationService()
    tz = ZoneInfo("Asia/Taipei")
    start = datetime(2026, 1, 5, 13, 0, tzinfo=tz)
    bars = [
        MarketDataBarDTO(
            stock_id=1,
            timeframe="5m",
            timestamp=start + timedelta(minutes=5 * index),
            open_price=Decimal("100"),
            high_price=Decimal("101"),
            low_price=Decimal("99"),
            close_price=Decimal("100"),
            volume=100,
            source="ibkr",
        )
        for index in range(5)
    ]

    aggregated = service.aggregate(
        bars,
        target_timeframe="1h",
        market="TW",
    )

    assert aggregated[0].quality_status == "partial"


def test_market_data_ingestion_canonicalizes_provider_source_names():
    class FakePriceDataSource:
        def get_source_name(self):
            return "Yahoo Finance"

    service = MarketDataIngestionService(
        stock_repository=None,
        bar_repository=None,
        price_data_source=FakePriceDataSource(),
    )

    assert service.storage_source_name() == "yahoo_finance"

    record = service.raw_bar_to_record(
        {
            "timestamp": datetime(2026, 1, 5, 9, 0, tzinfo=ZoneInfo("Asia/Taipei")),
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100,
            "volume": 100,
        },
        stock_id=1,
        symbol="2330.TW",
        market="TW",
        timeframe="5m",
        source="Yahoo Finance",
    )

    assert record["source"] == "yahoo_finance"


@pytest.mark.asyncio
async def test_aggregate_derived_bars_filters_source_bars_by_canonical_provider():
    stock = SimpleNamespace(id=1, symbol="2330.TW", market="TW")

    class FakeStockRepository:
        async def get(self, db, stock_id):
            return stock

    class FakeBarRepository:
        def __init__(self):
            self.source_filters = []

        async def get_bars(self, **kwargs):
            self.source_filters.append(kwargs["source"])
            return []

        async def delete_window(self, **kwargs):
            return 0

        async def upsert_batch(self, db, bars):
            return bars

    class FakePriceDataSource:
        def get_source_name(self):
            return "Yahoo Finance"

    bar_repo = FakeBarRepository()
    service = MarketDataIngestionService(
        stock_repository=FakeStockRepository(),
        bar_repository=bar_repo,
        price_data_source=FakePriceDataSource(),
    )

    await service.aggregate_derived_bars(
        db=None,
        stock_id=1,
        target_timeframe="15m",
        start_at=datetime(2026, 1, 5, 9, 0, tzinfo=ZoneInfo("Asia/Taipei")),
        end_at=datetime(2026, 1, 5, 10, 0, tzinfo=ZoneInfo("Asia/Taipei")),
    )

    assert bar_repo.source_filters == ["yahoo_finance"]


def test_strategy_spec_declares_timeframe_requirements():
    spec = GoldenCrossStrategy().get_spec()

    assert spec.required_timeframes == ["1d"]
    assert spec.lookback_bars["1d"] >= 20
    assert {indicator.name for indicator in spec.required_indicators} == {
        "SMA_5",
        "SMA_20",
    }


def test_market_calendar_expected_tw_5m_bars_for_one_session():
    calendar = MarketCalendarService()
    tz = ZoneInfo("Asia/Taipei")
    expected = calendar.expected_timestamps(
        market="TW",
        timeframe="5m",
        start_at=datetime(2026, 1, 5, 0, 0, tzinfo=tz),
        end_at=datetime(2026, 1, 6, 0, 0, tzinfo=tz),
    )

    assert len(expected) == 54
    assert expected[0] == datetime(2026, 1, 5, 9, 0, tzinfo=tz)
    assert expected[-1] == datetime(2026, 1, 5, 13, 25, tzinfo=tz)


def test_daily_price_point_maps_to_market_data_bar_record():
    service = MarketDataIngestionService(
        stock_repository=object(),
        bar_repository=object(),
        price_data_source=object(),
    )

    record = service.price_point_to_daily_bar_record(
        price_point={
            "date": datetime(2026, 1, 5).date(),
            "open": 100,
            "high": 110,
            "low": 95,
            "close": 108,
            "volume": 1000,
        },
        stock_id=1,
        symbol="2330.TW",
        market="TW",
        source="yahoo_finance",
    )

    assert record["timeframe"] == "1d"
    assert record["timestamp"] == datetime(
        2026, 1, 5, 0, 0, tzinfo=ZoneInfo("Asia/Taipei")
    )
    assert record["source_type"] == "source"
    assert record["open_price"] == Decimal("100")


@pytest.mark.asyncio
async def test_market_data_validation_reports_missing_and_invalid_bars():
    tz = ZoneInfo("Asia/Taipei")
    stock = SimpleNamespace(id=1, symbol="2330.TW", market="TW")
    valid_bar = SimpleNamespace(
        stock_id=1,
        timeframe="5m",
        timestamp=datetime(2026, 1, 5, 9, 0, tzinfo=tz),
        open_price=Decimal("100"),
        high_price=Decimal("101"),
        low_price=Decimal("99"),
        close_price=Decimal("100"),
        volume=100,
        quality_status="complete",
    )
    invalid_bar = SimpleNamespace(
        stock_id=1,
        timeframe="5m",
        timestamp=datetime(2026, 1, 5, 9, 5, tzinfo=tz),
        open_price=Decimal("100"),
        high_price=Decimal("98"),
        low_price=Decimal("99"),
        close_price=Decimal("100"),
        volume=100,
        quality_status="complete",
    )

    class FakeStockRepository:
        async def get(self, db, stock_id):
            return stock

    class FakeBarRepository:
        async def get_bars(self, **kwargs):
            return [valid_bar, invalid_bar]

    service = MarketDataValidationService(
        stock_repository=FakeStockRepository(),
        bar_repository=FakeBarRepository(),
    )

    report = await service.validate_window(
        db=None,
        stock_id=1,
        timeframe="5m",
        start_at=datetime(2026, 1, 5, 9, 0, tzinfo=tz),
        end_at=datetime(2026, 1, 5, 9, 15, tzinfo=tz),
    )

    assert report.expected_count == 3
    assert report.actual_count == 2
    assert report.invalid_ohlcv_count == 1
    assert report.missing_timestamps == [
        datetime(2026, 1, 5, 9, 10, tzinfo=tz)
    ]
    assert not report.is_complete


@pytest.mark.asyncio
async def test_market_data_validation_treats_partial_bars_as_incomplete():
    tz = ZoneInfo("Asia/Taipei")
    stock = SimpleNamespace(id=1, symbol="2330.TW", market="TW")
    partial_bar = SimpleNamespace(
        stock_id=1,
        timeframe="15m",
        timestamp=datetime(2026, 1, 5, 9, 0, tzinfo=tz),
        open_price=Decimal("100"),
        high_price=Decimal("101"),
        low_price=Decimal("99"),
        close_price=Decimal("100"),
        volume=100,
        quality_status="partial",
    )

    class FakeStockRepository:
        async def get(self, db, stock_id):
            return stock

    class FakeBarRepository:
        async def get_bars(self, **kwargs):
            return [partial_bar]

    service = MarketDataValidationService(
        stock_repository=FakeStockRepository(),
        bar_repository=FakeBarRepository(),
    )

    report = await service.validate_window(
        db=None,
        stock_id=1,
        timeframe="15m",
        start_at=datetime(2026, 1, 5, 9, 0, tzinfo=tz),
        end_at=datetime(2026, 1, 5, 9, 15, tzinfo=tz),
    )

    assert report.partial_count == 1
    assert report.partial_timestamps == [datetime(2026, 1, 5, 9, 0, tzinfo=tz)]
    assert not report.is_complete


@pytest.mark.asyncio
async def test_market_data_validation_allows_backfilled_higher_timeframe_bars():
    tz = ZoneInfo("Asia/Taipei")
    stock = SimpleNamespace(id=1, symbol="2330.TW", market="TW")
    backfilled_bar = SimpleNamespace(
        stock_id=1,
        timeframe="15m",
        timestamp=datetime(2026, 1, 5, 9, 0, tzinfo=tz),
        open_price=Decimal("100"),
        high_price=Decimal("101"),
        low_price=Decimal("99"),
        close_price=Decimal("100"),
        volume=100,
        quality_status="backfilled",
    )

    class FakeStockRepository:
        async def get(self, db, stock_id):
            return stock

    class FakeBarRepository:
        async def get_bars(self, **kwargs):
            return [backfilled_bar]

    service = MarketDataValidationService(
        stock_repository=FakeStockRepository(),
        bar_repository=FakeBarRepository(),
    )

    report = await service.validate_window(
        db=None,
        stock_id=1,
        timeframe="15m",
        start_at=datetime(2026, 1, 5, 9, 0, tzinfo=tz),
        end_at=datetime(2026, 1, 5, 9, 15, tzinfo=tz),
    )

    assert report.partial_count == 0
    assert report.partial_timestamps == []
    assert report.is_complete


@pytest.mark.asyncio
async def test_collect_backfilled_bars_replaces_selected_derived_bucket():
    tz = ZoneInfo("Asia/Taipei")
    target_timestamp = datetime(2026, 1, 5, 9, 0, tzinfo=tz)
    stock = SimpleNamespace(id=1, symbol="2330.TW", market="TW")

    class FakeStockRepository:
        async def get(self, db, stock_id):
            return stock

    class FakeBarRepository:
        def __init__(self):
            self.deleted = []
            self.records = []

        async def delete_timestamps(self, **kwargs):
            self.deleted.append(kwargs)
            return len(kwargs["timestamps"])

        async def upsert_batch(self, db, bars):
            self.records.extend(bars)
            return bars

    class FakePriceDataSource:
        def get_source_name(self):
            return "provider"

        async def fetch_bars(self, **kwargs):
            return [
                {
                    "timestamp": target_timestamp,
                    "open": 100,
                    "high": 101,
                    "low": 99,
                    "close": 100,
                    "volume": 100,
                }
            ]

    bar_repo = FakeBarRepository()
    service = MarketDataIngestionService(
        stock_repository=FakeStockRepository(),
        bar_repository=bar_repo,
        price_data_source=FakePriceDataSource(),
    )

    result = await service.collect_backfilled_bars(
        db=None,
        stock_id=1,
        timeframe="15m",
        start_at=target_timestamp,
        end_at=target_timestamp + timedelta(minutes=15),
        target_timestamps=[target_timestamp],
    )

    assert result.records_written == 1
    assert result.quality_status == "backfilled"
    assert bar_repo.deleted[0]["source_type"] == "derived"
    assert bar_repo.records[0]["quality_status"] == "backfilled"
    assert bar_repo.records[0]["source"] == "provider"
