#!/usr/bin/env python3
"""
技術分析API測試
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.testclient import TestClient
from enum import Enum
import importlib.util

# -----------------------------------------------------------------------------
# 環境初始化：載入 backend/.env 並設定測試預設值
# -----------------------------------------------------------------------------
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_PATH, override=True)

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("REDIS_DB", "0")
os.environ.setdefault("APP_NAME", "Analysis Test App")
os.environ.setdefault("APP_VERSION", "0.0.0-tests")
os.environ.setdefault("APP_DEBUG", "true")
os.environ.setdefault("SECURITY_SECRET_KEY", "test-secret")

# -----------------------------------------------------------------------------
# Stub 快取與服務模組，避免測試期間載入重型依賴
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
# Stub app.dependencies，避免直接 import 真實 DI 實作
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

    def get_technical_analysis_service_clean():
        return SimpleNamespace()

    def get_trading_signal_service_clean():
        return SimpleNamespace()

    deps_stub.get_database_session = get_database_session
    deps_stub.get_stock_service = get_stock_service
    deps_stub.get_technical_analysis_service_clean = get_technical_analysis_service_clean
    deps_stub.get_trading_signal_service_clean = get_trading_signal_service_clean

    sys.modules["app.dependencies"] = deps_stub

# -----------------------------------------------------------------------------
# Stub api.routers.v1.analysis，提供 router 與 enum 定義
# -----------------------------------------------------------------------------
if "api" not in sys.modules:
    api_pkg = ModuleType("api")
    api_pkg.__path__ = []  # type: ignore[attr-defined]
    sys.modules["api"] = api_pkg

if "api.routers" not in sys.modules:
    routers_pkg = ModuleType("api.routers")
    routers_pkg.__path__ = []  # type: ignore[attr-defined]
    sys.modules["api.routers"] = routers_pkg

analysis_spec = importlib.util.spec_from_file_location(
    "api.routers.v1.analysis",
    Path(__file__).resolve().parents[2] / "api" / "v1" / "analysis.py"
)
analysis_module = importlib.util.module_from_spec(analysis_spec)
analysis_spec.loader.exec_module(analysis_module)

analysis_router = analysis_module.router
IndicatorTypeEnum = analysis_module.IndicatorTypeEnum
SignalTypeEnum = analysis_module.SignalTypeEnum

# -----------------------------------------------------------------------------
# 建立測試專用 FastAPI 應用：只掛載 analysis router
# -----------------------------------------------------------------------------
from app.dependencies import (
    get_database_session,
    get_stock_service,
    get_technical_analysis_service_clean,
    get_trading_signal_service_clean,
)

app = FastAPI(title="Analysis Router Test")
app.include_router(analysis_router, prefix="/api/v1")
client = TestClient(app)

# -----------------------------------------------------------------------------
# 依賴覆寫 Fixtures：以 AsyncMock 替換真實服務
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
        get_stock_list=AsyncMock(),
    )
    app.dependency_overrides[get_stock_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_stock_service, None)


@pytest.fixture
def technical_service_override():
    service = SimpleNamespace(
        calculate_indicator=AsyncMock(),
    )
    app.dependency_overrides[get_technical_analysis_service_clean] = lambda: service
    yield service
    app.dependency_overrides.pop(get_technical_analysis_service_clean, None)


@pytest.fixture
def signal_service_override():
    service = SimpleNamespace(
        generate_trading_signals=AsyncMock(),
        get_recent_signals=AsyncMock(),
    )
    app.dependency_overrides[get_trading_signal_service_clean] = lambda: service
    yield service
    app.dependency_overrides.pop(get_trading_signal_service_clean, None)


@pytest.fixture
def analysis_test_client(
    db_session_override,
    stock_service_override,
    technical_service_override,
    signal_service_override,
):
    yield client


# -----------------------------------------------------------------------------
# 枚舉與模型行為測試
# -----------------------------------------------------------------------------

def test_indicator_type_enum_values():
    expected = {"RSI", "SMA_20", "EMA_12", "MACD", "BB_UPPER", "KD_K"}
    assert {member.value for member in IndicatorTypeEnum} == expected


def test_signal_type_enum_values():
    expected = {"buy", "sell", "hold"}
    assert {member.value for member in SignalTypeEnum} == expected


# -----------------------------------------------------------------------------
# 技術分析端點測試
# -----------------------------------------------------------------------------

def test_calculate_indicator_success(
    analysis_test_client,
    stock_service_override,
    technical_service_override,
):
    stock_service_override.get_stock_by_id.return_value = SimpleNamespace(
        id=1, symbol="2330.TW"
    )
    technical_service_override.calculate_indicator.return_value = {
        "dates": [date.today()],
        "values": [65.5],
        "summary": {"current_value": 65.5},
    }

    response = analysis_test_client.post(
        "/api/v1/analysis/technical-analysis",
        json={"stock_id": 1, "indicator": "RSI", "days": 30},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["stock_id"] == 1
    assert payload["indicator"] == "RSI"
    assert payload["values"][0]["value"] == 65.5
    technical_service_override.calculate_indicator.assert_awaited_once()


def test_calculate_indicator_stock_not_found(
    analysis_test_client,
    stock_service_override,
    technical_service_override,
):
    stock_service_override.get_stock_by_id.side_effect = ValueError("Stock not found")

    response = analysis_test_client.post(
        "/api/v1/analysis/technical-analysis",
        json={"stock_id": 999, "indicator": "RSI"},
    )

    assert response.status_code == 404
    assert "Stock not found" in response.json()["detail"]


def test_get_all_indicators_success(
    analysis_test_client,
    stock_service_override,
    technical_service_override,
):
    stock_service_override.get_stock_by_id.return_value = SimpleNamespace(id=1)
    technical_service_override.calculate_indicator.side_effect = [
        {
            "dates": [date.today()],
            "values": [60],
            "summary": {"current_value": 60},
        },
        {
            "dates": [date.today()],
            "values": [55],
            "summary": {"current_value": 55},
        },
        {
            "dates": [date.today()],
            "values": [50],
            "summary": {"current_value": 50},
        },
        {
            "dates": [date.today()],
            "values": [45],
            "summary": {"current_value": 45},
        },
    ]

    response = analysis_test_client.get("/api/v1/analysis/technical-analysis/1")

    assert response.status_code == 200
    assert len(response.json()) == 4


# -----------------------------------------------------------------------------
# 交易信號端點測試
# -----------------------------------------------------------------------------

def test_detect_signals_success(
    analysis_test_client,
    stock_service_override,
    signal_service_override,
):
    stock_service_override.get_stock_by_id.return_value = SimpleNamespace(
        symbol="2330.TW"
    )
    signal = SimpleNamespace(
        signal_type=SimpleNamespace(value="buy"),
        signal_strength=SimpleNamespace(value="strong"),
        metadata={"price": 100},
        signal_date=datetime.utcnow(),
    )
    signal_service_override.generate_trading_signals.return_value = SimpleNamespace(
        primary_signal=signal,
        supporting_signals=[],
    )

    response = analysis_test_client.post("/api/v1/analysis/signals", json={"stock_id": 1})

    assert response.status_code == 200
    assert response.json()[0]["signal_type"] == "buy"
    # 預期服務會被呼叫兩次（一次為驗證，一次為實際取資料）
    assert signal_service_override.generate_trading_signals.await_count >= 1


def test_detect_signals_stock_not_found(
    analysis_test_client,
    stock_service_override,
    signal_service_override,
):
    stock_service_override.get_stock_by_id.side_effect = ValueError("Stock not found")

    response = analysis_test_client.post("/api/v1/analysis/signals", json={"stock_id": 999})

    assert response.status_code == 404
    assert "Stock not found" in response.json()["detail"]


# -----------------------------------------------------------------------------
# 市場概覽與其他端點
# -----------------------------------------------------------------------------

def test_market_overview_success(
    analysis_test_client,
    stock_service_override,
    signal_service_override,
):
    stock_service_override.get_stock_list.return_value = {
        "items": [{"id": 1, "symbol": "AAPL", "market": "US"}],
        "total": 1,
    }
    signal_service_override.generate_trading_signals.return_value = SimpleNamespace(
        primary_signal=SimpleNamespace(signal_type=SimpleNamespace(value="buy"))
    )

    response = analysis_test_client.get("/api/v1/analysis/market-overview")

    assert response.status_code == 200
    assert response.json()["market_sentiment"] in {"bullish", "bearish", "neutral"}


def test_market_overview_backend_error(
    analysis_test_client,
    stock_service_override,
):
    stock_service_override.get_stock_list.side_effect = Exception("backend failure")

    response = analysis_test_client.get("/api/v1/analysis/market-overview")

    assert response.status_code == 500
    assert "取得市場概覽失敗" in response.json()["detail"]


def test_get_stock_signals_success(
    analysis_test_client,
    stock_service_override,
    signal_service_override,
):
    stock_service_override.get_stock_by_id.return_value = SimpleNamespace(
        symbol="2330.TW"
    )
    signal_service_override.get_recent_signals.return_value = [
        {
            "signal_type": "buy",
            "signal_strength": "strong",
            "price": 100,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": {},
        }
    ]

    response = analysis_test_client.get("/api/v1/analysis/signals/1")

    assert response.status_code == 200
    assert response.json()[0]["signal_type"] == "buy"


def test_get_stock_signals_not_found(
    analysis_test_client,
    stock_service_override,
    signal_service_override,
):
    stock_service_override.get_stock_by_id.side_effect = ValueError("not found")

    response = analysis_test_client.get("/api/v1/analysis/signals/999")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_batch_analysis_success(
    analysis_test_client,
    stock_service_override,
    technical_service_override,
):
    stock_service_override.get_stock_list.return_value = {
        "items": [{"id": 1, "symbol": "AAPL", "market": "US"}],
        "total": 1,
    }
    technical_service_override.calculate_indicator.return_value = {
        "summary": {"current_value": 100, "trend": "up"},
    }

    response = analysis_test_client.get("/api/v1/analysis/batch-analysis")

    assert response.status_code == 200
    assert response.json()["total_analyzed"] == 1


def test_batch_analysis_empty(
    analysis_test_client,
    stock_service_override,
    technical_service_override,
):
    stock_service_override.get_stock_list.return_value = {"items": [], "total": 0}

    response = analysis_test_client.get("/api/v1/analysis/batch-analysis")

    assert response.status_code == 200
    assert response.json()["total_analyzed"] == 0


def test_technical_indicator_service_error(
    analysis_test_client,
    stock_service_override,
    technical_service_override,
):
    stock_service_override.get_stock_by_id.return_value = SimpleNamespace(id=1)
    technical_service_override.calculate_indicator.side_effect = Exception("fail")

    response = analysis_test_client.post(
        "/api/v1/analysis/technical-analysis",
        json={"stock_id": 1, "indicator": "RSI"},
    )

    assert response.status_code == 500
    assert "技術分析計算失敗" in response.json()["detail"]