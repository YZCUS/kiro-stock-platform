#!/usr/bin/env python3
"""
數據回補命令行工具
"""
import asyncio
import sys
import argparse
from pathlib import Path
from datetime import date, datetime, timedelta
import logging

# 將專案根目錄加入 Python 路徑
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.settings import settings
from services.data.backfill import data_backfill_service, BackfillStrategy, BackfillPriority
from models.repositories.crud_stock import stock_crud
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BackfillCLI:
    """數據回補命令行介面"""
    
    def __init__(self):
        self.engine = create_async_engine(
            settings.database.url.replace("postgresql://", "postgresql+asyncpg://"),
            echo=False
        )
        self.async_session_local = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
    
    async def close(self):
        """關閉資料庫連接"""
        await self.engine.dispose()
    
    async def list_stocks(self, market: str = None, limit: int = 50):
        """列出股票"""
        async with self.async_session_local() as session:
            if market:
                stocks = await stock_crud.get_by_market(session, market=market, limit=limit)
            else:
                stocks = await stock_crud.get_multi(session, limit=limit)
            
            print(f"\n找到 {len(stocks)} 支股票:")
            print(f"{'ID':<5} {'代號':<12} {'市場':<6} {'名稱':<20}")
            print("-" * 50)
            
            for stock in stocks:
                print(f"{stock.id:<5} {stock.symbol:<12} {stock.market:<6} {stock.name or 'N/A':<20}")
    
    async def analyze_gaps(self, stock_id: int = None, days: int = 90):
        """分析數據缺口"""
        async with self.async_session_local() as session:
            if stock_id:
                stocks = [await stock_crud.get(session, stock_id)]
                if not stocks[0]:
                    print(f"找不到股票 ID: {stock_id}")
                    return
            else:
                stocks = await stock_crud.get_multi(session, limit=100)
            
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            print(f"\n分析數據缺口 ({start_date} 到 {end_date}):")
            print(f"{'股票代號':<12} {'市場':<6} {'缺失天數':<10} {'缺失比例':<10}")
            print("-" * 50)
            
            total_gaps = 0
            stocks_with_gaps = 0
            
            for stock in stocks:
                try:
                    from models.repositories.crud_price_history import price_history_crud
                    missing_dates = await price_history_crud.get_missing_dates(
                        session, stock_id=stock.id, start_date=start_date, end_date=end_date
                    )
                    
                    if missing_dates:
                        stocks_with_gaps += 1
                        total_gaps += len(missing_dates)
                        
                        total_days = (end_date - start_date).days + 1
                        missing_ratio = len(missing_dates) / total_days
                        
                        print(f"{stock.symbol:<12} {stock.market:<6} {len(missing_dates):<10} {missing_ratio:.1%}")
                
                except Exception as e:
                    logger.error(f"分析股票 {stock.symbol} 時發生錯誤: {str(e)}")
            
            print(f"\n總結: {stocks_with_gaps}/{len(stocks)} 支股票有缺口，總缺失 {total_gaps} 天")
    
    async def backfill_stock(
        self, 
        stock_id: int, 
        start_date: str, 
        end_date: str = None,
        strategy: str = "missing_only",
        priority: str = "normal"
    ):
        """回補單支股票"""
        async with self.async_session_local() as session:
            # 驗證股票存在
            stock = await stock_crud.get(session, stock_id)
            if not stock:
                print(f"找不到股票 ID: {stock_id}")
                return
            
            # 解析日期
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else date.today()
            
            # 轉換策略和優先級
            strategy_enum = BackfillStrategy(strategy)
            priority_enum = BackfillPriority(priority)
            
            print(f"\n開始回補股票: {stock.symbol} ({stock.market})")
            print(f"日期範圍: {start_dt} 到 {end_dt}")
            print(f"策略: {strategy}, 優先級: {priority}")
            
            try:
                # 建立回補任務
                task_id = await data_backfill_service.create_backfill_task(
                    session, stock_id, start_dt, end_dt, strategy_enum, priority_enum
                )
                
                print(f"任務 ID: {task_id}")
                print("正在執行回補...")
                
                # 執行回補
                result = await data_backfill_service.execute_backfill_task(session, task_id)
                
                # 顯示結果
                print(f"\n回補結果:")
                print(f"成功: {result.success}")
                print(f"處理日期數: {result.dates_processed}")
                print(f"成功日期數: {result.dates_successful}")
                print(f"失敗日期數: {result.dates_failed}")
                print(f"缺失日期數: {result.missing_dates_found}")
                print(f"填補日期數: {result.missing_dates_filled}")
                print(f"品質分數: {result.data_quality_score:.2f}")
                print(f"執行時間: {result.execution_time_seconds:.2f} 秒")
                
                if result.errors:
                    print(f"\n錯誤:")
                    for error in result.errors[:5]:  # 只顯示前5個錯誤
                        print(f"  - {error}")
                
                if result.warnings:
                    print(f"\n警告:")
                    for warning in result.warnings:
                        print(f"  - {warning}")
                
            except Exception as e:
                print(f"回補失敗: {str(e)}")
    
    async def batch_backfill(
        self, 
        market: str = None, 
        start_date: str = None, 
        end_date: str = None,
        strategy: str = "missing_only",
        max_stocks: int = 10
    ):
        """批次回補"""
        async with self.async_session_local() as session:
            # 獲取股票列表
            if market:
                stocks = await stock_crud.get_by_market(session, market=market, limit=max_stocks)
            else:
                stocks = await stock_crud.get_multi(session, limit=max_stocks)
            
            if not stocks:
                print("沒有找到股票")
                return
            
            # 解析日期
            if not start_date:
                start_dt = date.today() - timedelta(days=30)
            else:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
            
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else date.today()
            
            print(f"\n開始批次回補 {len(stocks)} 支股票")
            print(f"日期範圍: {start_dt} 到 {end_dt}")
            print(f"策略: {strategy}")
            
            # 執行批次回補
            stock_ids = [stock.id for stock in stocks]
            strategy_enum = BackfillStrategy(strategy)
            
            try:
                results = await data_backfill_service.batch_backfill_stocks(
                    session, stock_ids, start_dt, end_dt, strategy_enum, max_concurrent=3
                )
                
                # 統計結果
                successful = sum(1 for r in results if r.success)
                failed = len(results) - successful
                total_dates_filled = sum(r.dates_successful for r in results)
                total_execution_time = sum(r.execution_time_seconds for r in results)
                
                print(f"\n批次回補完成:")
                print(f"總股票數: {len(results)}")
                print(f"成功: {successful}")
                print(f"失敗: {failed}")
                print(f"總填補日期數: {total_dates_filled}")
                print(f"總執行時間: {total_execution_time:.2f} 秒")
                print(f"成功率: {successful/len(results)*100:.1f}%")
                
                # 顯示詳細結果
                print(f"\n詳細結果:")
                print(f"{'任務ID':<30} {'成功':<6} {'填補天數':<8} {'執行時間':<10}")
                print("-" * 60)
                
                for result in results:
                    task_id_short = result.task_id.split('_')[1:3]  # 簡化顯示
                    task_display = '_'.join(task_id_short) if len(task_id_short) >= 2 else result.task_id[:30]
                    
                    print(f"{task_display:<30} {'✓' if result.success else '✗':<6} {result.dates_successful:<8} {result.execution_time_seconds:<10.2f}")
                
            except Exception as e:
                print(f"批次回補失敗: {str(e)}")
    
    async def check_task_status(self, task_id: str = None):
        """檢查任務狀態"""
        if task_id:
            status = data_backfill_service.get_task_status(task_id)
            if status:
                print(f"\n任務狀態:")
                print(json.dumps(status, indent=2, ensure_ascii=False, default=str))
            else:
                print(f"找不到任務: {task_id}")
        else:
            all_status = data_backfill_service.get_all_tasks_status()
            print(f"\n所有任務狀態:")
            print(json.dumps(all_status, indent=2, ensure_ascii=False, default=str))


