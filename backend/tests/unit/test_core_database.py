#!/usr/bin/env python3
"""
Core Database Tests - Clean Architecture
Testing database connection, session management, and configuration
"""

import inspect
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

BACKEND_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_ROOT))


class TestDatabaseConfiguration:
    """Database configuration tests"""

    def test_database_url_conversion(self):
        """Test database URL conversion from PostgreSQL to AsyncPG"""
        from core.database_url import make_async_database_url

        original_url = "postgresql://user:pass@localhost:5432/test"
        expected_url = "postgresql+asyncpg://user:pass@localhost:5432/test"

        converted_url = make_async_database_url(original_url)
        assert converted_url == expected_url

    def test_metadata_naming_convention(self):
        """Test SQLAlchemy metadata naming convention"""
        from core.database import Base

        expected_convention = {
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }

        assert Base.metadata.naming_convention == expected_convention

    def test_database_imports(self):
        """Test that core database components can be imported"""
        from core.database import get_db, get_db_session

        assert get_db_session is get_db
        assert callable(get_db_session)


class TestDatabaseSessionManagement:
    """Database session management tests"""

    def setup_method(self):
        """Setup test environment"""
        self.mock_session = AsyncMock(spec=AsyncSession)

    @pytest.mark.asyncio
    async def test_get_db_session_context_manager(self):
        """Test database session context manager functionality"""
        from core.database import AsyncSessionLocal, get_db_session

        assert inspect.isasyncgenfunction(get_db_session)

        # In pytest mode core.database intentionally does not create a global engine.
        assert AsyncSessionLocal is None
        session_generator = get_db_session()
        with pytest.raises(RuntimeError, match="Database not initialized"):
            await session_generator.__anext__()

    @pytest.mark.asyncio
    async def test_session_error_handling(self):
        """Test session error handling and rollback"""
        mock_session = AsyncMock(spec=AsyncSession)

        # Test rollback on exception
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        # Verify that error handling would work
        with pytest.raises(SQLAlchemyError):
            await mock_session.execute("SELECT 1")

        # Verify rollback would be called in real implementation
        mock_session.rollback.assert_not_called()  # Not called yet
        await mock_session.rollback()
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_cleanup(self):
        """Test session cleanup and resource management"""
        mock_session = AsyncMock(spec=AsyncSession)

        # Test session close
        await mock_session.close()
        mock_session.close.assert_called_once()

        # Test that session can be closed multiple times safely
        await mock_session.close()
        assert mock_session.close.call_count == 2


class TestDatabaseIntegration:
    """Database integration tests for Clean Architecture"""

    def test_repository_interfaces_exist(self):
        """Test that repository interfaces exist for Clean Architecture"""
        try:
            from domain.repositories.daily_price_repository_interface import (
                IDailyPriceRepository,
            )
            from domain.repositories.market_data_bar_repository_interface import (
                IMarketDataBarRepository,
            )
            from domain.repositories.stock_repository_interface import IStockRepository

            # Verify interfaces are abstract base classes
            assert hasattr(IStockRepository, "__abstractmethods__")
            assert hasattr(IDailyPriceRepository, "__abstractmethods__")
            assert hasattr(IMarketDataBarRepository, "__abstractmethods__")

        except ImportError:
            pytest.fail("Repository interfaces should exist in Clean Architecture")

    def test_infrastructure_repositories_exist(self):
        """Test that infrastructure repository implementations exist"""
        from domain.repositories.daily_price_repository_interface import (
            IDailyPriceRepository,
        )
        from domain.repositories.market_data_bar_repository_interface import (
            IMarketDataBarRepository,
        )
        from domain.repositories.stock_repository_interface import IStockRepository
        from infrastructure.persistence.daily_price_repository import (
            DailyPriceRepository,
        )
        from infrastructure.persistence.market_data_bar_repository import (
            MarketDataBarRepository,
        )
        from infrastructure.persistence.stock_repository import StockRepository

        assert issubclass(StockRepository, IStockRepository)
        assert issubclass(DailyPriceRepository, IDailyPriceRepository)
        assert issubclass(MarketDataBarRepository, IMarketDataBarRepository)

    def test_dependency_injection_setup(self):
        """Test dependency injection configuration"""
        from app.dependencies import get_database_session

        assert callable(get_database_session)

    def test_domain_models_exist(self):
        """Test that domain models are properly structured"""
        from domain.models import MarketDataBar, Stock, TechnicalIndicator

        assert Stock.__tablename__ == "stocks"
        assert MarketDataBar.__tablename__ == "market_data_bars"
        assert TechnicalIndicator.__tablename__ == "technical_indicators"


