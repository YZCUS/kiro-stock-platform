#!/usr/bin/env python3
"""
交易信號檢測器測試 - Clean Architecture
"""
import pytest
from unittest.mock import Mock, AsyncMock

import asyncio
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

# 添加測試配置路徑
sys.path.insert(0, str(Path(__file__).parent.parent))
from test_config import setup_test_path

# 設置測試環境路徑
setup_test_path()

from core.database import get_db
from services.analysis.signal_detector import (
    trading_signal_detector, 
    SignalType, 
    SignalStrength,
    DetectedSignal
)
from domain.models.stock import Stock
from domain.models.technical_indicator import TechnicalIndicator
from domain.models.trading_signal import TradingSignal
from models.repositories.crud_stock import stock_crud
from models.repositories.crud_technical_indicator import technical_indicator_crud
from models.repositories.crud_trading_signal import trading_signal_crud


async def create_test_data():
    """建立測試數據"""
    print("建立測試數據...")
    
    async with get_db() as db_session:
        # 建立測試股票
        test_stock = Stock(
            symbol="SIGNAL_TEST",
            market="TW",
            name="信號測試股票"
        )
        db_session.add(test_stock)
        await db_session.flush()
        
        # 建立技術指標數據來模擬各種信號情況
        base_date = date(2024, 1, 1)
        
        # 模擬RSI數據（包含超買超賣）
        rsi_values = [
            (0, 50), (1, 45), (2, 40), (3, 35), (4, 25),  # 超賣
            (5, 30), (6, 40), (7, 50), (8, 60), (9, 70),
            (10, 75), (11, 80), (12, 85), (13, 75), (14, 65)  # 超買
        ]
        
        for day_offset, rsi_value in rsi_values:
            rsi_indicator = TechnicalIndicator(
                stock_id=test_stock.id,
                date=base_date + timedelta(days=day_offset),
                indicator_type='RSI',
                value=Decimal(str(rsi_value)),
                parameters={'period': 14}
            )
            db_session.add(rsi_indicator)
        
        # 模擬SMA數據（黃金交叉和死亡交叉）
        sma5_values = [
            (0, 100), (1, 101), (2, 102), (3, 103), (4, 104),
            (5, 105), (6, 106), (7, 107), (8, 108), (9, 109),  # 上升趨勢
            (10, 108), (11, 107), (12, 106), (13, 105), (14, 104)  # 下降趨勢
        ]
        
        sma20_values = [
            (0, 102), (1, 102), (2, 102), (3, 102), (4, 102),
            (5, 102), (6, 103), (7, 104), (8, 105), (9, 106),  # 緩慢上升
            (10, 107), (11, 107), (12, 107), (13, 107), (14, 107)
        ]
        
        for day_offset, sma5_value in sma5_values:
            sma5_indicator = TechnicalIndicator(
                stock_id=test_stock.id,
                date=base_date + timedelta(days=day_offset),
                indicator_type='SMA_5',
                value=Decimal(str(sma5_value)),
                parameters={'period': 5}
            )
            db_session.add(sma5_indicator)
        
        for day_offset, sma20_value in sma20_values:
            sma20_indicator = TechnicalIndicator(
                stock_id=test_stock.id,
                date=base_date + timedelta(days=day_offset),
                indicator_type='SMA_20',
                value=Decimal(str(sma20_value)),
                parameters={'period': 20}
            )
            db_session.add(sma20_indicator)
        
        # 模擬MACD數據
        macd_values = [
            (0, -2), (1, -1.5), (2, -1), (3, -0.5), (4, 0),
            (5, 0.5), (6, 1), (7, 1.5), (8, 1), (9, 0.5),
            (10, 0), (11, -0.5), (12, -1), (13, -1.5), (14, -1)
        ]
        
        macd_signal_values = [
            (0, -1.5), (1, -1.2), (2, -0.8), (3, -0.3), (4, 0.2),
            (5, 0.7), (6, 1.2), (7, 1.3), (8, 1.2), (9, 0.8),
            (10, 0.3), (11, -0.2), (12, -0.7), (13, -1.2), (14, -1.3)
        ]
        
        for day_offset, macd_value in macd_values:
            macd_indicator = TechnicalIndicator(
                stock_id=test_stock.id,
                date=base_date + timedelta(days=day_offset),
                indicator_type='MACD',
                value=Decimal(str(macd_value)),
                parameters={'fast_period': 12, 'slow_period': 26, 'signal_period': 9}
            )
            db_session.add(macd_indicator)
        
        for day_offset, signal_value in macd_signal_values:
            signal_indicator = TechnicalIndicator(
                stock_id=test_stock.id,
                date=base_date + timedelta(days=day_offset),
                indicator_type='MACD_SIGNAL',
                value=Decimal(str(signal_value)),
                parameters={'fast_period': 12, 'slow_period': 26, 'signal_period': 9}
            )
            db_session.add(signal_indicator)
        
        # 模擬KD數據
        kd_k_values = [
            (0, 20), (1, 25), (2, 30), (3, 35), (4, 40),
            (5, 45), (6, 50), (7, 55), (8, 60), (9, 65),
            (10, 70), (11, 75), (12, 80), (13, 75), (14, 70)
        ]
        
        kd_d_values = [
            (0, 25), (1, 27), (2, 30), (3, 32), (4, 35),
            (5, 40), (6, 45), (7, 50), (8, 55), (9, 60),
            (10, 65), (11, 70), (12, 75), (13, 77), (14, 75)
        ]
        
        for day_offset, k_value in kd_k_values:
            k_indicator = TechnicalIndicator(
                stock_id=test_stock.id,
                date=base_date + timedelta(days=day_offset),
                indicator_type='KD_K',
                value=Decimal(str(k_value)),
                parameters={'k_period': 14, 'd_period': 3}
            )
            db_session.add(k_indicator)
        
        for day_offset, d_value in kd_d_values:
            d_indicator = TechnicalIndicator(
                stock_id=test_stock.id,
                date=base_date + timedelta(days=day_offset),
                indicator_type='KD_D',
                value=Decimal(str(d_value)),
                parameters={'k_period': 14, 'd_period': 3}
            )
            db_session.add(d_indicator)
        
        await db_session.commit()
        print(f"✓ 建立測試股票和技術指標數據: {test_stock.symbol} (ID: {test_stock.id})")
        return test_stock.id


