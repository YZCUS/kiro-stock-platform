#!/usr/bin/env python3
"""
交易信號 API 測試
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

import importlib.util
import pytest
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.testclient import TestClient

# -----------------------------------------------------------------------------
# 測試環境設定：預先載入 .env 並填入必要環境變數
# -----------------------------------------------------------------------------
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_PATH, override=True)

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("REDIS_DB", "0")
os.environ.setdefault("APP_NAME", "Signals Test App")
os.environ.setdefault("APP_VERSION", "0.0.0-tests")
os.environ.setdefault("APP_DEBUG", "true")
os.environ.setdefault("SECURITY_SECRET_KEY", "test-secret")

# -----------------------------------------------------------------------------
# 建立必要的 stub，避免匯入真實基礎設施而拖慢或干擾測試
# -----------------------------------------------------------------------------
if "services" not in sys.modules:
    services_pkg = ModuleType("services")
    services_pkg.__path__ = []  # type: ignore[attr-defined]
    sys.modules["services"] = services_pkg

if "services.infrastructure" not in sys.modules:
    infra_pkg = ModuleType("services.infrastructure")
    infra_pkg.__path__ = []  # type: ignore[attr-defined]
    sys.modules["services.infrastructure"] = infra_pkg

if "services.infrastructure.redis_pubsub" not in sys.modules:
    redis_pubsub_stub = ModuleType("services.infrastructure.redis_pubsub")
    redis_pubsub_stub.redis_broadcaster = SimpleNamespace()
    sys.modules["services.infrastructure.redis_pubsub"] = redis_pubsub_stub

if "services.data" not in sys.modules:
    data_pkg = ModuleType("services.data")
    data_pkg.__path__ = []  # type: ignore[attr-defined]
    sys.modules["services.data"] = data_pkg

if "services.data.collection" not in sys.modules:
    collection_stub = ModuleType("services.data.collection")
    collection_stub.data_collection_service = SimpleNamespace()
    sys.modules["services.data.collection"] = collection_stub

# -----------------------------------------------------------------------------
# app.dependencies stub：提供 DI 函式簽名，稍後以 dependency_overrides 注入
# -----------------------------------------------------------------------------
if "app" not in sys.modules:
    app_pkg = ModuleType("app")
    app_pkg.__path__ = []  # type: ignore[attr-defined]
    sys.modules["app"] = app_pkg

if "app.dependencies" not in sys.modules:
    deps_stub = ModuleType("app.dependencies")

    async def get_database_session():
        yield None

    def get_stock_service():
        return SimpleNamespace()

    def get_trading_signal_service_clean():
        return SimpleNamespace()

    deps_stub.get_database_session = get_database_session
    deps_stub.get_stock_service = get_stock_service
    deps_stub.get_trading_signal_service_clean = get_trading_signal_service_clean

    sys.modules["app.dependencies"] = deps_stub

# -----------------------------------------------------------------------------
# 載入真實的 api/v1/signals router 模組（避免透過套件載入引發副作用）
# -----------------------------------------------------------------------------
signals_spec = importlib.util.spec_from_file_location(
    "api.v1.signals",
    Path(__file__).resolve().parents[2] / "api" / "v1" / "signals.py"
)
signals_module = importlib.util.module_from_spec(signals_spec)
signals_spec.loader.exec_module(signals_module)

signals_router = signals_module.router
SignalTypeEnum = signals_module.SignalTypeEnum
TradingSignalResponse = signals_module.TradingSignalResponse
SignalStatsResponse = signals_module.SignalStatsResponse
SignalHistoryResponse = signals_module.SignalHistoryResponse

from app.dependencies import (  # type: ignore  # noqa: E402
    get_database_session,
    get_stock_service,
    get_trading_signal_service_clean,
)

# -----------------------------------------------------------------------------
# 建立測試專用 FastAPI app 並注入 router
# -----------------------------------------------------------------------------
app = FastAPI(title="Signals Router Test App")
app.include_router(signals_router, prefix="/api/v1")
client = TestClient(app)

# -----------------------------------------------------------------------------
# fixture：以 AsyncMock 覆寫依賴，注入虛擬服務物件
# -----------------------------------------------------------------------------
@pytest.fixture
def db_session_override():
    session = AsyncMock()

    async def override_db():
        yield session

    app.dependency_overrides[get_database_session] = override_db
    yield session
    app.dependency_overrides.pop(get_database_session, None)


@pytest.fixture
def stock_service_override():
    service = SimpleNamespace(
        get_stock_by_id=AsyncMock(),
    )
    app.dependency_overrides[get_stock_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_stock_service, None)


@pytest.fixture
def signal_service_override():
    service = SimpleNamespace(
        list_signals=AsyncMock(),
        count_signals=AsyncMock(),
        get_signal_stats=AsyncMock(),
        get_detailed_signal_stats=AsyncMock(),
        generate_trading_signals=AsyncMock(),
        create_signal=AsyncMock(),
        get_signal=AsyncMock(),
        delete_signal=AsyncMock(),
    )
    app.dependency_overrides[get_trading_signal_service_clean] = lambda: service
    yield service
    app.dependency_overrides.pop(get_trading_signal_service_clean, None)


@pytest.fixture
def signals_test_client(
    db_session_override,
    stock_service_override,
    signal_service_override,
):
    yield client


# -----------------------------------------------------------------------------
# 輔助建構函式
# -----------------------------------------------------------------------------

def make_signal_dict(signal_id: int = 1, stock_id: int = 1, symbol: str = "2330.TW") -> dict:
    return {
        "id": signal_id,
        "stock_id": stock_id,
        "signal_type": "buy",
        "strength": "strong",
        "price": 600.0,
        "confidence": 0.82,
        "date": date.today(),
        "description": "黃金交叉",
        "indicators": {"macd": {"histogram": 1.2}},
        "created_at": datetime.utcnow(),
        "symbol": symbol,
    }


def make_signal_analysis(symbol: str = "2330.TW") -> SimpleNamespace:
    primary = SimpleNamespace(
        signal_type=SimpleNamespace(value="buy"),
        signal_strength=SimpleNamespace(value="strong"),
        metadata={"price": 610.0},
        confidence=0.9,
        description="Primary buy signal",
    )
    support = SimpleNamespace(
        signal_type=SimpleNamespace(value="sell"),
        signal_strength=SimpleNamespace(value="weak"),
        metadata={"price": 605.0},
        confidence=0.4,
        description="Weak contra signal",
    )
    return SimpleNamespace(primary_signal=primary, supporting_signals=[support])


# -----------------------------------------------------------------------------
# 測試案例
# -----------------------------------------------------------------------------

def test_get_all_signals_success(
    signals_test_client,
    stock_service_override,
    signal_service_override,
):
    signal_service_override.list_signals.return_value = [
        make_signal_dict(signal_id=1),
        make_signal_dict(signal_id=2, stock_id=2, symbol="AAPL"),
    ]
    signal_service_override.count_signals.return_value = 2
    signal_service_override.get_signal_stats.return_value = {
        "total_signals": 2,
        "buy_signals": 1,
        "sell_signals": 1,
        "hold_signals": 0,
        "avg_confidence": 0.7,
        "cross_signals": 0,
        "top_stocks": [
            {"stock_id": 1, "symbol": "2330.TW", "count": 1},
            {"stock_id": 2, "symbol": "AAPL", "count": 1},
        ],
    }
    stock_service_override.get_stock_by_id.side_effect = [
        SimpleNamespace(symbol="2330.TW"),
        SimpleNamespace(symbol="AAPL"),
    ]

    response = signals_test_client.get(
        "/api/v1/signals/",
        params={"market": "TW", "page": 1, "page_size": 50},
    )

    assert response.status_code == 200
    payload = SignalHistoryResponse(**response.json())
    assert payload.pagination["total"] == 2
    assert len(payload.signals) == 2
    signal_service_override.list_signals.assert_awaited_once()
    stock_service_override.get_stock_by_id.assert_awaited()


def test_get_all_signals_not_found(
    signals_test_client,
    stock_service_override,
    signal_service_override,
):
    signal_service_override.list_signals.return_value = [make_signal_dict()]
    signal_service_override.count_signals.return_value = 1
    signal_service_override.get_signal_stats.return_value = {}
    stock_service_override.get_stock_by_id.side_effect = ValueError("找不到股票資料")

    response = signals_test_client.get("/api/v1/signals/")

    assert response.status_code == 404
    assert "找不到股票資料" in response.json()["detail"]


def test_get_signal_statistics_success(
    signals_test_client,
    signal_service_override,
):
    signal_service_override.get_detailed_signal_stats.return_value = {
        "total_signals": 10,
        "buy_signals": 6,
        "sell_signals": 3,
        "hold_signals": 1,
        "cross_signals": 2,
        "avg_confidence": 0.68,
        "top_stocks": [{"stock_id": 1, "symbol": "2330.TW", "count": 4}],
    }

    response = signals_test_client.get("/api/v1/signals/stats", params={"days": 15})

    assert response.status_code == 200
    stats_payload = SignalStatsResponse(**response.json())
    assert stats_payload.total_signals == 10
    signal_service_override.get_detailed_signal_stats.assert_awaited_once()


def test_get_stock_signals_success(
    signals_test_client,
    stock_service_override,
    signal_service_override,
):
    stock_service_override.get_stock_by_id.return_value = SimpleNamespace(symbol="2330.TW")
    signal_service_override.list_signals.return_value = [make_signal_dict()]

    response = signals_test_client.get("/api/v1/signals/1", params={"days": 10})

    assert response.status_code == 200
    result = [TradingSignalResponse(**item) for item in response.json()]
    assert result[0].symbol == "2330.TW"
    signal_service_override.list_signals.assert_awaited_once()


def test_detect_stock_signals_with_save(
    signals_test_client,
    stock_service_override,
    signal_service_override,
):
    stock_service_override.get_stock_by_id.return_value = SimpleNamespace(symbol="2330.TW")
    signal_service_override.generate_trading_signals.return_value = make_signal_analysis()
    signal_service_override.create_signal.return_value = {"id": 99}

    response = signals_test_client.post(
        "/api/v1/signals/1/detect",
        params={"signal_types": [SignalTypeEnum.BUY.value, SignalTypeEnum.SELL.value]},
    )

    assert response.status_code == 200
    items = [TradingSignalResponse(**data) for data in response.json()]
    assert {item.signal_type for item in items} == {"buy", "sell"}
    signal_service_override.create_signal.assert_awaited()


def test_delete_signal_not_found(signals_test_client, signal_service_override):
    signal_service_override.get_signal.return_value = None

    response = signals_test_client.delete("/api/v1/signals/999")

    assert response.status_code == 404
    signal_service_override.delete_signal.assert_not_called()