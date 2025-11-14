"""
依賴注入容器 - 統一服務註冊與管理
實現控制反轉 (IoC) 和依賴注入 (DI) 模式
"""
from __future__ import annotations

from functools import lru_cache
from typing import Generator, Optional, TYPE_CHECKING
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

if TYPE_CHECKING:
    from domain.repositories.price_data_source_interface import IPriceDataSource
    from domain.repositories.stock_repository_interface import IStockRepository
    from domain.repositories.price_history_repository_interface import IPriceHistoryRepository
    from domain.repositories.technical_indicator_repository_interface import ITechnicalIndicatorRepository
    from domain.repositories.trading_signal_repository_interface import ITradingSignalRepository
    from domain.services.stock_service import StockService
    from domain.services.technical_analysis_service import TechnicalAnalysisService
    from domain.services.data_collection_service import DataCollectionService
    from domain.services.trading_signal_service import TradingSignalService
    from domain.services.data_validation_service import DataValidationService
    from infrastructure.realtime.websocket_service import WebSocketService

from app.settings import Settings, get_settings
from infrastructure.cache.redis_cache_service import RedisCacheService, ICacheService
from infrastructure.realtime.websocket_manager import (
    IWebSocketManager,
    RedisBackedWebSocketManager,
    SimpleWebSocketManager,
)
from infrastructure.realtime.redis_pubsub import redis_broadcaster


# =============================================================================
# 基礎依賴 (暫時使用簡化版本，逐步遷移)
# =============================================================================

async def get_database_session() -> Generator[AsyncSession, None, None]:
    """取得資料庫會話 (暫時保持現有實現)"""
    # 這裡暫時import現有的實現，後續會重構
    from core.database import get_db_session
    async for session in get_db_session():
        yield session


# Redis 客戶端單例
_redis_client_singleton = None


def get_redis_client(settings: Settings = Depends(get_settings)):
    """取得 Redis 客戶端（單例模式）"""
    global _redis_client_singleton

    if _redis_client_singleton is not None:
        return _redis_client_singleton

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
        _redis_client_singleton = client
        return client
    except Exception as e:
        print(f"Redis 連接失敗: {e}")
        return None


# =============================================================================
# 快取服務 (Clean Architecture)
# =============================================================================

# CacheService 單例
_cache_service_singleton: Optional[ICacheService] = None


def get_cache_service(
    settings: Settings = Depends(get_settings),
    redis_client=Depends(get_redis_client)
) -> ICacheService:
    """取得統一快取服務（單例模式）"""
    global _cache_service_singleton

    if _cache_service_singleton is not None:
        return _cache_service_singleton

    _cache_service_singleton = RedisCacheService(redis_client, settings.redis)
    return _cache_service_singleton

_websocket_manager_singleton: Optional[IWebSocketManager] = None


def get_websocket_manager(settings: Optional[Settings] = None) -> IWebSocketManager:
    """取得全域 WebSocket 管理器實例，支援 DI 與外部呼叫"""
    global _websocket_manager_singleton

    if _websocket_manager_singleton is not None:
        return _websocket_manager_singleton

    if settings is None:
        settings = get_settings()

    if settings.app.debug:
        _websocket_manager_singleton = SimpleWebSocketManager()
    else:
        _websocket_manager_singleton = RedisBackedWebSocketManager(redis_broadcaster)

    return _websocket_manager_singleton


def provide_websocket_manager(
    settings: Settings = Depends(get_settings),
) -> IWebSocketManager:
    """FastAPI 專用的 WebSocket 管理器依賴提供函式"""
    return get_websocket_manager(settings)


# =============================================================================
# Price Data Source 依賴
# =============================================================================