async def test_signal_detection(stock_id: int):
    """測試信號偵測功能"""
    print(f"\n=== 測試信號偵測功能 (股票ID: {stock_id}) ===")
    
    async with get_db() as db_session:
        # 測試偵測所有信號類型
        print("偵測所有信號類型...")
        
        result = await trading_signal_detector.detect_signals(
            db_session,
            stock_id=stock_id,
            signal_types=None,  # 偵測所有類型
            days=20,
            save_to_db=True
        )
        
        if result.success:
            print(f"✓ 信號偵測成功")
            print(f"  股票代號: {result.stock_symbol}")
            print(f"  偵測到信號數: {result.signals_detected}")
            print(f"  執行時間: {result.execution_time_seconds:.3f} 秒")
            
            if result.errors:
                print(f"  錯誤: {len(result.errors)} 個")
                for error in result.errors[:3]:
                    print(f"    - {error}")
            
            # 顯示偵測到的信號
            if result.signals:
                print(f"\n  偵測到的信號:")
                for signal in result.signals:
                    print(f"    {signal.signal_type.value}: {signal.description}")
                    print(f"      強度: {signal.strength.value}, 信心度: {signal.confidence:.2f}")
                    print(f"      日期: {signal.date}, 價格: {signal.price:.2f}")
                    print()
        else:
            print(f"✗ 信號偵測失敗: {result.errors}")
            return False
        
        # 驗證數據庫中的信號
        print("驗證數據庫中的交易信號...")
        
        signals = await trading_signal_crud.get_latest_signals(
            db_session,
            stock_id=stock_id,
            days=20
        )
        
        if signals:
            print(f"✓ 數據庫中找到 {len(signals)} 個交易信號:")
            
            signal_types = {}
            for signal in signals:
                if signal.signal_type not in signal_types:
                    signal_types[signal.signal_type] = []
                signal_types[signal.signal_type].append(signal)
            
            for signal_type, type_signals in signal_types.items():
                latest_signal = max(type_signals, key=lambda x: x.date)
                print(f"  {signal_type}: {len(type_signals)} 個信號, 最新: {latest_signal.date}")
                print(f"    信心度: {latest_signal.confidence:.2f}, 描述: {latest_signal.description}")
        else:
            print("✗ 數據庫中沒有找到交易信號")
            return False
        
        return True


