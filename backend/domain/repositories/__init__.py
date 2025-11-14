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

__all__ = [
    "IPriceDataSource",
    "PriceDataSourceError",
    "SymbolNotFoundError",
    "DataUnavailableError",
    "RateLimitError",
    "AuthenticationError",
]
