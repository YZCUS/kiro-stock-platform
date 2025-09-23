"""
數據收集排程和監控服務
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import date, datetime, timedelta, time
from dataclasses import dataclass
from enum import Enum
import logging

from core.config import settings
from services.data.collection import data_collection_service
from services.data.validation import data_validation_service
from services.data.cleaning import data_cleaning_service
from models.repositories.crud_stock import stock_crud
from models.domain.system_log import SystemLog

logger = logging.getLogger(__name__)


class ScheduleStatus(str, Enum):
    """排程狀態"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """任務優先級"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class ScheduledTask:
    """排程任務"""
    task_id: str
    task_type: str
    priority: TaskPriority
    scheduled_time: datetime
    parameters: Dict[str, Any]
    status: ScheduleStatus = ScheduleStatus.PENDING
    created_at: datetime = None
    started_at: datetime = None
    completed_at: datetime = None
    error_message: str = None
    result: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class CollectionSummary:
    """收集摘要"""
    date: date
    total_stocks: int
    successful_collections: int
    failed_collections: int
    total_data_points: int
    execution_time_seconds: float
    errors: List[str]
    quality_issues: List[str]


class DataCollectionScheduler:
    """數據收集排程器"""
    
    def __init__(self):
        self.tasks: List[ScheduledTask] = []
        self.is_running = False
        self.current_task: Optional[ScheduledTask] = None
    
    def schedule_daily_collection(
        self, 
        execution_time: time = time(16, 0),  # 下午4點
        priority: TaskPriority = TaskPriority.HIGH
    ) -> str:
        """排程每日數據收集"""
        now = datetime.now()
        scheduled_datetime = datetime.combine(now.date(), execution_time)
        
        # 如果今天的時間已過，排程到明天
        if scheduled_datetime <= now:
            scheduled_datetime += timedelta(days=1)
        
        task = ScheduledTask(
            task_id=f"daily_collection_{scheduled_datetime.strftime('%Y%m%d_%H%M')}",
            task_type="daily_collection",
            priority=priority,
            scheduled_time=scheduled_datetime,
            parameters={}
        )
        
        self.tasks.append(task)
        logger.info(f"已排程每日數據收集任務: {task.task_id} at {scheduled_datetime}")
        
        return task.task_id
    
    def schedule_stock_collection(
        self, 
        symbol: str, 
        market: str, 
        start_date: date = None, 
        end_date: date = None,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> str:
        """排程單支股票數據收集"""
        now = datetime.now()
        
        task = ScheduledTask(
            task_id=f"stock_collection_{symbol}_{market}_{now.strftime('%Y%m%d_%H%M%S')}",
            task_type="stock_collection",
            priority=priority,
            scheduled_time=now,  # 立即執行
            parameters={
                'symbol': symbol,
                'market': market,
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None
            }
        )
        
        self.tasks.append(task)
        logger.info(f"已排程股票數據收集任務: {task.task_id}")
        
        return task.task_id
    
    def schedule_data_validation(
        self, 
        stock_id: int = None, 
        priority: TaskPriority = TaskPriority.LOW
    ) -> str:
        """排程數據驗證"""
        now = datetime.now()
        
        task = ScheduledTask(
            task_id=f"data_validation_{stock_id or 'all'}_{now.strftime('%Y%m%d_%H%M%S')}",
            task_type="data_validation",
            priority=priority,
            scheduled_time=now + timedelta(minutes=5),  # 5分鐘後執行
            parameters={
                'stock_id': stock_id
            }
        )
        
        self.tasks.append(task)
        logger.info(f"已排程數據驗證任務: {task.task_id}")
        
        return task.task_id
    
    def schedule_backfill_data(
        self, 
        symbol: str, 
        market: str, 
        days: int = 365,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> str:
        """排程數據回補"""
        now = datetime.now()
        
        task = ScheduledTask(
            task_id=f"backfill_{symbol}_{market}_{now.strftime('%Y%m%d_%H%M%S')}",
            task_type="backfill_data",
            priority=priority,
            scheduled_time=now,
            parameters={
                'symbol': symbol,
                'market': market,
                'days': days
            }
        )
        
        self.tasks.append(task)
        logger.info(f"已排程數據回補任務: {task.task_id}")
        
        return task.task_id
    
    def get_pending_tasks(self) -> List[ScheduledTask]:
        """取得待執行任務"""
        now = datetime.now()
        return [
            task for task in self.tasks 
            if task.status == ScheduleStatus.PENDING and task.scheduled_time <= now
        ]
    
    def get_task_status(self, task_id: str) -> Optional[ScheduledTask]:
        """取得任務狀態"""
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任務"""
        for task in self.tasks:
            if task.task_id == task_id and task.status == ScheduleStatus.PENDING:
                task.status = ScheduleStatus.CANCELLED
                logger.info(f"已取消任務: {task_id}")
                return True
        return False
    
    async def start_scheduler(self, db_session):
        """啟動排程器"""
        if self.is_running:
            logger.warning("排程器已在運行中")
            return
        
        self.is_running = True
        logger.info("數據收集排程器已啟動")
        
        try:
            while self.is_running:
                # 取得待執行任務
                pending_tasks = self.get_pending_tasks()
                
                if pending_tasks:
                    # 按優先級排序
                    pending_tasks.sort(key=lambda x: (
                        {'urgent': 0, 'high': 1, 'normal': 2, 'low': 3}[x.priority.value],
                        x.scheduled_time
                    ))
                    
                    # 執行最高優先級任務
                    task = pending_tasks[0]
                    await self._execute_task(db_session, task)
                
                # 清理完成的任務（保留最近100個）
                self._cleanup_completed_tasks()
                
                # 等待下次檢查
                await asyncio.sleep(60)  # 每分鐘檢查一次
                
        except Exception as e:
            logger.error(f"排程器運行時發生錯誤: {str(e)}")
        finally:
            self.is_running = False
            logger.info("數據收集排程器已停止")
    
    def stop_scheduler(self):
        """停止排程器"""
        self.is_running = False
        logger.info("正在停止數據收集排程器...")
    
    async def _execute_task(self, db_session, task: ScheduledTask):
        """執行任務"""
        self.current_task = task
        task.status = ScheduleStatus.RUNNING
        task.started_at = datetime.now()
        
        logger.info(f"開始執行任務: {task.task_id} ({task.task_type})")
        
        try:
            if task.task_type == "daily_collection":
                result = await self._execute_daily_collection(db_session, task)
            elif task.task_type == "stock_collection":
                result = await self._execute_stock_collection(db_session, task)
            elif task.task_type == "data_validation":
                result = await self._execute_data_validation(db_session, task)
            elif task.task_type == "backfill_data":
                result = await self._execute_backfill_data(db_session, task)
            else:
                raise ValueError(f"未知的任務類型: {task.task_type}")
            
            task.status = ScheduleStatus.COMPLETED
            task.result = result
            logger.info(f"任務執行完成: {task.task_id}")
            
        except Exception as e:
            task.status = ScheduleStatus.FAILED
            task.error_message = str(e)
            logger.error(f"任務執行失敗: {task.task_id}, 錯誤: {str(e)}")
            
            # 記錄系統日誌
            log_entry = SystemLog.error(
                message=f"任務執行失敗: {task.task_id}",
                module="DataCollectionScheduler",
                function_name="_execute_task",
                extra_data={
                    'task_id': task.task_id,
                    'task_type': task.task_type,
                    'error': str(e)
                }
            )
            db_session.add(log_entry)
            await db_session.commit()
        
        finally:
            task.completed_at = datetime.now()
            self.current_task = None
    
    async def _execute_daily_collection(self, db_session, task: ScheduledTask) -> Dict[str, Any]:
        """執行每日數據收集"""
        start_time = datetime.now()
        
        # 收集所有股票數據
        result = await data_collection_service.collect_all_stocks_data(db_session)
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        # 建立收集摘要
        summary = CollectionSummary(
            date=date.today(),
            total_stocks=result.get('total_stocks', 0),
            successful_collections=result.get('success_count', 0),
            failed_collections=result.get('error_count', 0),
            total_data_points=result.get('total_data_saved', 0),
            execution_time_seconds=execution_time,
            errors=result.get('collection_errors', []) + result.get('save_errors', []),
            quality_issues=[]
        )
        
        # 記錄系統日誌
        log_entry = SystemLog.info(
            message=f"每日數據收集完成",
            module="DataCollectionScheduler",
            function_name="_execute_daily_collection",
            extra_data={
                'summary': {
                    'total_stocks': summary.total_stocks,
                    'successful_collections': summary.successful_collections,
                    'failed_collections': summary.failed_collections,
                    'total_data_points': summary.total_data_points,
                    'execution_time_seconds': summary.execution_time_seconds
                }
            }
        )
        db_session.add(log_entry)
        await db_session.commit()
        
        return {
            'summary': summary.__dict__,
            'raw_result': result
        }
    
    async def _execute_stock_collection(self, db_session, task: ScheduledTask) -> Dict[str, Any]:
        """執行單支股票數據收集"""
        params = task.parameters
        symbol = params['symbol']
        market = params['market']
        start_date = datetime.fromisoformat(params['start_date']).date() if params.get('start_date') else None
        end_date = datetime.fromisoformat(params['end_date']).date() if params.get('end_date') else None
        
        result = await data_collection_service.collect_stock_data(
            db_session, symbol, market, start_date, end_date
        )
        
        return result
    
    async def _execute_data_validation(self, db_session, task: ScheduledTask) -> Dict[str, Any]:
        """執行數據驗證"""
        params = task.parameters
        stock_id = params.get('stock_id')
        
        if stock_id:
            # 驗證單支股票
            quality_report = await data_validation_service.analyze_stock_data_quality(
                db_session, stock_id
            )
            return {'quality_report': quality_report.__dict__}
        else:
            # 驗證所有股票（簡化版本）
            stocks = await stock_crud.get_multi(db_session, limit=100)
            validation_results = []
            
            for stock in stocks[:10]:  # 限制數量避免過長執行時間
                try:
                    quality_report = await data_validation_service.analyze_stock_data_quality(
                        db_session, stock.id, days=30
                    )
                    validation_results.append({
                        'stock_id': stock.id,
                        'symbol': stock.symbol,
                        'quality_score': quality_report.quality_score
                    })
                except Exception as e:
                    logger.error(f"驗證股票 {stock.symbol} 時發生錯誤: {str(e)}")
            
            return {'validation_results': validation_results}
    
    async def _execute_backfill_data(self, db_session, task: ScheduledTask) -> Dict[str, Any]:
        """執行數據回補"""
        params = task.parameters
        symbol = params['symbol']
        market = params['market']
        days = params.get('days', 365)
        
        result = await data_collection_service.backfill_missing_data(
            db_session, symbol, market, days
        )
        
        return result
    
    def _cleanup_completed_tasks(self, keep_count: int = 100):
        """清理已完成的任務"""
        completed_tasks = [
            task for task in self.tasks 
            if task.status in [ScheduleStatus.COMPLETED, ScheduleStatus.FAILED, ScheduleStatus.CANCELLED]
        ]
        
        if len(completed_tasks) > keep_count:
            # 按完成時間排序，保留最新的
            completed_tasks.sort(key=lambda x: x.completed_at or datetime.min, reverse=True)
            tasks_to_remove = completed_tasks[keep_count:]
            
            for task in tasks_to_remove:
                self.tasks.remove(task)
            
            logger.info(f"清理了 {len(tasks_to_remove)} 個已完成的任務")
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """取得排程器狀態"""
        pending_count = len([t for t in self.tasks if t.status == ScheduleStatus.PENDING])
        running_count = len([t for t in self.tasks if t.status == ScheduleStatus.RUNNING])
        completed_count = len([t for t in self.tasks if t.status == ScheduleStatus.COMPLETED])
        failed_count = len([t for t in self.tasks if t.status == ScheduleStatus.FAILED])
        
        return {
            'is_running': self.is_running,
            'current_task': self.current_task.task_id if self.current_task else None,
            'task_counts': {
                'pending': pending_count,
                'running': running_count,
                'completed': completed_count,
                'failed': failed_count,
                'total': len(self.tasks)
            },
            'recent_tasks': [
                {
                    'task_id': task.task_id,
                    'task_type': task.task_type,
                    'status': task.status.value,
                    'scheduled_time': task.scheduled_time.isoformat(),
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None
                }
                for task in sorted(self.tasks, key=lambda x: x.created_at, reverse=True)[:10]
            ]
        }


# 建立全域排程器實例
data_scheduler = DataCollectionScheduler()