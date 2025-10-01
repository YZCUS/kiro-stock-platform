"""
技術指標快取服務
"""
import asyncio
import json
from typing import List, Dict, Any, Optional
from datetime import date, datetime, timedelta
from dataclasses import dataclass, asdict
import logging

from core.redis import redis_client
from app.settings import settings
from models.domain.technical_indicator import TechnicalIndicator
# ✅ Clean Architecture: 使用 repository implementations
from infrastructure.persistence.technical_indicator_repository import TechnicalIndicatorRepository
from infrastructure.persistence.stock_repository import StockRepository

logger = logging.getLogger(__name__)


@dataclass
class CachedIndicator:
    """快取的指標數據"""
    stock_id: int
    stock_symbol: str
    indicator_type: str
    value: float
    date: str
    parameters: Dict[str, Any]
    cached_at: str


@dataclass
class CacheStatistics:
    """快取統計"""
    total_keys: int
    hit_count: int
    miss_count: int
    hit_rate: float
    cache_size_mb: float
    oldest_entry: str
    newest_entry: str


class IndicatorCacheService:
    """技術指標快取服務"""
    
    def __init__(self):
        self.cache_prefix = "indicator"
        self.default_expire = settings.redis.default_ttl
        self.hit_count = 0
        self.miss_count = 0
    
    def _generate_cache_key(
        self, 
        stock_id: int, 
        indicator_type: str, 
        date: date = None
    ) -> str:
        """生成快取鍵"""
        if date:
            return f"{self.cache_prefix}:{stock_id}:{indicator_type}:{date.isoformat()}"
        else:
            return f"{self.cache_prefix}:{stock_id}:{indicator_type}:latest"
    
    def _generate_batch_cache_key(
        self, 
        stock_id: int, 
        indicator_types: List[str], 
        days: int = 30
    ) -> str:
        """生成批次快取鍵"""
        types_str = "_".join(sorted(indicator_types))
        return f"{self.cache_prefix}:batch:{stock_id}:{types_str}:{days}"
    
    async def cache_indicator(
        self,
        stock_id: int,
        stock_symbol: str,
        indicator_type: str,
        value: float,
        date: date,
        parameters: Dict[str, Any] = None,
        expire: int = None
    ) -> bool:
        """快取單個指標"""
        try:
            cache_key = self._generate_cache_key(stock_id, indicator_type, date)
            
            cached_indicator = CachedIndicator(
                stock_id=stock_id,
                stock_symbol=stock_symbol,
                indicator_type=indicator_type,
                value=value,
                date=date.isoformat(),
                parameters=parameters or {},
                cached_at=datetime.now().isoformat()
            )
            
            success = await redis_client.set(
                cache_key, 
                asdict(cached_indicator), 
                expire=expire or self.default_expire
            )
            
            # 同時快取為最新指標
            latest_key = self._generate_cache_key(stock_id, indicator_type)
            await redis_client.set(
                latest_key, 
                asdict(cached_indicator), 
                expire=expire or self.default_expire
            )
            
            if success:
                logger.debug(f"成功快取指標: {cache_key}")
            
            return success
            
        except Exception as e:
            logger.error(f"快取指標時發生錯誤: {str(e)}")
            return False
    
    async def get_cached_indicator(
        self,
        stock_id: int,
        indicator_type: str,
        date: date = None
    ) -> Optional[CachedIndicator]:
        """取得快取的指標"""
        try:
            cache_key = self._generate_cache_key(stock_id, indicator_type, date)
            cached_data = await redis_client.get(cache_key)
            
            if cached_data:
                self.hit_count += 1
                return CachedIndicator(**cached_data)
            else:
                self.miss_count += 1
                return None
                
        except Exception as e:
            logger.error(f"取得快取指標時發生錯誤: {str(e)}")
            self.miss_count += 1
            return None
    
    async def cache_indicators_batch(
        self,
        indicators: List[TechnicalIndicator],
        stock_symbol: str,
        expire: int = None
    ) -> int:
        """批次快取指標"""
        cached_count = 0
        
        for indicator in indicators:
            try:
                success = await self.cache_indicator(
                    stock_id=indicator.stock_id,
                    stock_symbol=stock_symbol,
                    indicator_type=indicator.indicator_type,
                    value=float(indicator.value) if indicator.value else 0,
                    date=indicator.date,
                    parameters=indicator.parameters,
                    expire=expire
                )
                
                if success:
                    cached_count += 1
                    
            except Exception as e:
                logger.error(f"批次快取指標時發生錯誤: {str(e)}")
        
        logger.info(f"批次快取完成: {cached_count}/{len(indicators)} 個指標")
        return cached_count
    
    async def get_stock_indicators_from_cache(
        self,
        stock_id: int,
        indicator_types: List[str],
        days: int = 30
    ) -> Dict[str, List[Dict[str, Any]]]:
        """從快取取得股票指標數據"""
        try:
            # 嘗試取得批次快取
            batch_key = self._generate_batch_cache_key(stock_id, indicator_types, days)
            batch_data = await redis_client.get(batch_key)
            
            if batch_data:
                self.hit_count += 1
                logger.debug(f"批次快取命中: {batch_key}")
                return batch_data
            
            # 批次快取未命中，嘗試個別快取
            indicators_data = {}
            cache_hits = 0
            
            for indicator_type in indicator_types:
                # 取得最新指標
                cached_indicator = await self.get_cached_indicator(
                    stock_id, indicator_type
                )
                
                if cached_indicator:
                    cache_hits += 1
                    if indicator_type not in indicators_data:
                        indicators_data[indicator_type] = []
                    
                    indicators_data[indicator_type].append({
                        'date': cached_indicator.date,
                        'value': cached_indicator.value,
                        'parameters': cached_indicator.parameters
                    })
            
            # 如果所有指標都有快取，則快取批次結果
            if cache_hits == len(indicator_types):
                await redis_client.set(
                    batch_key, 
                    indicators_data, 
                    expire=self.default_expire // 2  # 批次快取較短過期時間
                )
                logger.debug(f"建立批次快取: {batch_key}")
            
            return indicators_data
            
        except Exception as e:
            logger.error(f"從快取取得股票指標時發生錯誤: {str(e)}")
            return {}
    
    async def cache_stock_indicators_batch(
        self,
        db_session,
        stock_id: int,
        stock_symbol: str,
        indicator_types: List[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """批次快取股票指標數據"""
        try:
            # 從資料庫取得指標數據
            end_date = date.today()
            start_date = end_date - timedelta(days=days)

            # ✅ 使用 repository
            indicator_repo = TechnicalIndicatorRepository(db_session)
            indicators = await indicator_repo.get_by_stock_and_date_range(
                db_session,
                stock_id=stock_id,
                start_date=start_date,
                end_date=end_date,
                indicator_types=indicator_types
            )
            
            if not indicators:
                return {
                    'success': False,
                    'message': '沒有找到指標數據',
                    'cached_count': 0
                }
            
            # 批次快取
            cached_count = await self.cache_indicators_batch(
                indicators, stock_symbol
            )
            
            # 建立批次快取數據結構
            indicators_data = {}
            for indicator in indicators:
                if indicator.indicator_type not in indicators_data:
                    indicators_data[indicator.indicator_type] = []
                
                indicators_data[indicator.indicator_type].append({
                    'date': indicator.date.isoformat(),
                    'value': float(indicator.value) if indicator.value else 0,
                    'parameters': indicator.parameters
                })
            
            # 快取批次數據
            if indicator_types:
                batch_key = self._generate_batch_cache_key(stock_id, indicator_types, days)
                await redis_client.set(
                    batch_key, 
                    indicators_data, 
                    expire=self.default_expire // 2
                )
            
            return {
                'success': True,
                'cached_count': cached_count,
                'indicator_types': list(indicators_data.keys()),
                'total_data_points': len(indicators)
            }
            
        except Exception as e:
            logger.error(f"批次快取股票指標時發生錯誤: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'cached_count': 0
            }
    
    async def invalidate_stock_indicators(
        self,
        stock_id: int,
        indicator_types: List[str] = None
    ) -> int:
        """使股票指標快取失效"""
        try:
            invalidated_count = 0
            
            if indicator_types:
                # 使指定指標類型的快取失效
                for indicator_type in indicator_types:
                    # 最新指標快取
                    latest_key = self._generate_cache_key(stock_id, indicator_type)
                    if await redis_client.delete(latest_key):
                        invalidated_count += 1
                    
                    # 批次快取（需要模糊匹配）
                    # 這裡簡化處理，實際可以使用 Redis SCAN 命令
                    for days in [7, 14, 30, 60, 90]:
                        batch_key = self._generate_batch_cache_key(stock_id, [indicator_type], days)
                        if await redis_client.delete(batch_key):
                            invalidated_count += 1
            else:
                # 使所有指標快取失效（模糊匹配）
                # 實際實現中可以使用 Redis SCAN 命令來找出所有相關鍵
                common_indicator_types = [
                    'RSI', 'SMA_5', 'SMA_20', 'SMA_60', 'EMA_12', 'EMA_26',
                    'MACD', 'MACD_SIGNAL', 'MACD_HISTOGRAM',
                    'BB_UPPER', 'BB_MIDDLE', 'BB_LOWER',
                    'KD_K', 'KD_D'
                ]
                
                for indicator_type in common_indicator_types:
                    latest_key = self._generate_cache_key(stock_id, indicator_type)
                    if await redis_client.delete(latest_key):
                        invalidated_count += 1
            
            logger.info(f"使 {invalidated_count} 個指標快取失效")
            return invalidated_count
            
        except Exception as e:
            logger.error(f"使指標快取失效時發生錯誤: {str(e)}")
            return 0
    
    async def warm_up_cache(
        self,
        db_session,
        stock_ids: List[int],
        indicator_types: List[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """預熱快取"""
        try:
            logger.info(f"開始預熱 {len(stock_ids)} 支股票的指標快取")

            # ✅ 使用 repository
            stock_repo = StockRepository(db_session)

            warm_up_results = {
                'processed_stocks': 0,
                'successful_caches': 0,
                'failed_caches': 0,
                'total_indicators_cached': 0,
                'errors': []
            }

            for stock_id in stock_ids:
                try:
                    # 獲取股票資訊
                    stock = await stock_repo.get(db_session, stock_id)
                    if not stock:
                        warm_up_results['errors'].append(f"找不到股票 ID: {stock_id}")
                        continue
                    
                    # 快取股票指標
                    cache_result = await self.cache_stock_indicators_batch(
                        db_session,
                        stock_id=stock_id,
                        stock_symbol=stock.symbol,
                        indicator_types=indicator_types,
                        days=days
                    )
                    
                    warm_up_results['processed_stocks'] += 1
                    
                    if cache_result['success']:
                        warm_up_results['successful_caches'] += 1
                        warm_up_results['total_indicators_cached'] += cache_result['cached_count']
                    else:
                        warm_up_results['failed_caches'] += 1
                        warm_up_results['errors'].append(f"快取股票 {stock.symbol} 失敗: {cache_result.get('error', 'Unknown')}")
                    
                except Exception as e:
                    warm_up_results['failed_caches'] += 1
                    error_msg = f"處理股票 {stock_id} 時發生錯誤: {str(e)}"
                    logger.error(error_msg)
                    warm_up_results['errors'].append(error_msg)
            
            logger.info(f"快取預熱完成: {warm_up_results['successful_caches']}/{warm_up_results['processed_stocks']} 成功")
            return warm_up_results
            
        except Exception as e:
            logger.error(f"預熱快取時發生錯誤: {str(e)}")
            return {
                'processed_stocks': 0,
                'successful_caches': 0,
                'failed_caches': 0,
                'total_indicators_cached': 0,
                'errors': [str(e)]
            }
    
    async def get_or_calculate_indicators(
        self,
        db_session,
        stock_id: int,
        indicator_types: List[str],
        days: int = 30,
        force_refresh: bool = False
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        取得或計算指標（快取優先）
        
        Args:
            db_session: 資料庫會話
            stock_id: 股票ID
            indicator_types: 指標類型列表
            days: 天數
            force_refresh: 是否強制重新計算
            
        Returns:
            指標數據字典
        """
        try:
            if not force_refresh:
                # 嘗試從快取取得
                cached_data = await self.get_stock_indicators_from_cache(
                    stock_id, indicator_types, days
                )
                
                if cached_data and len(cached_data) == len(indicator_types):
                    logger.debug(f"從快取取得股票 {stock_id} 的指標數據")
                    return cached_data
            
            # 快取未命中或強制刷新，從資料庫取得
            logger.debug(f"從資料庫取得股票 {stock_id} 的指標數據")
            
            end_date = date.today()
            start_date = end_date - timedelta(days=days)

            # ✅ 使用 repository
            indicator_repo = TechnicalIndicatorRepository(db_session)
            indicators = await indicator_repo.get_by_stock_and_date_range(
                db_session,
                stock_id=stock_id,
                start_date=start_date,
                end_date=end_date,
                indicator_types=indicator_types
            )

            # 轉換為返回格式
            indicators_data = {}
            for indicator in indicators:
                if indicator.indicator_type not in indicators_data:
                    indicators_data[indicator.indicator_type] = []

                indicators_data[indicator.indicator_type].append({
                    'date': indicator.date.isoformat(),
                    'value': float(indicator.value) if indicator.value else 0,
                    'parameters': indicator.parameters
                })

            # 快取結果
            if indicators_data:
                stock_repo = StockRepository(db_session)
                stock = await stock_repo.get(db_session, stock_id)
                if stock:
                    await self.cache_indicators_batch(indicators, stock.symbol)
            
            return indicators_data
            
        except Exception as e:
            logger.error(f"取得或計算指標時發生錯誤: {str(e)}")
            return {}
    
    async def get_cache_statistics(self) -> CacheStatistics:
        """取得快取統計"""
        try:
            # 這裡簡化實現，實際可以使用 Redis INFO 命令取得更詳細統計
            total_hit_miss = self.hit_count + self.miss_count
            hit_rate = (self.hit_count / total_hit_miss) if total_hit_miss > 0 else 0
            
            return CacheStatistics(
                total_keys=0,  # 需要使用 Redis DBSIZE 命令
                hit_count=self.hit_count,
                miss_count=self.miss_count,
                hit_rate=hit_rate,
                cache_size_mb=0,  # 需要使用 Redis MEMORY USAGE 命令
                oldest_entry="",
                newest_entry=""
            )
            
        except Exception as e:
            logger.error(f"取得快取統計時發生錯誤: {str(e)}")
            return CacheStatistics(0, 0, 0, 0, 0, "", "")
    
    async def clear_expired_cache(self) -> int:
        """清理過期快取"""
        try:
            # Redis 會自動清理過期鍵，這裡主要是統計和日誌
            logger.info("Redis 自動清理過期快取")
            return 0
            
        except Exception as e:
            logger.error(f"清理過期快取時發生錯誤: {str(e)}")
            return 0
    
    async def refresh_stock_cache(
        self,
        db_session,
        stock_id: int,
        indicator_types: List[str] = None
    ) -> Dict[str, Any]:
        """刷新股票快取"""
        try:
            # ✅ 使用 repository
            stock_repo = StockRepository(db_session)

            # 獲取股票資訊
            stock = await stock_repo.get(db_session, stock_id)
            if not stock:
                return {
                    'success': False,
                    'error': f'找不到股票 ID: {stock_id}'
                }
            
            # 使舊快取失效
            invalidated_count = await self.invalidate_stock_indicators(
                stock_id, indicator_types
            )
            
            # 重新快取
            cache_result = await self.cache_stock_indicators_batch(
                db_session,
                stock_id=stock_id,
                stock_symbol=stock.symbol,
                indicator_types=indicator_types,
                days=30
            )
            
            return {
                'success': True,
                'stock_symbol': stock.symbol,
                'invalidated_count': invalidated_count,
                'cached_count': cache_result.get('cached_count', 0),
                'indicator_types': cache_result.get('indicator_types', [])
            }
            
        except Exception as e:
            logger.error(f"刷新股票快取時發生錯誤: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


# 建立全域服務實例
indicator_cache_service = IndicatorCacheService()