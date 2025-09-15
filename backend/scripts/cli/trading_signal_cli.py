#!/usr/bin/env python3
"""
交易信號管理命令行工具
"""
import asyncio
import sys
import argparse
from datetime import date, timedelta
from typing import List, Optional

# 添加項目根目錄到 Python 路徑
sys.path.append('/app')

from core.database import get_db
from services.analysis.signal_detector import (
    trading_signal_detector, 
    SignalType, 
    SignalStrength
)
from models.repositories.crud_stock import stock_crud
from models.repositories.crud_trading_signal import trading_signal_crud


async def detect_signals_command(
    stock_symbols: List[str],
    signal_types: List[str] = None,
    days: int = 30,
    min_confidence: float = 0.6,
    save_to_db: bool = True
):
    """偵測交易信號命令"""
    print(f"開始偵測 {len(stock_symbols)} 支股票的交易信號...")
    
    try:
        async with get_db() as db_session:
            # 獲取股票ID
            stock_ids = []
            for symbol in stock_symbols:
                stock = await stock_crud.get_by_symbol(db_session, symbol)
                if stock:
                    stock_ids.append(stock.id)
                    print(f"找到股票: {symbol} (ID: {stock.id})")
                else:
                    print(f"警告: 找不到股票 {symbol}")
            
            if not stock_ids:
                print("錯誤: 沒有找到任何有效的股票")
                return
            
            # 轉換信號類型
            signal_type_objects = None
            if signal_types:
                try:
                    signal_type_objects = [SignalType(st) for st in signal_types]
                except ValueError as e:
                    print(f"錯誤: 無效的信號類型 - {e}")
                    return
            
            # 批次偵測信號
            results = await trading_signal_detector.batch_detect_signals(
                db_session,
                stock_ids=stock_ids,
                signal_types=signal_type_objects,
                days=days,
                save_to_db=save_to_db
            )
            
            # 顯示結果
            successful = sum(1 for r in results if r.success)
            total_signals = sum(r.signals_detected for r in results)
            
            print(f"\n偵測完成:")
            print(f"  成功: {successful}/{len(results)} 支股票")
            print(f"  總信號數: {total_signals} 個")
            
            # 按股票顯示結果
            for result in results:
                if result.success and result.signals_detected > 0:
                    print(f"\n  {result.stock_symbol}:")
                    print(f"    偵測到 {result.signals_detected} 個信號")
                    
                    # 顯示高信心度信號
                    high_confidence_signals = [
                        s for s in result.signals 
                        if s.confidence >= min_confidence
                    ]
                    
                    if high_confidence_signals:
                        print(f"    高信心度信號 (≥{min_confidence}):")
                        for signal in high_confidence_signals[:5]:  # 只顯示前5個
                            print(f"      {signal.signal_type.value}: {signal.confidence:.2f} ({signal.date})")
                            print(f"        {signal.description}")
                
                elif not result.success:
                    print(f"\n  {result.stock_symbol}: 偵測失敗")
                    for error in result.errors[:2]:
                        print(f"    錯誤: {error}")
    
    except Exception as e:
        print(f"偵測信號時發生錯誤: {str(e)}")


async def list_signals_command(
    stock_symbols: List[str] = None,
    signal_types: List[str] = None,
    days: int = 7,
    min_confidence: float = 0.0,
    limit: int = 20
):
    """列出交易信號命令"""
    print("查詢交易信號...")
    
    try:
        async with get_db() as db_session:
            if stock_symbols:
                # 查詢指定股票的信號
                for symbol in stock_symbols:
                    stock = await stock_crud.get_by_symbol(db_session, symbol)
                    if not stock:
                        print(f"找不到股票: {symbol}")
                        continue
                    
                    print(f"\n{symbol} 的交易信號:")
                    
                    end_date = date.today()
                    start_date = end_date - timedelta(days=days)
                    
                    signals = await trading_signal_crud.get_stock_signals_by_date_range(
                        db_session,
                        stock_id=stock.id,
                        start_date=start_date,
                        end_date=end_date,
                        signal_types=signal_types,
                        min_confidence=min_confidence
                    )
                    
                    if signals:
                        for signal in signals[:limit]:
                            print(f"  {signal.date} | {signal.signal_type} | 信心度: {signal.confidence:.2f}")
                            print(f"    價格: {signal.price} | {signal.description}")
                    else:
                        print("  沒有找到符合條件的信號")
            
            else:
                # 查詢所有高信心度信號
                print(f"最近 {days} 天的高信心度信號 (≥{min_confidence}):")
                
                high_confidence_signals = await trading_signal_crud.get_high_confidence_signals(
                    db_session,
                    min_confidence=min_confidence,
                    days=days,
                    limit=limit
                )
                
                if high_confidence_signals:
                    # 按股票分組
                    signals_by_stock = {}
                    for signal in high_confidence_signals:
                        stock_id = signal.stock_id
                        if stock_id not in signals_by_stock:
                            signals_by_stock[stock_id] = []
                        signals_by_stock[stock_id].append(signal)
                    
                    for stock_id, stock_signals in signals_by_stock.items():
                        stock = await stock_crud.get(db_session, stock_id)
                        stock_symbol = stock.symbol if stock else f"ID:{stock_id}"
                        
                        print(f"\n{stock_symbol}:")
                        for signal in stock_signals:
                            print(f"  {signal.date} | {signal.signal_type} | {signal.confidence:.2f}")
                            print(f"    {signal.description}")
                else:
                    print("沒有找到符合條件的信號")
    
    except Exception as e:
        print(f"查詢信號時發生錯誤: {str(e)}")


