from types import SimpleNamespace

import pytest

from api.v1.stocks.prices import check_price_data_exists
from app import main as main_module


class FakeConnection:
    def __init__(self, error=None):
        self.error = error

    async def __aenter__(self):
        if self.error:
            raise self.error
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def execute(self, statement):
        return None


class FakeEngine:
    def __init__(self, error=None):
        self.error = error

    def connect(self):
        return FakeConnection(self.error)


@pytest.mark.asyncio
async def test_database_health_reports_real_connectivity(monkeypatch):
    monkeypatch.setattr(main_module.database_module, "engine", FakeEngine())
    assert (await main_module._database_health())["status"] == "healthy"

    monkeypatch.setattr(
        main_module.database_module,
        "engine",
        FakeEngine(ConnectionError("database unavailable")),
    )
    result = await main_module._database_health()
    assert result == {"status": "unhealthy", "error": "ConnectionError"}


class ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar(self):
        return self.value


class CoverageSession:
    def __init__(self, values):
        self.values = iter(values)

    async def execute(self, statement):
        return ScalarResult(next(self.values))


@pytest.mark.asyncio
async def test_data_exists_requires_market_coverage_not_one_row():
    result = await check_price_data_exists(
        date="2026-07-10",
        market="US",
        min_coverage=0.9,
        db=CoverageSession([1, 100]),
    )

    assert result["stock_count"] == 1
    assert result["active_stock_count"] == 100
    assert result["coverage_ratio"] == 0.01
    assert result["has_data"] is False
