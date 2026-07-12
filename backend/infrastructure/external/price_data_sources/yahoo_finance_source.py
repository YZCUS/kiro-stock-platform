"""
Yahoo Finance 數據源實現

使用 yfinance 庫作為價格數據源的具體實現。
"""

import logging
from datetime import date, datetime, time, timedelta
from typing import Dict, Any, List, Optional
import asyncio
import pandas as pd
from zoneinfo import ZoneInfo

from domain.repositories.price_data_source_interface import (
    IPriceDataSource,
    SymbolNotFoundError,
    DataUnavailableError,
    PriceDataSourceError,
)
from infrastructure.external.yfinance_wrapper import yfinance_wrapper

logger = logging.getLogger(__name__)


class YahooFinanceSource(IPriceDataSource):
    """
    Yahoo Finance 數據源實現

    使用 yfinance 提供股票價格數據。
    """

    def __init__(self):
        """初始化 Yahoo Finance 數據源"""
        self.wrapper = yfinance_wrapper
        self._source_name = "Yahoo Finance"

    async def fetch_historical_prices(
        self, symbol: str, start_date: date, end_date: date, market: str = "US"
    ) -> List[Dict[str, Any]]:
        """
        獲取指定日期範圍的歷史價格

        Args:
            symbol: 股票代碼
            start_date: 起始日期
            end_date: 結束日期
            market: 市場類型 ("US" 或 "TW")

        Returns:
            List[Dict]: 價格數據列表，每個字典包含:
                - date: 日期
                - open: 開盤價
                - high: 最高價
                - low: 最低價
                - close: 收盤價
                - volume: 成交量
                - adj_close: 調整後收盤價

        Raises:
            SymbolNotFoundError: 股票代碼不存在
            DataUnavailableError: 數據不可用
            PriceDataSourceError: 其他錯誤
        """
        try:
            # 格式化股票代碼
            formatted_symbol = self._format_symbol(symbol, market)

            # Yahoo Finance 的 end 參數是 exclusive，需要加1天
            end_date_inclusive = end_date + timedelta(days=1)

            # 在執行器中運行同步操作
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(
                None,
                lambda: self.wrapper.get_ticker(formatted_symbol).history(
                    start=start_date.isoformat(), end=end_date_inclusive.isoformat()
                ),
            )

            if df.empty:
                raise DataUnavailableError(
                    f"No data available for {formatted_symbol} "
                    f"between {start_date} and {end_date}"
                )

            # 轉換 DataFrame 為標準格式
            return self._dataframe_to_dict_list(df)

        except DataUnavailableError:
            raise
        except Exception as e:
            logger.error(f"Error fetching historical prices for {symbol}: {e}")
            raise PriceDataSourceError(
                f"Failed to fetch historical prices for {symbol}: {str(e)}"
            ) from e

    async def fetch_historical_prices_by_period(
        self, symbol: str, period: str, market: str = "US"
    ) -> List[Dict[str, Any]]:
        """
        使用預設時間段獲取歷史價格

        Args:
            symbol: 股票代碼
            period: 時間段 (如 "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max")
            market: 市場類型

        Returns:
            List[Dict]: 價格數據列表

        Raises:
            SymbolNotFoundError: 股票代碼不存在
            DataUnavailableError: 數據不可用
            PriceDataSourceError: 其他錯誤
        """
        try:
            formatted_symbol = self._format_symbol(symbol, market)

            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(
                None,
                lambda: self.wrapper.get_ticker(formatted_symbol).history(
                    period=period
                ),
            )

            if df.empty:
                raise DataUnavailableError(
                    f"No data available for {formatted_symbol} with period {period}"
                )

            return self._dataframe_to_dict_list(df)

        except DataUnavailableError:
            raise
        except Exception as e:
            logger.error(f"Error fetching prices by period for {symbol}: {e}")
            raise PriceDataSourceError(
                f"Failed to fetch prices by period for {symbol}: {str(e)}"
            ) from e

    async def fetch_bars(
        self,
        symbol: str,
        timeframe: str,
        start_at: datetime,
        end_at: datetime,
        market: str = "US",
    ) -> List[Dict[str, Any]]:
        """Fetch normalized OHLCV bars for a supported timeframe."""
        try:
            formatted_symbol = self._format_symbol(symbol, market)
            interval = self._map_timeframe_to_interval(timeframe)
            # yfinance's date parser is strict for history(start=..., end=...).
            # Date-only strings work for both daily and intraday intervals.
            start_arg = start_at.date().isoformat()
            end_arg = (end_at.date() + timedelta(days=1)).isoformat()

            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(
                None,
                lambda: self.wrapper.get_ticker(formatted_symbol).history(
                    start=start_arg,
                    end=end_arg,
                    interval=interval,
                ),
            )

            if df.empty:
                raise DataUnavailableError(
                    f"No {timeframe} bars available for {formatted_symbol} "
                    f"between {start_at} and {end_at}"
                )

            bars = self._dataframe_to_bar_dict_list(df, market, timeframe)
            market_tz = self._market_timezone(market)
            window_start = self._ensure_market_timezone(start_at, market_tz)
            window_end = self._ensure_market_timezone(end_at, market_tz)
            return [
                bar for bar in bars if window_start <= bar["timestamp"] < window_end
            ]

        except DataUnavailableError:
            raise
        except Exception as e:
            logger.error(f"Error fetching {timeframe} bars for {symbol}: {e}")
            raise PriceDataSourceError(
                f"Failed to fetch {timeframe} bars for {symbol}: {str(e)}"
            ) from e

    async def validate_symbol(self, symbol: str, market: str = "US") -> bool:
        """
        驗證股票代碼是否有效

        Args:
            symbol: 股票代碼
            market: 市場類型

        Returns:
            bool: 股票代碼是否有效
        """
        try:
            formatted_symbol = self._format_symbol(symbol, market)

            loop = asyncio.get_event_loop()
            ticker = await loop.run_in_executor(
                None, lambda: self.wrapper.get_ticker(formatted_symbol)
            )

            # 嘗試獲取短期歷史數據來驗證
            hist = await loop.run_in_executor(None, lambda: ticker.history(period="5d"))

            return not hist.empty

        except Exception as e:
            logger.warning(f"Symbol validation failed for {symbol}: {e}")
            return False

    async def get_stock_info(self, symbol: str, market: str = "US") -> Dict[str, Any]:
        """
        獲取股票基本資訊

        Args:
            symbol: 股票代碼
            market: 市場類型

        Returns:
            Dict: 股票資訊，可能包含:
                - long_name: 完整公司名稱
                - short_name: 簡稱
                - sector: 產業類別
                - industry: 行業
                - market_cap: 市值
                - currency: 貨幣

        Raises:
            SymbolNotFoundError: 股票代碼不存在
            PriceDataSourceError: 其他錯誤
        """
        try:
            formatted_symbol = self._format_symbol(symbol, market)

            loop = asyncio.get_event_loop()
            ticker = await loop.run_in_executor(
                None, lambda: self.wrapper.get_ticker(formatted_symbol)
            )

            if not hasattr(ticker, "info") or not ticker.info:
                raise SymbolNotFoundError(f"Stock info not available for {symbol}")

            # 轉換為標準格式
            info = ticker.info
            return {
                "long_name": info.get("longName"),
                "short_name": info.get("shortName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "market_cap": info.get("marketCap"),
                "currency": info.get("currency"),
                "website": info.get("website"),
                "description": info.get("longBusinessSummary"),
            }

        except SymbolNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error fetching stock info for {symbol}: {e}")
            raise PriceDataSourceError(
                f"Failed to fetch stock info for {symbol}: {str(e)}"
            ) from e

    def get_source_name(self) -> str:
        """
        獲取數據源名稱

        Returns:
            str: 數據源名稱
        """
        return self._source_name

    def is_available(self) -> bool:
        """
        檢查數據源是否可用

        Returns:
            bool: 數據源是否可用
        """
        return self.wrapper.available or self.wrapper.use_mock

    def _format_symbol(self, symbol: str, market: str) -> str:
        """
        根據市場格式化股票代碼

        Args:
            symbol: 原始股票代碼
            market: 市場類型

        Returns:
            str: 格式化後的股票代碼
        """
        if market == "TW":
            # 台股需要加上 .TW 後綴
            if not symbol.endswith(".TW") and not symbol.endswith(".TWO"):
                return f"{symbol}.TW"
        return symbol

    def _dataframe_to_dict_list(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        將 Pandas DataFrame 轉換為字典列表

        Args:
            df: Pandas DataFrame

        Returns:
            List[Dict]: 標準化的價格數據列表
        """
        result = []

        for idx, row in df.iterrows():
            # 處理日期索引
            if isinstance(idx, (datetime, pd.Timestamp)):
                date_value = idx.date()
            else:
                date_value = idx

            price_data = {
                "date": date_value,
                "open": float(row.get("Open", 0)),
                "high": float(row.get("High", 0)),
                "low": float(row.get("Low", 0)),
                "close": float(row.get("Close", 0)),
                "volume": int(row.get("Volume", 0)),
                "adj_close": float(row.get("Adj Close", row.get("Close", 0))),
            }
            result.append(price_data)

        return result

    def _dataframe_to_bar_dict_list(
        self, df: pd.DataFrame, market: str, timeframe: str
    ) -> List[Dict[str, Any]]:
        """Convert a yfinance DataFrame into normalized bar records."""
        result = []

        for idx, row in df.iterrows():
            result.append(
                {
                    "timestamp": self._normalize_bar_timestamp(idx, market, timeframe),
                    "open": float(row.get("Open", 0)),
                    "high": float(row.get("High", 0)),
                    "low": float(row.get("Low", 0)),
                    "close": float(row.get("Close", 0)),
                    "volume": int(row.get("Volume", 0)),
                    "adj_close": float(row.get("Adj Close", row.get("Close", 0))),
                }
            )

        return result

    def _normalize_bar_timestamp(
        self, index_value, market: str, timeframe: str
    ) -> datetime:
        market_tz = self._market_timezone(market)

        if isinstance(index_value, pd.Timestamp):
            timestamp = index_value.to_pydatetime()
        elif isinstance(index_value, datetime):
            timestamp = index_value
        else:
            timestamp = pd.to_datetime(index_value).to_pydatetime()

        if timeframe in {"1d", "1w"}:
            local_date = timestamp.date()
            return datetime.combine(local_date, time.min, tzinfo=market_tz)

        if timestamp.tzinfo is None:
            return timestamp.replace(tzinfo=market_tz)
        return timestamp.astimezone(market_tz)

    def _map_timeframe_to_interval(self, timeframe: str) -> str:
        interval_map = {
            "1m": "1m",
            "5m": "5m",
            "15m": "15m",
            "30m": "30m",
            "1h": "60m",
            "1d": "1d",
            "1w": "1wk",
        }
        if timeframe not in interval_map:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        return interval_map[timeframe]

    def _market_timezone(self, market: str) -> ZoneInfo:
        if market == "TW":
            return ZoneInfo("Asia/Taipei")
        return ZoneInfo("America/New_York")

    def _ensure_market_timezone(
        self,
        value: datetime,
        market_timezone: ZoneInfo,
    ) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=market_timezone)
        return value.astimezone(market_timezone)
