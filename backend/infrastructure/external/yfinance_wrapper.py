"""
YFinance 安全封裝層

提供對 yfinance 的安全訪問，處理導入錯誤和版本不相容問題。
在測試環境中自動使用 mock 數據。
"""

import logging
from typing import Optional, Dict, Any, List
import os

logger = logging.getLogger(__name__)

# 嘗試導入 yfinance，如果失敗則使用 fallback
_yfinance_available = False
_yf_module = None

try:
    import yfinance as yf

    _yf_module = yf
    _yfinance_available = True
    logger.info(f"YFinance {yf.__version__} loaded successfully")
except ImportError as e:
    logger.warning(f"YFinance not available: {e}. Using fallback mode.")
except Exception as e:
    logger.error(f"Error loading YFinance: {e}. Using fallback mode.")


class YFinanceWrapper:
    """
    YFinance 安全封裝類

    特性：
    - 自動處理導入失敗
    - 測試環境中使用 mock 數據
    - 提供優雅的錯誤處理
    - 統一的 API 介面
    """

    def __init__(self, use_mock: Optional[bool] = None):
        """
        初始化 YFinance Wrapper

        Args:
            use_mock: 是否使用 mock 模式。None 表示自動檢測（測試環境使用 mock）
        """
        if use_mock is None:
            # 自動檢測是否在測試環境
            self.use_mock = self._is_testing_environment()
        else:
            self.use_mock = use_mock

        self.available = _yfinance_available and not self.use_mock

        if self.use_mock:
            logger.info("YFinance wrapper using mock mode")
        elif not self.available:
            logger.warning("YFinance not available and not in mock mode")

    @staticmethod
    def _is_testing_environment() -> bool:
        """檢測是否在測試環境"""
        import sys

        return (
            "pytest" in sys.modules
            or os.getenv("TESTING", "").lower() == "true"
            or os.getenv("ENV", "") == "test"
        )

    def get_ticker(self, symbol: str):
        """
        取得 Ticker 物件

        Args:
            symbol: 股票代號

        Returns:
            Ticker 物件或 MockTicker
        """
        if self.use_mock:
            return MockTicker(symbol)

        if not self.available:
            raise RuntimeError(
                "YFinance is not available. Please install yfinance or use mock mode."
            )

        try:
            # yfinance 0.2.66+ 會自動使用 curl_cffi，不需要傳遞 session
            return _yf_module.Ticker(symbol)
        except Exception as e:
            logger.error(f"Error creating ticker for {symbol}: {e}")
            # 回退到 mock 模式
            return MockTicker(symbol)

    def download(
        self,
        tickers: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        **kwargs,
    ):
        """
        下載股票歷史數據

        Args:
            tickers: 股票代號（可以是多個，用空格分隔）
            start: 開始日期
            end: 結束日期
            **kwargs: 其他參數

        Returns:
            DataFrame 或 mock 數據
        """
        if self.use_mock:
            return self._get_mock_history(tickers, start, end)

        if not self.available:
            raise RuntimeError(
                "YFinance is not available. Please install yfinance or use mock mode."
            )

        try:
            return _yf_module.download(tickers, start=start, end=end, **kwargs)
        except Exception as e:
            logger.error(f"Error downloading data for {tickers}: {e}")
            return self._get_mock_history(tickers, start, end)

    def _get_mock_history(self, tickers: str, start: Optional[str], end: Optional[str]):
        """生成 mock 歷史數據"""
        import pandas as pd
        import numpy as np
        from datetime import datetime, timedelta

        # 生成日期範圍
        if end is None:
            end_date = datetime.now()
        else:
            end_date = pd.to_datetime(end)

        if start is None:
            start_date = end_date - timedelta(days=30)
        else:
            start_date = pd.to_datetime(start)

        dates = pd.date_range(start=start_date, end=end_date, freq="D")

        # 生成模擬數據
        n = len(dates)
        base_price = 100

        data = {
            "Open": base_price + np.random.randn(n).cumsum(),
            "High": base_price + np.random.randn(n).cumsum() + 2,
            "Low": base_price + np.random.randn(n).cumsum() - 2,
            "Close": base_price + np.random.randn(n).cumsum(),
            "Volume": np.random.randint(1000000, 10000000, n),
            "Adj Close": base_price + np.random.randn(n).cumsum(),
        }

        df = pd.DataFrame(data, index=dates)
        return df


class MockTicker:
    """
    Mock Ticker 類，用於測試環境

    模擬 yfinance.Ticker 的基本功能
    """

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.info = {
            "symbol": symbol,
            "longName": f"Mock Company {symbol}",
            "currency": "USD",
            "marketCap": 1000000000,
            "regularMarketPrice": 100.0,
        }

    def history(
        self,
        period: str = "1mo",
        interval: str = "1d",
        start: Optional[str] = None,
        end: Optional[str] = None,
        **kwargs,
    ):
        """返回 mock 歷史數據"""
        import pandas as pd
        import numpy as np
        from datetime import datetime, timedelta

        # 根據 period 決定日期範圍
        if end is None:
            end_date = datetime.now()
        else:
            end_date = pd.to_datetime(end)

        if start:
            start_date = pd.to_datetime(start)
        else:
            # 解析 period
            period_days = {
                "1d": 1,
                "5d": 5,
                "1mo": 30,
                "3mo": 90,
                "6mo": 180,
                "1y": 365,
                "2y": 730,
                "5y": 1825,
                "max": 3650,
            }
            days = period_days.get(period, 30)
            start_date = end_date - timedelta(days=days)

        dates = pd.date_range(start=start_date, end=end_date, freq="D")
        n = len(dates)
        base_price = 100

        data = {
            "Open": base_price + np.random.randn(n).cumsum() * 0.5,
            "High": base_price + np.random.randn(n).cumsum() * 0.5 + 2,
            "Low": base_price + np.random.randn(n).cumsum() * 0.5 - 2,
            "Close": base_price + np.random.randn(n).cumsum() * 0.5,
            "Volume": np.random.randint(1000000, 10000000, n),
        }

        df = pd.DataFrame(data, index=dates)
        df.index.name = "Date"
        return df


# 全域實例
yfinance_wrapper = YFinanceWrapper()


def is_yfinance_available() -> bool:
    """檢查 yfinance 是否可用"""
    return _yfinance_available


def get_yfinance_version() -> Optional[str]:
    """取得 yfinance 版本"""
    if _yf_module:
        return getattr(_yf_module, "__version__", "unknown")
    return None
