#!/usr/bin/env python3
"""
技術指標管理命令行工具
"""
import asyncio
import sys
import argparse
from datetime import date, timedelta
from typing import List, Optional

# 添加項目根目錄到 Python 路徑
sys.path.append('/app')

from core.database import get_db
from core.redis import redis_client
from services.infrastructure.storage import indicator_storage_service
from services.infrastructure.cache import indicator_cache_service
from services.infrastructure.sync import indicator_sync_service
from services.analysis.technical_analysis import IndicatorType
# ✅ Clean Architecture: 使用 repository interface 而非 CRUD
from infrastructure.persistence.stock_repository import StockRepository


async def calculate_indicators_command(
    stock_symbols: List[str],
    indicators: List[str] = None,
    days: int = 100,
    force: bool = False,
    enable_cache: bool = True
):
    """計算指標命令"""
    print(f"開始計算 {len(stock_symbols)} 支股票的技術指標...")
    
    try:
        # 連接 Redis
        await redis_client.connect()
        
        async with get_db() as db_session:
            # ✅ Clean Architecture: 實例化 repository
            stock_repo = StockRepository(db_session)

            # 獲取股票ID
            stock_ids = []
            for symbol in stock_symbols:
                stock = await stock_repo.get_by_symbol(db_session, symbol)
                if stock:
                    stock_ids.append(stock.id)
                    print(f"找到股票: {symbol} (ID: {stock.id})")
                else:
                    print(f"警告: 找不到股票 {symbol}")
            
            if not stock_ids:
                print("錯誤: 沒有找到任何有效的股票")
                return
            
            # 轉換指標類型
            indicator_types = None
            if indicators:
                try:
                    indicator_types = [IndicatorType(ind) for ind in indicators]
                except ValueError as e:
                    print(f"錯誤: 無效的指標類型 - {e}")
                    return
            
            # 批次計算指標
            results = await indicator_storage_service.batch_calculate_and_store(
                db_session,
                stock_ids=stock_ids,
                indicators=indicator_types,
                days=days,
                enable_cache=enable_cache,
                force_recalculate=force
            )
            
            # 顯示結果
            successful = sum(1 for r in results if r.success)
            total_stored = sum(r.indicators_stored for r in results)
            total_cached = sum(r.indicators_cached for r in results)
            
            print(f"\n計算完成:")
            print(f"  成功: {successful}/{len(results)} 支股票")
            print(f"  存儲指標: {total_stored} 個")
            print(f"  快取指標: {total_cached} 個")
            
            # 顯示錯誤
            for i, result in enumerate(results):
                if not result.success and result.errors:
                    print(f"  股票 {stock_symbols[i]} 錯誤: {result.errors[0]}")
    
    finally:
        await redis_client.disconnect()


async def cache_management_command(
    action: str,
    stock_symbols: List[str] = None,
    indicators: List[str] = None,
    days: int = 30
):
    """快取管理命令"""
    try:
        await redis_client.connect()

        async with get_db() as db_session:
            # ✅ Clean Architecture: 實例化 repository
            stock_repo = StockRepository(db_session)

            if action == "warm_up":
                # 預熱快取
                if stock_symbols:
                    stock_ids = []
                    for symbol in stock_symbols:
                        stock = await stock_repo.get_by_symbol(db_session, symbol)
                        if stock:
                            stock_ids.append(stock.id)
                else:
                    # 預熱所有股票
                    stocks, _ = await stock_repo.get_multi_with_filter(db_session, limit=100)
                    stock_ids = [stock.id for stock in stocks]
                
                print(f"開始預熱 {len(stock_ids)} 支股票的快取...")
                
                result = await indicator_cache_service.warm_up_cache(
                    db_session,
                    stock_ids=stock_ids,
                    indicator_types=indicators,
                    days=days
                )
                
                print(f"預熱完成:")
                print(f"  處理股票: {result['processed_stocks']}")
                print(f"  成功快取: {result['successful_caches']}")
                print(f"  快取指標: {result['total_indicators_cached']}")
                
                if result['errors']:
                    print(f"  錯誤: {len(result['errors'])} 個")
                    for error in result['errors'][:3]:
                        print(f"    - {error}")
            
            elif action == "clear":
                # 清理快取
                if stock_symbols:
                    for symbol in stock_symbols:
                        stock = await stock_repo.get_by_symbol(db_session, symbol)
                        if stock:
                            count = await indicator_cache_service.invalidate_stock_indicators(
                                stock.id, indicators
                            )
                            print(f"清理股票 {symbol} 的 {count} 個快取")
                else:
                    print("請指定要清理快取的股票代號")
            
            elif action == "stats":
                # 顯示快取統計
                stats = await indicator_cache_service.get_cache_statistics()
                print(f"快取統計:")
                print(f"  命中次數: {stats.hit_count}")
                print(f"  未命中次數: {stats.miss_count}")
                print(f"  命中率: {stats.hit_rate:.2%}")
                print(f"  總鍵數: {stats.total_keys}")
                print(f"  快取大小: {stats.cache_size_mb:.2f} MB")
    
    finally:
        await redis_client.disconnect()


