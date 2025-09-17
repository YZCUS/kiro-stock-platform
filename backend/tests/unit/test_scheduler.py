#!/usr/bin/env python3
"""
數據收集排程器測試
"""
import sys
import asyncio
import unittest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, date, time, timedelta
from dataclasses import asdict
from pathlib import Path

# 添加測試配置路徑
sys.path.insert(0, str(Path(__file__).parent.parent))
from test_config import setup_test_path

# 設置測試環境路徑
setup_test_path()

from services.infrastructure.scheduler import (
    DataCollectionScheduler,
    ScheduledTask,
    CollectionSummary,
    ScheduleStatus,
    TaskPriority,
    data_scheduler
)


class TestScheduledTask(unittest.TestCase):
    """排程任務測試"""

    def test_create_scheduled_task(self):
        """測試建立排程任務"""
        scheduled_time = datetime(2024, 1, 15, 16, 0)
        task = ScheduledTask(
            task_id="test_task",
            task_type="daily_collection",
            priority=TaskPriority.HIGH,
            scheduled_time=scheduled_time,
            parameters={"param1": "value1"}
        )

        self.assertEqual(task.task_id, "test_task")
        self.assertEqual(task.task_type, "daily_collection")
        self.assertEqual(task.priority, TaskPriority.HIGH)
        self.assertEqual(task.scheduled_time, scheduled_time)
        self.assertEqual(task.parameters, {"param1": "value1"})
        self.assertEqual(task.status, ScheduleStatus.PENDING)
        self.assertIsNotNone(task.created_at)

    def test_scheduled_task_post_init(self):
        """測試排程任務初始化後處理"""
        task = ScheduledTask(
            task_id="test_task",
            task_type="daily_collection",
            priority=TaskPriority.NORMAL,
            scheduled_time=datetime.now(),
            parameters={}
        )

        # created_at 應該被自動設置
        self.assertIsNotNone(task.created_at)
        self.assertIsInstance(task.created_at, datetime)


class TestCollectionSummary(unittest.TestCase):
    """收集摘要測試"""

    def test_create_collection_summary(self):
        """測試建立收集摘要"""
        summary = CollectionSummary(
            date=date(2024, 1, 15),
            total_stocks=100,
            successful_collections=95,
            failed_collections=5,
            total_data_points=1000,
            execution_time_seconds=120.5,
            errors=["Error 1", "Error 2"],
            quality_issues=["Issue 1"]
        )

        self.assertEqual(summary.total_stocks, 100)
        self.assertEqual(summary.successful_collections, 95)
        self.assertEqual(summary.failed_collections, 5)
        self.assertEqual(summary.total_data_points, 1000)
        self.assertEqual(summary.execution_time_seconds, 120.5)
        self.assertEqual(len(summary.errors), 2)
        self.assertEqual(len(summary.quality_issues), 1)


