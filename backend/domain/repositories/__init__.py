"""
Domain Repositories - 業務層儲存庫介面
定義業務層需要的數據訪問抽象，不依賴具體實現
"""

from .price_data_source_interface import (
    IPriceDataSource,
    PriceDataSourceError,
    SymbolNotFoundError,
    DataUnavailableError,
    RateLimitError,
    AuthenticationError,
)
from .quote_data_source_interface import IQuoteDataSource
from .market_info_provider_interface import IMarketInfoProvider
from .market_data_bar_repository_interface import IMarketDataBarRepository
from .daily_price_repository_interface import IDailyPriceRepository

__all__ = [
    "IPriceDataSource",
    "IQuoteDataSource",
    "IMarketInfoProvider",
    "IMarketDataBarRepository",
    "IDailyPriceRepository",
    "PriceDataSourceError",
    "SymbolNotFoundError",
    "DataUnavailableError",
    "RateLimitError",
    "AuthenticationError",
]
