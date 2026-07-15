from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from domain.market_data.daily_prices import has_valid_ohlc
from domain.services.market_data_validation_service import (
    MarketDataValidationService,
)
from infrastructure.persistence.daily_price_repository import (
    DailyPriceRepository,
)
from infrastructure.persistence.market_data_bar_repository import (
    MarketDataBarRepository,
)


class _EmptyScalarResult:
    def scalars(self):
        return self

    def all(self):
        return []


class _StockResult:
    def all(self):
        return [SimpleNamespace(id=1, symbol="AAPL", market="US")]


class _RecordingSession:
    def __init__(self, first_result=None):
        self.first_result = first_result
        self.statements = []
        self.commits = 0

    async def execute(self, statement):
        self.statements.append(statement)
        if len(self.statements) == 1 and self.first_result is not None:
            return self.first_result
        return _EmptyScalarResult()

    async def commit(self):
        self.commits += 1


def _market_bar(symbol: str, price: Decimal, day: int) -> dict:
    return {
        "stock_id": 1,
        "symbol": symbol,
        "market": "US",
        "timeframe": "1d",
        "timestamp": datetime(2026, 7, day, tzinfo=timezone.utc),
        "open_price": price,
        "high_price": price,
        "low_price": price,
        "close_price": price,
        "volume": 100,
        "source": "test",
        "source_type": "source",
        "is_adjusted": False,
        "generated_from_timeframe": None,
        "quality_status": "complete",
    }


def _daily_price(symbol: str, price: Decimal, day: int) -> dict:
    return {
        "stock_id": 1,
        "symbol": symbol,
        "market": "US",
        "date": date(2026, 7, day),
        "open_price": price,
        "high_price": price,
        "low_price": price,
        "close_price": price,
        "volume": 100,
        "source": "test",
    }


def _statement_values(statement) -> set:
    return set(statement.compile().params.values())


def test_valid_ohlc_guard_supports_mappings_and_objects() -> None:
    valid = _market_bar("AAPL", Decimal("100"), 14)
    invalid = _market_bar("DROP", Decimal("NaN"), 15)

    assert has_valid_ohlc(valid)
    assert has_valid_ohlc(SimpleNamespace(**valid))
    assert not has_valid_ohlc(invalid)
    assert not has_valid_ohlc(SimpleNamespace(**invalid))


@pytest.mark.asyncio
async def test_market_data_bar_repository_drops_non_finite_records() -> None:
    session = _RecordingSession()
    repository = MarketDataBarRepository()

    await repository.upsert_batch(
        session,
        [
            _market_bar("AAPL", Decimal("100"), 14),
            _market_bar("DROP", Decimal("NaN"), 15),
        ],
    )

    assert session.commits == 1
    assert len(session.statements) == 2
    insert_values = _statement_values(session.statements[0])
    assert "AAPL" in insert_values
    assert "DROP" not in insert_values


@pytest.mark.asyncio
async def test_daily_price_repository_drops_non_finite_records(
    monkeypatch,
) -> None:
    session = _RecordingSession(first_result=_StockResult())
    repository = DailyPriceRepository(session)

    async def no_created_prices(*args, **kwargs):
        return []

    monkeypatch.setattr(
        "infrastructure.persistence.daily_price_repository.fetch_daily_prices",
        no_created_prices,
    )

    await repository.create_batch(
        session,
        [
            _daily_price("AAPL", Decimal("100"), 14),
            _daily_price("DROP", Decimal("NaN"), 15),
        ],
    )

    assert session.commits == 1
    assert len(session.statements) == 2
    insert_values = _statement_values(session.statements[1])
    assert "AAPL" in insert_values
    assert "DROP" not in insert_values


def test_market_data_validation_treats_non_finite_ohlc_as_invalid() -> None:
    service = object.__new__(MarketDataValidationService)
    invalid_bar = SimpleNamespace(
        open_price=Decimal("NaN"),
        high_price=Decimal("NaN"),
        low_price=Decimal("NaN"),
        close_price=Decimal("NaN"),
        volume=100,
    )

    assert service._has_invalid_ohlcv(invalid_bar)
