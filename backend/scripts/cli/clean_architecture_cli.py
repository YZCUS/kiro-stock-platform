#!/usr/bin/env python3
"""
Clean Architecture CLI - 使用Domain Services的命令行工具
重構後的CLI，使用dependency injection和domain services
"""
import asyncio
import sys
import argparse
from pathlib import Path
from datetime import date, datetime, timedelta
import logging
import json
from typing import Optional, List

# 將專案根目錄加入 Python 路徑
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession

# Domain Services
from domain.services.stock_service import StockService
from domain.services.technical_analysis_service import TechnicalAnalysisService
from domain.services.trading_signal_service import TradingSignalService
from domain.services.data_collection_service import DataCollectionService

# Infrastructure
from infrastructure.persistence.stock_repository import StockRepository
from infrastructure.persistence.daily_price_repository import DailyPriceRepository
from infrastructure.cache.unified_cache_service import MockCacheService

# Core
from core.database import get_db_session

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CleanArchitectureCLI:
    """Clean Architecture命令行介面"""

    def __init__(self):
        # 初始化服務依賴
        self.cache_service = MockCacheService()

    async def _get_services(self, db: AsyncSession):
        """建立服務實例"""
        # Repository實例
        stock_repo = StockRepository(db)
        price_repo = DailyPriceRepository(db)

        # Domain Services
        stock_service = StockService(stock_repo, price_repo, self.cache_service)
        technical_service = TechnicalAnalysisService(
            stock_repo, price_repo, self.cache_service
        )
        signal_service = TradingSignalService(
            stock_repo, price_repo, self.cache_service
        )
        collection_service = DataCollectionService(
            stock_repo, price_repo, self.cache_service
        )

        return {
            "stock": stock_service,
            "technical": technical_service,
            "signal": signal_service,
            "collection": collection_service,
        }

    async def list_stocks(self, market: Optional[str] = None, limit: int = 20):
        """列出股票"""
        async for session in get_db_session():
            try:
                services = await self._get_services(session)

                # 使用Stock Service
                result = await services["stock"].get_stock_list(
                    db=session, market=market, is_active=True, page=1, per_page=limit
                )

                print(
                    f"\n📊 股票清單 {'(' + market + ' 市場)' if market else '(所有市場)'}"
                )
                print("=" * 60)

                for stock in result["items"]:
                    print(f"• {stock.symbol:8} | {stock.name:20} | {stock.market}")

                print(f"\n總計: {result['total']} 支股票")

            except Exception as e:
                logger.error(f"列出股票失敗: {e}")

    async def analyze_stock(self, symbol: str, days: int = 60):
        """分析單支股票"""
        async for session in get_db_session():
            try:
                services = await self._get_services(session)

                # 取得股票
                stock = await services["stock"].get_stock_by_symbol(session, symbol)

                print(f"\n🔍 分析股票: {stock.symbol} - {stock.name}")
                print("=" * 60)

                # 技術分析
                analysis = await services["technical"].calculate_stock_indicators(
                    db=session, stock_id=stock.id, analysis_days=days
                )

                print(f"📈 技術分析結果:")
                print(f"  計算指標數: {analysis.indicators_calculated}")
                print(f"  成功指標數: {analysis.indicators_successful}")
                print(f"  執行時間: {analysis.execution_time_seconds:.2f}秒")

                if analysis.errors:
                    print(f"  ⚠️  錯誤: {', '.join(analysis.errors)}")

                # 技術摘要
                summary = await services["technical"].get_stock_technical_summary(
                    db=session, stock_id=stock.id
                )

                print(f"\n📊 技術面摘要:")
                print(f"  當前價格: ${summary['current_price']:.2f}")
                print(f"  趨勢分析: {summary['trend_analysis']}")
                print(f"  技術信號: {', '.join(summary['technical_signals'])}")
                print(f"  支撐位: ${summary['support_resistance']['support']:.2f}")
                print(f"  阻力位: ${summary['support_resistance']['resistance']:.2f}")

            except Exception as e:
                logger.error(f"分析股票失敗: {e}")

    async def generate_signals(self, symbol: str, days: int = 60):
        """生成交易信號"""
        async for session in get_db_session():
            try:
                services = await self._get_services(session)

                # 取得股票
                stock = await services["stock"].get_stock_by_symbol(session, symbol)

                print(f"\n📡 生成交易信號: {stock.symbol} - {stock.name}")
                print("=" * 60)

                # 生成信號
                analysis = await services["signal"].generate_trading_signals(
                    db=session, stock_id=stock.id, analysis_days=days
                )

                print(f"🎯 信號分析結果:")
                print(f"  生成信號數: {analysis.signals_generated}")
                print(f"  風險分數: {analysis.risk_score:.2f}")
                print(f"  投資建議: {analysis.recommendation}")

                if analysis.primary_signal:
                    signal = analysis.primary_signal
                    print(f"\n🚀 主要信號:")
                    print(f"  信號類型: {signal.signal_type.value}")
                    print(f"  信號強度: {signal.signal_strength.value}")
                    print(f"  信號來源: {signal.signal_source.value}")
                    print(f"  信心度: {signal.confidence:.2%}")
                    if signal.target_price:
                        print(f"  目標價: ${signal.target_price:.2f}")
                    if signal.stop_loss:
                        print(f"  止損價: ${signal.stop_loss:.2f}")
                    print(f"  說明: {signal.description}")

                if analysis.supporting_signals:
                    print(f"\n🔄 支持信號:")
                    for i, signal in enumerate(analysis.supporting_signals, 1):
                        print(
                            f"  {i}. {signal.signal_type.value} ({signal.confidence:.1%}) - {signal.description}"
                        )

                print(f"\n💡 投資理由:")
                for reason in analysis.reasoning:
                    print(f"  • {reason}")

            except Exception as e:
                logger.error(f"生成交易信號失敗: {e}")

    async def scan_market(
        self, market: Optional[str] = None, min_confidence: float = 0.8
    ):
        """掃描市場信號"""
        async for session in get_db_session():
            try:
                services = await self._get_services(session)

                print(
                    f"\n🌐 掃描市場信號 {'(' + market + ' 市場)' if market else '(所有市場)'}"
                )
                print("=" * 60)

                # 掃描市場
                portfolio_signals = await services["signal"].scan_market_signals(
                    db=session, market=market, min_confidence=min_confidence
                )

                print(f"📊 市場概況:")
                print(f"  分析股票數: {portfolio_signals.total_stocks_analyzed}")
                print(f"  買入信號: {portfolio_signals.buy_signals}")
                print(f"  賣出信號: {portfolio_signals.sell_signals}")
                print(f"  持有信號: {portfolio_signals.hold_signals}")
                print(f"  市場情緒: {portfolio_signals.market_sentiment}")

                if portfolio_signals.high_confidence_signals:
                    print(f"\n⭐ 高信心信號 (>={min_confidence:.0%}):")
                    for signal in portfolio_signals.high_confidence_signals:
                        print(
                            f"  • {signal.symbol:8} | {signal.signal_type.value:10} | {signal.confidence:.1%} | {signal.description}"
                        )

                if portfolio_signals.risk_alerts:
                    print(f"\n⚠️  風險警告:")
                    for alert in portfolio_signals.risk_alerts:
                        print(f"  • {alert}")

            except Exception as e:
                logger.error(f"掃描市場失敗: {e}")

    async def collect_data(self, symbol: str, days: int = 30):
        """收集股票數據"""
        async for session in get_db_session():
            try:
                services = await self._get_services(session)

                # 取得股票
                stock = await services["stock"].get_stock_by_symbol(session, symbol)

                print(f"\n📥 收集數據: {stock.symbol} - {stock.name}")
                print("=" * 60)

                # 收集數據
                end_date = date.today()
                start_date = end_date - timedelta(days=days)

                result = await services["collection"].collect_stock_data(
                    db=session,
                    stock_id=stock.id,
                    start_date=start_date,
                    end_date=end_date,
                )

                print(f"📦 收集結果:")
                print(f"  狀態: {result.status.value}")
                print(f"  收集筆數: {result.records_collected}")
                print(f"  期間: {result.start_date} 到 {result.end_date}")
                print(f"  執行時間: {result.execution_time_seconds:.2f}秒")

                if result.errors:
                    print(f"  ❌ 錯誤: {', '.join(result.errors)}")

                if result.warnings:
                    print(f"  ⚠️  警告: {', '.join(result.warnings)}")

            except Exception as e:
                logger.error(f"收集數據失敗: {e}")

    async def health_check(self):
        """系統健康檢查"""
        async for session in get_db_session():
            try:
                services = await self._get_services(session)

                print(f"\n🏥 系統健康檢查")
                print("=" * 60)

                # 收集系統健康狀態
                health = await services["collection"].get_collection_health_status(
                    session
                )

                print(f"📊 系統狀態:")
                print(f"  整體狀態: {health['status']}")
                print(f"  節流等級: {health['throttle_level']}")
                print(f"  API可用性: {health['api_availability']:.1%}")
                print(
                    f"  數據新鮮度: {health['data_freshness']['coverage_percentage']:.1f}%"
                )
                print(
                    f"  收集速率: {health['collection_rate']['stocks_per_minute']:.1f} 股票/分鐘"
                )
                print(f"  成功率: {health['collection_rate']['success_rate']:.1%}")

                # 快取統計
                cache_stats = (
                    self.cache_service.get_statistics()
                    if hasattr(self.cache_service, "get_statistics")
                    else {}
                )
                if cache_stats:
                    print(f"\n💾 快取統計:")
                    print(f"  命中次數: {cache_stats.get('hit_count', 0)}")
                    print(f"  未命中次數: {cache_stats.get('miss_count', 0)}")
                    print(f"  命中率: {cache_stats.get('hit_rate', 0):.1%}")

            except Exception as e:
                logger.error(f"健康檢查失敗: {e}")


