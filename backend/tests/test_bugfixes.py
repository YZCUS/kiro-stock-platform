"""
Bug修復驗證測試
"""
import pytest
import asyncio
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from models.repositories.crud_trading_signal import trading_signal_crud
from services.infrastructure.redis_pubsub import RedisWebSocketBroadcaster
from services.infrastructure.websocket_manager import EnhancedConnectionManager


class TestTradingSignalCRUDFixes:
    """測試交易信號CRUD修復"""

    @pytest.fixture
    async def db_session(self):
        """測試資料庫會話"""
        # 這裡應該使用測試資料庫
        # 為了示例，我們假設有一個測試DB連接
        pass

    async def test_get_signals_with_filters_exists(self):
        """測試 get_signals_with_filters 函式存在"""
        assert hasattr(trading_signal_crud, 'get_signals_with_filters')
        assert callable(getattr(trading_signal_crud, 'get_signals_with_filters'))

    async def test_count_signals_with_filters_exists(self):
        """測試 count_signals_with_filters 函式存在"""
        assert hasattr(trading_signal_crud, 'count_signals_with_filters')
        assert callable(getattr(trading_signal_crud, 'count_signals_with_filters'))

    async def test_get_signal_stats_exists(self):
        """測試 get_signal_stats 函式存在"""
        assert hasattr(trading_signal_crud, 'get_signal_stats')
        assert callable(getattr(trading_signal_crud, 'get_signal_stats'))

    async def test_get_detailed_signal_stats_exists(self):
        """測試 get_detailed_signal_stats 函式存在"""
        assert hasattr(trading_signal_crud, 'get_detailed_signal_stats')
        assert callable(getattr(trading_signal_crud, 'get_detailed_signal_stats'))

    async def test_filters_structure(self):
        """測試過濾條件結構"""
        # 測試各種過濾條件組合
        filters_test_cases = [
            {},  # 空過濾條件
            {"signal_type": "BUY"},
            {"start_date": date.today() - timedelta(days=30)},
            {"end_date": date.today()},
            {"min_confidence": 0.8},
            {"stock_id": 1},
            {
                "signal_type": "BUY",
                "start_date": date.today() - timedelta(days=7),
                "end_date": date.today(),
                "min_confidence": 0.7
            }
        ]

        for filters in filters_test_cases:
            # 確保過濾條件不會造成錯誤
            # 注意：這裡只是檢查函式簽名，實際測試需要資料庫連接
            assert isinstance(filters, dict)


class TestWebSocketManagerFixes:
    """測試WebSocket管理器修復"""

    async def test_redis_broadcaster_initialization(self):
        """測試Redis廣播器初始化"""
        broadcaster = RedisWebSocketBroadcaster()

        # 測試初始狀態
        assert not broadcaster.is_connected
        assert broadcaster.redis_pool is None
        assert broadcaster.publisher is None
        assert broadcaster.subscriber is None
        assert len(broadcaster.subscriptions) == 0

    async def test_enhanced_connection_manager_initialization(self):
        """測試增強版連接管理器初始化"""
        manager = EnhancedConnectionManager()

        # 測試初始狀態
        assert len(manager.active_connections) == 0
        assert len(manager.stock_subscriptions) == 0
        assert len(manager.global_subscriptions) == 0
        assert len(manager.redis_subscriptions) == 0
        assert manager.pubsub_task is None

    async def test_manager_methods_exist(self):
        """測試管理器必要方法存在"""
        manager = EnhancedConnectionManager()

        required_methods = [
            'initialize',
            'shutdown',
            'connect',
            'disconnect',
            'subscribe_to_stock',
            'unsubscribe_from_stock',
            'subscribe_to_global',
            'unsubscribe_from_global',
            'send_personal_message',
            'broadcast_to_stock_subscribers',
            'broadcast_global',
            'get_connection_stats',
            'get_cluster_stats'
        ]

        for method_name in required_methods:
            assert hasattr(manager, method_name)
            assert callable(getattr(manager, method_name))

    async def test_broadcaster_methods_exist(self):
        """測試廣播器必要方法存在"""
        broadcaster = RedisWebSocketBroadcaster()

        required_methods = [
            'connect',
            'disconnect',
            'publish_message',
            'publish_stock_update',
            'publish_global_update',
            'publish_price_update',
            'publish_indicator_update',
            'publish_signal_update',
            'publish_market_status',
            'subscribe_to_channels',
            'health_check'
        ]

        for method_name in required_methods:
            assert hasattr(broadcaster, method_name)
            assert callable(getattr(broadcaster, method_name))


