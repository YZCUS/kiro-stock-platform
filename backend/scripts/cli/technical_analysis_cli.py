#!/usr/bin/env python3
"""
技術分析命令行工具
"""
import asyncio
import sys
import argparse
from pathlib import Path
from datetime import date, datetime, timedelta
import logging
import json

# 將專案根目錄加入 Python 路徑
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.settings import settings
from services.analysis.technical_analysis import technical_analysis_service, IndicatorType
from services.analysis.indicator_calculator import advanced_calculator
# ✅ Clean Architecture: 使用 repository implementations 而非 CRUD
from infrastructure.persistence.stock_repository import StockRepository
from infrastructure.persistence.price_history_repository import PriceHistoryRepository
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TechnicalAnalysisCLI:
    """技術分析命令行介面"""

    def __init__(self):
        self.engine = create_async_engine(
            settings.database.url.replace("postgresql://", "postgresql+asyncpg://"),
            echo=False
        )
        self.async_session_local = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        # Note: repositories 會在每個 async with session 中實例化
    
    async def close(self):
        """關閉資料庫連接"""
        await self.engine.dispose()
    
    async def list_stocks(self, market: str = None, limit: int = 20):
        """列出股票"""
        async with self.async_session_local() as session:
            # ✅ Clean Architecture: 實例化 repository
            stock_repo = StockRepository(session)

            if market:
                stocks, _ = await stock_repo.get_multi_with_filter(session, market=market, limit=limit)
            else:
                stocks, _ = await stock_repo.get_multi_with_filter(session, limit=limit)
            
            print(f"\n找到 {len(stocks)} 支股票:")
            print(f"{'ID':<5} {'代號':<12} {'市場':<6} {'名稱':<20}")
            print("-" * 50)
            
            for stock in stocks:
                print(f"{stock.id:<5} {stock.symbol:<12} {stock.market:<6} {stock.name or 'N/A':<20}")
    
    async def calculate_indicators(
        self,
        stock_id: int,
        indicators: str = "all",
        days: int = 100,
        save: bool = True
    ):
        """計算技術指標"""
        async with self.async_session_local() as session:
            # ✅ Clean Architecture: 實例化 repository
            stock_repo = StockRepository(session)

            # 驗證股票存在
            stock = await stock_repo.get(session, stock_id)
            if not stock:
                print(f"找不到股票 ID: {stock_id}")
                return
            
            # 解析指標列表
            if indicators == "all":
                indicator_list = None
            else:
                indicator_names = [name.strip().upper() for name in indicators.split(',')]
                indicator_list = []
                for name in indicator_names:
                    try:
                        indicator_list.append(IndicatorType(name))
                    except ValueError:
                        print(f"警告: 不支援的指標類型 '{name}'")
            
            print(f"\n開始計算股票 {stock.symbol} ({stock.market}) 的技術指標")
            print(f"計算天數: {days}")
            print(f"保存到資料庫: {'是' if save else '否'}")
            
            try:
                result = await technical_analysis_service.calculate_stock_indicators(
                    session,
                    stock_id=stock_id,
                    indicators=indicator_list,
                    days=days,
                    save_to_db=save
                )
                
                print(f"\n計算結果:")
                print(f"總指標數: {result.indicators_calculated}")
                print(f"成功計算: {result.indicators_successful}")
                print(f"計算失敗: {result.indicators_failed}")
                print(f"執行時間: {result.execution_time_seconds:.2f} 秒")
                
                if result.errors:
                    print(f"\n錯誤:")
                    for error in result.errors:
                        print(f"  - {error}")
                
                if result.warnings:
                    print(f"\n警告:")
                    for warning in result.warnings:
                        print(f"  - {warning}")
                
            except Exception as e:
                print(f"計算失敗: {str(e)}")
    
    async def batch_calculate(
        self,
        market: str = None,
        indicators: str = "RSI,SMA_20,EMA_12",
        days: int = 60,
        max_stocks: int = 10,
        concurrent: int = 3
    ):
        """批次計算指標"""
        async with self.async_session_local() as session:
            # ✅ Clean Architecture: 實例化 repository
            stock_repo = StockRepository(session)

            # 獲取股票列表
            if market:
                stocks, _ = await stock_repo.get_multi_with_filter(session, market=market, limit=max_stocks)
            else:
                stocks, _ = await stock_repo.get_multi_with_filter(session, limit=max_stocks)
            
            if not stocks:
                print("沒有找到股票")
                return
            
            # 解析指標列表
            indicator_names = [name.strip().upper() for name in indicators.split(',')]
            indicator_list = []
            for name in indicator_names:
                try:
                    indicator_list.append(IndicatorType(name))
                except ValueError:
                    print(f"警告: 不支援的指標類型 '{name}'")
            
            print(f"\n開始批次計算 {len(stocks)} 支股票的技術指標")
            print(f"指標: {[ind.value for ind in indicator_list]}")
            print(f"計算天數: {days}")
            print(f"並行數: {concurrent}")
            
            try:
                results = await technical_analysis_service.batch_calculate_indicators(
                    session,
                    stock_ids=[stock.id for stock in stocks],
                    indicators=indicator_list,
                    days=days,
                    max_concurrent=concurrent
                )
                
                # 統計結果
                successful = sum(1 for r in results if r.indicators_successful > 0)
                total_indicators = sum(r.indicators_successful for r in results)
                total_time = sum(r.execution_time_seconds for r in results)
                
                print(f"\n批次計算完成:")
                print(f"成功股票數: {successful}/{len(results)}")
                print(f"總指標數: {total_indicators}")
                print(f"總執行時間: {total_time:.2f} 秒")
                print(f"平均每股時間: {total_time/len(results):.2f} 秒")
                
                # 詳細結果
                print(f"\n詳細結果:")
                print(f"{'股票代號':<12} {'成功指標':<8} {'失敗指標':<8} {'執行時間':<10}")
                print("-" * 45)
                
                for i, result in enumerate(results):
                    stock_symbol = stocks[i].symbol
                    print(f"{stock_symbol:<12} {result.indicators_successful:<8} {result.indicators_failed:<8} {result.execution_time_seconds:<10.2f}")
                
            except Exception as e:
                print(f"批次計算失敗: {str(e)}")
    
    async def show_indicators(self, stock_id: int, indicator_types: str = None, days: int = 30):
        """顯示指標數據"""
        async with self.async_session_local() as session:
            # ✅ Clean Architecture: 實例化 repository
            stock_repo = StockRepository(session)

            # 驗證股票存在
            stock = await stock_repo.get(session, stock_id)
            if not stock:
                print(f"找不到股票 ID: {stock_id}")
                return
            
            # 解析指標類型
            if indicator_types:
                types_list = [t.strip() for t in indicator_types.split(',')]
            else:
                types_list = None
            
            print(f"\n股票 {stock.symbol} ({stock.market}) 的技術指標數據")
            print(f"查詢期間: 最近 {days} 天")
            
            try:
                indicators_data = await technical_analysis_service.get_stock_indicators(
                    session,
                    stock_id=stock_id,
                    indicator_types=types_list,
                    days=days
                )
                
                if not indicators_data:
                    print("沒有找到指標數據")
                    return
                
                for indicator_type, data in indicators_data.items():
                    print(f"\n{indicator_type}:")
                    print(f"  數據點數: {len(data)}")
                    
                    if data:
                        # 顯示最新的5個數據點
                        print(f"  最新數據:")
                        for i, point in enumerate(data[:5]):
                            print(f"    {point['date']}: {point['value']:.4f}")
                        
                        if len(data) > 5:
                            print(f"    ... (還有 {len(data) - 5} 個數據點)")
                
            except Exception as e:
                print(f"查詢指標數據失敗: {str(e)}")
    
    async def analyze_advanced(self, stock_id: int, days: int = 100):
        """進階技術分析"""
        async with self.async_session_local() as session:
            # ✅ Clean Architecture: 實例化 repositories
            stock_repo = StockRepository(session)
            price_repo = PriceHistoryRepository(session)

            # 驗證股票存在
            stock = await stock_repo.get(session, stock_id)
            if not stock:
                print(f"找不到股票 ID: {stock_id}")
                return

            print(f"\n進階技術分析: {stock.symbol} ({stock.market})")
            print(f"分析期間: 最近 {days} 天")

            try:
                # 獲取價格數據
                end_date = date.today()
                start_date = end_date - timedelta(days=days)

                price_data = await price_repo.get_stock_price_range(
                    session,
                    stock_id=stock_id,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if len(price_data) < 30:
                    print("價格數據不足，需要至少30天數據")
                    return
                
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
                
                # MACD 分析
                print(f"\n=== MACD 分析 ===")
                macd_components = advanced_calculator.calculate_complete_macd(df)
                if macd_components.macd_line:
                    latest_macd = macd_components.macd_line[-1]
                    latest_signal = macd_components.signal_line[-1]
                    latest_histogram = macd_components.histogram[-1]
                    
                    print(f"最新 MACD: {latest_macd:.4f}")
                    print(f"最新信號線: {latest_signal:.4f}")
                    print(f"最新柱狀圖: {latest_histogram:.4f}")
                    
                    if latest_macd > latest_signal:
                        print("MACD 信號: 看漲 (MACD 線在信號線上方)")
                    else:
                        print("MACD 信號: 看跌 (MACD 線在信號線下方)")
                
                # 布林通道分析
                print(f"\n=== 布林通道分析 ===")
                bb_components = advanced_calculator.calculate_complete_bollinger_bands(df)
                if bb_components.upper_band:
                    latest_price = df['close'].iloc[-1]
                    latest_upper = bb_components.upper_band[-1]
                    latest_middle = bb_components.middle_band[-1]
                    latest_lower = bb_components.lower_band[-1]
                    
                    print(f"當前價格: {latest_price:.2f}")
                    print(f"上軌: {latest_upper:.2f}")
                    print(f"中軌: {latest_middle:.2f}")
                    print(f"下軌: {latest_lower:.2f}")
                    
                    if latest_price > latest_upper:
                        print("布林通道信號: 可能超買")
                    elif latest_price < latest_lower:
                        print("布林通道信號: 可能超賣")
                    else:
                        print("布林通道信號: 價格在正常範圍內")
                
                # KD 指標分析
                print(f"\n=== KD 指標分析 ===")
                kd_components = advanced_calculator.calculate_complete_stochastic(df)
                if kd_components.k_values:
                    latest_k = kd_components.k_values[-1]
                    latest_d = kd_components.d_values[-1]
                    
                    print(f"最新 %K: {latest_k:.2f}")
                    print(f"最新 %D: {latest_d:.2f}")
                    
                    if latest_k > 80 and latest_d > 80:
                        print("KD 信號: 超買區域")
                    elif latest_k < 20 and latest_d < 20:
                        print("KD 信號: 超賣區域")
                    else:
                        print("KD 信號: 正常區域")
                    
                    if latest_k > latest_d:
                        print("KD 交叉: K 線在 D 線上方 (看漲)")
                    else:
                        print("KD 交叉: K 線在 D 線下方 (看跌)")
                
                # 型態識別
                print(f"\n=== 型態識別 ===")
                pattern_signals = advanced_calculator.detect_pattern_signals(df)
                
                total_patterns = (
                    len(pattern_signals['bullish_patterns']) +
                    len(pattern_signals['bearish_patterns']) +
                    len(pattern_signals['reversal_patterns'])
                )
                
                print(f"最近發現的型態:")
                print(f"  看漲型態: {len(pattern_signals['bullish_patterns'])} 個")
                print(f"  看跌型態: {len(pattern_signals['bearish_patterns'])} 個")
                print(f"  反轉型態: {len(pattern_signals['reversal_patterns'])} 個")
                
                # 顯示最近的型態
                recent_patterns = []
                recent_patterns.extend(pattern_signals['bullish_patterns'][-3:])
                recent_patterns.extend(pattern_signals['bearish_patterns'][-3:])
                
                if recent_patterns:
                    print(f"\n最近的型態:")
                    for pattern in sorted(recent_patterns, key=lambda x: x['date'], reverse=True)[:5]:
                        print(f"  {pattern['date']}: {pattern['pattern']} (強度: {pattern['strength']})")
                
                # 支撐阻力位
                print(f"\n=== 支撐阻力位 ===")
                sr_levels = advanced_calculator.calculate_support_resistance_levels(df)
                
                if sr_levels['support_levels']:
                    print(f"支撐位: {[f'{level:.2f}' for level in sr_levels['support_levels'][-3:]]}")
                
                if sr_levels['resistance_levels']:
                    print(f"阻力位: {[f'{level:.2f}' for level in sr_levels['resistance_levels'][-3:]]}")
                
            except Exception as e:
                print(f"進階分析失敗: {str(e)}")
    
    async def export_indicators(self, stock_id: int, output_file: str, days: int = 90):
        """匯出指標數據"""
        async with self.async_session_local() as session:
            # ✅ Clean Architecture: 實例化 repository
            stock_repo = StockRepository(session)

            # 驗證股票存在
            stock = await stock_repo.get(session, stock_id)
            if not stock:
                print(f"找不到股票 ID: {stock_id}")
                return
            
            print(f"\n匯出股票 {stock.symbol} ({stock.market}) 的指標數據")
            print(f"匯出期間: 最近 {days} 天")
            print(f"輸出檔案: {output_file}")
            
            try:
                indicators_data = await technical_analysis_service.get_stock_indicators(
                    session,
                    stock_id=stock_id,
                    days=days
                )
                
                if not indicators_data:
                    print("沒有找到指標數據")
                    return
                
                # 準備匯出數據
                export_data = {
                    'stock_info': {
                        'id': stock.id,
                        'symbol': stock.symbol,
                        'market': stock.market,
                        'name': stock.name
                    },
                    'export_date': datetime.now().isoformat(),
                    'period_days': days,
                    'indicators': indicators_data
                }
                
                # 寫入檔案
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
                
                print(f"成功匯出 {len(indicators_data)} 種指標數據到 {output_file}")
                
            except Exception as e:
                print(f"匯出失敗: {str(e)}")


async def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='技術分析命令行工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 列出股票
    list_parser = subparsers.add_parser('list', help='列出股票')
    list_parser.add_argument('--market', choices=['TW', 'US'], help='市場篩選')
    list_parser.add_argument('--limit', type=int, default=20, help='顯示數量限制')
    
    # 計算指標
    calc_parser = subparsers.add_parser('calc', help='計算技術指標')
    calc_parser.add_argument('stock_id', type=int, help='股票ID')
    calc_parser.add_argument('--indicators', default='all', help='指標列表 (逗號分隔) 或 "all"')
    calc_parser.add_argument('--days', type=int, default=100, help='計算天數')
    calc_parser.add_argument('--no-save', action='store_true', help='不保存到資料庫')
    
    # 批次計算
    batch_parser = subparsers.add_parser('batch', help='批次計算指標')
    batch_parser.add_argument('--market', choices=['TW', 'US'], help='市場篩選')
    batch_parser.add_argument('--indicators', default='RSI,SMA_20,EMA_12', help='指標列表')
    batch_parser.add_argument('--days', type=int, default=60, help='計算天數')
    batch_parser.add_argument('--max-stocks', type=int, default=10, help='最大股票數')
    batch_parser.add_argument('--concurrent', type=int, default=3, help='並行數')
    
    # 顯示指標
    show_parser = subparsers.add_parser('show', help='顯示指標數據')
    show_parser.add_argument('stock_id', type=int, help='股票ID')
    show_parser.add_argument('--indicators', help='指標類型 (逗號分隔)')
    show_parser.add_argument('--days', type=int, default=30, help='查詢天數')
    
    # 進階分析
    analyze_parser = subparsers.add_parser('analyze', help='進階技術分析')
    analyze_parser.add_argument('stock_id', type=int, help='股票ID')
    analyze_parser.add_argument('--days', type=int, default=100, help='分析天數')
    
    # 匯出數據
    export_parser = subparsers.add_parser('export', help='匯出指標數據')
    export_parser.add_argument('stock_id', type=int, help='股票ID')
    export_parser.add_argument('output_file', help='輸出檔案路徑')
    export_parser.add_argument('--days', type=int, default=90, help='匯出天數')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cli = TechnicalAnalysisCLI()
    
    try:
        if args.command == 'list':
            await cli.list_stocks(args.market, args.limit)
        
        elif args.command == 'calc':
            await cli.calculate_indicators(
                args.stock_id, args.indicators, args.days, not args.no_save
            )
        
        elif args.command == 'batch':
            await cli.batch_calculate(
                args.market, args.indicators, args.days, 
                args.max_stocks, args.concurrent
            )
        
        elif args.command == 'show':
            await cli.show_indicators(args.stock_id, args.indicators, args.days)
        
        elif args.command == 'analyze':
            await cli.analyze_advanced(args.stock_id, args.days)
        
        elif args.command == 'export':
            await cli.export_indicators(args.stock_id, args.output_file, args.days)
        
    except KeyboardInterrupt:
        print("\n操作已取消")
    except Exception as e:
        logger.error(f"執行命令時發生錯誤: {str(e)}")
    finally:
        await cli.close()


if __name__ == "__main__":
    asyncio.run(main())