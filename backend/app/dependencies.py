"""
依賴注入容器 - 統一服務註冊與管理
實現控制反轉 (IoC) 和依賴注入 (DI) 模式
"""
from functools import lru_cache
from typing import Generator, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

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


def get_trading_signal_repository_clean(
    db: AsyncSession = Depends(get_database_session)
) -> 'ITradingSignalRepository':
    """取得交易信號儲存庫 (Clean Architecture版本)"""
    from domain.repositories.trading_signal_repository_interface import ITradingSignalRepository
    from infrastructure.persistence.trading_signal_repository import TradingSignalRepository

    return TradingSignalRepository(db)


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
    cache_service: ICacheService = Depends(get_cache_service)
) -> 'DataCollectionService':
    """取得數據收集服務 (Clean Architecture版本)"""
    from domain.services.data_collection_service import DataCollectionService

    return DataCollectionService(stock_repo, price_repo, cache_service)


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
        stock_repo = StockRepository(db=None)  # db 會在調用時傳入
        price_repo = PriceHistoryRepository(db=None)
        signal_repo = TradingSignalRepository(db=None)

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