class TestDataCollectionScheduler(unittest.TestCase):
    """數據收集排程器測試"""

    def setUp(self):
        """設置測試環境"""
        self.scheduler = DataCollectionScheduler()

    def test_scheduler_initialization(self):
        """測試排程器初始化"""
        self.assertEqual(len(self.scheduler.tasks), 0)
        self.assertFalse(self.scheduler.is_running)
        self.assertIsNone(self.scheduler.current_task)

    def test_schedule_daily_collection(self):
        """測試排程每日數據收集"""
        execution_time = time(16, 0)
        task_id = self.scheduler.schedule_daily_collection(
            execution_time=execution_time,
            priority=TaskPriority.HIGH
        )

        self.assertIsNotNone(task_id)
        self.assertEqual(len(self.scheduler.tasks), 1)

        task = self.scheduler.tasks[0]
        self.assertEqual(task.task_type, "daily_collection")
        self.assertEqual(task.priority, TaskPriority.HIGH)
        self.assertTrue(task_id.startswith("daily_collection_"))

    def test_schedule_daily_collection_next_day(self):
        """測試排程每日數據收集（時間已過，排程到明天）"""
        # 使用已過的時間
        past_time = time(8, 0)  # 假設現在是下午

        task_id = self.scheduler.schedule_daily_collection(
            execution_time=past_time,
            priority=TaskPriority.NORMAL
        )

        task = self.scheduler.get_task_status(task_id)
        self.assertIsNotNone(task)

        # 排程時間應該是明天
        now = datetime.now()
        expected_date = now.date() + timedelta(days=1)
        self.assertEqual(task.scheduled_time.date(), expected_date)

    def test_schedule_stock_collection(self):
        """測試排程單支股票數據收集"""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 15)

        task_id = self.scheduler.schedule_stock_collection(
            symbol="2330",
            market="TW",
            start_date=start_date,
            end_date=end_date,
            priority=TaskPriority.NORMAL
        )

        self.assertIsNotNone(task_id)
        self.assertEqual(len(self.scheduler.tasks), 1)

        task = self.scheduler.tasks[0]
        self.assertEqual(task.task_type, "stock_collection")
        self.assertEqual(task.parameters['symbol'], "2330")
        self.assertEqual(task.parameters['market'], "TW")
        self.assertEqual(task.parameters['start_date'], start_date.isoformat())
        self.assertEqual(task.parameters['end_date'], end_date.isoformat())

    def test_schedule_data_validation(self):
        """測試排程數據驗證"""
        stock_id = 123

        task_id = self.scheduler.schedule_data_validation(
            stock_id=stock_id,
            priority=TaskPriority.LOW
        )

        self.assertIsNotNone(task_id)
        self.assertEqual(len(self.scheduler.tasks), 1)

        task = self.scheduler.tasks[0]
        self.assertEqual(task.task_type, "data_validation")
        self.assertEqual(task.parameters['stock_id'], stock_id)

        # 驗證排程時間（應該是5分鐘後）
        now = datetime.now()
        time_diff = (task.scheduled_time - now).total_seconds()
        self.assertAlmostEqual(time_diff, 300, delta=10)  # 5分鐘 ± 10秒

    def test_schedule_backfill_data(self):
        """測試排程數據回補"""
        task_id = self.scheduler.schedule_backfill_data(
            symbol="AAPL",
            market="US",
            days=30,
            priority=TaskPriority.URGENT
        )

        self.assertIsNotNone(task_id)
        self.assertEqual(len(self.scheduler.tasks), 1)

        task = self.scheduler.tasks[0]
        self.assertEqual(task.task_type, "backfill_data")
        self.assertEqual(task.priority, TaskPriority.URGENT)
        self.assertEqual(task.parameters['symbol'], "AAPL")
        self.assertEqual(task.parameters['market'], "US")
        self.assertEqual(task.parameters['days'], 30)

    def test_get_pending_tasks(self):
        """測試取得待執行任務"""
        # 建立多個任務
        now = datetime.now()
        past_time = now - timedelta(minutes=5)
        future_time = now + timedelta(minutes=5)

        # 過去的任務（應該執行）
        task1 = ScheduledTask(
            task_id="task1",
            task_type="daily_collection",
            priority=TaskPriority.HIGH,
            scheduled_time=past_time,
            parameters={}
        )

        # 未來的任務（不應該執行）
        task2 = ScheduledTask(
            task_id="task2",
            task_type="stock_collection",
            priority=TaskPriority.NORMAL,
            scheduled_time=future_time,
            parameters={}
        )

        # 已完成的任務（不應該執行）
        task3 = ScheduledTask(
            task_id="task3",
            task_type="data_validation",
            priority=TaskPriority.LOW,
            scheduled_time=past_time,
            parameters={}
        )
        task3.status = ScheduleStatus.COMPLETED

        self.scheduler.tasks = [task1, task2, task3]

        pending_tasks = self.scheduler.get_pending_tasks()
        self.assertEqual(len(pending_tasks), 1)
        self.assertEqual(pending_tasks[0].task_id, "task1")

    def test_get_task_status(self):
        """測試取得任務狀態"""
        task = ScheduledTask(
            task_id="test_task",
            task_type="daily_collection",
            priority=TaskPriority.NORMAL,
            scheduled_time=datetime.now(),
            parameters={}
        )
        self.scheduler.tasks.append(task)

        # 找到任務
        found_task = self.scheduler.get_task_status("test_task")
        self.assertIsNotNone(found_task)
        self.assertEqual(found_task.task_id, "test_task")

        # 找不到任務
        not_found = self.scheduler.get_task_status("nonexistent_task")
        self.assertIsNone(not_found)

    def test_cancel_task(self):
        """測試取消任務"""
        task = ScheduledTask(
            task_id="test_task",
            task_type="daily_collection",
            priority=TaskPriority.NORMAL,
            scheduled_time=datetime.now(),
            parameters={}
        )
        self.scheduler.tasks.append(task)

        # 取消成功
        result = self.scheduler.cancel_task("test_task")
        self.assertTrue(result)
        self.assertEqual(task.status, ScheduleStatus.CANCELLED)

        # 重複取消失敗
        result = self.scheduler.cancel_task("test_task")
        self.assertFalse(result)

        # 取消不存在的任務
        result = self.scheduler.cancel_task("nonexistent_task")
        self.assertFalse(result)

    def test_stop_scheduler(self):
        """測試停止排程器"""
        self.scheduler.is_running = True
        self.scheduler.stop_scheduler()
        self.assertFalse(self.scheduler.is_running)

    def test_cleanup_completed_tasks(self):
        """測試清理已完成任務"""
        # 建立120個已完成任務
        for i in range(120):
            task = ScheduledTask(
                task_id=f"task_{i}",
                task_type="daily_collection",
                priority=TaskPriority.NORMAL,
                scheduled_time=datetime.now(),
                parameters={}
            )
            task.status = ScheduleStatus.COMPLETED
            task.completed_at = datetime.now() - timedelta(days=i)  # 不同的完成時間
            self.scheduler.tasks.append(task)

        # 加入一些待執行任務
        for i in range(5):
            task = ScheduledTask(
                task_id=f"pending_task_{i}",
                task_type="stock_collection",
                priority=TaskPriority.NORMAL,
                scheduled_time=datetime.now(),
                parameters={}
            )
            self.scheduler.tasks.append(task)

        # 清理，保留100個已完成任務
        self.scheduler._cleanup_completed_tasks(keep_count=100)

        # 應該有100個已完成任務 + 5個待執行任務 = 105個任務
        self.assertEqual(len(self.scheduler.tasks), 105)

        # 檢查保留的是最新的已完成任務
        completed_tasks = [t for t in self.scheduler.tasks if t.status == ScheduleStatus.COMPLETED]
        self.assertEqual(len(completed_tasks), 100)

    def test_get_scheduler_status(self):
        """測試取得排程器狀態"""
        # 建立不同狀態的任務
        tasks_data = [
            (ScheduleStatus.PENDING, 3),
            (ScheduleStatus.RUNNING, 1),
            (ScheduleStatus.COMPLETED, 5),
            (ScheduleStatus.FAILED, 2)
        ]

        for status, count in tasks_data:
            for i in range(count):
                task = ScheduledTask(
                    task_id=f"task_{status.value}_{i}",
                    task_type="daily_collection",
                    priority=TaskPriority.NORMAL,
                    scheduled_time=datetime.now(),
                    parameters={}
                )
                task.status = status
                self.scheduler.tasks.append(task)

        # 設置當前任務
        current_task = ScheduledTask(
            task_id="current_task",
            task_type="stock_collection",
            priority=TaskPriority.HIGH,
            scheduled_time=datetime.now(),
            parameters={}
        )
        self.scheduler.current_task = current_task
        self.scheduler.is_running = True

        status = self.scheduler.get_scheduler_status()

        self.assertTrue(status['is_running'])
        self.assertEqual(status['current_task'], "current_task")
        self.assertEqual(status['task_counts']['pending'], 3)
        self.assertEqual(status['task_counts']['running'], 1)
        self.assertEqual(status['task_counts']['completed'], 5)
        self.assertEqual(status['task_counts']['failed'], 2)
        self.assertEqual(status['task_counts']['total'], 11)
        self.assertEqual(len(status['recent_tasks']), 10)  # 最多10個