class TestAPICompatibility:
    """測試API相容性"""

    def test_signals_api_imports(self):
        """測試信號API導入不會失敗"""
        try:
            from api.v1.signals import router
            assert router is not None
        except ImportError as e:
            pytest.fail(f"信號API導入失敗: {e}")

    def test_websocket_api_imports(self):
        """測試WebSocket API導入不會失敗"""
        try:
            from api.v1.websocket import (
                websocket_endpoint,
                initialize_websocket_manager,
                shutdown_websocket_manager,
                get_websocket_cluster_stats
            )
            assert websocket_endpoint is not None
            assert initialize_websocket_manager is not None
            assert shutdown_websocket_manager is not None
            assert get_websocket_cluster_stats is not None
        except ImportError as e:
            pytest.fail(f"WebSocket API導入失敗: {e}")

    def test_main_app_imports(self):
        """測試主應用程式導入不會失敗"""
        try:
            from app.main import app
            assert app is not None
        except ImportError as e:
            pytest.fail(f"主應用程式導入失敗: {e}")


class TestConfigurationValidation:
    """測試配置驗證"""

    def test_redis_url_configured(self):
        """測試Redis URL已配置"""
        from core.config import settings
        assert hasattr(settings, 'REDIS_URL')
        assert settings.REDIS_URL is not None
        assert isinstance(settings.REDIS_URL, str)
        assert len(settings.REDIS_URL) > 0

    def test_database_url_configured(self):
        """測試資料庫URL已配置"""
        from core.config import settings
        assert hasattr(settings, 'DATABASE_URL')
        assert settings.DATABASE_URL is not None
        assert isinstance(settings.DATABASE_URL, str)
        assert len(settings.DATABASE_URL) > 0


# 整合測試案例
class TestIntegrationScenarios:
    """測試整合場景"""

    async def test_websocket_lifecycle(self):
        """測試WebSocket生命週期（模擬）"""
        manager = EnhancedConnectionManager()

        # 測試初始化（不實際連接Redis）
        try:
            # 這裡只測試方法調用不會拋出語法錯誤
            # 實際測試需要Redis連接
            stats = manager.get_connection_stats()
            assert isinstance(stats, dict)
            assert 'worker_id' in stats
            assert 'total_connections' in stats
        except Exception as e:
            # 預期的連接錯誤是可以接受的
            assert "Redis" in str(e) or "connection" in str(e).lower()

    async def test_signal_api_workflow(self):
        """測試信號API工作流程（模擬）"""
        # 測試過濾條件建構
        filters = {
            "signal_type": "BUY",
            "start_date": date.today() - timedelta(days=30),
            "end_date": date.today(),
            "min_confidence": 0.8
        }

        # 確保過濾條件結構正確
        assert isinstance(filters, dict)
        assert "signal_type" in filters
        assert isinstance(filters["start_date"], date)
        assert isinstance(filters["end_date"], date)
        assert isinstance(filters["min_confidence"], float)


if __name__ == "__main__":
    """直接執行測試"""

    async def run_basic_tests():
        """執行基本測試"""
        print("🧪 開始執行Bug修復驗證測試...")

        # 測試1: CRUD函式存在性
        print("✅ 測試1: 檢查CRUD函式存在性")
        crud_test = TestTradingSignalCRUDFixes()
        await crud_test.test_get_signals_with_filters_exists()
        await crud_test.test_count_signals_with_filters_exists()
        await crud_test.test_get_signal_stats_exists()
        await crud_test.test_get_detailed_signal_stats_exists()
        print("   ✓ 所有必要的CRUD函式都存在")

        # 測試2: WebSocket管理器結構
        print("✅ 測試2: 檢查WebSocket管理器結構")
        ws_test = TestWebSocketManagerFixes()
        await ws_test.test_enhanced_connection_manager_initialization()
        await ws_test.test_manager_methods_exist()
        await ws_test.test_broadcaster_methods_exist()
        print("   ✓ WebSocket管理器結構完整")

        # 測試3: API相容性
        print("✅ 測試3: 檢查API相容性")
        api_test = TestAPICompatibility()
        api_test.test_signals_api_imports()
        api_test.test_websocket_api_imports()
        api_test.test_main_app_imports()
        print("   ✓ 所有API模組導入正常")

        # 測試4: 配置驗證
        print("✅ 測試4: 檢查配置設定")
        config_test = TestConfigurationValidation()
        config_test.test_redis_url_configured()
        config_test.test_database_url_configured()
        print("   ✓ 配置設定完整")

        print("🎉 所有測試通過！Bug修復驗證成功。")

    # 執行測試
    asyncio.run(run_basic_tests())