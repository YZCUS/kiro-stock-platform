"""
Infrastructure - Cache Layer
集中管理所有快取相關功能
"""

# 核心介面和實現
from .unified_cache_service import (
    ICacheService,
    RedisCacheService,
    MockCacheService,
    StockCacheService,
    TechnicalAnalysisCacheService,
    TradingSignalCacheService,
    DataCollectionCacheService,
)

# 向後兼容
from .redis_cache_service import MockCacheService as LegacyMockCacheService

__all__ = [
    "ICacheService",
    "RedisCacheService",
    "MockCacheService",
    "StockCacheService",
    "TechnicalAnalysisCacheService",
    "TradingSignalCacheService",
    "DataCollectionCacheService",
]
