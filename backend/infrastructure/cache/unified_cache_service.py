"""
統一快取服務 - Infrastructure Layer
整合所有快取功能，提供統一的快取抽象
"""
import json
import redis
from typing import Optional, List, Dict, Any, Union
from datetime import date, datetime, timedelta
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class ICacheService(ABC):
    """快取服務介面"""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """取得快取數據"""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """設置快取數據"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """刪除快取數據"""
        pass

    @abstractmethod
    def get_cache_key(self, prefix: str, **kwargs) -> str:
        """生成快取鍵"""
        pass

    @abstractmethod
    async def clear_pattern(self, pattern: str) -> int:
        """清除匹配模式的快取"""
        pass


class RedisCacheService(ICacheService):
    """Redis快取服務實現"""

    def __init__(self, redis_client=None, default_ttl: int = 300):
        self.redis_client = redis_client
        self.default_ttl = default_ttl
        self.hit_count = 0
        self.miss_count = 0

    async def get(self, key: str) -> Optional[Any]:
        """取得快取數據"""
        if not self.redis_client:
            return None

        try:
            data = self.redis_client.get(key)
            if data:
                self.hit_count += 1
                return json.loads(data)
            else:
                self.miss_count += 1
                return None
        except Exception as e:
            logger.error(f"快取讀取失敗 {key}: {e}")
            self.miss_count += 1
            return None

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """設置快取數據"""
        if not self.redis_client:
            return False

        try:
            ttl = ttl or self.default_ttl
            success = self.redis_client.setex(
                key,
                ttl,
                json.dumps(value, ensure_ascii=False, default=str)
            )
            if success:
                logger.debug(f"成功設置快取: {key}")
            return bool(success)
        except Exception as e:
            logger.error(f"快取設置失敗 {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """刪除快取數據"""
        if not self.redis_client:
            return False

        try:
            result = self.redis_client.delete(key)
            return bool(result)
        except Exception as e:
            logger.error(f"快取刪除失敗 {key}: {e}")
            return False

    def get_cache_key(self, prefix: str, **kwargs) -> str:
        """生成快取鍵"""
        key_parts = [prefix]
        for key, value in sorted(kwargs.items()):
            if value is not None:
                key_parts.append(f"{key}:{value}")
        return ":".join(key_parts)

    async def clear_pattern(self, pattern: str) -> int:
        """清除匹配模式的快取"""
        if not self.redis_client:
            return 0

        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"清除快取模式失敗 {pattern}: {e}")
            return 0

    def get_statistics(self) -> Dict[str, Any]:
        """取得快取統計"""
        total = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total) if total > 0 else 0

        return {
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate": hit_rate,
            "total_requests": total
        }


class MockCacheService(ICacheService):
    """Mock快取服務實現（用於測試）"""

    def __init__(self):
        self.cache = {}
        self.expires = {}

    async def get(self, key: str) -> Optional[Any]:
        """取得快取數據"""
        # 檢查過期
        if key in self.expires:
            if datetime.now() > self.expires[key]:
                del self.cache[key]
                del self.expires[key]
                return None

        return self.cache.get(key)

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """設置快取數據"""
        self.cache[key] = value
        if ttl:
            self.expires[key] = datetime.now() + timedelta(seconds=ttl)
        return True

    async def delete(self, key: str) -> bool:
        """刪除快取數據"""
        if key in self.cache:
            del self.cache[key]
            if key in self.expires:
                del self.expires[key]
            return True
        return False

    def get_cache_key(self, prefix: str, **kwargs) -> str:
        """生成快取鍵"""
        key_parts = [prefix]
        for key, value in sorted(kwargs.items()):
            if value is not None:
                key_parts.append(f"{key}:{value}")
        return ":".join(key_parts)

    async def clear_pattern(self, pattern: str) -> int:
        """清除匹配模式的快取"""
        # 簡化實現：清除所有包含pattern前綴的鍵
        pattern_prefix = pattern.replace("*", "")
        keys_to_delete = [k for k in self.cache.keys() if k.startswith(pattern_prefix)]

        for key in keys_to_delete:
            await self.delete(key)

        return len(keys_to_delete)


class StockCacheService:
    """股票專用快取服務"""

    def __init__(self, cache_service: ICacheService):
        self.cache = cache_service

    async def get_stock_list(
        self,
        market: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        per_page: int = 50
    ) -> Optional[Dict[str, Any]]:
        """取得股票清單快取"""
        cache_key = self.cache.get_cache_key(
            "stock_list",
            market=market,
            is_active=is_active,
            search=search,
            page=page,
            per_page=per_page
        )
        return await self.cache.get(cache_key)

    async def set_stock_list(
        self,
        data: Dict[str, Any],
        market: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        per_page: int = 50,
        ttl: int = 300
    ) -> bool:
        """設置股票清單快取"""
        cache_key = self.cache.get_cache_key(
            "stock_list",
            market=market,
            is_active=is_active,
            search=search,
            page=page,
            per_page=per_page
        )
        return await self.cache.set(cache_key, data, ttl)

    async def get_active_stocks(self, market: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """取得活躍股票快取"""
        cache_key = self.cache.get_cache_key("active_stocks", market=market)
        return await self.cache.get(cache_key)

    async def set_active_stocks(
        self,
        data: List[Dict[str, Any]],
        market: Optional[str] = None,
        ttl: int = 1800
    ) -> bool:
        """設置活躍股票快取"""
        cache_key = self.cache.get_cache_key("active_stocks", market=market)
        return await self.cache.set(cache_key, data, ttl)

    async def clear_stock_caches(self) -> int:
        """清除股票相關快取"""
        patterns = ["stock_list:*", "active_stocks:*", "simple_stocks:*"]
        total_cleared = 0
        for pattern in patterns:
            cleared = await self.cache.clear_pattern(pattern)
            total_cleared += cleared
        return total_cleared


class TechnicalAnalysisCacheService:
    """技術分析專用快取服務"""

    def __init__(self, cache_service: ICacheService):
        self.cache = cache_service

    async def get_technical_analysis(
        self,
        stock_id: int,
        indicators: List[str] = None,
        days: int = 100
    ) -> Optional[Dict[str, Any]]:
        """取得技術分析快取"""
        cache_key = self.cache.get_cache_key(
            "technical_analysis",
            stock_id=stock_id,
            indicators=",".join(indicators) if indicators else "all",
            days=days
        )
        return await self.cache.get(cache_key)

    async def set_technical_analysis(
        self,
        stock_id: int,
        data: Dict[str, Any],
        indicators: List[str] = None,
        days: int = 100,
        ttl: int = 300
    ) -> bool:
        """設置技術分析快取"""
        cache_key = self.cache.get_cache_key(
            "technical_analysis",
            stock_id=stock_id,
            indicators=",".join(indicators) if indicators else "all",
            days=days
        )
        return await self.cache.set(cache_key, data, ttl)

    async def get_technical_summary(self, stock_id: int) -> Optional[Dict[str, Any]]:
        """取得技術摘要快取"""
        cache_key = self.cache.get_cache_key("technical_summary", stock_id=stock_id)
        return await self.cache.get(cache_key)

    async def set_technical_summary(
        self,
        stock_id: int,
        data: Dict[str, Any],
        ttl: int = 600
    ) -> bool:
        """設置技術摘要快取"""
        cache_key = self.cache.get_cache_key("technical_summary", stock_id=stock_id)
        return await self.cache.set(cache_key, data, ttl)


class TradingSignalCacheService:
    """交易信號專用快取服務"""

    def __init__(self, cache_service: ICacheService):
        self.cache = cache_service

    async def get_trading_signals(
        self,
        stock_id: int,
        analysis_days: int = 60
    ) -> Optional[Dict[str, Any]]:
        """取得交易信號快取"""
        cache_key = self.cache.get_cache_key(
            "trading_signals",
            stock_id=stock_id,
            analysis_days=analysis_days
        )
        return await self.cache.get(cache_key)

    async def set_trading_signals(
        self,
        stock_id: int,
        data: Dict[str, Any],
        analysis_days: int = 60,
        ttl: int = 3600
    ) -> bool:
        """設置交易信號快取"""
        cache_key = self.cache.get_cache_key(
            "trading_signals",
            stock_id=stock_id,
            analysis_days=analysis_days
        )
        return await self.cache.set(cache_key, data, ttl)

    async def get_market_signals(
        self,
        market: Optional[str] = None,
        min_confidence: float = 0.8
    ) -> Optional[Dict[str, Any]]:
        """取得市場信號快取"""
        cache_key = self.cache.get_cache_key(
            "market_signals",
            market=market,
            min_confidence=min_confidence
        )
        return await self.cache.get(cache_key)

    async def set_market_signals(
        self,
        data: Dict[str, Any],
        market: Optional[str] = None,
        min_confidence: float = 0.8,
        ttl: int = 1800
    ) -> bool:
        """設置市場信號快取"""
        cache_key = self.cache.get_cache_key(
            "market_signals",
            market=market,
            min_confidence=min_confidence
        )
        return await self.cache.set(cache_key, data, ttl)


class DataCollectionCacheService:
    """數據收集專用快取服務"""

    def __init__(self, cache_service: ICacheService):
        self.cache = cache_service

    async def get_collection_status(
        self,
        stock_id: int,
        start_date: str,
        end_date: str
    ) -> Optional[Dict[str, Any]]:
        """取得收集狀態快取"""
        cache_key = self.cache.get_cache_key(
            "data_collection_status",
            stock_id=stock_id,
            start_date=start_date,
            end_date=end_date
        )
        return await self.cache.get(cache_key)

    async def set_collection_status(
        self,
        stock_id: int,
        start_date: str,
        end_date: str,
        data: Dict[str, Any],
        ttl: int = 3600
    ) -> bool:
        """設置收集狀態快取"""
        cache_key = self.cache.get_cache_key(
            "data_collection_status",
            stock_id=stock_id,
            start_date=start_date,
            end_date=end_date
        )
        return await self.cache.set(cache_key, data, ttl)

    async def get_collection_health(self) -> Optional[Dict[str, Any]]:
        """取得收集健康狀態快取"""
        cache_key = self.cache.get_cache_key("collection_health")
        return await self.cache.get(cache_key)

    async def set_collection_health(
        self,
        data: Dict[str, Any],
        ttl: int = 600
    ) -> bool:
        """設置收集健康狀態快取"""
        cache_key = self.cache.get_cache_key("collection_health")
        return await self.cache.set(cache_key, data, ttl)