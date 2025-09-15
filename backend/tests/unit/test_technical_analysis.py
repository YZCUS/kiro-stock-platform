#!/usr/bin/env python3
"""
技術分析功能測試腳本
"""
import asyncio
import sys
from pathlib import Path
from datetime import date, timedelta
import logging

# 將專案根目錄加入 Python 路徑
sys.path.append(str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from core.config import settings
from services.analysis.technical_analysis import technical_analysis_service, IndicatorType
from services.analysis.indicator_calculator import advanced_calculator
from models.repositories.crud_stock import stock_crud
from models.repositories.crud_price_history import price_history_crud
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_basic_indicator_calculation():
    """測試基本指標計算"""
    logger.info("測試基本指標計算...")
    
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=False
    )
    
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    try:
        async with AsyncSessionLocal() as session:
            # 獲取測試股票
            stocks = await stock_crud.get_multi(session, limit=3)
            
            if not stocks:
                logger.error("沒有找到測試股票")
                return False
            
            test_stock = stocks[0]
            logger.info(f"使用測試股票: {test_stock.symbol} ({test_stock.market})")
            
            # 測試單一指標計算
            indicators_to_test = [
                IndicatorType.RSI,
                IndicatorType.SMA_20,
                IndicatorType.EMA_12,
                IndicatorType.MACD
            ]
            
            result = await technical_analysis_service.calculate_stock_indicators(
                session,
                stock_id=test_stock.id,
                indicators=indicators_to_test,
                days=60,
                save_to_db=True
            )
            
            logger.info(f"計算結果: 成功 {result.indicators_successful}/{result.indicators_calculated}")
            logger.info(f"執行時間: {result.execution_time_seconds:.2f} 秒")
            
            if result.errors:
                logger.warning(f"錯誤: {result.errors}")
            
            return result.indicators_successful > 0
            
    except Exception as e:
        logger.error(f"測試基本指標計算時發生錯誤: {str(e)}")
        return False
    
    finally:
        await engine.dispose()


async def test_batch_indicator_calculation():
    """測試批次指標計算"""
    logger.info("測試批次指標計算...")
    
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=False
    )
    
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    try:
        async with AsyncSessionLocal() as session:
            stocks = await stock_crud.get_multi(session, limit=3)
            
            if len(stocks) < 3:
                logger.error("需要至少3支股票進行批次測試")
                return False
            
            stock_ids = [stock.id for stock in stocks]
            logger.info(f"批次計算 {len(stock_ids)} 支股票的技術指標")
            
            # 測試批次計算
            results = await technical_analysis_service.batch_calculate_indicators(
                session,
                stock_ids=stock_ids,
                indicators=[IndicatorType.RSI, IndicatorType.SMA_20, IndicatorType.EMA_12],
                days=30,
                max_concurrent=2
            )
            
            successful = sum(1 for r in results if r.indicators_successful > 0)
            total_indicators = sum(r.indicators_successful for r in results)
            
            logger.info(f"批次計算結果: {successful}/{len(results)} 支股票成功")
            logger.info(f"總計算指標數: {total_indicators}")
            
            for i, result in enumerate(results):
                stock_symbol = stocks[i].symbol
                status = "✓" if result.indicators_successful > 0 else "✗"
                logger.info(f"  {status} {stock_symbol}: {result.indicators_successful} 個指標")
            
            return successful > 0
            
    except Exception as e:
        logger.error(f"測試批次指標計算時發生錯誤: {str(e)}")
        return False
    
    finally:
        await engine.dispose()


