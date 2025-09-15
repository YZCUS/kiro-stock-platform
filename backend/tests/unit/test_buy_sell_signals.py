#!/usr/bin/env python3
"""
買賣點標示功能測試
"""
import asyncio
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal

# 添加項目根目錄到 Python 路徑
sys.path.append('/app')

from core.database import get_db
from services.trading.buy_sell_generator import (
    buy_sell_signal_generator,
    BuySellAction,
    SignalPriority
)
from services.trading.signal_notification import (
    signal_notification_service,
    NotificationType,
    AlertLevel
)
from models.domain.stock import Stock
from models.domain.trading_signal import TradingSignal
from models.domain.price_history import PriceHistory
from models.repositories.crud_stock import stock_crud
from models.repositories.crud_trading_signal import trading_signal_crud
from models.repositories.crud_price_history import price_history_crud


async def create_test_data():
    """建立測試數據"""
    print("建立測試數據...")
    
    async with get_db() as db_session:
        # 建立測試股票
        test_stock = Stock(
            symbol="BUYSELL_TEST",
            market="TW",
            name="買賣點測試股票"
        )
        db_session.add(test_stock)
        await db_session.flush()
        
        # 建立價格數據（模擬上升趨勢）
        base_date = date(2024, 1, 1)
        base_price = 100.0
        
        for i in range(30):
            current_date = base_date + timedelta(days=i)
            
            # 模擬價格趨勢（整體上升，有波動）
            trend = i * 0.5  # 上升趨勢
            noise = (i % 3 - 1) * 2  # 波動
            current_price = base_price + trend + noise
            
            price_history = PriceHistory(
                stock_id=test_stock.id,
                date=current_date,
                open_price=Decimal(str(current_price * 0.99)),
                high_price=Decimal(str(current_price * 1.02)),
                low_price=Decimal(str(current_price * 0.98)),
                close_price=Decimal(str(current_price)),
                volume=1000000 + i * 50000,
                adjusted_close=Decimal(str(current_price))
            )
            db_session.add(price_history)
        
        # 建立交易信號（模擬各種信號情況）
        signal_data = [
            # 買入信號
            (5, "golden_cross", 0.8, "黃金交叉信號"),
            (8, "rsi_oversold", 0.7, "RSI超賣信號"),
            (12, "macd_bullish", 0.75, "MACD看漲信號"),
            (15, "kd_golden_cross", 0.65, "KD黃金交叉"),
            
            # 賣出信號
            (20, "death_cross", 0.85, "死亡交叉信號"),
            (23, "rsi_overbought", 0.72, "RSI超買信號"),
            (26, "macd_bearish", 0.68, "MACD看跌信號"),
            (28, "kd_death_cross", 0.63, "KD死亡交叉"),
        ]
        
        for day_offset, signal_type, confidence, description in signal_data:
            signal_date = base_date + timedelta(days=day_offset)
            signal_price = base_price + day_offset * 0.5
            
            trading_signal = TradingSignal(
                stock_id=test_stock.id,
                signal_type=signal_type,
                date=signal_date,
                price=Decimal(str(signal_price)),
                confidence=confidence,
                description=description
            )
            db_session.add(trading_signal)
        
        await db_session.commit()
        print(f"✓ 建立測試股票和數據: {test_stock.symbol} (ID: {test_stock.id})")
        return test_stock.id


async def test_buy_sell_point_generation(stock_id: int):
    """測試買賣點生成功能"""
    print(f"\n=== 測試買賣點生成功能 (股票ID: {stock_id}) ===")
    
    async with get_db() as db_session:
        # 測試生成買賣點
        print("生成買賣點標示...")
        
        result = await buy_sell_signal_generator.generate_buy_sell_points(
            db_session,
            stock_id=stock_id,
            days=35,
            min_confidence=0.6
        )
        
        if result.success:
            print(f"✓ 買賣點生成成功")
            print(f"  股票代號: {result.stock_symbol}")
            print(f"  市場趨勢: {result.market_trend}")
            print(f"  整體建議: {result.overall_recommendation.value}")
            print(f"  信心度: {result.confidence_score:.3f}")
            print(f"  風險評估: {result.risk_assessment}")
            print(f"  買賣點數量: {len(result.buy_sell_points)}")
            print(f"  執行時間: {result.execution_time_seconds:.3f} 秒")
            
            if result.errors:
                print(f"  錯誤: {len(result.errors)} 個")
                for error in result.errors[:3]:
                    print(f"    - {error}")
            
            # 顯示買賣點詳情
            if result.buy_sell_points:
                print(f"\n  買賣點詳情:")
                for i, point in enumerate(result.buy_sell_points[:10]):  # 只顯示前10個
                    action_text = "買入" if point.action == BuySellAction.BUY else "賣出"
                    print(f"    {i+1}. {point.date} | {action_text} | 優先級: {point.priority.value}")
                    print(f"       價格: {point.price:.2f} | 信心度: {point.confidence:.3f}")
                    print(f"       風險: {point.risk_level} | 理由: {point.reason}")
                    
                    if point.stop_loss:
                        print(f"       止損: {point.stop_loss:.2f}")
                    if point.take_profit:
                        print(f"       止盈: {point.take_profit:.2f}")
                    print()
            
            return True
        else:
            print(f"✗ 買賣點生成失敗: {result.errors}")
            return False