async def signal_statistics_command(
    stock_symbols: List[str] = None,
    days: int = 30
):
    """信號統計命令"""
    print(f"統計最近 {days} 天的交易信號...")
    
    try:
        async with get_db() as db_session:
            if stock_symbols:
                # 統計指定股票的信號
                for symbol in stock_symbols:
                    stock = await stock_crud.get_by_symbol(db_session, symbol)
                    if not stock:
                        print(f"找不到股票: {symbol}")
                        continue
                    
                    print(f"\n{symbol} 信號統計:")
                    
                    # 基本統計
                    stats = await trading_signal_crud.get_signal_statistics(
                        db_session,
                        stock_id=stock.id,
                        days=days
                    )
                    
                    print(f"  總信號數: {stats['total_signals']}")
                    print(f"  平均信心度: {stats['avg_confidence']:.3f}")
                    print(f"  最高信心度: {stats['max_confidence']:.3f}")
                    print(f"  信號類型數: {stats['signal_types_count']}")
                    
                    # 信號類型分布
                    distribution = await trading_signal_crud.get_signal_type_distribution(
                        db_session,
                        stock_id=stock.id,
                        days=days
                    )
                    
                    if distribution:
                        print("  信號類型分布:")
                        for signal_type, count in sorted(distribution.items(), key=lambda x: x[1], reverse=True):
                            print(f"    {signal_type}: {count} 個")
            
            else:
                # 全市場信號統計
                print("全市場信號統計:")
                
                # 基本統計
                stats = await trading_signal_crud.get_signal_statistics(
                    db_session,
                    days=days
                )
                
                print(f"  總信號數: {stats['total_signals']}")
                print(f"  平均信心度: {stats['avg_confidence']:.3f}")
                print(f"  最高信心度: {stats['max_confidence']:.3f}")
                print(f"  信號類型數: {stats['signal_types_count']}")
                
                # 信號類型分布
                distribution = await trading_signal_crud.get_signal_type_distribution(
                    db_session,
                    days=days
                )
                
                if distribution:
                    print("\n信號類型分布:")
                    for signal_type, count in sorted(distribution.items(), key=lambda x: x[1], reverse=True):
                        print(f"  {signal_type}: {count} 個")
    
    except Exception as e:
        print(f"統計信號時發生錯誤: {str(e)}")


async def signal_analysis_command(
    stock_symbol: str,
    signal_type: str,
    days: int = 90
):
    """信號分析命令"""
    print(f"分析 {stock_symbol} 的 {signal_type} 信號...")
    
    try:
        async with get_db() as db_session:
            stock = await stock_crud.get_by_symbol(db_session, stock_symbol)
            if not stock:
                print(f"找不到股票: {stock_symbol}")
                return
            
            # 信號表現分析
            performance = await trading_signal_crud.get_signal_performance_analysis(
                db_session,
                stock_id=stock.id,
                signal_type=signal_type,
                days=days
            )
            
            print(f"\n{signal_type} 信號分析結果:")
            print(f"  分析期間: {days} 天")
            print(f"  總信號數: {performance['total_signals']}")
            
            if performance['total_signals'] > 0:
                print(f"  平均信心度: {performance['avg_confidence']:.3f}")
                print(f"  最新信號: {performance.get('latest_signal_date', '無')}")
                print(f"  最早信號: {performance.get('earliest_signal_date', '無')}")
                
                # 信心度分布
                confidence_dist = performance.get('confidence_distribution', {})
                if confidence_dist:
                    print("  信心度分布:")
                    print(f"    很高 (≥0.9): {confidence_dist.get('very_high', 0)} 個")
                    print(f"    高 (0.8-0.9): {confidence_dist.get('high', 0)} 個")
                    print(f"    中 (0.6-0.8): {confidence_dist.get('medium', 0)} 個")
                    print(f"    低 (<0.6): {confidence_dist.get('low', 0)} 個")
                
                # 月度分布
                monthly_dist = performance.get('monthly_distribution', {})
                if monthly_dist:
                    print("  月度分布:")
                    for month, count in sorted(monthly_dist.items()):
                        print(f"    {month}: {count} 個")
            else:
                print("  沒有找到該類型的信號")
    
    except Exception as e:
        print(f"分析信號時發生錯誤: {str(e)}")