async def test_advanced_indicator_calculation():
    """測試進階指標計算"""
    logger.info("測試進階指標計算...")
    
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=False
    )
    
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    try:
        async with AsyncSessionLocal() as session:
            stocks = await stock_crud.get_multi(session, limit=1)
            
            if not stocks:
                logger.error("沒有找到測試股票")
                return False
            
            test_stock = stocks[0]
            
            # 獲取價格數據
            end_date = date.today()
            start_date = end_date - timedelta(days=100)
            
            price_data = await price_history_crud.get_stock_price_range(
                session,
                stock_id=test_stock.id,
                start_date=start_date,
                end_date=end_date
            )
            
            if len(price_data) < 50:
                logger.error("價格數據不足")
                return False
            
            # 轉換為 DataFrame
            data = []
            for price in reversed(price_data):
                data.append({
                    'date': price.date,
                    'open': float(price.open_price) if price.open_price else np.nan,
                    'high': float(price.high_price) if price.high_price else np.nan,
                    'low': float(price.low_price) if price.low_price else np.nan,
                    'close': float(price.close_price) if price.close_price else np.nan,
                    'volume': float(price.volume) if price.volume else 0
                })
            
            df = pd.DataFrame(data)
            df.set_index('date', inplace=True)
            df.fillna(method='ffill', inplace=True)
            
            # 測試進階指標計算
            tests_passed = 0
            total_tests = 0
            
            # 測試 MACD 組件
            total_tests += 1
            try:
                macd_components = advanced_calculator.calculate_complete_macd(df)
                if macd_components.macd_line and len(macd_components.macd_line) > 0:
                    tests_passed += 1
                    logger.info(f"✓ MACD 計算成功: {len(macd_components.macd_line)} 個數據點")
                else:
                    logger.warning("✗ MACD 計算失敗")
            except Exception as e:
                logger.error(f"✗ MACD 計算異常: {str(e)}")
            
            # 測試布林通道
            total_tests += 1
            try:
                bb_components = advanced_calculator.calculate_complete_bollinger_bands(df)
                if bb_components.upper_band and len(bb_components.upper_band) > 0:
                    tests_passed += 1
                    logger.info(f"✓ 布林通道計算成功: {len(bb_components.upper_band)} 個數據點")
                else:
                    logger.warning("✗ 布林通道計算失敗")
            except Exception as e:
                logger.error(f"✗ 布林通道計算異常: {str(e)}")
            
            # 測試 KD 指標
            total_tests += 1
            try:
                kd_components = advanced_calculator.calculate_complete_stochastic(df)
                if kd_components.k_values and len(kd_components.k_values) > 0:
                    tests_passed += 1
                    logger.info(f"✓ KD 指標計算成功: {len(kd_components.k_values)} 個數據點")
                else:
                    logger.warning("✗ KD 指標計算失敗")
            except Exception as e:
                logger.error(f"✗ KD 指標計算異常: {str(e)}")
            
            # 測試動量指標
            total_tests += 1
            try:
                momentum_indicators = advanced_calculator.calculate_momentum_indicators(df)
                if momentum_indicators and len(momentum_indicators) > 0:
                    tests_passed += 1
                    logger.info(f"✓ 動量指標計算成功: {len(momentum_indicators)} 個指標")
                else:
                    logger.warning("✗ 動量指標計算失敗")
            except Exception as e:
                logger.error(f"✗ 動量指標計算異常: {str(e)}")
            
            # 測試成交量指標
            total_tests += 1
            try:
                volume_indicators = advanced_calculator.calculate_volume_indicators(df)
                if volume_indicators and len(volume_indicators) > 0:
                    tests_passed += 1
                    logger.info(f"✓ 成交量指標計算成功: {len(volume_indicators)} 個指標")
                else:
                    logger.warning("✗ 成交量指標計算失敗")
            except Exception as e:
                logger.error(f"✗ 成交量指標計算異常: {str(e)}")
            
            logger.info(f"進階指標測試結果: {tests_passed}/{total_tests} 通過")
            return tests_passed >= total_tests * 0.8  # 80% 通過率
            
    except Exception as e:
        logger.error(f"測試進階指標計算時發生錯誤: {str(e)}")
        return False
    
    finally:
        await engine.dispose()


