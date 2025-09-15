#!/usr/bin/env python3
"""
買賣點標示管理命令行工具
"""
import asyncio
import sys
import argparse
from datetime import date, timedelta
from typing import List, Optional

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
    NotificationType
)
from models.repositories.crud_stock import stock_crud


async def generate_buy_sell_points_command(
    stock_symbols: List[str],
    days: int = 30,
    min_confidence: float = 0.6
):
    """生成買賣點命令"""
    print(f"開始生成 {len(stock_symbols)} 支股票的買賣點標示...")
    
    try:
        async with get_db() as db_session:
            for symbol in stock_symbols:
                stock = await stock_crud.get_by_symbol(db_session, symbol)
                if not stock:
                    print(f"找不到股票: {symbol}")
                    continue
                
                print(f"\n分析股票: {symbol}")
                
                # 生成買賣點
                result = await buy_sell_signal_generator.generate_buy_sell_points(
                    db_session,
                    stock_id=stock.id,
                    days=days,
                    min_confidence=min_confidence
                )
                
                if result.success:
                    print(f"✓ 買賣點生成成功")
                    print(f"  市場趨勢: {result.market_trend}")
                    print(f"  整體建議: {result.overall_recommendation.value}")
                    print(f"  信心度: {result.confidence_score:.3f}")
                    print(f"  風險評估: {result.risk_assessment}")
                    print(f"  買賣點數量: {len(result.buy_sell_points)}")
                    
                    # 顯示買賣點
                    if result.buy_sell_points:
                        print("  買賣點詳情:")
                        for i, point in enumerate(result.buy_sell_points[:5]):  # 只顯示前5個
                            action_text = "買入" if point.action == BuySellAction.BUY else "賣出"
                            print(f"    {i+1}. {point.date} | {action_text} | {point.priority.value}")
                            print(f"       價格: {point.price:.2f} | 信心度: {point.confidence:.3f}")
                            print(f"       風險: {point.risk_level}")
                            print(f"       理由: {point.reason}")
                            
                            if point.stop_loss and point.take_profit:
                                print(f"       止損: {point.stop_loss:.2f} | 止盈: {point.take_profit:.2f}")
                else:
                    print(f"✗ 買賣點生成失敗: {result.errors}")
    
    except Exception as e:
        print(f"生成買賣點時發生錯誤: {str(e)}")


async def analyze_market_trend_command(
    stock_symbols: List[str],
    days: int = 30
):
    """分析市場趨勢命令"""
    print(f"分析 {len(stock_symbols)} 支股票的市場趨勢...")
    
    try:
        async with get_db() as db_session:
            trend_summary = {}
            
            for symbol in stock_symbols:
                stock = await stock_crud.get_by_symbol(db_session, symbol)
                if not stock:
                    print(f"找不到股票: {symbol}")
                    continue
                
                # 生成買賣點分析
                result = await buy_sell_signal_generator.generate_buy_sell_points(
                    db_session,
                    stock_id=stock.id,
                    days=days,
                    min_confidence=0.5
                )
                
                if result.success:
                    trend = result.market_trend
                    recommendation = result.overall_recommendation.value
                    confidence = result.confidence_score
                    
                    print(f"\n{symbol}:")
                    print(f"  趨勢: {trend}")
                    print(f"  建議: {recommendation}")
                    print(f"  信心度: {confidence:.3f}")
                    print(f"  風險: {result.risk_assessment}")
                    
                    # 統計趨勢分布
                    if trend not in trend_summary:
                        trend_summary[trend] = []
                    trend_summary[trend].append(symbol)
                else:
                    print(f"{symbol}: 分析失敗")
            
            # 顯示趨勢摘要
            if trend_summary:
                print(f"\n趨勢摘要:")
                for trend, symbols in trend_summary.items():
                    print(f"  {trend}: {len(symbols)} 支股票")
                    print(f"    {', '.join(symbols[:5])}")  # 只顯示前5支
                    if len(symbols) > 5:
                        print(f"    ... 還有 {len(symbols) - 5} 支")
    
    except Exception as e:
        print(f"分析市場趨勢時發生錯誤: {str(e)}")