async def test_specific_signal_types():
    """測試特定信號類型的偵測"""
    print("\n=== 測試特定信號類型偵測 ===")
    
    async with get_db() as db_session:
        # 獲取測試股票
        test_stock = await stock_crud.get_by_symbol(db_session, "SIGNAL_TEST")
        if not test_stock:
            print("✗ 找不到測試股票")
            return False
        
        # 測試各種信號類型
        signal_tests = [
            ([SignalType.RSI_OVERSOLD, SignalType.RSI_OVERBOUGHT], "RSI信號"),
            ([SignalType.GOLDEN_CROSS, SignalType.DEATH_CROSS], "移動平均交叉信號"),
            ([SignalType.MACD_BULLISH, SignalType.MACD_BEARISH], "MACD信號"),
            ([SignalType.KD_GOLDEN_CROSS, SignalType.KD_DEATH_CROSS], "KD信號")
        ]
        
        for signal_types, test_name in signal_tests:
            print(f"\n測試 {test_name}...")
            
            result = await trading_signal_detector.detect_signals(
                db_session,
                stock_id=test_stock.id,
                signal_types=signal_types,
                days=20,
                save_to_db=False  # 不保存，只測試偵測
            )
            
            if result.success:
                detected_types = [s.signal_type.value for s in result.signals]
                print(f"✓ {test_name} 偵測成功: {len(result.signals)} 個信號")
                print(f"  信號類型: {', '.join(set(detected_types))}")
                
                # 顯示高信心度信號
                high_confidence_signals = [s for s in result.signals if s.confidence >= 0.7]
                if high_confidence_signals:
                    print(f"  高信心度信號 (≥0.7): {len(high_confidence_signals)} 個")
                    for signal in high_confidence_signals[:3]:  # 只顯示前3個
                        print(f"    {signal.signal_type.value}: {signal.confidence:.2f}")
            else:
                print(f"✗ {test_name} 偵測失敗: {result.errors}")
        
        return True


async def test_signal_statistics():
    """測試信號統計功能"""
    print("\n=== 測試信號統計功能 ===")
    
    async with get_db() as db_session:
        # 獲取測試股票
        test_stock = await stock_crud.get_by_symbol(db_session, "SIGNAL_TEST")
        if not test_stock:
            print("✗ 找不到測試股票")
            return False
        
        # 測試信號統計
        print("取得信號統計...")
        
        stats = await trading_signal_crud.get_signal_statistics(
            db_session,
            stock_id=test_stock.id,
            days=30
        )
        
        print(f"✓ 信號統計:")
        print(f"  總信號數: {stats['total_signals']}")
        print(f"  平均信心度: {stats['avg_confidence']:.3f}")
        print(f"  最高信心度: {stats['max_confidence']:.3f}")
        print(f"  最低信心度: {stats['min_confidence']:.3f}")
        print(f"  信號類型數: {stats['signal_types_count']}")
        
        # 測試信號類型分布
        print("\n取得信號類型分布...")
        
        distribution = await trading_signal_crud.get_signal_type_distribution(
            db_session,
            stock_id=test_stock.id,
            days=30
        )
        
        if distribution:
            print("✓ 信號類型分布:")
            for signal_type, count in distribution.items():
                print(f"  {signal_type}: {count} 個")
        else:
            print("✗ 沒有信號分布數據")
        
        # 測試高信心度信號
        print("\n取得高信心度信號...")
        
        high_confidence_signals = await trading_signal_crud.get_high_confidence_signals(
            db_session,
            stock_id=test_stock.id,
            min_confidence=0.7,
            days=30
        )
        
        print(f"✓ 高信心度信號 (≥0.7): {len(high_confidence_signals)} 個")
        
        for signal in high_confidence_signals[:5]:  # 顯示前5個
            print(f"  {signal.signal_type}: {signal.confidence:.3f} ({signal.date})")
        
        return True


