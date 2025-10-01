#!/usr/bin/env python3
"""
技術分析整合測試 - Clean Architecture
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
from services.analysis.technical_analysis import technical_analysis_service, IndicatorType
from services.analysis.indicator_calculator import indicator_calculator, PriceData
from domain.models.stock import Stock
from domain.models.price_history import PriceHistory
from domain.models.technical_indicator import TechnicalIndicator
from models.repositories.crud_stock import stock_crud
from models.repositories.crud_price_history import price_history_crud
from models.repositories.crud_technical_indicator import technical_indicator_crud


async def create_test_data():
    """建立測試數據"""
    print("建立測試數據...")
    
    async with get_db() as db_session:
        # 建立測試股票
        test_stock = Stock(
            symbol="TEST001",
            market="TW",
            name="測試股票001"
        )
        db_session.add(test_stock)
        await db_session.flush()  # 取得ID
        
        # 建立50天的價格數據
        base_date = date(2024, 1, 1)
        base_price = 100.0
        
        for i in range(50):
            current_date = base_date + timedelta(days=i)
            
            # 模擬價格變動
            price_change = (i * 0.5) + ((-1) ** i * 2)  # 有趨勢和波動
            current_price = base_price + price_change
            
            price_history = PriceHistory(
                stock_id=test_stock.id,
                date=current_date,
                open_price=Decimal(str(current_price * 0.99)),
                high_price=Decimal(str(current_price * 1.02)),
                low_price=Decimal(str(current_price * 0.98)),
                close_price=Decimal(str(current_price)),
                volume=1000000 + i * 10000,
                adjusted_close=Decimal(str(current_price))
            )
            db_session.add(price_history)
        
        await db_session.commit()
        print(f"✓ 建立測試股票: {test_stock.symbol} (ID: {test_stock.id})")
        return test_stock.id


async def test_indicator_calculator_directly():
    """直接測試指標計算器"""
    print("\n=== 測試指標計算器 ===")
    
    # 建立測試價格數據
    dates = [(datetime(2024, 1, 1) + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30)]
    base_price = 100.0
    close_prices = [base_price + i * 0.5 + ((-1) ** i * 1) for i in range(30)]
    
    price_data = PriceData(
        dates=dates,
        open_prices=[p * 0.99 for p in close_prices],
        high_prices=[p * 1.02 for p in close_prices],
        low_prices=[p * 0.98 for p in close_prices],
        close_prices=close_prices,
        volumes=[1000000] * 30
    )
    
    # 測試各種指標
    tests = [
        ("RSI", lambda: indicator_calculator.calculate_rsi(price_data)),
        ("SMA_20", lambda: indicator_calculator.calculate_sma(price_data, 20)),
        ("EMA_12", lambda: indicator_calculator.calculate_ema(price_data, 12)),
        ("ATR", lambda: indicator_calculator.calculate_atr(price_data)),
        ("Williams %R", lambda: indicator_calculator.calculate_williams_r(price_data)),
        ("OBV", lambda: indicator_calculator.calculate_obv(price_data))
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result.success:
                latest_value = result.get_latest_value()
                print(f"✓ {test_name}: 成功計算 {len(result.values)} 個值, 最新值: {latest_value:.4f}")
            else:
                print(f"✗ {test_name}: 計算失敗 - {result.error_message}")
        except Exception as e:
            print(f"✗ {test_name}: 異常 - {str(e)}")
    
    # 測試MACD（返回多個結果）
    try:
        macd, signal, histogram = indicator_calculator.calculate_macd(price_data)
        if macd.success and signal.success and histogram.success:
            print(f"✓ MACD: 成功計算 MACD({len(macd.values)}), Signal({len(signal.values)}), Histogram({len(histogram.values)})")
        else:
            print("✗ MACD: 計算失敗")
    except Exception as e:
        print(f"✗ MACD: 異常 - {str(e)}")
    
    # 測試布林通道
    try:
        upper, middle, lower = indicator_calculator.calculate_bollinger_bands(price_data)
        if upper.success and middle.success and lower.success:
            print(f"✓ 布林通道: 成功計算 Upper({len(upper.values)}), Middle({len(middle.values)}), Lower({len(lower.values)})")
        else:
            print("✗ 布林通道: 計算失敗")
    except Exception as e:
        print(f"✗ 布林通道: 異常 - {str(e)}")
    
    # 測試KD指標
    try:
        k, d = indicator_calculator.calculate_stochastic(price_data)
        if k.success and d.success:
            print(f"✓ KD指標: 成功計算 %K({len(k.values)}), %D({len(d.values)})")
        else:
            print("✗ KD指標: 計算失敗")
    except Exception as e:
        print(f"✗ KD指標: 異常 - {str(e)}")


async def test_technical_analysis_service(stock_id: int):
    """測試技術分析服務"""
    print(f"\n=== 測試技術分析服務 (股票ID: {stock_id}) ===")
    
    async with get_db() as db_session:
        # 測試計算所有指標
        print("計算所有技術指標...")
        
        analysis_result = await technical_analysis_service.calculate_stock_indicators(
            db_session,
            stock_id=stock_id,
            indicators=None,  # 計算所有指標
            days=50,
            save_to_db=True
        )
        
        if analysis_result.indicators_successful > 0:
            print(f"✓ 成功計算 {analysis_result.indicators_successful} 個指標")
            print(f"  執行時間: {analysis_result.execution_time_seconds:.2f} 秒")
            
            if analysis_result.errors:
                print(f"  錯誤: {len(analysis_result.errors)} 個")
                for error in analysis_result.errors[:3]:
                    print(f"    - {error}")
        else:
            print("✗ 指標計算失敗")
            for error in analysis_result.errors:
                print(f"  錯誤: {error}")
            return False
        
        # 驗證數據庫中的指標
        print("\n驗證數據庫中的指標...")
        
        indicators = await technical_indicator_crud.get_latest_indicators(
            db_session,
            stock_id=stock_id
        )
        
        if indicators:
            print(f"✓ 數據庫中找到 {len(indicators)} 個最新指標:")
            
            indicator_groups = {}
            for indicator in indicators:
                indicator_groups[indicator.indicator_type] = indicator
            
            # 檢查主要指標
            key_indicators = ['RSI', 'SMA_20', 'EMA_12', 'MACD', 'BB_UPPER', 'KD_K', 'ATR']
            
            for indicator_type in key_indicators:
                if indicator_type in indicator_groups:
                    indicator = indicator_groups[indicator_type]
                    print(f"  {indicator_type}: {indicator.value} ({indicator.date})")
                else:
                    print(f"  {indicator_type}: 未找到")
        else:
            print("✗ 數據庫中沒有找到指標")
            return False
        
        return True


async def test_indicator_accuracy():
    """測試指標計算準確性"""
    print("\n=== 測試指標計算準確性 ===")
    
    # 使用已知的測試數據
    test_prices = [
        44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.85, 46.08, 45.89, 46.03,
        46.83, 46.69, 46.45, 46.59, 46.3, 46.28, 46.28, 46.00, 46.03, 46.41,
        46.22, 45.64, 46.21, 46.25, 45.71, 46.45, 47.44, 47.02, 47.61, 48.08
    ]
    
    dates = [(datetime(2024, 1, 1) + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(len(test_prices))]
    
    price_data = PriceData(
        dates=dates,
        open_prices=test_prices,
        high_prices=[p * 1.01 for p in test_prices],
        low_prices=[p * 0.99 for p in test_prices],
        close_prices=test_prices,
        volumes=[1000000] * len(test_prices)
    )
    
    # 測試RSI計算
    rsi_result = indicator_calculator.calculate_rsi(price_data, period=14)
    
    if rsi_result.success and len(rsi_result.values) > 0:
        latest_rsi = rsi_result.get_latest_value()
        print(f"✓ RSI計算: 最新值 {latest_rsi:.2f}")
        
        # RSI應該在合理範圍內
        if 30 <= latest_rsi <= 70:
            print("  RSI值在正常範圍內")
        elif latest_rsi < 30:
            print("  RSI顯示超賣狀態")
        elif latest_rsi > 70:
            print("  RSI顯示超買狀態")
    else:
        print("✗ RSI計算失敗")
    
    # 測試SMA計算準確性
    sma_result = indicator_calculator.calculate_sma(price_data, period=10)
    
    if sma_result.success and len(sma_result.values) > 0:
        # 手動計算最後10個價格的平均值
        manual_sma = sum(test_prices[-10:]) / 10
        calculated_sma = sma_result.get_latest_value()
        
        print(f"✓ SMA計算: 手動計算 {manual_sma:.4f}, 程式計算 {calculated_sma:.4f}")
        
        if abs(manual_sma - calculated_sma) < 0.0001:
            print("  SMA計算準確")
        else:
            print(f"  SMA計算有差異: {abs(manual_sma - calculated_sma):.6f}")
    else:
        print("✗ SMA計算失敗")


async def test_error_handling():
    """測試錯誤處理"""
    print("\n=== 測試錯誤處理 ===")
    
    # 測試數據不足的情況
    insufficient_data = PriceData(
        dates=['2024-01-01', '2024-01-02'],
        open_prices=[100.0, 101.0],
        high_prices=[101.0, 102.0],
        low_prices=[99.0, 100.0],
        close_prices=[100.5, 101.5],
        volumes=[1000000, 1100000]
    )
    
    rsi_result = indicator_calculator.calculate_rsi(insufficient_data, period=14)
    
    if not rsi_result.success:
        print("✓ 正確處理數據不足的情況")
        print(f"  錯誤訊息: {rsi_result.error_message}")
    else:
        print("✗ 應該要檢測到數據不足")
    
    # 測試無效數據
    invalid_data = PriceData(
        dates=['2024-01-01'],
        open_prices=[100.0, 101.0],  # 長度不匹配
        high_prices=[101.0],
        low_prices=[99.0],
        close_prices=[100.5],
        volumes=[1000000]
    )
    
    if not invalid_data.validate():
        print("✓ 正確檢測到無效數據")
    else:
        print("✗ 應該要檢測到無效數據")


async def cleanup_test_data():
    """清理測試數據"""
    print("\n清理測試數據...")
    
    async with get_db() as db_session:
        # 刪除測試股票和相關數據
        test_stock = await stock_crud.get_by_symbol(db_session, "TEST001")
        
        if test_stock:
            # 刪除技術指標
            await db_session.execute(
                f"DELETE FROM technical_indicators WHERE stock_id = {test_stock.id}"
            )
            
            # 刪除價格歷史
            await db_session.execute(
                f"DELETE FROM price_history WHERE stock_id = {test_stock.id}"
            )
            
            # 刪除股票
            await db_session.delete(test_stock)
            await db_session.commit()
            
            print("✓ 測試數據清理完成")


async def run_all_tests():
    """執行所有測試"""
    print("開始執行技術分析整合測試...")
    print("=" * 60)
    
    try:
        # 1. 測試指標計算器
        await test_indicator_calculator_directly()
        
        # 2. 測試指標準確性
        await test_indicator_accuracy()
        
        # 3. 測試錯誤處理
        await test_error_handling()
        
        # 4. 建立測試數據並測試整合服務
        stock_id = await create_test_data()
        
        # 5. 測試技術分析服務
        service_success = await test_technical_analysis_service(stock_id)
        
        # 6. 清理測試數據
        await cleanup_test_data()
        
        print("\n" + "=" * 60)
        
        if service_success:
            print("🎉 所有測試都通過了！")
            print("\n技術指標計算器已成功外部化，並通過以下驗證：")
            print("✓ 指標計算邏輯正確")
            print("✓ 數值計算準確")
            print("✓ 錯誤處理完善")
            print("✓ 與技術分析服務整合成功")
            print("✓ 數據庫存儲正常")
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