"""
Redis 快取工具
"""
import redis
import json
from typing import Optional, List, Dict, Any
from core.config import settings


# Redis 連接配置
try:
    redis_client = redis.Redis(
        host=getattr(settings, 'REDIS_HOST', 'localhost'),
        port=getattr(settings, 'REDIS_PORT', 6379),
        db=getattr(settings, 'REDIS_DB', 0),
        decode_responses=True,
        socket_timeout=5
    )
    # 測試連接
    redis_client.ping()
except Exception as e:
    print(f"Redis 連接失敗，快取將被禁用: {e}")
    redis_client = None


def get_cache_key(prefix: str, market: Optional[str] = None) -> str:
    """生成快取鍵"""
    key_parts = [prefix]
    if market:
        key_parts.append(f"market:{market}")
    return ":".join(key_parts)


def get_cached_data(cache_key: str) -> Optional[List[Dict[str, Any]]]:
    """從快取獲取數據"""
    if not redis_client:
        return None

    try:
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)
    except Exception as e:
        print(f"快取讀取失敗: {e}")

    return None


def set_cached_data(cache_key: str, data: List[Dict[str, Any]], ttl: int = 300) -> None:
    """設置快取數據"""
    if not redis_client:
        return

    try:
        redis_client.setex(cache_key, ttl, json.dumps(data, ensure_ascii=False))
    except Exception as e:
        print(f"快取設置失敗: {e}")