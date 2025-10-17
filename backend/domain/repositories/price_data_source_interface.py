"""
價格數據源接口 - Domain Layer

定義統一的價格數據源接口，支持多種數據提供商（Yahoo Finance、Alpha Vantage、FMP 等）
遵循依賴倒置原則，業務邏輯依賴於抽象接口而非具體實現
"""
from abc import ABC, abstractmethod
from datetime import date
from typing import List, Dict, Any, Optional


class IPriceDataSource(ABC):
    """價格數據源抽象接口"""

    @abstractmethod
    async def fetch_historical_prices(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        market: str = "US"
    ) -> List[Dict[str, Any]]:
        """
        獲取歷史價格數據

        Args:
            symbol: 股票代碼
            start_date: 開始日期
            end_date: 結束日期（inclusive）
            market: 市場代碼（US, TW 等）

        Returns:
            List[Dict] 包含以下鍵值：
            - date: datetime.date - 日期
            - open: float - 開盤價
            - high: float - 最高價
            - low: float - 最低價
            - close: float - 收盤價
            - volume: int - 成交量
            - adj_close: float - 調整後收盤價

        Raises:
            ValueError: 股票代碼無效或日期範圍錯誤
            Exception: 數據獲取失敗
        """
        pass

    @abstractmethod
    async def fetch_historical_prices_by_period(
        self,
        symbol: str,
        period: str,
        market: str = "US"
    ) -> List[Dict[str, Any]]:
        """
        使用 period 參數獲取歷史價格數據

        Args:
            symbol: 股票代碼
            period: 時間週期（如 '1d', '5d', '1mo', '1y' 等）
            market: 市場代碼（US, TW 等）

        Returns:
            List[Dict] 格式同 fetch_historical_prices

        Raises:
            ValueError: 股票代碼無效或 period 參數錯誤
            Exception: 數據獲取失敗
        """
        pass

    @abstractmethod
    async def validate_symbol(
        self,
        symbol: str,
        market: str = "US"
    ) -> bool:
        """
        驗證股票代碼是否有效

        Args:
            symbol: 股票代碼
            market: 市場代碼（US, TW 等）

        Returns:
            bool: True 表示有效，False 表示無效

        Note:
            此方法會嘗試獲取少量數據來驗證股票是否存在且可交易
        """
        pass

    @abstractmethod
    async def get_stock_info(
        self,
        symbol: str,
        market: str = "US"
    ) -> Dict[str, Any]:
        """
        獲取股票基本資訊

        Args:
            symbol: 股票代碼
            market: 市場代碼（US, TW 等）

        Returns:
            Dict 包含以下鍵值（根據數據源可能不同）：
            - long_name: str - 公司全名
            - short_name: str - 公司簡稱
            - sector: str - 所屬行業
            - industry: str - 所屬產業
            - market_cap: float - 市值
            - currency: str - 貨幣單位
            - exchange: str - 交易所

        Raises:
            ValueError: 股票代碼無效
            Exception: 數據獲取失敗
        """
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """
        返回數據源名稱

        Returns:
            str: 數據源名稱（如 'yahoo_finance', 'alpha_vantage'）
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        檢查數據源是否可用

        Returns:
            bool: True 表示數據源可用，False 表示不可用

        Note:
            用於檢查 API 密鑰、網絡連接、配額限制等
        """
        pass


class PriceDataSourceError(Exception):
    """價格數據源通用錯誤"""
    pass


class SymbolNotFoundError(PriceDataSourceError):
    """股票代碼不存在錯誤"""
    pass


class DataUnavailableError(PriceDataSourceError):
    """數據不可用錯誤（可能是非交易日、數據延遲等）"""
    pass


class RateLimitError(PriceDataSourceError):
    """API 調用頻率限制錯誤"""
    pass


class AuthenticationError(PriceDataSourceError):
    """認證失敗錯誤（API 密鑰無效等）"""
    pass
