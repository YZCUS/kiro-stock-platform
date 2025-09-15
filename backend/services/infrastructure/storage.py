"""
技術指標存儲和快取整合服務
"""
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import date, datetime, timedelta
from dataclasses import dataclass
import logging

from core.database import AsyncSession
from core.redis import redis_client
from services.analysis.technical_analysis import technical_analysis_service, IndicatorType, AnalysisResult
from services.infrastructure.cache import indicator_cache_service
from models.repositories.crud_technical_indicator import technical_indicator_crud
from models.repositories.crud_stock import stock_crud
from models.domain.technical_indicator import TechnicalIndicator

logger = logging.getLogger(__name__)


@dataclass
class StorageResult:
    """存儲結果"""
    success: bool
    indicators_stored: int
    indicators_cached: int
    errors: List[str]
    execution_time_seconds: float


@dataclass
class SyncResult:
    """同步結果"""
    success: bool
    stocks_processed: int
    indicators_updated: int
    cache_refreshed: int
    errors: List[str]


class IndicatorStorageService:
    """技術指標存儲和快取整合服務"""
    
    def __init__(self):
        self.batch_size = 100
        self.cache_expire_seconds = 1800  # 30分鐘
        self.max_concurrent_stocks = 5
    
    async def calculate_and_store_indicators(
        self,
        db_session: AsyncSession,
        stock_id: int,
        indicators: List[IndicatorType] = None,
        days: int = 100,
        enable_cache: bool = True,
        force_recalculate: bool = False
    ) -> StorageResult:
        """
        計算並存儲技術指標
        
        Args:
            db_session: 資料庫會話
            stock_id: 股票ID
            indicators: 要計算的指標列表
            days: 計算天數
            enable_cache: 是否啟用快取
            force_recalculate: 是否強制重新計算
            
        Returns:
            存儲結果
        """
        start_time = datetime.now()
        errors = []
        
        try:
            # 獲取股票資訊
            stock = await stock_crud.get(db_session, stock_id)
            if not stock:
                return StorageResult(
                    success=False,
                    indicators_stored=0,
                    indicators_cached=0,
                    errors=[f"找不到股票 ID: {stock_id}"],
                    execution_time_seconds=0
                )
            
            # 檢查是否需要重新計算
            if not force_recalculate and enable_cache:
                # 檢查快取中是否有最新數據
                cached_data = await indicator_cache_service.get_stock_indicators_from_cache(
                    stock_id, 
                    [ind.value for ind in indicators] if indicators else [],
                    days=1  # 檢查今天的數據
                )
                
                if cached_data:
                    logger.info(f"股票 {stock.symbol} 的指標已是最新，跳過計算")
                    return StorageResult(
                        success=True,
                        indicators_stored=0,
                        indicators_cached=len(cached_data),
                        errors=[],
                        execution_time_seconds=(datetime.now() - start_time).total_seconds()
                    )
            
            # 計算技術指標
            logger.info(f"開始計算股票 {stock.symbol} 的技術指標")
            analysis_result = await technical_analysis_service.calculate_stock_indicators(
                db_session,
                stock_id=stock_id,
                indicators=indicators,
                days=days,
                save_to_db=True  # 直接保存到資料庫
            )
            
            indicators_stored = analysis_result.indicators_successful
            indicators_cached = 0
            
            # 如果啟用快取，將結果快取
            if enable_cache and analysis_result.indicators_successful > 0:
                try:
                    # 獲取剛存儲的指標數據
                    end_date = date.today()
                    start_date = end_date - timedelta(days=7)  # 快取最近7天
                    
                    stored_indicators = await technical_indicator_crud.get_stock_indicators_by_date_range(
                        db_session,
                        stock_id=stock_id,
                        start_date=start_date,
                        end_date=end_date
                    )
                    
                    # 批次快取
                    cached_count = await indicator_cache_service.cache_indicators_batch(
                        stored_indicators,
                        stock.symbol,
                        expire=self.cache_expire_seconds
                    )
                    
                    indicators_cached = cached_count
                    logger.info(f"成功快取 {cached_count} 個指標")
                    
                except Exception as e:
                    error_msg = f"快取指標時發生錯誤: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            # 合併分析錯誤
            errors.extend(analysis_result.errors)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return StorageResult(
                success=analysis_result.indicators_successful > 0,
                indicators_stored=indicators_stored,
                indicators_cached=indicators_cached,
                errors=errors,
                execution_time_seconds=execution_time
            )
            
        except Exception as e:
            error_msg = f"計算和存儲指標時發生錯誤: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return StorageResult(
                success=False,
                indicators_stored=0,
                indicators_cached=0,
                errors=errors,
                execution_time_seconds=execution_time
            )
    
    async def batch_calculate_and_store(
        self,
        db_session: AsyncSession,
        stock_ids: List[int],
        indicators: List[IndicatorType] = None,
        days: int = 100,
        enable_cache: bool = True,
        force_recalculate: bool = False
    ) -> List[StorageResult]:
        """
        批次計算和存儲技術指標
        
        Args:
            db_session: 資料庫會話
            stock_ids: 股票ID列表
            indicators: 要計算的指標列表
            days: 計算天數
            enable_cache: 是否啟用快取
            force_recalculate: 是否強制重新計算
            
        Returns:
            存儲結果列表
        """
        logger.info(f"開始批次計算和存儲 {len(stock_ids)} 支股票的技術指標")
        
        semaphore = asyncio.Semaphore(self.max_concurrent_stocks)
        
        async def process_single_stock(stock_id):
            async with semaphore:
                return await self.calculate_and_store_indicators(
                    db_session,
                    stock_id=stock_id,
                    indicators=indicators,
                    days=days,
                    enable_cache=enable_cache,
                    force_recalculate=force_recalculate
                )
        
        # 並行處理
        tasks = [process_single_stock(stock_id) for stock_id in stock_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 處理異常結果
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"處理股票 {stock_ids[i]} 時發生異常: {str(result)}")
                error_result = StorageResult(
                    success=False,
                    indicators_stored=0,
                    indicators_cached=0,
                    errors=[str(result)],
                    execution_time_seconds=0
                )
                final_results.append(error_result)
            else:
                final_results.append(result)
        
        # 統計結果
        successful = sum(1 for r in final_results if r.success)
        total_stored = sum(r.indicators_stored for r in final_results)
        total_cached = sum(r.indicators_cached for r in final_results)
        
        logger.info(f"批次處理完成: {successful}/{len(final_results)} 成功, "
                   f"存儲 {total_stored} 個指標, 快取 {total_cached} 個指標")
        
        return final_results
    
    async def get_indicators_with_cache(
        self,
        db_session: AsyncSession,
        stock_id: int,
        indicator_types: List[str],
        days: int = 30,
        force_refresh: bool = False
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        取得指標數據（優先使用快取）
        
        Args:
            db_session: 資料庫會話
            stock_id: 股票ID
            indicator_types: 指標類型列表
            days: 天數
            force_refresh: 是否強制刷新
            
        Returns:
            指標數據字典
        """
        return await indicator_cache_service.get_or_calculate_indicators(
            db_session,
            stock_id=stock_id,
            indicator_types=indicator_types,
            days=days,
            force_refresh=force_refresh
        )
    
    async def sync_indicators_with_cache(
        self,
        db_session: AsyncSession,
        stock_ids: List[int] = None,
        indicator_types: List[str] = None,
        sync_days: int = 7
    ) -> SyncResult:
        """
        同步指標數據和快取
        
        Args:
            db_session: 資料庫會話
            stock_ids: 股票ID列表（None表示所有股票）
            indicator_types: 指標類型列表（None表示所有類型）
            sync_days: 同步天數
            
        Returns:
            同步結果
        """
        start_time = datetime.now()
        errors = []
        
        try:
            # 如果沒有指定股票，獲取所有股票
            if stock_ids is None:
                stocks = await stock_crud.get_multi(db_session, limit=1000)
                stock_ids = [stock.id for stock in stocks]
            
            logger.info(f"開始同步 {len(stock_ids)} 支股票的指標數據和快取")
            
            stocks_processed = 0
            indicators_updated = 0
            cache_refreshed = 0
            
            for stock_id in stock_ids:
                try:
                    # 獲取股票資訊
                    stock = await stock_crud.get(db_session, stock_id)
                    if not stock:
                        errors.append(f"找不到股票 ID: {stock_id}")
                        continue
                    
                    # 檢查資料庫中的最新指標日期
                    latest_indicators = await technical_indicator_crud.get_latest_indicators(
                        db_session,
                        stock_id=stock_id,
                        indicator_types=indicator_types
                    )
                    
                    # 檢查是否需要更新
                    today = date.today()
                    needs_update = False
                    
                    if not latest_indicators:
                        needs_update = True
                    else:
                        # 檢查最新數據是否是今天的
                        latest_date = max(ind.date for ind in latest_indicators)
                        if latest_date < today:
                            needs_update = True
                    
                    if needs_update:
                        # 計算和存儲最新指標
                        storage_result = await self.calculate_and_store_indicators(
                            db_session,
                            stock_id=stock_id,
                            indicators=[IndicatorType(t) for t in indicator_types] if indicator_types else None,
                            days=sync_days,
                            enable_cache=True,
                            force_recalculate=True
                        )
                        
                        if storage_result.success:
                            indicators_updated += storage_result.indicators_stored
                            cache_refreshed += storage_result.indicators_cached
                        else:
                            errors.extend(storage_result.errors)
                    else:
                        # 只刷新快取
                        cache_result = await indicator_cache_service.refresh_stock_cache(
                            db_session,
                            stock_id=stock_id,
                            indicator_types=indicator_types
                        )
                        
                        if cache_result['success']:
                            cache_refreshed += cache_result['cached_count']
                        else:
                            errors.append(cache_result['error'])
                    
                    stocks_processed += 1
                    
                    # 每處理10支股票提交一次
                    if stocks_processed % 10 == 0:
                        await db_session.commit()
                        logger.info(f"已處理 {stocks_processed}/{len(stock_ids)} 支股票")
                    
                except Exception as e:
                    error_msg = f"同步股票 {stock_id} 時發生錯誤: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            # 最終提交
            await db_session.commit()
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"同步完成: 處理 {stocks_processed} 支股票, "
                       f"更新 {indicators_updated} 個指標, "
                       f"刷新 {cache_refreshed} 個快取, "
                       f"耗時 {execution_time:.2f} 秒")
            
            return SyncResult(
                success=len(errors) == 0,
                stocks_processed=stocks_processed,
                indicators_updated=indicators_updated,
                cache_refreshed=cache_refreshed,
                errors=errors
            )
            
        except Exception as e:
            error_msg = f"同步指標數據和快取時發生錯誤: {str(e)}"
            logger.error(error_msg)
            
            return SyncResult(
                success=False,
                stocks_processed=0,
                indicators_updated=0,
                cache_refreshed=0,
                errors=[error_msg]
            )
    
    async def cleanup_old_data(
        self,
        db_session: AsyncSession,
        keep_days: int = 365,
        stock_ids: List[int] = None
    ) -> Dict[str, Any]:
        """
        清理舊的指標數據
        
        Args:
            db_session: 資料庫會話
            keep_days: 保留天數
            stock_ids: 股票ID列表（None表示所有股票）
            
        Returns:
            清理結果
        """
        try:
            logger.info(f"開始清理 {keep_days} 天前的指標數據")
            
            total_deleted = 0
            
            if stock_ids is None:
                # 清理所有股票的舊數據
                stocks = await stock_crud.get_multi(db_session, limit=1000)
                stock_ids = [stock.id for stock in stocks]
            
            for stock_id in stock_ids:
                deleted_count = await technical_indicator_crud.delete_old_indicators(
                    db_session,
                    stock_id=stock_id,
                    keep_days=keep_days
                )
                total_deleted += deleted_count
            
            logger.info(f"清理完成: 刪除 {total_deleted} 條舊指標數據")
            
            return {
                'success': True,
                'deleted_count': total_deleted,
                'keep_days': keep_days,
                'stocks_processed': len(stock_ids)
            }
            
        except Exception as e:
            error_msg = f"清理舊數據時發生錯誤: {str(e)}"
            logger.error(error_msg)
            
            return {
                'success': False,
                'error': error_msg,
                'deleted_count': 0
            }
    
    async def get_storage_statistics(
        self,
        db_session: AsyncSession
    ) -> Dict[str, Any]:
        """
        取得存儲統計資訊
        
        Returns:
            統計資訊
        """
        try:
            from sqlalchemy import select, func, distinct
            
            # 統計指標數據
            result = await db_session.execute(
                select(
                    func.count(TechnicalIndicator.id).label('total_indicators'),
                    func.count(distinct(TechnicalIndicator.stock_id)).label('total_stocks'),
                    func.count(distinct(TechnicalIndicator.indicator_type)).label('total_indicator_types'),
                    func.max(TechnicalIndicator.date).label('latest_date'),
                    func.min(TechnicalIndicator.date).label('earliest_date')
                )
            )
            
            row = result.first()
            
            # 取得快取統計
            cache_stats = await indicator_cache_service.get_cache_statistics()
            
            return {
                'database': {
                    'total_indicators': row.total_indicators or 0,
                    'total_stocks': row.total_stocks or 0,
                    'total_indicator_types': row.total_indicator_types or 0,
                    'latest_date': row.latest_date.isoformat() if row.latest_date else None,
                    'earliest_date': row.earliest_date.isoformat() if row.earliest_date else None
                },
                'cache': {
                    'hit_count': cache_stats.hit_count,
                    'miss_count': cache_stats.miss_count,
                    'hit_rate': cache_stats.hit_rate,
                    'total_keys': cache_stats.total_keys,
                    'cache_size_mb': cache_stats.cache_size_mb
                }
            }
            
        except Exception as e:
            logger.error(f"取得存儲統計時發生錯誤: {str(e)}")
            return {
                'database': {},
                'cache': {},
                'error': str(e)
            }
    
    async def validate_data_integrity(
        self,
        db_session: AsyncSession,
        stock_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        驗證數據完整性
        
        Args:
            db_session: 資料庫會話
            stock_id: 股票ID
            days: 檢查天數
            
        Returns:
            驗證結果
        """
        try:
            stock = await stock_crud.get(db_session, stock_id)
            if not stock:
                return {
                    'success': False,
                    'error': f'找不到股票 ID: {stock_id}'
                }
            
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            # 檢查指標數據完整性
            indicators = await technical_indicator_crud.get_stock_indicators_by_date_range(
                db_session,
                stock_id=stock_id,
                start_date=start_date,
                end_date=end_date
            )
            
            # 按指標類型分組
            indicator_groups = {}
            for indicator in indicators:
                if indicator.indicator_type not in indicator_groups:
                    indicator_groups[indicator.indicator_type] = []
                indicator_groups[indicator.indicator_type].append(indicator)
            
            # 檢查每個指標類型的數據完整性
            integrity_report = {
                'stock_symbol': stock.symbol,
                'check_period': f'{start_date} to {end_date}',
                'indicator_types': {},
                'overall_health': 'good'
            }
            
            issues_found = 0
            
            for indicator_type, type_indicators in indicator_groups.items():
                # 檢查數據點數量
                expected_days = (end_date - start_date).days + 1
                actual_days = len(type_indicators)
                
                # 檢查數據連續性
                dates = sorted([ind.date for ind in type_indicators])
                missing_dates = []
                
                current_date = start_date
                while current_date <= end_date:
                    if current_date not in dates:
                        missing_dates.append(current_date)
                    current_date += timedelta(days=1)
                
                # 檢查數值異常
                values = [float(ind.value) for ind in type_indicators if ind.value is not None]
                null_values = len(type_indicators) - len(values)
                
                health_status = 'good'
                issues = []
                
                if len(missing_dates) > expected_days * 0.1:  # 超過10%缺失
                    health_status = 'poor'
                    issues.append(f'缺失 {len(missing_dates)} 天數據')
                    issues_found += 1
                elif len(missing_dates) > 0:
                    health_status = 'fair'
                    issues.append(f'缺失 {len(missing_dates)} 天數據')
                
                if null_values > actual_days * 0.05:  # 超過5%空值
                    health_status = 'poor'
                    issues.append(f'{null_values} 個空值')
                    issues_found += 1
                
                integrity_report['indicator_types'][indicator_type] = {
                    'expected_days': expected_days,
                    'actual_days': actual_days,
                    'missing_dates': len(missing_dates),
                    'null_values': null_values,
                    'health_status': health_status,
                    'issues': issues
                }
            
            # 整體健康狀態
            if issues_found > 5:
                integrity_report['overall_health'] = 'poor'
            elif issues_found > 0:
                integrity_report['overall_health'] = 'fair'
            
            return {
                'success': True,
                'integrity_report': integrity_report,
                'issues_found': issues_found
            }
            
        except Exception as e:
            logger.error(f"驗證數據完整性時發生錯誤: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


# 建立全域服務實例
indicator_storage_service = IndicatorStorageService()