async def test_signal_priority_sorting():
    """測試信號優先級排序"""
    print("\n=== 測試信號優先級排序 ===")
    
    async with get_db() as db_session:
        # 獲取測試股票
        test_stock = await stock_crud.get_by_symbol(db_session, "BUYSELL_TEST")
        if not test_stock:
            print("✗ 找不到測試股票")
            return False
        
        # 生成買賣點
        result = await buy_sell_signal_generator.generate_buy_sell_points(
            db_session,
            stock_id=test_stock.id,
            days=35,
            min_confidence=0.5  # 降低閾值以獲得更多信號
        )
        
        if result.success and result.buy_sell_points:
            print(f"✓ 獲得 {len(result.buy_sell_points)} 個買賣點")
            
            # 按優先級分組
            priority_groups = {}
            for point in result.buy_sell_points:
                priority = point.priority.value
                if priority not in priority_groups:
                    priority_groups[priority] = []
                priority_groups[priority].append(point)
            
            print("按優先級分組:")
            for priority in ['critical', 'high', 'medium', 'low']:
                if priority in priority_groups:
                    points = priority_groups[priority]
                    print(f"  {priority.upper()}: {len(points)} 個")
                    
                    # 顯示該優先級的信號
                    for point in points[:3]:  # 只顯示前3個
                        action_text = "買入" if point.action == BuySellAction.BUY else "賣出"
                        print(f"    {point.date} | {action_text} | {point.confidence:.3f}")
            
            # 測試高優先級信號過濾
            high_priority_points = [
                p for p in result.buy_sell_points 
                if p.priority in [SignalPriority.HIGH, SignalPriority.CRITICAL]
            ]
            
            print(f"\n高優先級信號: {len(high_priority_points)} 個")
            for point in high_priority_points:
                action_text = "買入" if point.action == BuySellAction.BUY else "賣出"
                print(f"  {point.date} | {action_text} | {point.priority.value} | {point.confidence:.3f}")
            
            return True
        else:
            print("✗ 沒有獲得買賣點數據")
            return False


async def test_notification_system():
    """測試通知系統"""
    print("\n=== 測試通知系統 ===")
    
    try:
        # 測試添加通知規則
        print("1. 測試添加通知規則...")
        
        rule_id = signal_notification_service.add_notification_rule(
            user_id=1,
            stock_symbols=["BUYSELL_TEST"],
            signal_types=["golden_cross", "death_cross"],
            min_confidence=0.7,
            min_priority=SignalPriority.MEDIUM,
            notification_types=[NotificationType.IN_APP, NotificationType.EMAIL]
        )
        
        print(f"✓ 添加通知規則: {rule_id}")
        
        # 測試獲取用戶規則
        user_rules = signal_notification_service.get_user_notification_rules(1)
        print(f"✓ 用戶規則數量: {len(user_rules)}")
        
        # 測試處理交易信號通知
        print("\n2. 測試交易信號通知...")
        
        async with get_db() as db_session:
            test_stock = await stock_crud.get_by_symbol(db_session, "BUYSELL_TEST")
            if test_stock:
                # 建立測試信號
                test_signal = TradingSignal(
                    stock_id=test_stock.id,
                    signal_type="golden_cross",
                    date=date.today(),
                    price=Decimal("120.50"),
                    confidence=0.85,
                    description="測試黃金交叉信號"
                )
                
                await signal_notification_service.process_trading_signal(
                    db_session, test_stock.id, test_signal
                )
                
                print("✓ 處理交易信號通知")
        
        # 測試處理通知隊列
        print("\n3. 測試處理通知隊列...")
        
        await signal_notification_service.process_notification_queue()
        
        # 獲取通知統計
        stats = signal_notification_service.get_notification_statistics()
        print(f"✓ 通知統計:")
        print(f"  總訊息數: {stats.get('total_messages', 0)}")
        print(f"  已發送: {stats.get('sent_messages', 0)}")
        print(f"  失敗: {stats.get('failed_messages', 0)}")
        print(f"  待發送: {stats.get('pending_messages', 0)}")
        print(f"  成功率: {stats.get('success_rate', 0):.2%}")
        
        # 獲取用戶訊息
        user_messages = signal_notification_service.get_user_messages(1, limit=10)
        print(f"✓ 用戶訊息數量: {len(user_messages)}")
        
        for msg in user_messages[:3]:  # 顯示前3個
            print(f"  {msg.created_at.strftime('%H:%M:%S')} | {msg.title} | {msg.status}")
        
        return True
        
    except Exception as e:
        print(f"✗ 通知系統測試失敗: {str(e)}")
        return False


