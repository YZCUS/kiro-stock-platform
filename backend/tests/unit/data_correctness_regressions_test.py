from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from domain.models.user_portfolio import UserPortfolio
from domain.models.strategy_signal import StrategySignal
from domain.repositories.price_data_source_interface import RateLimitError
from domain.services.data_collection_service import (
    DataCollectionService,
    DataCollectionStatus,
)
from domain.services.market_calendar_service import MarketCalendarService
from domain.services.price_alert_service import PriceAlertService
from domain.services.qlib_data_readiness_service import (
    QlibDataReadinessService,
)
from domain.services.strategy_evaluation_service import (
    StrategyEvaluationService,
)
from domain.services.strategy_signal_service import StrategySignalService
from domain.strategies.strategy_interface import (
    SignalDirection,
    StrategyType,
    TradingSignal,
)
from infrastructure.external.price_data_sources.yahoo_finance_source import (
    YahooFinanceSource,
)


def _signal(
    *,
    direction: str,
    signal_scope: str = "canonical",
    signal_date: date = date(2026, 7, 10),
    valid_until: date | None = date(2026, 7, 20),
    created_at: datetime = datetime(2026, 7, 10, tzinfo=timezone.utc),
    signal_id: int = 1,
):
    return SimpleNamespace(
        id=signal_id,
        strategy_type="golden_cross",
        signal_horizon="20d",
        direction=direction,
        confidence=Decimal("80"),
        signal_scope=signal_scope,
        signal_date=signal_date,
        valid_until=valid_until,
        created_at=created_at,
    )


def test_composite_score_only_uses_unexpired_canonical_signals_deterministically():
    service = StrategyEvaluationService()
    stock = SimpleNamespace(id=7, symbol="AAPL", market="US")
    weights = {
        ("golden_cross", "20d"): SimpleNamespace(weight=Decimal("1")),
    }
    canonical_short = _signal(direction="SHORT", signal_id=2)
    same_day_older = _signal(
        direction="LONG",
        created_at=datetime(2026, 7, 9, tzinfo=timezone.utc),
        signal_id=9,
    )
    user_signal = _signal(direction="LONG", signal_scope="user", signal_id=20)
    expired = _signal(
        direction="LONG",
        valid_until=date(2026, 7, 11),
        signal_id=30,
    )

    forward = service._score_stock(
        stock,
        [same_day_older, user_signal, expired, canonical_short],
        weights,
        weight_version_id=3,
        score_date=date(2026, 7, 12),
    )
    reverse = service._score_stock(
        stock,
        [canonical_short, expired, user_signal, same_day_older],
        weights,
        weight_version_id=3,
        score_date=date(2026, 7, 12),
    )

    assert forward["composite_score"] == pytest.approx(-0.8)
    assert reverse["composite_score"] == pytest.approx(-0.8)
    assert forward["strategy_contributions"] == reverse["strategy_contributions"]


def test_canonical_signal_identity_is_enforced_by_database_index():
    index = next(
        index
        for index in StrategySignal.__table__.indexes
        if index.name == "uq_strategy_signals_canonical_identity"
    )

    assert index.unique is True
    assert [column.name for column in index.columns] == [
        "stock_id",
        "strategy_type",
        "signal_horizon",
        "signal_date",
    ]
    assert "signal_scope = 'canonical'" in str(
        index.dialect_options["postgresql"]["where"]
    )


class _ScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None


class _AlertDb:
    def __init__(self, alerts, bars):
        self._results = [_ScalarResult(alerts), _ScalarResult(bars)]
        self.statements = []
        self.commits = 0

    async def execute(self, statement, *args, **kwargs):
        self.statements.append(statement)
        return self._results.pop(0)

    async def commit(self):
        self.commits += 1


class _MarketInfo:
    def __init__(self, price=101):
        self.price = price
        self.calls = []

    async def get_quote(self, db, symbol, market, stock_id=None):
        self.calls.append((symbol, market, stock_id))
        return {"price": self.price, "source": "provider"}