async def filter_signals_command(
    stock_symbols: List[str] = None,
    action: str = None,
    min_priority: str = "medium",
    min_confidence: float = 0.7,
    days: int = 7
):
    """過濾信號命令"""
    print("過濾買賣信號...")
    
    try:
        # 轉換優先級
        priority_map = {
            "low": SignalPriority.LOW,
            "medium": SignalPriority.MEDIUM,
            "high": SignalPriority.HIGH,
            "critical": SignalPriority.CRITICAL
        }
        min_priority_enum = priority_map.get(min_priority, SignalPriority.MEDIUM)
        
        async with get_db() as db_session:
            filtered_points = []
            
            # 如果沒有指定股票，獲取所有活躍股票
            if not stock_symbols:
                stocks = await stock_crud.get_multi(db_session, limit=20)
                stock_symbols = [stock.symbol for stock in stocks]
            
            for symbol in stock_symbols:
                stock = await stock_crud.get_by_symbol(db_session, symbol)
                if not stock:
                    continue
                
                # 生成買賣點
                result = await buy_sell_signal_generator.generate_buy_sell_points(
                    db_session,
                    stock_id=stock.id,
                    days=days,
                    min_confidence=min_confidence
                )
                
                if result.success:
                    for point in result.buy_sell_points:
                        # 過濾條件
                        if action and point.action.value != action:
                            continue
                        
                        # 檢查優先級
                        priority_levels = {
                            SignalPriority.LOW: 1,
                            SignalPriority.MEDIUM: 2,
                            SignalPriority.HIGH: 3,
                            SignalPriority.CRITICAL: 4
                        }
                        
                        if priority_levels.get(point.priority, 0) < priority_levels.get(min_priority_enum, 0):
                            continue
                        
                        filtered_points.append((symbol, point))
            
            # 按信心度排序
            filtered_points.sort(key=lambda x: x[1].confidence, reverse=True)
            
            print(f"\n找到 {len(filtered_points)} 個符合條件的買賣點:")
            
            for symbol, point in filtered_points[:20]:  # 只顯示前20個
                action_text = "買入" if point.action == BuySellAction.BUY else "賣出"
                print(f"  {symbol} | {action_text} | {point.priority.value}")
                print(f"    日期: {point.date} | 價格: {point.price:.2f}")
                print(f"    信心度: {point.confidence:.3f} | 風險: {point.risk_level}")
                print(f"    理由: {point.reason}")
                print()
    
    except Exception as e:
        print(f"過濾信號時發生錯誤: {str(e)}")


async def setup_notifications_command(
    user_id: int,
    stock_symbols: List[str] = None,
    min_confidence: float = 0.8,
    min_priority: str = "high",
    notification_types: List[str] = None
):
    """設置通知命令"""
    print(f"為用戶 {user_id} 設置買賣點通知...")
    
    try:
        # 轉換通知類型
        type_map = {
            "email": NotificationType.EMAIL,
            "sms": NotificationType.SMS,
            "push": NotificationType.PUSH,
            "webhook": NotificationType.WEBHOOK,
            "in_app": NotificationType.IN_APP
        }
        
        notification_type_enums = []
        if notification_types:
            for nt in notification_types:
                if nt in type_map:
                    notification_type_enums.append(type_map[nt])
        else:
            notification_type_enums = [NotificationType.IN_APP]
        
        # 轉換優先級
        priority_map = {
            "low": SignalPriority.LOW,
            "medium": SignalPriority.MEDIUM,
            "high": SignalPriority.HIGH,
            "critical": SignalPriority.CRITICAL
        }
        min_priority_enum = priority_map.get(min_priority, SignalPriority.HIGH)
        
        # 添加通知規則
        rule_id = signal_notification_service.add_notification_rule(
            user_id=user_id,
            stock_symbols=stock_symbols,
            min_confidence=min_confidence,
            min_priority=min_priority_enum,
            notification_types=notification_type_enums
        )
        
        print(f"✓ 成功添加通知規則: {rule_id}")
        print(f"  用戶ID: {user_id}")
        print(f"  股票: {stock_symbols or '所有股票'}")
        print(f"  最小信心度: {min_confidence}")
        print(f"  最小優先級: {min_priority}")
        print(f"  通知類型: {', '.join([nt.value for nt in notification_type_enums])}")
        
        # 顯示用戶的所有規則
        user_rules = signal_notification_service.get_user_notification_rules(user_id)
        print(f"\n用戶 {user_id} 的所有通知規則 ({len(user_rules)} 個):")
        
        for rule in user_rules:
            print(f"  規則ID: {rule.rule_id}")
            print(f"    股票: {rule.stock_symbols or '所有'}")
            print(f"    信心度: ≥{rule.min_confidence}")
            print(f"    優先級: ≥{rule.min_priority.value}")
            print(f"    通知類型: {[nt.value for nt in rule.notification_types]}")
            print(f"    狀態: {'啟用' if rule.enabled else '停用'}")
            print()
    
    except Exception as e:
        print(f"設置通知時發生錯誤: {str(e)}")


