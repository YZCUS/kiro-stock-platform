"""
資料庫連接和設定
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
try:
    from sqlalchemy.ext.asyncio import async_sessionmaker
except ImportError:
    from sqlalchemy.orm import sessionmaker as async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData
from typing import AsyncGenerator

import os

# 檢查是否在測試環境中
import sys
_is_testing = 'pytest' in sys.modules or 'test' in sys.argv[0] if sys.argv else False

if not _is_testing:
    try:
        from app.settings import settings
        # 建立異步資料庫引擎
        engine = create_async_engine(
            settings.database.url.replace("postgresql://", "postgresql+asyncpg://"),
            echo=settings.app.debug,
            future=True
        )
    except Exception:
        # 如果設定有問題，則使用記憶體資料庫
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False,
            future=True
        )
else:
    # 測試環境中使用同步 SQLite 記憶體資料庫
    from sqlalchemy import create_engine
    engine = None  # 在測試中不創建引擎，讓測試自己處理

# 建立異步會話工廠
if engine is not None:
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
else:
    AsyncSessionLocal = None

# 建立基礎模型類別
Base = declarative_base()

# 設定元數據命名約定
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

Base.metadata = MetaData(naming_convention=convention)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """取得資料庫會話"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# 別名函式以保持向後相容性
get_db_session = get_db