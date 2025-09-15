#!/usr/bin/env python3
"""
技術指標存儲和快取功能測試
"""
import asyncio
import sys
from datetime import date, timedelta

# 添加項目根目錄到 Python 路徑
sys.path.append('/app')

from core.database import get_db
from core.redis import redis_client
from services.infrastructure.storage import indicator_storage_service
from services.infrastructure.cache import indicator_cache_service
from services.infrastructure.sync import indicator_sync_service
from services.analysis.technical_analysis import IndicatorType
from models.repositories.crud_stock import stock_crud
from models.repositories.crud_technical_indicator import technical_indicator_crud


async def test_indicator_storage():
    """測試指標存儲功能"""
    print("=== 測試指標存儲功能 ===")
    
    try:
        await redis_client.connect()
        
        async with get_db() as db_session:
            # 獲取測試股票
            test_stocks = await stock_crud.get_multi(db_session, limit=3)
            if not test_stocks:
                print("錯誤: 沒有找到測試股票")
                return False
            
            test_stock = test_stocks[0]
            print(f"使用測試股票: {test_stock.symbol} (ID: {test_stock.id})")
            
            # 測試計算和存儲指標
            print("\n1. 測試計算和存儲指標...")
            storage_result = await indicator_storage_service.calculate_and_store_indicators(
                db_session,
                stock_id=test_stock.id,
                indicators=[IndicatorType.RSI, IndicatorType.SMA_20, IndicatorType.MACD],
                days=50,
                enable_cache=True,
                force_recalculate=True
            )
            
            if storage_result.success:
                print(f"✓ 成功存儲 {storage_result.indicators_stored} 個指標")
                print(f"✓ 成功快取 {storage_result.indicators_cached} 個指標")
                print(f"✓ 執行時間: {storage_result.execution_time_seconds:.2f} 秒")
            else:
                print(f"✗ 存儲失敗: {storage_result.errors}")
                return False
            
            # 測試從資料庫查詢指標
            print("\n2. 測試從資料庫查詢指標...")
            end_date = date.today()
            start_date = end_date - timedelta(days=7)
            
            indicators = await technical_indicator_crud.get_stock_indicators_by_date_range(
                db_session,
                stock_id=test_stock.id,
                start_date=start_date,
                end_date=end_date,
                indicator_types=['RSI', 'SMA_20', 'MACD']
            )
            
            print(f"✓ 查詢到 {len(indicators)} 個指標記錄")
            
            # 按類型分組顯示
            indicator_groups = {}
            for indicator in indicators:
                if indicator.indicator_type not in indicator_groups:
                    indicator_groups[indicator.indicator_type] = []
                indicator_groups[indicator.indicator_type].append(indicator)
            
            for indicator_type, type_indicators in indicator_groups.items():
                latest = max(type_indicators, key=lambda x: x.date)
                print(f"  {indicator_type}: {len(type_indicators)} 個記錄, 最新值: {latest.value} ({latest.date})")
            
            return True
            
    except Exception as e:
        print(f"✗ 測試失敗: {str(e)}")
        return False
    
    finally:
        await redis_client.disconnect()


