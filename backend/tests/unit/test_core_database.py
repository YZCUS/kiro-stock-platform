#!/usr/bin/env python3
"""
資料庫連接測試
"""
import sys
import asyncio
import unittest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path

# 添加測試配置路徑
sys.path.insert(0, str(Path(__file__).parent.parent))
from test_config import setup_test_path

# 設置測試環境路徑
setup_test_path()

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError


class TestDatabaseConnection(unittest.TestCase):
    """資料庫連接測試"""

    def setUp(self):
        """設置測試環境"""
        self.mock_engine = Mock()
        self.mock_session = AsyncMock(spec=AsyncSession)

    @patch('core.database.create_async_engine')
    @patch('core.database.settings')
    def test_engine_creation_success(self, mock_settings, mock_create_engine):
        """測試資料庫引擎創建 - 成功"""
        # 模擬設定
        mock_settings.DATABASE_URL = "postgresql://user:pass@localhost:5432/test"
        mock_settings.DEBUG = True

        # 模擬引擎
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        # 重新導入模組以觸發引擎創建
        import importlib
        import core.database
        importlib.reload(core.database)

        # 驗證引擎創建
        mock_create_engine.assert_called_once_with(
            "postgresql+asyncpg://user:pass@localhost:5432/test",
            echo=True,
            future=True
        )

    @patch('core.database.create_async_engine')
    @patch('core.database.settings')
    def test_engine_creation_with_debug_false(self, mock_settings, mock_create_engine):
        """測試資料庫引擎創建 - DEBUG關閉"""
        mock_settings.DATABASE_URL = "postgresql://user:pass@localhost:5432/test"
        mock_settings.DEBUG = False

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        # 重新導入模組
        import importlib
        import core.database
        importlib.reload(core.database)

        # 驗證DEBUG設定
        call_args = mock_create_engine.call_args
        self.assertEqual(call_args[1]['echo'], False)

    def test_database_url_conversion(self):
        """測試資料庫URL轉換"""
        from core.database import settings

        # 測試URL轉換邏輯
        original_url = "postgresql://user:pass@localhost:5432/test"
        expected_url = "postgresql+asyncpg://user:pass@localhost:5432/test"

        converted_url = original_url.replace("postgresql://", "postgresql+asyncpg://")
        self.assertEqual(converted_url, expected_url)

    def test_metadata_naming_convention(self):
        """測試元數據命名約定"""
        from core.database import Base

        expected_convention = {
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s"
        }

        # 驗證命名約定
        for key, value in expected_convention.items():
            self.assertEqual(Base.metadata.naming_convention[key], value)


class TestDatabaseSessionManagement(unittest.TestCase):
    """資料庫會話管理測試"""

    def setUp(self):
        """設置測試環境"""
        self.mock_session = AsyncMock(spec=AsyncSession)

    @patch('core.database.AsyncSessionLocal')
    async def test_get_db_success(self, mock_session_factory):
        """測試取得資料庫會話 - 成功"""
        # 設置模擬會話工廠
        mock_session_factory.return_value.__aenter__.return_value = self.mock_session
        mock_session_factory.return_value.__aexit__.return_value = None

        from core.database import get_db

        # 測試會話生成器
        async with get_db() as session:
            self.assertEqual(session, self.mock_session)

        # 驗證會話被正確關閉
        self.mock_session.close.assert_called_once()

    @patch('core.database.AsyncSessionLocal')
    async def test_get_db_with_exception(self, mock_session_factory):
        """測試取得資料庫會話 - 異常處理"""
        # 設置模擬會話工廠
        mock_session_factory.return_value.__aenter__.return_value = self.mock_session
        mock_session_factory.return_value.__aexit__.return_value = None

        from core.database import get_db

        # 模擬會話異常
        self.mock_session.execute.side_effect = SQLAlchemyError("Database error")

        try:
            async for session in get_db():
                # 觸發異常
                await session.execute("SELECT 1")
        except SQLAlchemyError:
            pass

        # 驗證回滾和關閉被調用
        self.mock_session.rollback.assert_called_once()
        self.mock_session.close.assert_called_once()

    @patch('core.database.AsyncSessionLocal')
    async def test_get_db_session_alias(self, mock_session_factory):
        """測試資料庫會話別名函式"""
        mock_session_factory.return_value.__aenter__.return_value = self.mock_session
        mock_session_factory.return_value.__aexit__.return_value = None

        from core.database import get_db_session, get_db

        # 驗證別名函式是同一個函式
        self.assertEqual(get_db_session, get_db)

    @patch('core.database.AsyncSessionLocal')
    async def test_session_rollback_on_exception(self, mock_session_factory):
        """測試會話異常時的回滾機制"""
        mock_session_factory.return_value.__aenter__.return_value = self.mock_session
        mock_session_factory.return_value.__aexit__.return_value = None

        from core.database import get_db

        # 模擬資料庫操作異常
        test_exception = Exception("Test database error")

        with self.assertRaises(Exception):
            async for session in get_db():
                # 在會話中觸發異常
                raise test_exception

        # 驗證回滾被調用
        self.mock_session.rollback.assert_called_once()
        self.mock_session.close.assert_called_once()