async def test_risk_assessment():
    """測試風險評估功能"""
    print("\n=== 測試風險評估功能 ===")
    
    async with get_db() as db_session:
        # 獲取測試股票
        test_stock = await stock_crud.get_by_symbol(db_session, "BUYSELL_TEST")
        if not test_stock:
            print("✗ 找不到測試股票")
            return False
        
        # 生成買賣點並分析風險
        result = await buy_sell_signal_generator.generate_buy_sell_points(
            db_session,
            stock_id=test_stock.id,
            days=35,
            min_confidence=0.5
        )
        
        if result.success:
            print(f"✓ 風險評估結果:")
            print(f"  整體風險: {result.risk_assessment}")
            print(f"  市場趨勢: {result.market_trend}")
            
            # 按風險等級分組買賣點
            risk_groups = {}
            for point in result.buy_sell_points:
                risk = point.risk_level
                if risk not in risk_groups:
                    risk_groups[risk] = []
                risk_groups[risk].append(point)
            
            print("\n按風險等級分組:")
            for risk_level in ['low', 'medium', 'high', 'very_high']:
                if risk_level in risk_groups:
                    points = risk_groups[risk_level]
                    print(f"  {risk_level.upper()}: {len(points)} 個買賣點")
                    
                    # 顯示該風險等級的信號
                    for point in points[:2]:  # 只顯示前2個
                        action_text = "買入" if point.action == BuySellAction.BUY else "賣出"
                        print(f"    {point.date} | {action_text} | 信心度: {point.confidence:.3f}")
            
            # 分析止損止盈設定
            points_with_stops = [p for p in result.buy_sell_points if p.stop_loss and p.take_profit]
            if points_with_stops:
                print(f"\n止損止盈分析 ({len(points_with_stops)} 個點):")
                
                for point in points_with_stops[:3]:
                    action_text = "買入" if point.action == BuySellAction.BUY else "賣出"
                    stop_loss_pct = abs(point.stop_loss - point.price) / point.price * 100
                    take_profit_pct = abs(point.take_profit - point.price) / point.price * 100
                    
                    print(f"  {action_text} @ {point.price:.2f}")
                    print(f"    止損: {point.stop_loss:.2f} ({stop_loss_pct:.1f}%)")
                    print(f"    止盈: {point.take_profit:.2f} ({take_profit_pct:.1f}%)")
            
            return True
        else:
            print(f"✗ 風險評估失敗: {result.errors}")
            return False


async def cleanup_test_data():
    """清理測試數據"""
    print("\n清理測試數據...")
    
    async with get_db() as db_session:
        # 刪除測試股票和相關數據
        test_stock = await stock_crud.get_by_symbol(db_session, "BUYSELL_TEST")
        
        if test_stock:
            # 刪除交易信號
            await db_session.execute(
                f"DELETE FROM trading_signals WHERE stock_id = {test_stock.id}"
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
    print("開始執行買賣點標示功能測試...")
    print("=" * 60)
    
    try:
        # 1. 建立測試數據
        stock_id = await create_test_data()
        
        # 2. 測試買賣點生成
        generation_success = await test_buy_sell_point_generation(stock_id)
        
        # 3. 測試信號優先級排序
        priority_success = await test_signal_priority_sorting()
        
        # 4. 測試通知系統
        notification_success = await test_notification_system()
        
        # 5. 測試風險評估
        risk_success = await test_risk_assessment()
        
        # 6. 清理測試數據
        await cleanup_test_data()
        
        print("\n" + "=" * 60)
        
        all_success = all([
            generation_success, priority_success, 
            notification_success, risk_success
        ])
        
        if all_success:
            print("🎉 所有測試都通過了！")
            print("\n買賣點標示系統已成功實作，包含以下功能：")
            print("✓ 智能買賣點生成")
            print("✓ 信號優先級排序")
            print("✓ 風險評估和止損止盈計算")
            print("✓ 市場趨勢分析")
            print("✓ 通知和警報系統")
            print("✓ 多種通知類型支援")
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