#!/usr/bin/env python3
"""
數據收集服務測試腳本
"""
import asyncio
import sys
from pathlib import Path
from datetime import date, timedelta

# 將專案根目錄加入 Python 路徑
sys.path.append(str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from core.config import settings
from services.data.collection import data_collection_service
from services.data.validation import data_validation_service
from models.repositories.crud_stock import stock_crud
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_yahoo_finance_connection():
    """測試 Yahoo Finance 連接"""
    logger.info("測試 Yahoo Finance 連接...")
    
    from services.data.collection import YahooFinanceCollector
    collector = YahooFinanceCollector()
    
    # 測試台股
    tw_data = await collector.fetch_stock_data(
        "2330.TW", "TW", 
        start_date=date.today() - timedelta(days=7),
        end_date=date.today()
    )
    
    if tw_data:
        logger.info(f"台股測試成功：獲取到 {len(tw_data)} 筆 2330.TW 數據")
        logger.info(f"最新數據：{tw_data[-1]}")
    else:
        logger.error("台股測試失敗")
    
    # 測試美股
    us_data = await collector.fetch_stock_data(
        "AAPL", "US",
        start_date=date.today() - timedelta(days=7),
        end_date=date.today()
    )
    
    if us_data:
        logger.info(f"美股測試成功：獲取到 {len(us_data)} 筆 AAPL 數據")
        logger.info(f"最新數據：{us_data[-1]}")
    else:
        logger.error("美股測試失敗")
    
    return tw_data is not None and us_data is not None


async def test_data_collection_service():
    """測試數據收集服務"""
    logger.info("測試數據收集服務...")
    
    # 建立資料庫連接
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=False
    )
    
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    try:
        async with AsyncSessionLocal() as session:
            # 確保測試股票存在
            test_stocks = [
                ("2330.TW", "TW", "台積電"),
                ("AAPL", "US", "Apple Inc.")
            ]
            
            for symbol, market, name in test_stocks:
                try:
                    stock = await stock_crud.get_by_symbol(session, symbol=symbol, market=market)
                    if not stock:
                        stock = await stock_crud.create_stock(
                            session, symbol=symbol, market=market, name=name
                        )
                        logger.info(f"建立測試股票：{stock.display_name}")
                except Exception as e:
                    logger.error(f"建立股票 {symbol} 失敗：{str(e)}")
            
            # 測試單支股票數據收集
            logger.info("測試單支股票數據收集...")
            result = await data_collection_service.collect_stock_data(
                session, "2330.TW", "TW",
                start_date=date.today() - timedelta(days=5),
                end_date=date.today()
            )
            
            logger.info(f"單支股票收集結果：{result}")
            
            # 測試數據驗證
            logger.info("測試數據驗證...")
            stock = await stock_crud.get_by_symbol(session, symbol="2330.TW", market="TW")
            if stock:
                quality_report = await data_validation_service.analyze_stock_data_quality(
                    session, stock.id, days=30
                )
                logger.info(f"數據品質報告：")
                logger.info(f"  - 品質分數：{quality_report.quality_score}")
                logger.info(f"  - 總記錄數：{quality_report.total_records}")
                logger.info(f"  - 有效記錄數：{quality_report.valid_records}")
                logger.info(f"  - 缺失日期數：{len(quality_report.missing_dates)}")
            
    except Exception as e:
        logger.error(f"測試數據收集服務時發生錯誤：{str(e)}")
        return False
    
    finally:
        await engine.dispose()
    
    return True


async def test_batch_collection():
    """測試批次數據收集"""
    logger.info("測試批次數據收集...")
    
    from services.data.collection import YahooFinanceCollector
    collector = YahooFinanceCollector()
    
    # 測試股票列表
    test_stocks = [
        ("2330.TW", "TW"),
        ("2317.TW", "TW"),
        ("AAPL", "US"),
        ("GOOGL", "US")
    ]
    
    result = await collector.fetch_multiple_stocks(
        test_stocks,
        start_date=date.today() - timedelta(days=3),
        end_date=date.today(),
        batch_size=2
    )
    
    logger.info(f"批次收集結果：")
    logger.info(f"  - 成功數量：{result.success_count}")
    logger.info(f"  - 失敗數量：{result.error_count}")
    logger.info(f"  - 總數據點：{len(result.collected_data)}")
    
    if result.errors:
        logger.warning(f"  - 錯誤：{result.errors}")
    
    return result.success_count > 0


async def main():
    """主測試函數"""
    logger.info("開始數據收集服務測試...")
    
    tests = [
        ("Yahoo Finance 連接測試", test_yahoo_finance_connection),
        ("批次數據收集測試", test_batch_collection),
        ("數據收集服務測試", test_data_collection_service),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            logger.info(f"\n{'='*50}")
            logger.info(f"執行：{test_name}")
            logger.info(f"{'='*50}")
            
            result = await test_func()
            results[test_name] = result
            
            if result:
                logger.info(f"✅ {test_name} - 通過")
            else:
                logger.error(f"❌ {test_name} - 失敗")
                
        except Exception as e:
            logger.error(f"❌ {test_name} - 異常：{str(e)}")
            results[test_name] = False
    
    # 總結
    logger.info(f"\n{'='*50}")
    logger.info("測試結果總結")
    logger.info(f"{'='*50}")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ 通過" if result else "❌ 失敗"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\n總計：{passed}/{total} 個測試通過")
    
    if passed == total:
        logger.info("🎉 所有測試都通過了！")
        return 0
    else:
        logger.error("⚠️  部分測試失敗，請檢查配置和網路連接")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)