async def sync_management_command(
    action: str,
    schedule_name: str = None,
    stock_symbols: List[str] = None,
    indicators: List[str] = None,
    frequency: str = "daily"
):
    """同步管理命令"""
    try:
        await redis_client.connect()
        
        if action == "create_schedule":
            if not schedule_name or not stock_symbols:
                print("錯誤: 建立排程需要指定排程名稱和股票代號")
                return
            
            async with get_db() as db_session:
                # ✅ Clean Architecture: 實例化 repository
                stock_repo = StockRepository(db_session)

                # 獲取股票ID
                stock_ids = []
                for symbol in stock_symbols:
                    stock = await stock_repo.get_by_symbol(db_session, symbol)
                    if stock:
                        stock_ids.append(stock.id)
                
                result = await indicator_sync_service.create_sync_schedule(
                    schedule_name=schedule_name,
                    stock_ids=stock_ids,
                    indicator_types=indicators,
                    sync_frequency=frequency
                )
                
                if result['success']:
                    print(f"成功建立同步排程 '{schedule_name}'")
                    print(f"  股票數量: {result['stock_count']}")
                    print(f"  指標數量: {result['indicator_count']}")
                    print(f"  下次同步: {result['next_sync']}")
                else:
                    print(f"建立排程失敗: {result['error']}")
        
        elif action == "run_schedule":
            if not schedule_name:
                print("錯誤: 請指定要執行的排程名稱")
                return
            
            result = await indicator_sync_service.execute_sync_schedule(
                schedule_name, force_sync=True
            )
            
            if result['success']:
                print(f"同步排程 '{schedule_name}' 執行成功")
                print(f"  處理股票: {result['stocks_processed']}")
                print(f"  更新指標: {result['indicators_updated']}")
                print(f"  刷新快取: {result['cache_refreshed']}")
            else:
                print(f"同步排程執行失敗: {result['error']}")
        
        elif action == "list_schedules":
            schedules = await indicator_sync_service.get_sync_schedules()
            
            if schedules:
                print("同步排程列表:")
                for name, info in schedules.items():
                    status = "啟用" if info['enabled'] else "停用"
                    print(f"  {name} ({status})")
                    print(f"    股票數: {info['stock_count']}")
                    print(f"    指標數: {info['indicator_count']}")
                    print(f"    頻率: {info['sync_frequency']}")
                    print(f"    上次同步: {info['last_sync'] or '從未'}")
                    print(f"    下次同步: {info['next_sync'] or '無'}")
                    print()
            else:
                print("沒有找到任何同步排程")
        
        elif action == "sync_missing":
            result = await indicator_sync_service.sync_missing_indicators(
                days_back=7, max_stocks=100
            )
            
            if result['success']:
                print(f"同步缺失指標完成:")
                print(f"  檢查股票: {result['stocks_checked']}")
                print(f"  缺失股票: {result['missing_stocks']}")
                print(f"  成功同步: {result['successful_syncs']}")
                print(f"  存儲指標: {result['total_indicators_stored']}")
                print(f"  快取指標: {result['total_indicators_cached']}")
            else:
                print(f"同步缺失指標失敗: {result['error']}")
        
        elif action == "status":
            status = await indicator_sync_service.get_sync_status()
            
            print(f"同步狀態:")
            print(f"  運行中: {'是' if status['is_running'] else '否'}")
            print(f"  當前股票ID: {status['current_stock_id'] or '無'}")
            print(f"  進度: {status['progress_percentage']:.1f}%")
            print(f"  開始時間: {status['start_time'] or '無'}")
            print(f"  預計完成: {status['estimated_completion'] or '無'}")
            print(f"  最後錯誤: {status['last_error'] or '無'}")
            print(f"  活躍排程: {status['active_schedules']}")
    
    finally:
        await redis_client.disconnect()


async def data_integrity_command(
    stock_symbols: List[str],
    days: int = 30
):
    """數據完整性檢查命令"""
    try:
        await redis_client.connect()
        
        async with get_db() as db_session:
            # ✅ Clean Architecture: 實例化 repository
            stock_repo = StockRepository(db_session)

            for symbol in stock_symbols:
                stock = await stock_repo.get_by_symbol(db_session, symbol)
                if not stock:
                    print(f"找不到股票: {symbol}")
                    continue
                
                print(f"\n檢查股票 {symbol} 的數據完整性...")
                
                result = await indicator_storage_service.validate_data_integrity(
                    db_session, stock.id, days
                )
                
                if result['success']:
                    report = result['integrity_report']
                    print(f"  整體健康狀態: {report['overall_health']}")
                    print(f"  檢查期間: {report['check_period']}")
                    print(f"  發現問題: {result['issues_found']} 個")
                    
                    for indicator_type, info in report['indicator_types'].items():
                        print(f"  {indicator_type}:")
                        print(f"    預期天數: {info['expected_days']}")
                        print(f"    實際天數: {info['actual_days']}")
                        print(f"    缺失天數: {info['missing_dates']}")
                        print(f"    空值數量: {info['null_values']}")
                        print(f"    健康狀態: {info['health_status']}")
                        
                        if info['issues']:
                            for issue in info['issues']:
                                print(f"      問題: {issue}")
                else:
                    print(f"  檢查失敗: {result['error']}")
    
    finally:
        await redis_client.disconnect()


