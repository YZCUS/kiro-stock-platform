"""
Redis 連接和快取設定
"""
import redis.asyncio as redis
import json
from typing import Any, Optional
import logging

from core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis 客戶端封裝"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
    
    async def connect(self):
        """建立 Redis 連接"""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            # 測試連接
            await self.redis_client.ping()
            logger.info("Redis 連接成功")
        except Exception as e:
            logger.error(f"Redis 連接失敗: {e}")
            self.redis_client = None
    
    async def disconnect(self):
        """關閉 Redis 連接"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis 連接已關閉")
    
    async def get(self, key: str) -> Optional[Any]:
        """取得快取值"""
        if not self.redis_client:
            return None
        
        try:
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis GET 錯誤: {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        expire: int = settings.CACHE_EXPIRE_SECONDS
    ) -> bool:
        """設定快取值"""
        if not self.redis_client:
            return False
        
        try:
            json_value = json.dumps(value, ensure_ascii=False, default=str)
            await self.redis_client.set(key, json_value, ex=expire)
            return True
        except Exception as e:
            logger.error(f"Redis SET 錯誤: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """刪除快取值"""
        if not self.redis_client:
            return False
        
        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE 錯誤: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """檢查鍵是否存在"""
        if not self.redis_client:
            return False
        
        try:
            return await self.redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS 錯誤: {e}")
            return False


# 建立全域 Redis 客戶端實例
redis_client = RedisClient()