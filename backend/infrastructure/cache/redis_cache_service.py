"""
Redis 快取服務 - 統一的快取實現
整合原本分散在多個位置的快取邏輯
"""

import json
import redis
from typing import Any, Optional, Dict, List
from abc import ABC, abstractmethod


class ICacheService(ABC):
    """快取服務介面 (Domain Layer)"""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """取得快取值"""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """設置快取值"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """刪除快取值"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """檢查快取是否存在"""
        pass

    @abstractmethod
    def get_cache_key(self, prefix: str, **kwargs) -> str:
        """生成快取鍵"""
        pass


class RedisCacheService(ICacheService):
    """Redis 快取服務實現 (Infrastructure Layer)"""

    def __init__(self, redis_client: redis.Redis, redis_settings):
        """
        初始化Redis快取服務

        Args:
            redis_client: Redis客戶端實例
            redis_settings: Redis設定
        """
        self.redis_client = redis_client
        self.settings = redis_settings
        self.is_connected = redis_client is not None

    def get_cache_key(self, prefix: str, **kwargs) -> str:
        """
        生成標準化的快取鍵

        Args:
            prefix: 快取前綴
            **kwargs: 額外的鍵值參數

        Returns:
            標準化的快取鍵字符串
        """
        key_parts = [prefix]
        for key, value in sorted(kwargs.items()):  # 排序確保一致性
            if value is not None:
                # 處理特殊類型
                if isinstance(value, (list, tuple)):
                    value = ",".join(str(v) for v in value)
                elif isinstance(value, dict):
                    value = json.dumps(value, sort_keys=True)
                key_parts.append(f"{key}:{value}")
        return ":".join(key_parts)

    async def get(self, key: str) -> Optional[Any]:
        """
        從快取取得數據

        Args:
            key: 快取鍵

        Returns:
            快取的數據，不存在則返回None
        """
        if not self.is_connected:
            return None

        try:
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"Redis get 操作失敗 [{key}]: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """
        設置快取數據

        Args:
            key: 快取鍵
            value: 要快取的數據
            ttl: 過期時間（秒），None則使用預設TTL

        Returns:
            設置是否成功
        """
        if not self.is_connected:
            return False

        try:
            ttl = ttl or self.settings.default_ttl
            serialized_value = json.dumps(value, ensure_ascii=False, default=str)
            result = self.redis_client.setex(key, ttl, serialized_value)
            return bool(result)
        except Exception as e:
            print(f"Redis set 操作失敗 [{key}]: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        刪除快取數據

        Args:
            key: 快取鍵

        Returns:
            刪除是否成功
        """
        if not self.is_connected:
            return False

        try:
            result = self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            print(f"Redis delete 操作失敗 [{key}]: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """
        檢查快取是否存在

        Args:
            key: 快取鍵

        Returns:
            快取是否存在
        """
        if not self.is_connected:
            return False

        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            print(f"Redis exists 操作失敗 [{key}]: {e}")
            return False

    async def get_multi(self, keys: List[str]) -> Dict[str, Any]:
        """
        批次取得多個快取值

        Args:
            keys: 快取鍵列表

        Returns:
            鍵值對字典
        """
        if not self.is_connected or not keys:
            return {}

        try:
            values = self.redis_client.mget(keys)
            result = {}
            for key, value in zip(keys, values):
                if value:
                    try:
                        result[key] = json.loads(value)
                    except json.JSONDecodeError:
                        result[key] = value
            return result
        except Exception as e:
            print(f"Redis mget 操作失敗: {e}")
            return {}

    async def set_multi(self, data: Dict[str, Any], ttl: int = None) -> bool:
        """
        批次設置多個快取值

        Args:
            data: 要設置的鍵值對
            ttl: 過期時間

        Returns:
            設置是否成功
        """
        if not self.is_connected or not data:
            return False

        try:
            ttl = ttl or self.settings.default_ttl
            pipeline = self.redis_client.pipeline()

            for key, value in data.items():
                serialized_value = json.dumps(value, ensure_ascii=False, default=str)
                pipeline.setex(key, ttl, serialized_value)

            results = pipeline.execute()
            return all(results)
        except Exception as e:
            print(f"Redis mset 操作失敗: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """
        清除符合模式的快取

        Args:
            pattern: 匹配模式（支援 * 通配符）

        Returns:
            清除的鍵數量
        """
        if not self.is_connected:
            return 0

        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            print(f"Redis clear_pattern 操作失敗 [{pattern}]: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """
        取得Redis統計資訊

        Returns:
            統計資訊字典
        """
        if not self.is_connected:
            return {"connected": False}

        try:
            info = self.redis_client.info()
            return {
                "connected": True,
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses"),
                "hit_rate": round(
                    info.get("keyspace_hits", 0)
                    / max(
                        info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1
                    )
                    * 100,
                    2,
                ),
            }
        except Exception as e:
            print(f"Redis stats 操作失敗: {e}")
            return {"connected": False, "error": str(e)}


class MockCacheService(ICacheService):
    """Mock 快取服務 (用於測試)"""

    def __init__(self):
        self._cache = {}

    def get_cache_key(self, prefix: str, **kwargs) -> str:
        key_parts = [prefix]
        for key, value in sorted(kwargs.items()):
            if value is not None:
                key_parts.append(f"{key}:{value}")
        return ":".join(key_parts)

    async def get(self, key: str) -> Optional[Any]:
        return self._cache.get(key)

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        self._cache[key] = value
        return True

    async def delete(self, key: str) -> bool:
        return self._cache.pop(key, None) is not None

    async def exists(self, key: str) -> bool:
        return key in self._cache

    def clear(self):
        """清空快取 (測試用)"""
        self._cache.clear()
