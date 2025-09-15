"""
FastAPI Dependencies
"""
from typing import AsyncGenerator
from core.database import get_db
from core.redis import redis_client


async def get_database() -> AsyncGenerator:
    """Get database session dependency"""
    async for session in get_db():
        yield session


async def get_redis():
    """Get Redis client dependency"""
    return redis_client