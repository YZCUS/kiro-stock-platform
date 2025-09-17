"""
Redis 連接和快取設定
"""
import redis.asyncio as redis
import json
import asyncio
from typing import Any, Optional
import logging
from functools import wraps

from core.config import settings

logger = logging.getLogger(__name__)


def with_retry(max_retries: int = 3, delay: float = 1.0):
    """Redis操作重試裝飾器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            last_exception = None

            for attempt in range(max_retries):
                try:
                    # 檢查連接狀態
                    if not await self._ensure_connection():
                        return None if func.__name__ == 'get' else False

                    return await func(self, *args, **kwargs)

                except (redis.ConnectionError, redis.TimeoutError, redis.RedisError) as e:
                    last_exception = e
                    logger.warning(f"Redis操作失敗 (嘗試 {attempt + 1}/{max_retries}): {e}")

                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay * (2 ** attempt))  # 指數退避
                        # 嘗試重新連接
                        await self._reconnect()

                except Exception as e:
                    # 非Redis相關錯誤，不重試
                    logger.error(f"Redis操作錯誤: {e}")
                    return None if func.__name__ == 'get' else False

            logger.error(f"Redis操作最終失敗: {last_exception}")
            return None if func.__name__ == 'get' else False

        return wrapper
    return decorator


class RedisClient:
    """Redis 客戶端封裝 - 支持連接池和重試機制"""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.connection_pool: Optional[redis.ConnectionPool] = None
        self._is_connected: bool = False
    
    async def connect(self):
        """建立 Redis 連接"""
        try:
            # 創建連接池
            self.connection_pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )

            # 創建Redis客戶端
            self.redis_client = redis.Redis(connection_pool=self.connection_pool)

            # 測試連接
            await self.redis_client.ping()
            self._is_connected = True
            logger.info("Redis 連接成功")

        except Exception as e:
            logger.error(f"Redis 連接失敗: {e}")
            self.redis_client = None
            self.connection_pool = None
            self._is_connected = False
    
    async def disconnect(self):
        """關閉 Redis 連接"""
        try:
            if self.redis_client:
                await self.redis_client.close()

            if self.connection_pool:
                await self.connection_pool.disconnect()

            self._is_connected = False
            logger.info("Redis 連接已關閉")

        except Exception as e:
            logger.error(f"關閉Redis連接時發生錯誤: {e}")

        finally:
            self.redis_client = None
            self.connection_pool = None
            self._is_connected = False

    async def _ensure_connection(self) -> bool:
        """確保Redis連接有效"""
        if not self.redis_client:
            return False

        try:
            await self.redis_client.ping()
            self._is_connected = True
            return True
        except Exception as e:
            logger.warning(f"Redis連接無效: {e}")
            self._is_connected = False
            return False

    async def _reconnect(self):
        """重新連接Redis"""
        logger.info("嘗試重新連接Redis...")
        await self.disconnect()
        await self.connect()

    @property
    def is_connected(self) -> bool:
        """檢查連接狀態"""
        return self._is_connected and self.redis_client is not None
    
    @with_retry(max_retries=3, delay=0.5)
    async def get(self, key: str) -> Optional[Any]:
        """取得快取值"""
        value = await self.redis_client.get(key)
        if value:
            return json.loads(value)
        return None

    @with_retry(max_retries=3, delay=0.5)
    async def set(
        self,
        key: str,
        value: Any,
        expire: int = settings.CACHE_EXPIRE_SECONDS
    ) -> bool:
        """設定快取值"""
        json_value = json.dumps(value, ensure_ascii=False, default=str)
        await self.redis_client.set(key, json_value, ex=expire)
        return True

    @with_retry(max_retries=3, delay=0.5)
    async def delete(self, key: str) -> bool:
        """刪除快取值"""
        await self.redis_client.delete(key)
        return True

    @with_retry(max_retries=3, delay=0.5)
    async def exists(self, key: str) -> bool:
        """檢查鍵是否存在"""
        return await self.redis_client.exists(key) > 0

    @with_retry(max_retries=2, delay=0.3)
    async def ping(self) -> bool:
        """檢查Redis服務狀態"""
        await self.redis_client.ping()
        return True

    async def get_connection_info(self) -> dict:
        """獲取連接信息"""
        info = {
            "is_connected": self.is_connected,
            "redis_client_exists": self.redis_client is not None,
            "connection_pool_exists": self.connection_pool is not None
        }

        if self.redis_client:
            try:
                # 獲取連接池統計信息
                if self.connection_pool:
                    pool_info = {
                        "max_connections": getattr(self.connection_pool, 'max_connections', 'unknown'),
                        "created_connections": getattr(self.connection_pool, 'created_connections', 'unknown')
                    }
                    info.update(pool_info)

                # 測試ping響應時間
                import time
                start_time = time.time()
                await self.redis_client.ping()
                ping_time = (time.time() - start_time) * 1000
                info["ping_time_ms"] = round(ping_time, 2)

            except Exception as e:
                info["connection_error"] = str(e)

        return info


# 建立全域 Redis 客戶端實例
redis_client = RedisClient()