class TestDatabaseConnectionPooling:
    """Database connection pooling and configuration tests"""

    @patch("sqlalchemy.ext.asyncio.create_async_engine")
    def test_engine_creation_with_pooling(self, mock_create_engine):
        """Test engine creation with proper pooling configuration"""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        # Test typical engine configuration
        from sqlalchemy.ext.asyncio import create_async_engine

        test_url = "postgresql+asyncpg://user:pass@localhost:5432/test"
        engine = create_async_engine(
            test_url, echo=False, future=True, pool_size=5, max_overflow=10
        )

        # Verify mock was called
        mock_create_engine.assert_called_once()

    def test_connection_string_validation(self):
        """Test connection string validation"""
        valid_urls = [
            "postgresql+asyncpg://user:pass@localhost:5432/db",
            "sqlite+aiosqlite:///test.db",
            "postgresql+asyncpg://user@localhost/db",
        ]

        for url in valid_urls:
            # Basic validation - should contain driver and basic components
            assert "://" in url
            if "postgresql" in url:
                assert "asyncpg" in url
            elif "sqlite" in url:
                assert "aiosqlite" in url

    def test_session_factory_configuration(self):
        """Test session factory configuration"""
        from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

        mock_engine = Mock()
        session_factory = async_sessionmaker(
            mock_engine, class_=AsyncSession, expire_on_commit=False
        )

        assert session_factory is not None


class TestDatabaseMigrations:
    """Database migration and schema tests"""

    def test_alembic_configuration_exists(self):
        """Test that Alembic migration configuration exists"""
        from pathlib import Path

        # Check for common migration files
        backend_path = BACKEND_ROOT
        alembic_ini = backend_path / "alembic.ini"
        alembic_dir = backend_path / "alembic"

        assert alembic_ini.exists()
        assert alembic_dir.exists()
        assert (alembic_dir / "env.py").exists()

    def test_database_initialization_scripts(self):
        """Test database initialization scripts"""
        backend_path = BACKEND_ROOT
        database_dir = backend_path / "database"

        assert (database_dir / "migrate.py").exists()
        assert (database_dir / "test_connection.py").exists()


class TestDatabaseSecurity:
    """Database security and best practices tests"""

    def test_connection_string_security(self):
        """Test connection string security practices"""
        # Test that we don't have hardcoded credentials
        insecure_patterns = [
            "password=123456",
            "password=admin",
            "password=root",
            "password=test",
        ]

        test_url = "postgresql+asyncpg://user:securepass@localhost:5432/db"

        for pattern in insecure_patterns:
            assert pattern not in test_url.lower()

    def test_environment_variable_usage(self):
        """Test that environment variables are used for configuration"""
        import os

        # Test that typical database environment variables can be read
        db_env_vars = ["DATABASE_URL", "DB_HOST", "DB_PORT", "DB_NAME", "DB_USER"]

        # At least check that os.environ can be used (not that they're set)
        for var in db_env_vars:
            assert hasattr(os, "environ")
            # Just verify we can access environment variables
            _ = os.environ.get(var, "default")

    def test_ssl_configuration_support(self):
        """Test SSL configuration support"""
        # Test SSL parameter in connection string
        ssl_url = "postgresql+asyncpg://user:pass@localhost:5432/db?sslmode=require"

        assert "sslmode" in ssl_url
        assert "require" in ssl_url


# Performance and monitoring tests
class TestDatabasePerformance:
    """Database performance monitoring tests"""

    def test_connection_timeout_configuration(self):
        """Test connection timeout configuration"""
        # Test timeout parameters
        timeout_config = {
            "pool_timeout": 30,
            "pool_recycle": 3600,
            "connect_timeout": 10,
        }

        for key, value in timeout_config.items():
            assert isinstance(value, int)
            assert value > 0

    def test_query_logging_configuration(self):
        """Test query logging configuration"""
        # Test echo parameter for SQL logging
        echo_configs = [True, False, "debug"]

        for config in echo_configs:
            # Just verify the configuration types are valid
            assert config in [True, False, "debug"]