async def main():
    """主函數"""
    parser = argparse.ArgumentParser(
        description="Clean Architecture CLI - 股票分析工具"
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # 列出股票
    list_parser = subparsers.add_parser("list", help="列出股票")
    list_parser.add_argument("--market", choices=["TW", "US"], help="市場代碼")
    list_parser.add_argument("--limit", type=int, default=20, help="顯示數量")

    # 分析股票
    analyze_parser = subparsers.add_parser("analyze", help="分析股票")
    analyze_parser.add_argument("symbol", help="股票代號")
    analyze_parser.add_argument("--days", type=int, default=60, help="分析天數")

    # 生成信號
    signal_parser = subparsers.add_parser("signal", help="生成交易信號")
    signal_parser.add_argument("symbol", help="股票代號")
    signal_parser.add_argument("--days", type=int, default=60, help="分析天數")

    # 掃描市場
    scan_parser = subparsers.add_parser("scan", help="掃描市場信號")
    scan_parser.add_argument("--market", choices=["TW", "US"], help="市場代碼")
    scan_parser.add_argument("--confidence", type=float, default=0.8, help="最低信心度")

    # 收集數據
    collect_parser = subparsers.add_parser("collect", help="收集股票數據")
    collect_parser.add_argument("symbol", help="股票代號")
    collect_parser.add_argument("--days", type=int, default=30, help="收集天數")

    # 健康檢查
    subparsers.add_parser("health", help="系統健康檢查")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cli = CleanArchitectureCLI()

    try:
        if args.command == "list":
            await cli.list_stocks(args.market, args.limit)
        elif args.command == "analyze":
            await cli.analyze_stock(args.symbol, args.days)
        elif args.command == "signal":
            await cli.generate_signals(args.symbol, args.days)
        elif args.command == "scan":
            await cli.scan_market(args.market, args.confidence)
        elif args.command == "collect":
            await cli.collect_data(args.symbol, args.days)
        elif args.command == "health":
            await cli.health_check()

    except KeyboardInterrupt:
        print("\n操作已取消")
    except Exception as e:
        logger.error(f"執行失敗: {e}")
    finally:
        print("\n任務完成")


if __name__ == "__main__":
    asyncio.run(main())