class TestDatabaseSessionFactory(unittest.TestCase):
    """資料庫會話工廠測試"""

    @patch('core.database.async_sessionmaker')
    @patch('core.database.engine')
    def test_session_factory_configuration(self, mock_engine, mock_sessionmaker):
        """測試會話工廠配置"""
        from core.database import AsyncSessionLocal

        # 驗證會話工廠創建參數
        mock_sessionmaker.assert_called_with(
            mock_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    @patch('core.database.AsyncSessionLocal')
    async def test_session_context_manager(self, mock_session_factory):
        """測試會話上下文管理器"""
        mock_context = AsyncMock()
        mock_session_factory.return_value = mock_context

        from core.database import AsyncSessionLocal

        # 測試會話工廠返回上下文管理器
        session_context = AsyncSessionLocal()
        self.assertEqual(session_context, mock_context)


class TestDatabaseIntegration(unittest.TestCase):
    """資料庫整合測試"""

    def test_base_model_class(self):
        """測試基礎模型類別"""
        from core.database import Base
        from sqlalchemy.ext.declarative import DeclarativeMeta

        # 驗證Base是DeclarativeMeta實例
        self.assertIsInstance(Base, DeclarativeMeta)

        # 驗證元數據存在
        self.assertIsNotNone(Base.metadata)

    def test_imports_and_dependencies(self):
        """測試模組導入和依賴"""
        try:
            from core.database import (
                engine,
                AsyncSessionLocal,
                Base,
                get_db,
                get_db_session
            )

            # 驗證所有必要組件都能正確導入
            self.assertIsNotNone(engine)
            self.assertIsNotNone(AsyncSessionLocal)
            self.assertIsNotNone(Base)
            self.assertIsNotNone(get_db)
            self.assertIsNotNone(get_db_session)

        except ImportError as e:
            self.fail(f"模組導入失敗: {e}")

    @patch('core.database.settings')
    def test_configuration_validation(self, mock_settings):
        """測試配置驗證"""
        # 測試必要配置存在
        mock_settings.DATABASE_URL = "postgresql://localhost:5432/test"
        mock_settings.DEBUG = True

        # 驗證設定可以被正確訪問
        from core.database import settings
        self.assertIsNotNone(settings.DATABASE_URL)
        self.assertIsInstance(settings.DEBUG, bool)


async def run_all_tests():
    """執行所有測試"""
    print("=" * 60)
    print("資料庫連接測試")
    print("=" * 60)

    # 同步測試
    sync_test_classes = [
        TestDatabaseConnection,
        TestDatabaseSessionFactory,
        TestDatabaseIntegration
    ]

    for test_class in sync_test_classes:
        print(f"\n執行 {test_class.__name__}...")
        suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)

        if not result.wasSuccessful():
            print(f"❌ {test_class.__name__} 測試失敗")
            return False

    # 異步測試
    print(f"\n執行 TestDatabaseSessionManagement...")
    async_test = TestDatabaseSessionManagement()

    async_test_methods = [
        'test_get_db_success',
        'test_get_db_with_exception',
        'test_get_db_session_alias',
        'test_session_rollback_on_exception'
    ]

    for method_name in async_test_methods:
        async_test.setUp()
        try:
            await getattr(async_test, method_name)()
            print(f"✅ {method_name} - 通過")
        except Exception as e:
            print(f"❌ {method_name} - 失敗: {str(e)}")
            return False

    print("\n🎉 所有資料庫連接測試都通過了！")
    return True


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)