async def notification_stats_command():
    """通知統計命令"""
    print("獲取通知統計...")
    
    try:
        stats = signal_notification_service.get_notification_statistics()
        
        print(f"通知系統統計:")
        print(f"  總訊息數: {stats.get('total_messages', 0)}")
        print(f"  已發送: {stats.get('sent_messages', 0)}")
        print(f"  失敗: {stats.get('failed_messages', 0)}")
        print(f"  待發送: {stats.get('pending_messages', 0)}")
        print(f"  成功率: {stats.get('success_rate', 0):.2%}")
        print(f"  活躍用戶: {stats.get('active_users', 0)}")
        print(f"  總規則數: {stats.get('total_rules', 0)}")
        
        # 按類型統計
        type_stats = stats.get('type_statistics', {})
        if type_stats:
            print(f"\n按通知類型統計:")
            for msg_type, type_data in type_stats.items():
                print(f"  {msg_type}:")
                print(f"    總數: {type_data['total']}")
                print(f"    成功: {type_data['sent']}")
                print(f"    失敗: {type_data['failed']}")
        
        # 按用戶統計
        user_stats = stats.get('user_statistics', {})
        if user_stats:
            print(f"\n按用戶統計 (前10名):")
            sorted_users = sorted(user_stats.items(), key=lambda x: x[1], reverse=True)
            for user_id, count in sorted_users[:10]:
                print(f"  用戶 {user_id}: {count} 個訊息")
    
    except Exception as e:
        print(f"獲取通知統計時發生錯誤: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description="買賣點標示管理工具")
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 生成買賣點命令
    generate_parser = subparsers.add_parser('generate', help='生成買賣點標示')
    generate_parser.add_argument('symbols', nargs='+', help='股票代號列表')
    generate_parser.add_argument('--days', type=int, default=30, help='分析天數')
    generate_parser.add_argument('--min-confidence', type=float, default=0.6, help='最小信心度')
    
    # 分析趨勢命令
    trend_parser = subparsers.add_parser('trend', help='分析市場趨勢')
    trend_parser.add_argument('symbols', nargs='+', help='股票代號列表')
    trend_parser.add_argument('--days', type=int, default=30, help='分析天數')
    
    # 過濾信號命令
    filter_parser = subparsers.add_parser('filter', help='過濾買賣信號')
    filter_parser.add_argument('--symbols', nargs='*', help='股票代號列表')
    filter_parser.add_argument('--action', choices=['buy', 'sell'], help='動作類型')
    filter_parser.add_argument('--min-priority', choices=['low', 'medium', 'high', 'critical'], 
                              default='medium', help='最小優先級')
    filter_parser.add_argument('--min-confidence', type=float, default=0.7, help='最小信心度')
    filter_parser.add_argument('--days', type=int, default=7, help='查詢天數')
    
    # 設置通知命令
    notify_parser = subparsers.add_parser('notify', help='設置通知規則')
    notify_parser.add_argument('user_id', type=int, help='用戶ID')
    notify_parser.add_argument('--symbols', nargs='*', help='股票代號列表')
    notify_parser.add_argument('--min-confidence', type=float, default=0.8, help='最小信心度')
    notify_parser.add_argument('--min-priority', choices=['low', 'medium', 'high', 'critical'], 
                              default='high', help='最小優先級')
    notify_parser.add_argument('--types', nargs='*', 
                              choices=['email', 'sms', 'push', 'webhook', 'in_app'],
                              help='通知類型')
    
    # 通知統計命令
    subparsers.add_parser('stats', help='通知統計')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 執行對應命令
    if args.command == 'generate':
        asyncio.run(generate_buy_sell_points_command(
            stock_symbols=args.symbols,
            days=args.days,
            min_confidence=args.min_confidence
        ))
    
    elif args.command == 'trend':
        asyncio.run(analyze_market_trend_command(
            stock_symbols=args.symbols,
            days=args.days
        ))
    
    elif args.command == 'filter':
        asyncio.run(filter_signals_command(
            stock_symbols=args.symbols,
            action=args.action,
            min_priority=args.min_priority,
            min_confidence=args.min_confidence,
            days=args.days
        ))
    
    elif args.command == 'notify':
        asyncio.run(setup_notifications_command(
            user_id=args.user_id,
            stock_symbols=args.symbols,
            min_confidence=args.min_confidence,
            min_priority=args.min_priority,
            notification_types=args.types
        ))
    
    elif args.command == 'stats':
        asyncio.run(notification_stats_command())


if __name__ == "__main__":
    main()