class TestDataCollectionSchedulerAsync(unittest.TestCase):
    """數據收集排程器異步測試"""

    def setUp(self):
        """設置測試環境"""
        self.scheduler = DataCollectionScheduler()
        self.mock_db_session = AsyncMock()

    @patch('services.infrastructure.scheduler.data_collection_service')
    @patch('services.infrastructure.scheduler.SystemLog')
    async def test_execute_daily_collection(self, mock_system_log, mock_data_collection_service):
        """測試執行每日數據收集"""
        # 模擬數據收集結果
        mock_result = {
            'total_stocks': 100,
            'success_count': 95,
            'error_count': 5,
            'total_data_saved': 1000,
            'collection_errors': ['Error 1'],
            'save_errors': ['Error 2']
        }
        mock_data_collection_service.collect_all_stocks_data.return_value = mock_result

        # 模擬SystemLog
        mock_log_entry = Mock()
        mock_system_log.info.return_value = mock_log_entry

        # 建立任務
        task = ScheduledTask(
            task_id="daily_task",
            task_type="daily_collection",
            priority=TaskPriority.HIGH,
            scheduled_time=datetime.now(),
            parameters={}
        )

        # 執行任務
        result = await self.scheduler._execute_daily_collection(self.mock_db_session, task)

        # 驗證結果
        self.assertIn('summary', result)
        self.assertIn('raw_result', result)

        summary = result['summary']
        self.assertEqual(summary['total_stocks'], 100)
        self.assertEqual(summary['successful_collections'], 95)
        self.assertEqual(summary['failed_collections'], 5)
        self.assertEqual(summary['total_data_points'], 1000)

        # 驗證數據收集服務被調用
        mock_data_collection_service.collect_all_stocks_data.assert_called_once_with(self.mock_db_session)

        # 驗證系統日誌被記錄
        mock_system_log.info.assert_called_once()
        self.mock_db_session.add.assert_called_once_with(mock_log_entry)
        self.mock_db_session.commit.assert_called_once()

    @patch('services.infrastructure.scheduler.data_collection_service')
    async def test_execute_stock_collection(self, mock_data_collection_service):
        """測試執行單支股票數據收集"""
        # 模擬數據收集結果
        mock_result = {'success': True, 'data_points': 100}
        mock_data_collection_service.collect_stock_data.return_value = mock_result

        # 建立任務
        task = ScheduledTask(
            task_id="stock_task",
            task_type="stock_collection",
            priority=TaskPriority.NORMAL,
            scheduled_time=datetime.now(),
            parameters={
                'symbol': '2330',
                'market': 'TW',
                'start_date': '2024-01-01',
                'end_date': '2024-01-15'
            }
        )

        # 執行任務
        result = await self.scheduler._execute_stock_collection(self.mock_db_session, task)

        # 驗證結果
        self.assertEqual(result, mock_result)

        # 驗證數據收集服務被正確調用
        mock_data_collection_service.collect_stock_data.assert_called_once_with(
            self.mock_db_session,
            '2330',
            'TW',
            date(2024, 1, 1),
            date(2024, 1, 15)
        )

    @patch('services.infrastructure.scheduler.data_validation_service')
    @patch('services.infrastructure.scheduler.stock_crud')
    async def test_execute_data_validation_single_stock(self, mock_stock_crud, mock_data_validation_service):
        """測試執行單支股票數據驗證"""
        # 模擬質量報告
        mock_quality_report = Mock()
        mock_quality_report.__dict__ = {'quality_score': 0.95, 'issues': []}
        mock_data_validation_service.analyze_stock_data_quality.return_value = mock_quality_report

        # 建立任務
        task = ScheduledTask(
            task_id="validation_task",
            task_type="data_validation",
            priority=TaskPriority.LOW,
            scheduled_time=datetime.now(),
            parameters={'stock_id': 123}
        )

        # 執行任務
        result = await self.scheduler._execute_data_validation(self.mock_db_session, task)

        # 驗證結果
        self.assertIn('quality_report', result)
        self.assertEqual(result['quality_report']['quality_score'], 0.95)

        # 驗證數據驗證服務被調用
        mock_data_validation_service.analyze_stock_data_quality.assert_called_once_with(
            self.mock_db_session, 123
        )

    @patch('services.infrastructure.scheduler.data_validation_service')
    @patch('services.infrastructure.scheduler.stock_crud')
    async def test_execute_data_validation_all_stocks(self, mock_stock_crud, mock_data_validation_service):
        """測試執行所有股票數據驗證"""
        # 模擬股票列表
        mock_stocks = []
        for i in range(15):  # 15支股票，但只會處理前10支
            stock = Mock()
            stock.id = i + 1
            stock.symbol = f"STOCK_{i+1}"
            mock_stocks.append(stock)
        mock_stock_crud.get_multi.return_value = mock_stocks

        # 模擬質量報告
        mock_quality_report = Mock()
        mock_quality_report.quality_score = 0.8
        mock_data_validation_service.analyze_stock_data_quality.return_value = mock_quality_report

        # 建立任務（沒有指定stock_id）
        task = ScheduledTask(
            task_id="validation_all_task",
            task_type="data_validation",
            priority=TaskPriority.LOW,
            scheduled_time=datetime.now(),
            parameters={}
        )

        # 執行任務
        result = await self.scheduler._execute_data_validation(self.mock_db_session, task)

        # 驗證結果
        self.assertIn('validation_results', result)
        validation_results = result['validation_results']
        self.assertEqual(len(validation_results), 10)  # 只處理前10支

        # 驗證每個結果
        for i, validation_result in enumerate(validation_results):
            self.assertEqual(validation_result['stock_id'], i + 1)
            self.assertEqual(validation_result['symbol'], f"STOCK_{i+1}")
            self.assertEqual(validation_result['quality_score'], 0.8)

    @patch('services.infrastructure.scheduler.data_collection_service')
    async def test_execute_backfill_data(self, mock_data_collection_service):
        """測試執行數據回補"""
        # 模擬回補結果
        mock_result = {'backfilled_days': 30, 'data_points': 300}
        mock_data_collection_service.backfill_missing_data.return_value = mock_result

        # 建立任務
        task = ScheduledTask(
            task_id="backfill_task",
            task_type="backfill_data",
            priority=TaskPriority.NORMAL,
            scheduled_time=datetime.now(),
            parameters={
                'symbol': 'AAPL',
                'market': 'US',
                'days': 30
            }
        )

        # 執行任務
        result = await self.scheduler._execute_backfill_data(self.mock_db_session, task)

        # 驗證結果
        self.assertEqual(result, mock_result)

        # 驗證數據收集服務被正確調用
        mock_data_collection_service.backfill_missing_data.assert_called_once_with(
            self.mock_db_session, 'AAPL', 'US', 30
        )

    async def test_execute_task_unknown_type(self):
        """測試執行未知類型任務"""
        task = ScheduledTask(
            task_id="unknown_task",
            task_type="unknown_type",
            priority=TaskPriority.NORMAL,
            scheduled_time=datetime.now(),
            parameters={}
        )

        # 執行任務應該引發異常
        await self.scheduler._execute_task(self.mock_db_session, task)

        # 任務應該被標記為失敗
        self.assertEqual(task.status, ScheduleStatus.FAILED)
        self.assertIn("未知的任務類型", task.error_message)


async def run_all_tests():
    """執行所有測試"""
    print("=" * 60)
    print("數據收集排程器測試")
    print("=" * 60)

    # 同步測試
    sync_test_classes = [
        TestScheduledTask,
        TestCollectionSummary,
        TestDataCollectionScheduler
    ]

    for test_class in sync_test_classes:
        print(f"\n執行 {test_class.__name__}...")
        suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)

        if not result.wasSuccessful():
            print(f"❌ {test_class.__name__} 測試失敗")
            return False

    # 異步測試
    print(f"\n執行 TestDataCollectionSchedulerAsync...")
    async_test = TestDataCollectionSchedulerAsync()

    async_test_methods = [
        'test_execute_daily_collection',
        'test_execute_stock_collection',
        'test_execute_data_validation_single_stock',
        'test_execute_data_validation_all_stocks',
        'test_execute_backfill_data',
        'test_execute_task_unknown_type'
    ]

    for method_name in async_test_methods:
        async_test.setUp()
        try:
            await getattr(async_test, method_name)()
            print(f"✅ {method_name} - 通過")
        except Exception as e:
            print(f"❌ {method_name} - 失敗: {str(e)}")
            return False

    print("\n🎉 所有排程器測試都通過了！")
    return True


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)