async def test_indicator_data_retrieval():
    """測試指標數據檢索"""
    logger.info("測試指標數據檢索...")
    
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=False
    )
    
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    try:
        async with AsyncSessionLocal() as session:
            stocks = await stock_crud.get_multi(session, limit=1)
            
            if not stocks:
                logger.error("沒有找到測試股票")
                return False
            
            test_stock = stocks[0]
            
            # 先計算一些指標
            await technical_analysis_service.calculate_stock_indicators(
                session,
                stock_id=test_stock.id,
                indicators=[IndicatorType.RSI, IndicatorType.SMA_20],
                days=30,
                save_to_db=True
            )
            
            # 檢索指標數據
            indicators_data = await technical_analysis_service.get_stock_indicators(
                session,
                stock_id=test_stock.id,
                indicator_types=['RSI', 'SMA_20'],
                days=30
            )
            
            logger.info(f"檢索到的指標類型: {list(indicators_data.keys())}")
            
            for indicator_type, data in indicators_data.items():
                logger.info(f"{indicator_type}: {len(data)} 個數據點")
                if data:
                    latest = data[0]  # 最新數據
                    logger.info(f"  最新值: {latest['value']} (日期: {latest['date']})")
            
            return len(indicators_data) > 0
            
    except Exception as e:
        logger.error(f"測試指標數據檢索時發生錯誤: {str(e)}")
        return False
    
    finally:
        await engine.dispose()


async def test_pattern_recognition():
    """測試型態識別"""
    logger.info("測試型態識別...")
    
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=False
    )
    
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    try:
        async with AsyncSessionLocal() as session:
            stocks = await stock_crud.get_multi(session, limit=1)
            
            if not stocks:
                logger.error("沒有找到測試股票")
                return False
            
            test_stock = stocks[0]
            
            # 獲取價格數據
            end_date = date.today()
            start_date = end_date - timedelta(days=60)
            
            price_data = await price_history_crud.get_stock_price_range(
                session,
                stock_id=test_stock.id,
                start_date=start_date,
                end_date=end_date
            )
            
            if len(price_data) < 30:
                logger.error("價格數據不足")
                return False
            
            # 轉換為 DataFrame
            data = []
            for price in reversed(price_data):
                data.append({
                    'date': price.date,
                    'open': float(price.open_price) if price.open_price else np.nan,
                    'high': float(price.high_price) if price.high_price else np.nan,
                    'low': float(price.low_price) if price.low_price else np.nan,
                    'close': float(price.close_price) if price.close_price else np.nan,
                    'volume': float(price.volume) if price.volume else 0
                })
            
            df = pd.DataFrame(data)
            df.set_index('date', inplace=True)
            df.fillna(method='ffill', inplace=True)
            
            # 測試型態識別
            pattern_signals = advanced_calculator.detect_pattern_signals(df)
            
            total_patterns = (
                len(pattern_signals['bullish_patterns']) +
                len(pattern_signals['bearish_patterns']) +
                len(pattern_signals['reversal_patterns'])
            )
            
            logger.info(f"偵測到的型態數量:")
            logger.info(f"  看漲型態: {len(pattern_signals['bullish_patterns'])}")
            logger.info(f"  看跌型態: {len(pattern_signals['bearish_patterns'])}")
            logger.info(f"  反轉型態: {len(pattern_signals['reversal_patterns'])}")
            logger.info(f"  總計: {total_patterns}")
            
            # 顯示一些型態詳情
            for pattern in pattern_signals['bullish_patterns'][:3]:
                logger.info(f"  看漲型態: {pattern['pattern']} 於 {pattern['date']}")
            
            for pattern in pattern_signals['bearish_patterns'][:3]:
                logger.info(f"  看跌型態: {pattern['pattern']} 於 {pattern['date']}")
            
            return True  # 型態識別功能正常運行即為成功
            
    except Exception as e:
        logger.error(f"測試型態識別時發生錯誤: {str(e)}")
        return False
    
    finally:
        await engine.dispose()


async def main():
    """主測試函數"""
    logger.info("開始技術分析功能測試...")
    
    tests = [
        ("基本指標計算", test_basic_indicator_calculation),
        ("批次指標計算", test_batch_indicator_calculation),
        ("進階指標計算", test_advanced_indicator_calculation),
        ("指標數據檢索", test_indicator_data_retrieval),
        ("型態識別", test_pattern_recognition),
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
        logger.info("🎉 所有技術分析測試都通過了！")
        return 0
    else:
        logger.error("⚠️  部分技術分析測試失敗，請檢查實現")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)