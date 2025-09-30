"""
Pytest 配置和共享 fixtures

提供測試所需的共享資源和配置
"""
import pytest
import os
from pathlib import Path
from unittest.mock import Mock, patch

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_ROOT / ".env", override=True)

# 設定測試環境變數
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("ENV", "test")
os.environ.setdefault("DATABASE_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("APP_APP_NAME", "Test App")
os.environ.setdefault("APP_APP_VERSION", "0.0.0-test")
os.environ.setdefault("APP_APP_DEBUG", "true")
os.environ.setdefault("SECURITY_SECRET_KEY", "test-secret")


# =============================================================================
# YFinance Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_yfinance_ticker():
    """
    Mock yfinance.Ticker

    返回一個 MockTicker 實例，提供測試數據
    """
    from infrastructure.external.yfinance_wrapper import MockTicker

    def _create_ticker(symbol: str):
        return MockTicker(symbol)

    return _create_ticker


@pytest.fixture
def mock_yfinance_download():
    """Mock yfinance.download 返回模擬的歷史數據"""
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta

    def _download(tickers, start=None, end=None, **kwargs):
        if end is None:
            end_date = datetime.now()
        else:
            end_date = pd.to_datetime(end)

        if start is None:
            start_date = end_date - timedelta(days=30)
        else:
            start_date = pd.to_datetime(start)

        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        n = len(dates)
        base_price = 100

        data = {
            'Open': base_price + np.random.randn(n).cumsum() * 0.5,
            'High': base_price + np.random.randn(n).cumsum() * 0.5 + 2,
            'Low': base_price + np.random.randn(n).cumsum() * 0.5 - 2,
            'Close': base_price + np.random.randn(n).cumsum() * 0.5,
            'Volume': np.random.randint(1000000, 10000000, n),
            'Adj Close': base_price + np.random.randn(n).cumsum() * 0.5,
        }

        return pd.DataFrame(data, index=dates)

    return _download


@pytest.fixture(autouse=True)
def auto_mock_yfinance_in_tests(request):
    """
    自動在所有測試中啟用 yfinance mock 模式

    如果測試需要真實的 yfinance，可以使用 marker 排除：
    @pytest.mark.real_yfinance
    """
    if 'real_yfinance' in request.keywords:
        yield
        return

    # 啟用 mock 模式（直接設定，而非 patch）
    try:
        from infrastructure.external import yfinance_wrapper
        original_use_mock = yfinance_wrapper.use_mock
        yfinance_wrapper.use_mock = True
        yield
        yfinance_wrapper.use_mock = original_use_mock
    except ImportError:
        # 如果模組未導入，直接跳過
        yield


# =============================================================================
# Pytest 配置
# =============================================================================

def pytest_configure(config):
    """Pytest 配置"""
    config.addinivalue_line(
        "markers", "real_yfinance: 測試使用真實的 yfinance（不使用 mock）"
    )
    config.addinivalue_line(
        "markers", "slow: 標記為慢速測試"
    )
    config.addinivalue_line(
        "markers", "integration: 標記為整合測試"
    )