async def test_indicator_cache():
    """測試指標快取功能"""
    print("\n=== 測試指標快取功能 ===")
    
    try:
        await redis_client.connect()
        
        async with get_db() as db_session:
            # 獲取測試股票
            test_stocks = await stock_crud.get_multi(db_session, limit=2)
            if not test_stocks:
                print("錯誤: 沒有找到測試股票")
                return False
            
            test_stock = test_stocks[0]
            print(f"使用測試股票: {test_stock.symbol} (ID: {test_stock.id})")
            
            # 測試快取預熱
            print("\n1. 測試快取預熱...")
            warm_up_result = await indicator_cache_service.warm_up_cache(
                db_session,
                stock_ids=[test_stock.id],
                indicator_types=['RSI', 'SMA_20', 'MACD'],
                days=30
            )
            
            if warm_up_result['successful_caches'] > 0:
                print(f"✓ 成功預熱 {warm_up_result['successful_caches']} 支股票的快取")
                print(f"✓ 快取 {warm_up_result['total_indicators_cached']} 個指標")
            else:
                print(f"✗ 預熱失敗: {warm_up_result['errors']}")
            
            # 測試從快取取得指標
            print("\n2. 測試從快取取得指標...")
            cached_data = await indicator_cache_service.get_stock_indicators_from_cache(
                test_stock.id,
                indicator_types=['RSI', 'SMA_20', 'MACD'],
                days=30
            )
            
            if cached_data:
                print(f"✓ 從快取取得 {len(cached_data)} 種指標類型")
                for indicator_type, data_points in cached_data.items():
                    print(f"  {indicator_type}: {len(data_points)} 個數據點")
            else:
                print("✗ 快取中沒有數據")
            
            # 測試快取命中率
            print("\n3. 測試快取命中率...")
            
            # 第一次查詢（可能命中快取）
            start_time = asyncio.get_event_loop().time()
            data1 = await indicator_storage_service.get_indicators_with_cache(
                db_session,
                stock_id=test_stock.id,
                indicator_types=['RSI', 'SMA_20'],
                days=30,
                force_refresh=False
            )
            cache_time = asyncio.get_event_loop().time() - start_time
            
            # 第二次查詢（強制從資料庫）
            start_time = asyncio.get_event_loop().time()
            data2 = await indicator_storage_service.get_indicators_with_cache(
                db_session,
                stock_id=test_stock.id,
                indicator_types=['RSI', 'SMA_20'],
                days=30,
                force_refresh=True
            )
            db_time = asyncio.get_event_loop().time() - start_time
            
            print(f"✓ 快取查詢時間: {cache_time:.4f} 秒")
            print(f"✓ 資料庫查詢時間: {db_time:.4f} 秒")
            
            if cache_time < db_time:
                print(f"✓ 快取效能提升: {(db_time/cache_time):.2f}x")
            
            # 測試快取統計
            print("\n4. 測試快取統計...")
            cache_stats = await indicator_cache_service.get_cache_statistics()
            print(f"✓ 快取命中次數: {cache_stats.hit_count}")
            print(f"✓ 快取未命中次數: {cache_stats.miss_count}")
            print(f"✓ 快取命中率: {cache_stats.hit_rate:.2%}")
            
            return True
            
    except Exception as e:
        print(f"✗ 測試失敗: {str(e)}")
        return False
    
    finally:
        await redis_client.disconnect()


async def test_indicator_sync():
    """測試指標同步功能"""
    print("\n=== 測試指標同步功能 ===")
    
    try:
        await redis_client.connect()
        
        async with get_db() as db_session:
            # 獲取測試股票
            test_stocks = await stock_crud.get_multi(db_session, limit=3)
            if not test_stocks:
                print("錯誤: 沒有找到測試股票")
                return False
            
            test_stock_ids = [stock.id for stock in test_stocks[:2]]
            print(f"使用測試股票: {[stock.symbol for stock in test_stocks[:2]]}")
            
            # 測試建立同步排程
            print("\n1. 測試建立同步排程...")
            schedule_result = await indicator_sync_service.create_sync_schedule(
                schedule_name="test_schedule",
                stock_ids=test_stock_ids,
                indicator_types=['RSI', 'SMA_20', 'MACD'],
                sync_frequency='manual'
            )
            
            if schedule_result['success']:
                print(f"✓ 成功建立同步排程")
                print(f"  股票數量: {schedule_result['stock_count']}")
                print(f"  指標數量: {schedule_result['indicator_count']}")
            else:
                print(f"✗ 建立排程失敗: {schedule_result['error']}")
                return False
            
            # 測試執行同步排程
            print("\n2. 測試執行同步排程...")
            sync_result = await indicator_sync_service.execute_sync_schedule(
                "test_schedule",
                force_sync=True
            )
            
            if sync_result['success']:
                print(f"✓ 同步排程執行成功")
                print(f"  處理股票: {sync_result['stocks_processed']}")
                print(f"  更新指標: {sync_result['indicators_updated']}")
                print(f"  刷新快取: {sync_result['cache_refreshed']}")
            else:
                print(f"✗ 同步排程執行失敗: {sync_result['error']}")
            
            # 測試單支股票同步
            print("\n3. 測試單支股票同步...")
            single_sync_result = await indicator_sync_service.sync_single_stock(
                stock_id=test_stock_ids[0],
                indicator_types=['RSI', 'EMA_12'],
                force_recalculate=True
            )
            
            if single_sync_result['success']:
                print(f"✓ 單支股票同步成功")
                print(f"  股票代號: {single_sync_result['stock_symbol']}")
                print(f"  存儲指標: {single_sync_result['indicators_stored']}")
                print(f"  快取指標: {single_sync_result['indicators_cached']}")
            else:
                print(f"✗ 單支股票同步失敗: {single_sync_result['error']}")
            
            # 測試同步狀態
            print("\n4. 測試同步狀態...")
            sync_status = await indicator_sync_service.get_sync_status()
            print(f"✓ 同步運行中: {sync_status['is_running']}")
            print(f"✓ 活躍排程數: {sync_status['active_schedules']}")
            
            # 測試排程列表
            print("\n5. 測試排程列表...")
            schedules = await indicator_sync_service.get_sync_schedules()
            print(f"✓ 找到 {len(schedules)} 個排程")
            for name, info in schedules.items():
                print(f"  {name}: {info['stock_count']} 支股票, 狀態: {'啟用' if info['enabled'] else '停用'}")
            
            # 清理測試排程
            await indicator_sync_service.delete_schedule("test_schedule")
            print("✓ 清理測試排程")
            
            return True
            
    except Exception as e:
        print(f"✗ 測試失敗: {str(e)}")
        return False
    
    finally:
        await redis_client.disconnect()