def _alert(alert_id: int, stock_id: int = 1):
    return SimpleNamespace(
        id=alert_id,
        stock_id=stock_id,
        symbol="AAPL" if stock_id == 1 else "MSFT",
        market="US",
        source_timeframe="1d",
        condition="ABOVE",
        target_price=Decimal("100"),
        last_checked_at=None,
        last_price=None,
        last_source=None,
        triggered=False,
        active=True,
        triggered_at=None,
    )


@pytest.mark.asyncio
async def test_price_alerts_batch_latest_bar_query_and_group_provider_fallback():
    alerts = [_alert(1), _alert(2), _alert(3, stock_id=2)]
    market_info = _MarketInfo()
    db = _AlertDb(alerts, bars=[])
    service = PriceAlertService(market_info)

    result = await service.check_alerts(db, limit=500)

    assert len(db.statements) == 2
    assert sorted(market_info.calls) == [
        ("AAPL", "US", 1),
        ("MSFT", "US", 2),
    ]
    assert result["checked"] == 3
    assert all(alert.last_checked_at is not None for alert in alerts)


def test_price_alert_query_prioritizes_never_or_least_recently_checked_alerts():
    statement = PriceAlertService()._alerts_to_check_query(
        now=datetime(2026, 7, 12, tzinfo=timezone.utc),
        limit=500,
    )

    sql = str(statement.compile(compile_kwargs={"literal_binds": True})).lower()
    order_by = sql.split("order by", 1)[1]
    assert "last_checked_at" in order_by
    assert order_by.index("last_checked_at") < order_by.index("price_alerts.id")


@pytest.mark.asyncio
async def test_yahoo_intraday_fetch_strictly_filters_requested_half_open_window():
    index = pd.DatetimeIndex(
        [
            "2026-07-10 09:30",
            "2026-07-10 14:00",
            "2026-07-10 14:30",
            "2026-07-10 15:00",
        ],
        tz="America/New_York",
    )
    frame = pd.DataFrame(
        {
            "Open": [100, 101, 102, 103],
            "High": [101, 102, 103, 104],
            "Low": [99, 100, 101, 102],
            "Close": [100, 101, 102, 103],
            "Volume": [10, 11, 12, 13],
        },
        index=index,
    )
    ticker = SimpleNamespace(history=lambda **kwargs: frame)
    source = YahooFinanceSource()
    source.wrapper = SimpleNamespace(get_ticker=lambda symbol: ticker)
    tz = ZoneInfo("America/New_York")

    bars = await source.fetch_bars(
        "AAPL",
        "30m",
        datetime(2026, 7, 10, 14, 0, tzinfo=tz),
        datetime(2026, 7, 10, 15, 0, tzinfo=tz),
        "US",
    )

    assert [bar["timestamp"].hour for bar in bars] == [14, 14]
    assert [bar["timestamp"].minute for bar in bars] == [0, 30]


def test_market_calendar_excludes_nyse_independence_day():
    calendar = MarketCalendarService()
    tz = ZoneInfo("America/New_York")

    expected = calendar.expected_timestamps(
        "US",
        "5m",
        datetime(2025, 7, 4, tzinfo=tz),
        datetime(2025, 7, 5, tzinfo=tz),
    )

    assert expected == []
    assert (
        calendar.expected_timestamps(
            "US",
            "1d",
            datetime(2025, 7, 4, tzinfo=tz),
            datetime(2025, 7, 5, tzinfo=tz),
        )
        == []
    )


def test_market_calendar_excludes_nyse_national_day_of_mourning():
    calendar = MarketCalendarService()
    assert calendar.trading_days("US", date(2025, 1, 9), date(2025, 1, 9)) == []


def test_market_calendar_honors_nyse_early_close():
    calendar = MarketCalendarService()
    tz = ZoneInfo("America/New_York")

    expected = calendar.expected_timestamps(
        "US",
        "5m",
        datetime(2025, 11, 28, tzinfo=tz),
        datetime(2025, 11, 29, tzinfo=tz),
    )

    assert len(expected) == 42
    assert expected[-1] == datetime(2025, 11, 28, 12, 55, tzinfo=tz)