def get_price_data_source(
    settings: Settings = Depends(get_settings)
) -> 'IPriceDataSource':
    """取得價格數據源 (根據環境變數配置)"""
    from domain.repositories.price_data_source_interface import IPriceDataSource
    from infrastructure.external.price_data_sources import YahooFinanceSource

    # 根據配置選擇數據源
    source_type = settings.external_api.price_data_source.lower()

    if source_type == "yahoo_finance":
        return YahooFinanceSource()
    # elif source_type == "alpha_vantage":
    #     from infrastructure.external.price_data_sources import AlphaVantageSource
    #     return AlphaVantageSource()
    # elif source_type == "fmp":
    #     from infrastructure.external.price_data_sources import FMPSource
    #     return FMPSource()
    else:
        # 預設使用 Yahoo Finance
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Unknown price data source: {source_type}, using Yahoo Finance as default")
        return YahooFinanceSource()


# =============================================================================
# Repository 依賴 (新的Clean Architecture實現)
# =============================================================================

def get_stock_repository(
    db: AsyncSession = Depends(get_database_session),
    price_data_source: 'IPriceDataSource' = Depends(get_price_data_source)
) -> 'IStockRepository':
    """取得股票儲存庫 (Clean Architecture版本)"""
    from domain.repositories.stock_repository_interface import IStockRepository
    from infrastructure.persistence.stock_repository import StockRepository

    return StockRepository(db, price_data_source)

def get_price_history_repository_clean(
    db: AsyncSession = Depends(get_database_session)
) -> 'IPriceHistoryRepository':
    """取得價格歷史儲存庫 (Clean Architecture版本)"""
    from domain.repositories.price_history_repository_interface import IPriceHistoryRepository
    from infrastructure.persistence.price_history_repository import PriceHistoryRepository

    return PriceHistoryRepository(db)


def get_technical_indicator_repository_clean(
    db: AsyncSession = Depends(get_database_session)
) -> 'ITechnicalIndicatorRepository':
    """取得技術指標儲存庫 (Clean Architecture版本)"""
    from domain.repositories.technical_indicator_repository_interface import ITechnicalIndicatorRepository
    from infrastructure.persistence.technical_indicator_repository import TechnicalIndicatorRepository

    return TechnicalIndicatorRepository(db)


def get_trading_signal_repository_clean(
    db: AsyncSession = Depends(get_database_session)
) -> 'ITradingSignalRepository':
    """取得交易信號儲存庫 (Clean Architecture版本)"""
    from domain.repositories.trading_signal_repository_interface import ITradingSignalRepository
    from infrastructure.persistence.trading_signal_repository import TradingSignalRepository

    return TradingSignalRepository(db)


# =============================================================================
# Domain Services 依賴 (Clean Architecture實現)
# =============================================================================

def get_stock_service(
    stock_repo: 'IStockRepository' = Depends(get_stock_repository),
    price_repo: 'IPriceHistoryRepository' = Depends(get_price_history_repository_clean),
    cache_service: ICacheService = Depends(get_cache_service)
) -> 'StockService':
    """取得股票業務服務 (Clean Architecture版本)"""
    from domain.services.stock_service import StockService

    return StockService(stock_repo, price_repo, cache_service)


def get_technical_analysis_service_clean(
    stock_repo: 'IStockRepository' = Depends(get_stock_repository),
    price_repo: 'IPriceHistoryRepository' = Depends(get_price_history_repository_clean),
    cache_service: ICacheService = Depends(get_cache_service)
) -> 'TechnicalAnalysisService':
    """取得技術分析服務 (Clean Architecture版本)"""
    from domain.services.technical_analysis_service import TechnicalAnalysisService

    return TechnicalAnalysisService(stock_repo, price_repo, cache_service)


def get_data_collection_service_clean(
    stock_repo: 'IStockRepository' = Depends(get_stock_repository),
    price_repo: 'IPriceHistoryRepository' = Depends(get_price_history_repository_clean),
    cache_service: ICacheService = Depends(get_cache_service),
    price_data_source: 'IPriceDataSource' = Depends(get_price_data_source)
) -> 'DataCollectionService':
    """取得數據收集服務 (Clean Architecture版本)"""
    from domain.services.data_collection_service import DataCollectionService

    return DataCollectionService(stock_repo, price_repo, cache_service, price_data_source)


