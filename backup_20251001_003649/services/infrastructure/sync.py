"""
技術指標同步和更新服務
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import date, datetime, timedelta
from dataclasses import dataclass
import logging

from core.database import AsyncSession, get_db
from services.infrastructure.storage import indicator_storage_service
from services.infrastructure.cache import indicator_cache_service
from services.analysis.technical_analysis import IndicatorType
from infrastructure.persistence.stock_repository import StockRepository
from infrastructure.persistence.technical_indicator_repository import TechnicalIndicatorRepository

logger = logging.getLogger(__name__)


@dataclass
class SyncSchedule:
    """同步排程"""
    stock_ids: List[int]
    indicator_types: List[str]
    sync_frequency: str  # 'daily', 'hourly', 'manual'
    last_sync: Optional[datetime]
    next_sync: Optional[datetime]
    enabled: bool


@dataclass
class SyncStatus:
    """同步狀態"""
    is_running: bool
    current_stock_id: Optional[int]
    progress_percentage: float
    start_time: Optional[datetime]
    estimated_completion: Optional[datetime]
    last_error: Optional[str]


class IndicatorSyncService:
    """技術指標同步服務"""
    
    def __init__(self):
        self.sync_status = SyncStatus(
            is_running=False,
            current_stock_id=None,
            progress_percentage=0.0,
            start_time=None,
            estimated_completion=None,
            last_error=None
        )
        self.sync_schedules: Dict[str, SyncSchedule] = {}
        self.default_indicators = [
            IndicatorType.RSI,
            IndicatorType.SMA_5,
            IndicatorType.SMA_20,
            IndicatorType.SMA_60,
            IndicatorType.EMA_12,
            IndicatorType.EMA_26,
            IndicatorType.MACD,
            IndicatorType.BB_UPPER,
            IndicatorType.KD_K
        ]
    
    async def create_sync_schedule(
        self,
        schedule_name: str,
        stock_ids: List[int],
        indicator_types: List[str] = None,
        sync_frequency: str = 'daily'
    ) -> Dict[str, Any]:
        """
        建立同步排程
        
        Args:
            schedule_name: 排程名稱
            stock_ids: 股票ID列表
            indicator_types: 指標類型列表
            sync_frequency: 同步頻率
            
        Returns:
            建立結果
        """
        try:
            if indicator_types is None:
                indicator_types = [ind.value for ind in self.default_indicators]
            
            # 計算下次同步時間
            next_sync = self._calculate_next_sync_time(sync_frequency)
            
            schedule = SyncSchedule(
                stock_ids=stock_ids,
                indicator_types=indicator_types,
                sync_frequency=sync_frequency,
                last_sync=None,
                next_sync=next_sync,
                enabled=True
            )
            
            self.sync_schedules[schedule_name] = schedule
            
            logger.info(f"建立同步排程 '{schedule_name}': {len(stock_ids)} 支股票, "
                       f"{len(indicator_types)} 種指標, 頻率: {sync_frequency}")
            
            return {
                'success': True,
                'schedule_name': schedule_name,
                'stock_count': len(stock_ids),
                'indicator_count': len(indicator_types),
                'next_sync': next_sync.isoformat() if next_sync else None
            }
            
        except Exception as e:
            logger.error(f"建立同步排程時發生錯誤: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _calculate_next_sync_time(self, frequency: str) -> Optional[datetime]:
        """計算下次同步時間"""
        now = datetime.now()
        
        if frequency == 'daily':
            # 每天16:30執行（股市收盤後）
            next_sync = now.replace(hour=16, minute=30, second=0, microsecond=0)
            if next_sync <= now:
                next_sync += timedelta(days=1)
            return next_sync
        
        elif frequency == 'hourly':
            # 每小時執行
            next_sync = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            return next_sync
        
        elif frequency == 'manual':
            return None
        
        else:
            logger.warning(f"未知的同步頻率: {frequency}")
            return None
    
    async def execute_sync_schedule(
        self,
        schedule_name: str,
        force_sync: bool = False
    ) -> Dict[str, Any]:
        """
        執行同步排程
        
        Args:
            schedule_name: 排程名稱
            force_sync: 是否強制同步
            
        Returns:
            執行結果
        """
        if self.sync_status.is_running and not force_sync:
            return {
                'success': False,
                'error': '同步正在進行中，請稍後再試'
            }
        
        if schedule_name not in self.sync_schedules:
            return {
                'success': False,
                'error': f'找不到同步排程: {schedule_name}'
            }
        
        schedule = self.sync_schedules[schedule_name]
        
        if not schedule.enabled:
            return {
                'success': False,
                'error': f'同步排程 {schedule_name} 已停用'
            }
        
        # 檢查是否到了同步時間
        now = datetime.now()
        if not force_sync and schedule.next_sync and now < schedule.next_sync:
            return {
                'success': False,
                'error': f'尚未到同步時間，下次同步: {schedule.next_sync}'
            }
        
        try:
            # 更新同步狀態
            self.sync_status.is_running = True
            self.sync_status.start_time = now
            self.sync_status.progress_percentage = 0.0
            self.sync_status.last_error = None
            
            logger.info(f"開始執行同步排程 '{schedule_name}'")
            
            # 執行同步
            async with get_db() as db_session:
                sync_result = await indicator_storage_service.sync_indicators_with_cache(
                    db_session,
                    stock_ids=schedule.stock_ids,
                    indicator_types=schedule.indicator_types,
                    sync_days=7
                )
            
            # 更新排程狀態
            schedule.last_sync = now
            schedule.next_sync = self._calculate_next_sync_time(schedule.sync_frequency)
            
            # 重置同步狀態
            self.sync_status.is_running = False
            self.sync_status.current_stock_id = None
            self.sync_status.progress_percentage = 100.0
            
            if sync_result.success:
                logger.info(f"同步排程 '{schedule_name}' 執行成功")
                return {
                    'success': True,
                    'schedule_name': schedule_name,
                    'stocks_processed': sync_result.stocks_processed,
                    'indicators_updated': sync_result.indicators_updated,
                    'cache_refreshed': sync_result.cache_refreshed,
                    'next_sync': schedule.next_sync.isoformat() if schedule.next_sync else None
                }
            else:
                self.sync_status.last_error = '; '.join(sync_result.errors)
                return {
                    'success': False,
                    'error': f'同步失敗: {"; ".join(sync_result.errors[:3])}'
                }
            
        except Exception as e:
            error_msg = f"執行同步排程時發生錯誤: {str(e)}"
            logger.error(error_msg)
            
            self.sync_status.is_running = False
            self.sync_status.last_error = error_msg
            
            return {
                'success': False,
                'error': error_msg
            }
    
    async def sync_single_stock(
        self,
        stock_id: int,
        indicator_types: List[str] = None,
        force_recalculate: bool = False
    ) -> Dict[str, Any]:
        """
        同步單支股票的指標
        
        Args:
            stock_id: 股票ID
            indicator_types: 指標類型列表
            force_recalculate: 是否強制重新計算
            
        Returns:
            同步結果
        """
        try:
            async with get_db() as db_session:
                # 獲取股票資訊
                stock_repo = StockRepository(db_session)
                stock = await stock_repo.get_by_id(db_session, stock_id)
                if not stock:
                    return {
                        'success': False,
                        'error': f'找不到股票 ID: {stock_id}'
                    }
                
                # 執行同步
                storage_result = await indicator_storage_service.calculate_and_store_indicators(
                    db_session,
                    stock_id=stock_id,
                    indicators=[IndicatorType(t) for t in indicator_types] if indicator_types else None,
                    days=100,
                    enable_cache=True,
                    force_recalculate=force_recalculate
                )
                
                return {
                    'success': storage_result.success,
                    'stock_symbol': stock.symbol,
                    'indicators_stored': storage_result.indicators_stored,
                    'indicators_cached': storage_result.indicators_cached,
                    'execution_time': storage_result.execution_time_seconds,
                    'errors': storage_result.errors
                }
                
        except Exception as e:
            logger.error(f"同步單支股票時發生錯誤: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def sync_missing_indicators(
        self,
        days_back: int = 7,
        max_stocks: int = 100
    ) -> Dict[str, Any]:
        """
        同步缺失的指標數據
        
        Args:
            days_back: 檢查天數
            max_stocks: 最大處理股票數
            
        Returns:
            同步結果
        """
        try:
            async with get_db() as db_session:
                # 獲取所有股票
                stock_repo = StockRepository(db_session)
                stocks = await stock_repo.get_all(db_session, skip=0, limit=max_stocks)

                missing_data_stocks = []
                end_date = date.today()
                start_date = end_date - timedelta(days=days_back)

                # 檢查每支股票的指標完整性
                indicator_repo = TechnicalIndicatorRepository(db_session)
                for stock in stocks:
                    indicators = await indicator_repo.get_by_stock_and_date_range(
                        db_session,
                        stock_id=stock.id,
                        start_date=start_date,
                        end_date=end_date
                    )
                    
                    # 檢查是否有最近的數據
                    if not indicators:
                        missing_data_stocks.append(stock.id)
                    else:
                        latest_date = max(ind.date for ind in indicators)
                        if (end_date - latest_date).days > 2:  # 超過2天沒有數據
                            missing_data_stocks.append(stock.id)
                
                if not missing_data_stocks:
                    return {
                        'success': True,
                        'message': '所有股票的指標數據都是最新的',
                        'stocks_checked': len(stocks),
                        'missing_stocks': 0
                    }
                
                logger.info(f"發現 {len(missing_data_stocks)} 支股票缺失指標數據，開始同步")
                
                # 批次同步缺失數據
                sync_results = await indicator_storage_service.batch_calculate_and_store(
                    db_session,
                    stock_ids=missing_data_stocks,
                    indicators=self.default_indicators,
                    days=days_back + 30,  # 多計算一些天數確保完整性
                    enable_cache=True,
                    force_recalculate=True
                )
                
                # 統計結果
                successful_syncs = sum(1 for r in sync_results if r.success)
                total_indicators = sum(r.indicators_stored for r in sync_results)
                total_cached = sum(r.indicators_cached for r in sync_results)
                
                return {
                    'success': True,
                    'stocks_checked': len(stocks),
                    'missing_stocks': len(missing_data_stocks),
                    'successful_syncs': successful_syncs,
                    'total_indicators_stored': total_indicators,
                    'total_indicators_cached': total_cached
                }
                
        except Exception as e:
            logger.error(f"同步缺失指標時發生錯誤: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def refresh_cache_for_active_stocks(
        self,
        activity_days: int = 7,
        max_stocks: int = 50
    ) -> Dict[str, Any]:
        """
        為活躍股票刷新快取
        
        Args:
            activity_days: 活躍天數定義
            max_stocks: 最大處理股票數
            
        Returns:
            刷新結果
        """
        try:
            async with get_db() as db_session:
                # 這裡簡化實現，實際可以根據查詢頻率等指標確定活躍股票
                # 目前選擇最近有指標更新的股票
                from sqlalchemy import select, func, desc
                from models.domain.technical_indicator import TechnicalIndicator

                result = await db_session.execute(
                    select(
                        TechnicalIndicator.stock_id,
                        func.max(TechnicalIndicator.updated_at).label('last_update')
                    ).group_by(
                        TechnicalIndicator.stock_id
                    ).order_by(
                        desc('last_update')
                    ).limit(max_stocks)
                )

                active_stock_ids = [row.stock_id for row in result.fetchall()]
                
                if not active_stock_ids:
                    return {
                        'success': True,
                        'message': '沒有找到活躍股票',
                        'refreshed_stocks': 0
                    }
                
                logger.info(f"為 {len(active_stock_ids)} 支活躍股票刷新快取")
                
                refreshed_count = 0
                errors = []
                
                for stock_id in active_stock_ids:
                    try:
                        cache_result = await indicator_cache_service.refresh_stock_cache(
                            db_session,
                            stock_id=stock_id
                        )
                        
                        if cache_result['success']:
                            refreshed_count += 1
                        else:
                            errors.append(cache_result['error'])
                            
                    except Exception as e:
                        errors.append(f"刷新股票 {stock_id} 快取時發生錯誤: {str(e)}")
                
                return {
                    'success': len(errors) == 0,
                    'refreshed_stocks': refreshed_count,
                    'total_active_stocks': len(active_stock_ids),
                    'errors': errors[:5]  # 只返回前5個錯誤
                }
                
        except Exception as e:
            logger.error(f"刷新活躍股票快取時發生錯誤: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """取得同步狀態"""
        return {
            'is_running': self.sync_status.is_running,
            'current_stock_id': self.sync_status.current_stock_id,
            'progress_percentage': self.sync_status.progress_percentage,
            'start_time': self.sync_status.start_time.isoformat() if self.sync_status.start_time else None,
            'estimated_completion': self.sync_status.estimated_completion.isoformat() if self.sync_status.estimated_completion else None,
            'last_error': self.sync_status.last_error,
            'active_schedules': len([s for s in self.sync_schedules.values() if s.enabled])
        }
    
    async def get_sync_schedules(self) -> Dict[str, Dict[str, Any]]:
        """取得所有同步排程"""
        schedules_info = {}
        
        for name, schedule in self.sync_schedules.items():
            schedules_info[name] = {
                'stock_count': len(schedule.stock_ids),
                'indicator_count': len(schedule.indicator_types),
                'sync_frequency': schedule.sync_frequency,
                'last_sync': schedule.last_sync.isoformat() if schedule.last_sync else None,
                'next_sync': schedule.next_sync.isoformat() if schedule.next_sync else None,
                'enabled': schedule.enabled
            }
        
        return schedules_info
    
    async def enable_schedule(self, schedule_name: str) -> Dict[str, Any]:
        """啟用同步排程"""
        if schedule_name not in self.sync_schedules:
            return {
                'success': False,
                'error': f'找不到同步排程: {schedule_name}'
            }
        
        self.sync_schedules[schedule_name].enabled = True
        self.sync_schedules[schedule_name].next_sync = self._calculate_next_sync_time(
            self.sync_schedules[schedule_name].sync_frequency
        )
        
        return {
            'success': True,
            'message': f'同步排程 {schedule_name} 已啟用'
        }
    
    async def disable_schedule(self, schedule_name: str) -> Dict[str, Any]:
        """停用同步排程"""
        if schedule_name not in self.sync_schedules:
            return {
                'success': False,
                'error': f'找不到同步排程: {schedule_name}'
            }
        
        self.sync_schedules[schedule_name].enabled = False
        self.sync_schedules[schedule_name].next_sync = None
        
        return {
            'success': True,
            'message': f'同步排程 {schedule_name} 已停用'
        }
    
    async def delete_schedule(self, schedule_name: str) -> Dict[str, Any]:
        """刪除同步排程"""
        if schedule_name not in self.sync_schedules:
            return {
                'success': False,
                'error': f'找不到同步排程: {schedule_name}'
            }
        
        del self.sync_schedules[schedule_name]
        
        return {
            'success': True,
            'message': f'同步排程 {schedule_name} 已刪除'
        }
    
    async def run_scheduled_sync_check(self):
        """執行排程同步檢查（由定時任務調用）"""
        now = datetime.now()
        
        for schedule_name, schedule in self.sync_schedules.items():
            if (schedule.enabled and 
                schedule.next_sync and 
                now >= schedule.next_sync and
                not self.sync_status.is_running):
                
                logger.info(f"執行排程同步: {schedule_name}")
                result = await self.execute_sync_schedule(schedule_name)
                
                if result['success']:
                    logger.info(f"排程同步 {schedule_name} 執行成功")
                else:
                    logger.error(f"排程同步 {schedule_name} 執行失敗: {result['error']}")


# 建立全域服務實例
indicator_sync_service = IndicatorSyncService()