@pytest.mark.parametrize(
    "closed_day",
    [
        date(2024, 7, 24),
        date(2024, 10, 31),
        date(2025, 1, 23),
        date(2025, 1, 29),
        date(2026, 2, 18),
        date(2026, 7, 10),
    ],
)
def test_market_calendar_excludes_twse_scheduled_and_emergency_closures(closed_day):
    calendar = MarketCalendarService()
    assert calendar.trading_days("TW", closed_day, closed_day) == []


class _MappingResult:
    def __init__(self, row):
        self._row = row

    def mappings(self):
        return self

    def one(self):
        return self._row


class _CoverageDb:
    def __init__(self):
        self.statement = None

    async def execute(self, statement, params):
        self.statement = statement
        return _MappingResult(
            {
                "stocks_with_daily_bars": 1,
                "rows": 252,
                "min_date": date(2025, 1, 1),
                "max_date": date(2025, 12, 31),
                "min_bars": 252,
                "median_bars": 252,
                "max_bars": 252,
                "adjusted_rows": 0,
            }
        )


@pytest.mark.asyncio
async def test_qlib_readiness_counts_one_canonical_bar_per_market_local_date():
    db = _CoverageDb()
    service = QlibDataReadinessService()

    await service._coverage_summary(db, "US", active_stocks=1)

    sql = str(db.statement).lower()
    assert "row_number()" in sql
    assert "partition by" in sql
    assert "daily_rank = 1" in sql
    assert "america/new_york" in sql


class _StockRepository:
    def __init__(self, stock):
        self.stock = stock

    async def get(self, db, stock_id):
        return self.stock if self.stock.id == stock_id else None


class _PriceRepository:
    def __init__(self, latest, missing_dates):
        self.latest = latest
        self.missing_dates = missing_dates

    async def get_latest_price(self, db, stock_id):
        return self.latest

    async def get_missing_dates(self, db, stock_id, start_date, end_date):
        return self.missing_dates


class _FailingPriceSource:
    def __init__(self, error):
        self.error = error

    async def fetch_historical_prices(self, **kwargs):
        raise self.error

    def get_source_name(self):
        return "failing"


def _collection_service(error, latest, missing_dates):
    stock = SimpleNamespace(id=1, symbol="AAPL", name="Apple", market="US")
    service = DataCollectionService(
        stock_repository=_StockRepository(stock),
        price_repository=_PriceRepository(latest, missing_dates),
        cache_service=SimpleNamespace(),
        price_data_source=_FailingPriceSource(error),
    )
    service.retry_count = 1
    return service, stock


@pytest.mark.asyncio
async def test_collection_timeout_is_failed_instead_of_no_data():
    today = date.today()
    service, stock = _collection_service(
        TimeoutError("provider timeout"),
        SimpleNamespace(date=today),
        [today - timedelta(days=2)],
    )

    result = await service.collect_stock_data(
        None,
        stock.id,
        start_date=today - timedelta(days=5),
        end_date=today,
    )

    assert result.status is DataCollectionStatus.FAILED
    assert "provider timeout" in result.errors[0]


@pytest.mark.asyncio
async def test_collection_preserves_typed_rate_limit_status():
    today = date.today()
    service, stock = _collection_service(
        RateLimitError("quota exceeded"),
        None,
        [today],
    )

    result = await service.collect_stock_data(
        None,
        stock.id,
        start_date=today - timedelta(days=1),
        end_date=today,
    )

    assert result.status is DataCollectionStatus.RATE_LIMITED


@pytest.mark.asyncio
async def test_collection_freshness_checks_start_and_interior_gaps():
    today = date.today()
    missing_day = today - timedelta(days=3)
    service, stock = _collection_service(
        AssertionError("provider should not be called"),
        SimpleNamespace(date=today),
        [missing_day],
    )

    assert await service._check_data_freshness(
        None,
        stock.id,
        start_date=today - timedelta(days=10),
        end_date=today,
    )


