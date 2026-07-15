"""Strategy signal pagination contract tests."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from api.routers.v1 import strategies
from domain.services.strategy_signal_service import StrategySignalService


class CountResult:
    def __init__(self, value: int):
        self.value = value

    def scalar(self):
        return self.value


class RecordingDB:
    def __init__(self, count: int):
        self.count = count
        self.statement = None

    async def execute(self, statement):
        self.statement = statement
        return CountResult(self.count)


@pytest.mark.asyncio
async def test_count_user_signals_counts_all_filtered_matches_without_pagination():
    service = StrategySignalService()
    db = RecordingDB(count=137)

    total = await service.count_user_signals(
        db=db,
        user_id=uuid4(),
        strategy_type="golden_cross",
        status="active",
        direction="LONG",
        stock_id=42,
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31),
    )

    assert total == 137
    statement = str(db.statement)
    assert "count(strategy_signals.id)" in statement.lower()
    assert "strategy_signals.user_id" in statement
    assert "strategy_signals.strategy_type" in statement
    assert "strategy_signals.status" in statement
    assert "strategy_signals.valid_until" in statement
    assert "strategy_signals.direction" in statement
    assert "strategy_signals.stock_id" in statement
    assert "strategy_signals.signal_date" in statement
    assert "LIMIT" not in statement
    assert "OFFSET" not in statement


@pytest.mark.asyncio
async def test_signals_endpoint_returns_filtered_total_not_page_length(monkeypatch):
    user_id = uuid4()
    service = SimpleNamespace(
        get_user_signals=AsyncMock(return_value=[]),
        count_user_signals=AsyncMock(return_value=137),
    )
    monkeypatch.setattr(strategies, "signal_service", service)
    db = object()

    response = await strategies.get_user_signals(
        strategy_type="golden_cross",
        status="active",
        direction="LONG",
        stock_id=42,
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31),
        sort_by="signal_date",
        sort_order="desc",
        limit=25,
        offset=50,
        db=db,
        current_user=SimpleNamespace(id=user_id),
    )

    assert response.signals == []
    assert response.total == 137
    service.get_user_signals.assert_awaited_once_with(
        db=db,
        user_id=user_id,
        strategy_type="golden_cross",
        status="active",
        direction="LONG",
        stock_id=42,
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31),
        sort_by="signal_date",
        sort_order="desc",
        limit=25,
        offset=50,
    )
    service.count_user_signals.assert_awaited_once_with(
        db=db,
        user_id=user_id,
        strategy_type="golden_cross",
        status="active",
        direction="LONG",
        stock_id=42,
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31),
    )