async def cleanup_signals_command(
    keep_days: int = 365,
    stock_symbols: List[str] = None
):
    """清理舊信號命令"""
    print(f"清理 {keep_days} 天前的交易信號...")
    
    try:
        async with get_db() as db_session:
            if stock_symbols:
                total_deleted = 0
                for symbol in stock_symbols:
                    stock = await stock_crud.get_by_symbol(db_session, symbol)
                    if stock:
                        deleted = await trading_signal_crud.delete_old_signals(
                            db_session,
                            stock_id=stock.id,
                            keep_days=keep_days
                        )
                        total_deleted += deleted
                        print(f"  {symbol}: 刪除 {deleted} 個舊信號")
                    else:
                        print(f"  找不到股票: {symbol}")
                
                print(f"\n總共刪除 {total_deleted} 個舊信號")
            
            else:
                # 清理所有股票的舊信號
                deleted = await trading_signal_crud.delete_old_signals(
                    db_session,
                    keep_days=keep_days
                )
                print(f"刪除 {deleted} 個舊信號")
    
    except Exception as e:
        print(f"清理信號時發生錯誤: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description="交易信號管理工具")
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 偵測信號命令
    detect_parser = subparsers.add_parser('detect', help='偵測交易信號')
    detect_parser.add_argument('symbols', nargs='+', help='股票代號列表')
    detect_parser.add_argument('--signal-types', nargs='*', help='信號類型列表')
    detect_parser.add_argument('--days', type=int, default=30, help='偵測天數')
    detect_parser.add_argument('--min-confidence', type=float, default=0.6, help='最小信心度')
    detect_parser.add_argument('--no-save', action='store_true', help='不保存到資料庫')
    
    # 列出信號命令
    list_parser = subparsers.add_parser('list', help='列出交易信號')
    list_parser.add_argument('--symbols', nargs='*', help='股票代號列表')
    list_parser.add_argument('--signal-types', nargs='*', help='信號類型列表')
    list_parser.add_argument('--days', type=int, default=7, help='查詢天數')
    list_parser.add_argument('--min-confidence', type=float, default=0.0, help='最小信心度')
    list_parser.add_argument('--limit', type=int, default=20, help='最大顯示數量')
    
    # 統計命令
    stats_parser = subparsers.add_parser('stats', help='信號統計')
    stats_parser.add_argument('--symbols', nargs='*', help='股票代號列表')
    stats_parser.add_argument('--days', type=int, default=30, help='統計天數')
    
    # 分析命令
    analyze_parser = subparsers.add_parser('analyze', help='信號分析')
    analyze_parser.add_argument('symbol', help='股票代號')
    analyze_parser.add_argument('signal_type', help='信號類型')
    analyze_parser.add_argument('--days', type=int, default=90, help='分析天數')
    
    # 清理命令
    cleanup_parser = subparsers.add_parser('cleanup', help='清理舊信號')
    cleanup_parser.add_argument('--keep-days', type=int, default=365, help='保留天數')
    cleanup_parser.add_argument('--symbols', nargs='*', help='股票代號列表')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 執行對應命令
    if args.command == 'detect':
        asyncio.run(detect_signals_command(
            stock_symbols=args.symbols,
            signal_types=args.signal_types,
            days=args.days,
            min_confidence=args.min_confidence,
            save_to_db=not args.no_save
        ))
    
    elif args.command == 'list':
        asyncio.run(list_signals_command(
            stock_symbols=args.symbols,
            signal_types=args.signal_types,
            days=args.days,
            min_confidence=args.min_confidence,
            limit=args.limit
        ))
    
    elif args.command == 'stats':
        asyncio.run(signal_statistics_command(
            stock_symbols=args.symbols,
            days=args.days
        ))
    
    elif args.command == 'analyze':
        asyncio.run(signal_analysis_command(
            stock_symbol=args.symbol,
            signal_type=args.signal_type,
            days=args.days
        ))
    
    elif args.command == 'cleanup':
        asyncio.run(cleanup_signals_command(
            keep_days=args.keep_days,
            stock_symbols=args.symbols
        ))


if __name__ == "__main__":
    main()