async def test_data_integrity():
    """測試數據完整性檢查"""
    print("\n=== 測試數據完整性檢查 ===")
    
    try:
        await redis_client.connect()
        
        async with get_db() as db_session:
            # 獲取測試股票
            test_stocks = await stock_crud.get_multi(db_session, limit=1)
            if not test_stocks:
                print("錯誤: 沒有找到測試股票")
                return False
            
            test_stock = test_stocks[0]
            print(f"檢查股票: {test_stock.symbol} (ID: {test_stock.id})")
            
            # 測試數據完整性檢查
            integrity_result = await indicator_storage_service.validate_data_integrity(
                db_session,
                stock_id=test_stock.id,
                days=30
            )
            
            if integrity_result['success']:
                report = integrity_result['integrity_report']
                print(f"✓ 數據完整性檢查完成")
                print(f"  整體健康狀態: {report['overall_health']}")
                print(f"  檢查期間: {report['check_period']}")
                print(f"  發現問題: {integrity_result['issues_found']} 個")
                
                for indicator_type, info in report['indicator_types'].items():
                    print(f"  {indicator_type}:")
                    print(f"    數據完整度: {info['actual_days']}/{info['expected_days']} 天")
                    print(f"    健康狀態: {info['health_status']}")
                    
                    if info['issues']:
                        for issue in info['issues']:
                            print(f"    問題: {issue}")
            else:
                print(f"✗ 數據完整性檢查失敗: {integrity_result['error']}")
                return False
            
            # 測試存儲統計
            print("\n測試存儲統計...")
            stats = await indicator_storage_service.get_storage_statistics(db_session)
            
            print(f"✓ 資料庫統計:")
            db_stats = stats['database']
            print(f"  總指標數: {db_stats.get('total_indicators', 0):,}")
            print(f"  總股票數: {db_stats.get('total_stocks', 0)}")
            print(f"  指標類型數: {db_stats.get('total_indicator_types', 0)}")
            
            print(f"✓ 快取統計:")
            cache_stats = stats['cache']
            print(f"  命中率: {cache_stats.get('hit_rate', 0):.2%}")
            print(f"  總鍵數: {cache_stats.get('total_keys', 0):,}")
            
            return True
            
    except Exception as e:
        print(f"✗ 測試失敗: {str(e)}")
        return False
    
    finally:
        await redis_client.disconnect()


async def run_all_tests():
    """執行所有測試"""
    print("開始執行技術指標存儲和快取功能測試...\n")
    
    tests = [
        ("指標存儲功能", test_indicator_storage),
        ("指標快取功能", test_indicator_cache),
        ("指標同步功能", test_indicator_sync),
        ("數據完整性檢查", test_data_integrity)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"執行測試: {test_name}")
        print('='*60)
        
        try:
            result = await test_func()
            if result:
                print(f"\n✓ {test_name} 測試通過")
                passed += 1
            else:
                print(f"\n✗ {test_name} 測試失敗")
        except Exception as e:
            print(f"\n✗ {test_name} 測試異常: {str(e)}")
    
    print(f"\n{'='*60}")
    print(f"測試結果: {passed}/{total} 通過")
    print('='*60)
    
    if passed == total:
        print("🎉 所有測試都通過了！")
        return True
    else:
        print("❌ 部分測試失敗，請檢查錯誤訊息")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)