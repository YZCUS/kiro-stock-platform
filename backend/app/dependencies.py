"""
依賴注入容器 - 統一服務註冊與管理
實現控制反轉 (IoC) 和依賴注入 (DI) 模式
"""
from functools import lru_cache
from typing import Generator
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.settings import Settings, get_settings


# =============================================================================
# 基礎依賴 (暫時使用簡化版本，逐步遷移)
# =============================================================================

async def get_database_session() -> Generator[AsyncSession, None, None]:
    """取得資料庫會話 (暫時保持現有實現)"""
    # 這裡暫時import現有的實現，後續會重構
    from core.database import get_db_session
    async for session in get_db_session():
        yield session


@lru_cache()
def get_redis_client(settings: Settings = Depends(get_settings)):
    """取得 Redis 客戶端"""
    import redis

    try:
        client = redis.Redis(
            host=settings.redis.host,
            port=settings.redis.port,
            db=settings.redis.db,
            password=settings.redis.password,
            decode_responses=True,
            socket_timeout=settings.redis.socket_timeout
        )
        # 測試連接
        client.ping()
        return client
    except Exception as e:
        print(f"Redis 連接失敗: {e}")
        return None


# =============================================================================
# 快取服務
# =============================================================================

class SimpleCacheService:
    """簡化的快取服務 (過渡期使用)"""

    def __init__(self, redis_client, redis_settings):
        self.redis_client = redis_client
        self.settings = redis_settings

    def get_cache_key(self, prefix: str, **kwargs) -> str:
        """生成快取鍵"""
        key_parts = [prefix]
        for key, value in kwargs.items():
            if value is not None:
                key_parts.append(f"{key}:{value}")
        return ":".join(key_parts)

    async def get(self, key: str):
        """取得快取數據"""
        if not self.redis_client:
            return None
        try:
            import json
            data = self.redis_client.get(key)
            return json.loads(data) if data else None
        except Exception:
            return None

    async def set(self, key: str, value, ttl: int = None):
        """設置快取數據"""
        if not self.redis_client:
            return
        try:
            import json
            ttl = ttl or self.settings.default_ttl
            self.redis_client.setex(key, ttl, json.dumps(value, ensure_ascii=False))
        except Exception:
            pass


def get_cache_service(
    settings: Settings = Depends(get_settings),
    redis_client=Depends(get_redis_client)
) -> SimpleCacheService:
    """取得快取服務"""
    return SimpleCacheService(redis_client, settings.redis)


# =============================================================================
# Domain Services 依賴 (Clean Architecture實現)
# =============================================================================

def get_stock_service(
    stock_repo: 'IStockRepository' = Depends(get_stock_repository),
    price_repo: 'IPriceHistoryRepository' = Depends(get_price_history_repository_clean),
    cache_service: SimpleCacheService = Depends(get_cache_service)
) -> 'StockService':
    """取得股票業務服務 (Clean Architecture版本)"""
    from domain.services.stock_service import StockService

    return StockService(stock_repo, price_repo, cache_service)

def get_technical_analysis_service_clean(
    stock_repo: 'IStockRepository' = Depends(get_stock_repository),
    price_repo: 'IPriceHistoryRepository' = Depends(get_price_history_repository_clean),
    cache_service: SimpleCacheService = Depends(get_cache_service)
) -> 'TechnicalAnalysisService':
    """取得技術分析服務 (Clean Architecture版本)"""
    from domain.services.technical_analysis_service import TechnicalAnalysisService

    return TechnicalAnalysisService(stock_repo, price_repo, cache_service)

def get_data_collection_service_clean(
    stock_repo: 'IStockRepository' = Depends(get_stock_repository),
    price_repo: 'IPriceHistoryRepository' = Depends(get_price_history_repository_clean),
    cache_service: SimpleCacheService = Depends(get_cache_service)
) -> 'DataCollectionService':
    """取得數據收集服務 (Clean Architecture版本)"""
    from domain.services.data_collection_service import DataCollectionService

    return DataCollectionService(stock_repo, price_repo, cache_service)

def get_trading_signal_service_clean(
    stock_repo: 'IStockRepository' = Depends(get_stock_repository),
    price_repo: 'IPriceHistoryRepository' = Depends(get_price_history_repository_clean),
    cache_service: SimpleCacheService = Depends(get_cache_service)
) -> 'TradingSignalService':
    """取得交易信號服務 (Clean Architecture版本)"""
    from domain.services.trading_signal_service import TradingSignalService

    return TradingSignalService(stock_repo, price_repo, cache_service)

# =============================================================================
# 現有服務的依賴 (逐步重構)
# =============================================================================

def get_technical_analysis_service():
    """取得技術分析服務 (暫時保持現有實現)"""
    from services.analysis.technical_analysis import TechnicalAnalysisService
    return TechnicalAnalysisService()


def get_data_collection_service():
    """取得數據收集服務 (暫時保持現有實現)"""
    from services.data.collection import data_collection_service
    return data_collection_service


def get_data_validation_service():
    """取得數據驗證服務 (暫時保持現有實現)"""
    from services.data.validation import data_validation_service
    return data_validation_service


# =============================================================================
# Repository 依賴 (新的Clean Architecture實現)
# =============================================================================

def get_stock_repository(
    db: AsyncSession = Depends(get_database_session)
) -> 'IStockRepository':
    """取得股票儲存庫 (Clean Architecture版本)"""
    from domain.repositories.stock_repository_interface import IStockRepository
    from infrastructure.persistence.stock_repository import StockRepository

    return StockRepository(db)

def get_price_history_repository_clean(
    db: AsyncSession = Depends(get_database_session)
) -> 'IPriceHistoryRepository':
    """取得價格歷史儲存庫 (Clean Architecture版本)"""
    from domain.repositories.price_history_repository_interface import IPriceHistoryRepository
    from infrastructure.persistence.price_history_repository import PriceHistoryRepository

    return PriceHistoryRepository(db)

def get_stock_repository_legacy():
    """取得股票儲存庫 (Legacy版本，過渡期使用)"""
    from models.repositories.crud_stock import stock_crud
    return stock_crud


def get_price_history_repository():
    """取得價格歷史儲存庫"""
    from models.repositories.crud_price_history import price_history_crud
    return price_history_crud


def get_technical_indicator_repository():
    """取得技術指標儲存庫"""
    from models.repositories.crud_technical_indicator import technical_indicator_crud
    return technical_indicator_crud


def get_trading_signal_repository():
    """取得交易信號儲存庫"""
    from models.repositories.crud_trading_signal import trading_signal_crud
    return trading_signal_crud