async def storage_stats_command():
    """存儲統計命令"""
    try:
        await redis_client.connect()
        
        async with get_db() as db_session:
            stats = await indicator_storage_service.get_storage_statistics(db_session)
            
            print("存儲統計:")
            print("\n資料庫:")
            db_stats = stats['database']
            print(f"  總指標數: {db_stats.get('total_indicators', 0):,}")
            print(f"  總股票數: {db_stats.get('total_stocks', 0)}")
            print(f"  指標類型數: {db_stats.get('total_indicator_types', 0)}")
            print(f"  最新日期: {db_stats.get('latest_date', '無')}")
            print(f"  最早日期: {db_stats.get('earliest_date', '無')}")
            
            print("\n快取:")
            cache_stats = stats['cache']
            print(f"  命中次數: {cache_stats.get('hit_count', 0):,}")
            print(f"  未命中次數: {cache_stats.get('miss_count', 0):,}")
            print(f"  命中率: {cache_stats.get('hit_rate', 0):.2%}")
            print(f"  總鍵數: {cache_stats.get('total_keys', 0):,}")
            print(f"  快取大小: {cache_stats.get('cache_size_mb', 0):.2f} MB")
    
    finally:
        await redis_client.disconnect()


def main():
    parser = argparse.ArgumentParser(description="技術指標管理工具")
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 計算指標命令
    calc_parser = subparsers.add_parser('calculate', help='計算技術指標')
    calc_parser.add_argument('symbols', nargs='+', help='股票代號列表')
    calc_parser.add_argument('--indicators', nargs='*', help='指標類型列表')
    calc_parser.add_argument('--days', type=int, default=100, help='計算天數')
    calc_parser.add_argument('--force', action='store_true', help='強制重新計算')
    calc_parser.add_argument('--no-cache', action='store_true', help='不使用快取')
    
    # 快取管理命令
    cache_parser = subparsers.add_parser('cache', help='快取管理')
    cache_parser.add_argument('action', choices=['warm_up', 'clear', 'stats'], help='快取操作')
    cache_parser.add_argument('--symbols', nargs='*', help='股票代號列表')
    cache_parser.add_argument('--indicators', nargs='*', help='指標類型列表')
    cache_parser.add_argument('--days', type=int, default=30, help='天數')
    
    # 同步管理命令
    sync_parser = subparsers.add_parser('sync', help='同步管理')
    sync_parser.add_argument('action', choices=[
        'create_schedule', 'run_schedule', 'list_schedules', 
        'sync_missing', 'status'
    ], help='同步操作')
    sync_parser.add_argument('--name', help='排程名稱')
    sync_parser.add_argument('--symbols', nargs='*', help='股票代號列表')
    sync_parser.add_argument('--indicators', nargs='*', help='指標類型列表')
    sync_parser.add_argument('--frequency', default='daily', help='同步頻率')
    
    # 數據完整性檢查命令
    integrity_parser = subparsers.add_parser('integrity', help='數據完整性檢查')
    integrity_parser.add_argument('symbols', nargs='+', help='股票代號列表')
    integrity_parser.add_argument('--days', type=int, default=30, help='檢查天數')
    
    # 存儲統計命令
    subparsers.add_parser('stats', help='存儲統計')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 執行對應命令
    if args.command == 'calculate':
        asyncio.run(calculate_indicators_command(
            stock_symbols=args.symbols,
            indicators=args.indicators,
            days=args.days,
            force=args.force,
            enable_cache=not args.no_cache
        ))
    
    elif args.command == 'cache':
        asyncio.run(cache_management_command(
            action=args.action,
            stock_symbols=args.symbols,
            indicators=args.indicators,
            days=args.days
        ))
    
    elif args.command == 'sync':
        asyncio.run(sync_management_command(
            action=args.action,
            schedule_name=args.name,
            stock_symbols=args.symbols,
            indicators=args.indicators,
            frequency=args.frequency
        ))
    
    elif args.command == 'integrity':
        asyncio.run(data_integrity_command(
            stock_symbols=args.symbols,
            days=args.days
        ))
    
    elif args.command == 'stats':
        asyncio.run(storage_stats_command())


if __name__ == "__main__":
    main()