def get_trading_signal_service_clean(
    stock_repo: 'IStockRepository' = Depends(get_stock_repository),
    price_repo: 'IPriceHistoryRepository' = Depends(get_price_history_repository_clean),
    cache_service: ICacheService = Depends(get_cache_service),
    signal_repo: 'ITradingSignalRepository' = Depends(get_trading_signal_repository_clean)
) -> 'TradingSignalService':
    """取得交易信號服務 (Clean Architecture版本)"""
    from domain.services.trading_signal_service import TradingSignalService

    return TradingSignalService(stock_repo, price_repo, cache_service, signal_repo)


def get_data_validation_service_clean(
    stock_repo: 'IStockRepository' = Depends(get_stock_repository),
    price_repo: 'IPriceHistoryRepository' = Depends(get_price_history_repository_clean),
    cache_service: ICacheService = Depends(get_cache_service)
) -> 'DataValidationService':
    """取得數據驗證服務 (Clean Architecture版本)"""
    from domain.services.data_validation_service import DataValidationService

    return DataValidationService(stock_repo, price_repo, cache_service)


# =============================================================================
# WebSocket Services 依賴
# =============================================================================

# WebSocketService 的全域單例實例
_websocket_service_singleton: Optional['WebSocketService'] = None


def get_websocket_service() -> 'WebSocketService':
    """
    取得 WebSocket 服務 (全域單例模式)

    重要：WebSocketService 應該是單例的，所有 WebSocket 連線共享同一個實例。
    這避免了為每個連線創建新的服務實例，大幅降低記憶體使用。

    架構說明：
    - WebSocketService 本身是單例
    - stock_service 和 trading_signal_service 也應該是單例
    - 但它們依賴 Repository（需要 db session 進行操作）
    - Repository 是輕量級的（只包含查詢邏輯，不持有狀態）
    - 每次資料庫操作時，db session 作為參數傳入

    因此，單例策略：
    1. WebSocketService: 單例 ✓
    2. StockService/TradingSignalService: 單例 ✓
    3. Repository: 輕量級，可以是單例 ✓
    4. CacheService: 單例 ✓
    5. WebSocketManager: 單例 ✓
    6. DB Session: 每個請求獨立 ✓
    """
    global _websocket_service_singleton

    if _websocket_service_singleton is None:
        from api.v1.websocket import WebSocketService
        from domain.services.stock_service import StockService
        from domain.services.trading_signal_service import TradingSignalService
        from infrastructure.persistence.stock_repository import StockRepository
        from infrastructure.persistence.price_history_repository import PriceHistoryRepository
        from infrastructure.persistence.trading_signal_repository import TradingSignalRepository

        # 獲取單例依賴
        settings = get_settings()
        cache_service = get_cache_service(settings, get_redis_client(settings))
        websocket_manager = get_websocket_manager(settings)

        # 創建 Repository 單例（輕量級，只包含查詢邏輯）
        # 注意：Repository 的 __init__ 不持有 db，db 在每個方法調用時傳入
        stock_repo = StockRepository(db_session=None)  # db 會在調用時傳入
        price_repo = PriceHistoryRepository(db_session=None)
        signal_repo = TradingSignalRepository(db_session=None)

        # 創建 Service 單例
        stock_service = StockService(stock_repo, price_repo, cache_service)
        trading_signal_service = TradingSignalService(
            stock_repo, price_repo, cache_service, signal_repo
        )

        # 創建 WebSocketService 單例
        _websocket_service_singleton = WebSocketService(
            stock_service=stock_service,
            trading_signal_service=trading_signal_service,
            websocket_manager=websocket_manager,
            cache_service=cache_service
        )

    return _websocket_service_singleton