class _LockingQuery:
    def __init__(self, portfolio):
        self.portfolio = portfolio
        self.for_update = False

    def filter(self, *args):
        return self

    def with_for_update(self):
        self.for_update = True
        return self

    def first(self):
        return self.portfolio


class _LockingSession:
    def __init__(self, portfolio):
        self.query_result = _LockingQuery(portfolio)

    def query(self, model):
        assert model is UserPortfolio
        return self.query_result


def test_position_oversell_check_reads_the_position_for_update():
    portfolio = UserPortfolio(
        id=7,
        user_id=uuid4(),
        stock_id=1,
        quantity=Decimal("2"),
        avg_cost=Decimal("100"),
        total_cost=Decimal("200"),
    )
    session = _LockingSession(portfolio)

    with pytest.raises(ValueError, match="賣出數量不可超過目前持倉"):
        UserPortfolio.create_or_update_position(
            session,
            portfolio.user_id,
            portfolio.stock_id,
            Decimal("3"),
            Decimal("120"),
            "SELL",
        )

    assert session.query_result.for_update is True


class _CanonicalDb:
    def __init__(self, stock):
        self.stock = stock
        self.added = []
        self.existing = None
        self.execute_count = 0

    async def execute(self, statement):
        self.execute_count += 1
        if self.execute_count % 2 == 1:
            return _ScalarResult([self.stock])
        return _ScalarResult([self.existing] if self.existing else [])

    def add(self, signal):
        self.added.append(signal)
        self.existing = signal

    async def commit(self):
        return None


class _CanonicalStrategy:
    strategy_type = StrategyType.GOLDEN_CROSS

    def get_default_params(self):
        return {"short_period": 5, "long_period": 20}

    async def batch_analyze(self, stock_ids, db, params):
        assert stock_ids == [1]
        assert params == {"short_period": 5, "long_period": 20}
        return [
            TradingSignal(
                stock_id=1,
                stock_symbol="AAPL",
                strategy_type=self.strategy_type,
                direction=SignalDirection.LONG,
                confidence=80,
                entry_zone=(100, 101),
                stop_loss=95,
                take_profit=[110],
                signal_date=date(2026, 7, 12),
                valid_until=date(2026, 8, 1),
            )
        ]


@pytest.mark.asyncio
async def test_canonical_signal_generation_is_user_independent_and_idempotent(
    monkeypatch,
):
    stock = SimpleNamespace(id=1, symbol="AAPL", market="US")
    db = _CanonicalDb(stock)
    service = StrategySignalService()
    monkeypatch.setattr(
        "domain.services.strategy_signal_service.strategy_registry.get_all_strategies",
        lambda: [_CanonicalStrategy()],
    )

    first = await service.generate_canonical_signals(db, market="US")
    second = await service.generate_canonical_signals(db, market="US")

    assert first["generated_signals"] == 1
    assert second["generated_signals"] == 0
    assert len(db.added) == 1
    assert db.added[0].user_id is None
    assert db.added[0].signal_scope == "canonical"


@pytest.mark.asyncio
async def test_internal_signal_generation_runs_personalized_and_canonical_paths(
    monkeypatch,
):
    from api.routers.v1 import strategies as strategies_router

    async def personalized(db, user_id):
        return {
            "processed_subscriptions": 2,
            "generated_signals": 3,
            "errors": [],
        }

    async def canonical(db, market):
        return {
            "processed_strategies": 1,
            "generated_signals": 4,
            "errors": [],
        }

    monkeypatch.setattr(
        strategies_router.signal_service,
        "batch_generate_signals",
        personalized,
    )
    monkeypatch.setattr(
        strategies_router.signal_service,
        "generate_canonical_signals",
        canonical,
        raising=False,
    )

    result = await strategies_router.generate_signals_internal(
        user_id=None,
        market="US",
        db=object(),
    )

    assert result["generated_signals"] == 3
    assert result["canonical_generated_signals"] == 4