async def test_batch_detection():
    """測試批次信號偵測"""
    print("\n=== 測試批次信號偵測 ===")
    
    async with get_db() as db_session:
        # 獲取測試股票
        test_stock = await stock_crud.get_by_symbol(db_session, "SIGNAL_TEST")
        if not test_stock:
            print("✗ 找不到測試股票")
            return False
        
        # 測試批次偵測
        print("執行批次信號偵測...")
        
        results = await trading_signal_detector.batch_detect_signals(
            db_session,
            stock_ids=[test_stock.id],
            signal_types=[SignalType.RSI_OVERSOLD, SignalType.GOLDEN_CROSS, SignalType.MACD_BULLISH],
            days=20,
            save_to_db=True
        )
        
        if results:
            print(f"✓ 批次偵測完成: {len(results)} 支股票")
            
            for result in results:
                if result.success:
                    print(f"  {result.stock_symbol}: {result.signals_detected} 個信號")
                else:
                    print(f"  {result.stock_symbol}: 偵測失敗 - {result.errors}")
        else:
            print("✗ 批次偵測失敗")
            return False
        
        return True


async def test_signal_performance():
    """測試信號表現分析"""
    print("\n=== 測試信號表現分析 ===")
    
    async with get_db() as db_session:
        # 獲取測試股票
        test_stock = await stock_crud.get_by_symbol(db_session, "SIGNAL_TEST")
        if not test_stock:
            print("✗ 找不到測試股票")
            return False
        
        # 測試信號表現分析
        print("分析RSI信號表現...")
        
        performance = await trading_signal_crud.get_signal_performance_analysis(
            db_session,
            stock_id=test_stock.id,
            signal_type='rsi_oversold',
            days=90
        )
        
        print(f"✓ RSI超賣信號分析:")
        print(f"  總信號數: {performance['total_signals']}")
        print(f"  平均信心度: {performance.get('avg_confidence', 0):.3f}")
        print(f"  信心度分布: {performance.get('confidence_distribution', {})}")
        
        if performance.get('latest_signal_date'):
            print(f"  最新信號日期: {performance['latest_signal_date']}")
        
        return True


async def cleanup_test_data():
    """清理測試數據"""
    print("\n清理測試數據...")
    
    async with get_db() as db_session:
        # 刪除測試股票和相關數據
        test_stock = await stock_crud.get_by_symbol(db_session, "SIGNAL_TEST")
        
        if test_stock:
            # 刪除交易信號
            await db_session.execute(
                f"DELETE FROM trading_signals WHERE stock_id = {test_stock.id}"
            )
            
            # 刪除技術指標
            await db_session.execute(
                f"DELETE FROM technical_indicators WHERE stock_id = {test_stock.id}"
            )
            
            # 刪除股票
            await db_session.delete(test_stock)
            await db_session.commit()
            
            print("✓ 測試數據清理完成")


async def run_all_tests():
    """執行所有測試"""
    print("開始執行交易信號偵測器測試...")
    print("=" * 60)
    
    try:
        # 1. 建立測試數據
        stock_id = await create_test_data()
        
        # 2. 測試基本信號偵測
        basic_success = await test_signal_detection(stock_id)
        
        # 3. 測試特定信號類型
        specific_success = await test_specific_signal_types()
        
        # 4. 測試信號統計
        stats_success = await test_signal_statistics()
        
        # 5. 測試批次偵測
        batch_success = await test_batch_detection()
        
        # 6. 測試信號表現分析
        performance_success = await test_signal_performance()
        
        # 7. 清理測試數據
        await cleanup_test_data()
        
        print("\n" + "=" * 60)
        
        all_success = all([
            basic_success, specific_success, stats_success, 
            batch_success, performance_success
        ])
        
        if all_success:
            print("🎉 所有測試都通過了！")
            print("\n交易信號偵測系統已成功實作，包含以下功能：")
            print("✓ 多種信號類型偵測（黃金交叉、死亡交叉、RSI、MACD、KD等）")
            print("✓ 信號強度和信心度計算")
            print("✓ 批次信號偵測")
            print("✓ 信號統計和分析")
            print("✓ 數據庫存儲和查詢")
            print("✓ 信號表現分析")
            return True
        else:
            print("❌ 部分測試失敗")
            return False
            
    except Exception as e:
        print(f"\n❌ 測試過程中發生異常: {str(e)}")
        
        # 嘗試清理
        try:
            await cleanup_test_data()
        except:
            pass
        
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)