async def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='數據回補命令行工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 列出股票
    list_parser = subparsers.add_parser('list', help='列出股票')
    list_parser.add_argument('--market', choices=['TW', 'US'], help='市場篩選')
    list_parser.add_argument('--limit', type=int, default=50, help='顯示數量限制')
    
    # 分析缺口
    gaps_parser = subparsers.add_parser('gaps', help='分析數據缺口')
    gaps_parser.add_argument('--stock-id', type=int, help='股票ID（可選）')
    gaps_parser.add_argument('--days', type=int, default=90, help='分析天數')
    
    # 回補單支股票
    backfill_parser = subparsers.add_parser('backfill', help='回補單支股票')
    backfill_parser.add_argument('stock_id', type=int, help='股票ID')
    backfill_parser.add_argument('start_date', help='開始日期 (YYYY-MM-DD)')
    backfill_parser.add_argument('--end-date', help='結束日期 (YYYY-MM-DD)')
    backfill_parser.add_argument('--strategy', choices=['missing_only', 'full_refresh', 'incremental', 'quality_based'], 
                                default='missing_only', help='回補策略')
    backfill_parser.add_argument('--priority', choices=['low', 'normal', 'high', 'urgent'], 
                                default='normal', help='優先級')
    
    # 批次回補
    batch_parser = subparsers.add_parser('batch', help='批次回補')
    batch_parser.add_argument('--market', choices=['TW', 'US'], help='市場篩選')
    batch_parser.add_argument('--start-date', help='開始日期 (YYYY-MM-DD)')
    batch_parser.add_argument('--end-date', help='結束日期 (YYYY-MM-DD)')
    batch_parser.add_argument('--strategy', choices=['missing_only', 'full_refresh', 'incremental', 'quality_based'], 
                             default='missing_only', help='回補策略')
    batch_parser.add_argument('--max-stocks', type=int, default=10, help='最大股票數')
    
    # 檢查任務狀態
    status_parser = subparsers.add_parser('status', help='檢查任務狀態')
    status_parser.add_argument('--task-id', help='任務ID（可選）')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cli = BackfillCLI()
    
    try:
        if args.command == 'list':
            await cli.list_stocks(args.market, args.limit)
        
        elif args.command == 'gaps':
            await cli.analyze_gaps(args.stock_id, args.days)
        
        elif args.command == 'backfill':
            await cli.backfill_stock(
                args.stock_id, args.start_date, args.end_date, 
                args.strategy, args.priority
            )
        
        elif args.command == 'batch':
            await cli.batch_backfill(
                args.market, args.start_date, args.end_date, 
                args.strategy, args.max_stocks
            )
        
        elif args.command == 'status':
            await cli.check_task_status(args.task_id)
        
    except KeyboardInterrupt:
        print("\n操作已取消")
    except Exception as e:
        logger.error(f"執行命令時發生錯誤: {str(e)}")
    finally:
        await cli.close()


if __name__ == "__main__":
    asyncio.run(main())