#!/usr/bin/env python3
"""
資料庫種子數據腳本
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
from decimal import Decimal

# 將專案根目錄加入 Python 路徑
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.settings import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_sample_stocks(session: AsyncSession):
    """建立範例股票數據"""
    from sqlalchemy import text

    logger.info("建立範例股票數據...")

    # 台股數據
    tw_stocks = [
        ("2330.TW", "TW", "台積電"),
        ("2317.TW", "TW", "鴻海"),
        ("2454.TW", "TW", "聯發科"),
        ("2881.TW", "TW", "富邦金"),
        ("2382.TW", "TW", "廣達"),
        ("2303.TW", "TW", "聯電"),
        ("2308.TW", "TW", "台達電"),
        ("2412.TW", "TW", "中華電"),
        ("1301.TW", "TW", "台塑"),
        ("1303.TW", "TW", "南亞"),
    ]

    # 美股數據
    us_stocks = [
        ("AAPL", "US", "Apple Inc."),
        ("GOOGL", "US", "Alphabet Inc."),
        ("MSFT", "US", "Microsoft Corporation"),
        ("AMZN", "US", "Amazon.com Inc."),
        ("TSLA", "US", "Tesla Inc."),
        ("META", "US", "Meta Platforms Inc."),
        ("NVDA", "US", "NVIDIA Corporation"),
        ("NFLX", "US", "Netflix Inc."),
        ("AMD", "US", "Advanced Micro Devices"),
        ("INTC", "US", "Intel Corporation"),
    ]

    all_stocks = tw_stocks + us_stocks

    for symbol, market, name in all_stocks:
        try:
            await session.execute(
                text(
                    """
                INSERT INTO stocks (symbol, market, name) 
                VALUES (:symbol, :market, :name)
                ON CONFLICT (symbol, market) DO NOTHING
            """
                ),
                {"symbol": symbol, "market": market, "name": name},
            )

        except Exception as e:
            logger.error(f"插入股票 {symbol} 失敗: {e}")

    await session.commit()
    logger.info(f"成功建立 {len(all_stocks)} 支股票數據")


async def create_sample_price_history(session: AsyncSession):
    """建立範例價格歷史數據"""
    from sqlalchemy import text
    import random

    logger.info("建立範例價格歷史數據...")

    # 取得所有股票
    result = await session.execute(text("SELECT id, symbol, market FROM stocks"))
    stocks = result.fetchall()

    # 為每支股票建立過去30天的價格數據
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    for stock_id, symbol, market in stocks:
        try:
            # 設定基礎價格（根據市場調整）
            if market == "TW":
                base_price = random.uniform(50, 600)  # 台股價格範圍
            else:
                base_price = random.uniform(20, 300)  # 美股價格範圍

            current_date = start_date
            current_price = base_price

            while current_date <= end_date:
                # 跳過週末
                if current_date.weekday() < 5:  # 0-4 是週一到週五
                    # 模擬價格波動
                    price_change = random.uniform(-0.05, 0.05)  # ±5% 波動
                    current_price *= 1 + price_change

                    # 計算開高低收
                    open_price = current_price * random.uniform(0.98, 1.02)
                    high_price = max(open_price, current_price) * random.uniform(
                        1.0, 1.03
                    )
                    low_price = min(open_price, current_price) * random.uniform(
                        0.97, 1.0
                    )
                    close_price = current_price

                    # 模擬成交量
                    volume = random.randint(1000000, 50000000)

                    await session.execute(
                        text(
                            """
                        INSERT INTO price_history 
                        (stock_id, date, open_price, high_price, low_price, close_price, volume, adjusted_close)
                        VALUES (:stock_id, :date, :open_price, :high_price, :low_price, :close_price, :volume, :adjusted_close)
                        ON CONFLICT (stock_id, date) DO NOTHING
                    """
                        ),
                        {
                            "stock_id": stock_id,
                            "date": current_date,
                            "open_price": round(Decimal(str(open_price)), 4),
                            "high_price": round(Decimal(str(high_price)), 4),
                            "low_price": round(Decimal(str(low_price)), 4),
                            "close_price": round(Decimal(str(close_price)), 4),
                            "volume": volume,
                            "adjusted_close": round(Decimal(str(close_price)), 4),
                        },
                    )

                current_date += timedelta(days=1)

        except Exception as e:
            logger.error(f"建立股票 {symbol} 價格數據失敗: {e}")

    await session.commit()
    logger.info("範例價格歷史數據建立完成")


async def create_sample_technical_indicators(session: AsyncSession):
    """建立範例技術指標數據"""
    from sqlalchemy import text
    import random

    logger.info("建立範例技術指標數據...")

    # 取得所有股票和最近的價格數據
    result = await session.execute(
        text(
            """
        SELECT DISTINCT ph.stock_id, ph.date 
        FROM price_history ph 
        ORDER BY ph.stock_id, ph.date DESC
        LIMIT 100
    """
        )
    )
    price_data = result.fetchall()

    indicator_types = [
        "RSI",
        "SMA_5",
        "SMA_20",
        "SMA_60",
        "EMA_12",
        "EMA_26",
        "MACD",
        "BB_UPPER",
        "BB_LOWER",
        "KD_K",
        "KD_D",
    ]

    for stock_id, date in price_data:
        for indicator_type in indicator_types:
            try:
                # 模擬不同指標的數值範圍
                if indicator_type == "RSI":
                    value = random.uniform(20, 80)
                elif "SMA" in indicator_type or "EMA" in indicator_type:
                    value = random.uniform(50, 300)
                elif indicator_type == "MACD":
                    value = random.uniform(-5, 5)
                elif "BB_" in indicator_type:
                    value = random.uniform(50, 300)
                elif "KD_" in indicator_type:
                    value = random.uniform(20, 80)
                else:
                    value = random.uniform(0, 100)

                await session.execute(
                    text(
                        """
                    INSERT INTO technical_indicators 
                    (stock_id, date, indicator_type, value, parameters)
                    VALUES (:stock_id, :date, :indicator_type, :value, :parameters)
                    ON CONFLICT (stock_id, date, indicator_type) DO NOTHING
                """
                    ),
                    {
                        "stock_id": stock_id,
                        "date": date,
                        "indicator_type": indicator_type,
                        "value": round(Decimal(str(value)), 8),
                        "parameters": {"period": 14 if "RSI" in indicator_type else 20},
                    },
                )

            except Exception as e:
                logger.error(f"建立技術指標數據失敗: {e}")

    await session.commit()
    logger.info("範例技術指標數據建立完成")


async def create_sample_trading_signals(session: AsyncSession):
    """建立範例交易信號數據"""
    from sqlalchemy import text
    import random

    logger.info("建立範例交易信號數據...")

    # 取得所有股票
    result = await session.execute(text("SELECT id, symbol FROM stocks LIMIT 5"))
    stocks = result.fetchall()

    signal_types = ["golden_cross", "death_cross", "buy", "sell"]

    for stock_id, symbol in stocks:
        # 為每支股票建立幾個隨機信號
        for _ in range(random.randint(1, 3)):
            try:
                signal_type = random.choice(signal_types)
                signal_date = date.today() - timedelta(days=random.randint(1, 30))
                price = Decimal(str(random.uniform(50, 300)))
                confidence = Decimal(str(random.uniform(0.6, 0.95)))

                descriptions = {
                    "golden_cross": f"{symbol} 短期均線上穿長期均線，形成黃金交叉",
                    "death_cross": f"{symbol} 短期均線下穿長期均線，形成死亡交叉",
                    "buy": f"{symbol} 技術指標顯示買入信號",
                    "sell": f"{symbol} 技術指標顯示賣出信號",
                }

                await session.execute(
                    text(
                        """
                    INSERT INTO trading_signals 
                    (stock_id, signal_type, date, price, confidence, description)
                    VALUES (:stock_id, :signal_type, :date, :price, :confidence, :description)
                """
                    ),
                    {
                        "stock_id": stock_id,
                        "signal_type": signal_type,
                        "date": signal_date,
                        "price": round(price, 4),
                        "confidence": round(confidence, 2),
                        "description": descriptions[signal_type],
                    },
                )

            except Exception as e:
                logger.error(f"建立交易信號數據失敗: {e}")

    await session.commit()
    logger.info("範例交易信號數據建立完成")


async def main():
    """主函數"""
    logger.info("開始建立種子數據...")

    # 建立資料庫引擎和會話
    engine = create_async_engine(
        settings.database.url.replace("postgresql://", "postgresql+asyncpg://"),
        echo=False,
    )

    AsyncSessionLocal = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    try:
        async with AsyncSessionLocal() as session:
            # 建立範例數據
            await create_sample_stocks(session)
            await create_sample_price_history(session)
            await create_sample_technical_indicators(session)
            await create_sample_trading_signals(session)

        logger.info("種子數據建立完成！")

    except Exception as e:
        logger.error(f"建立種子數據失敗: {e}")
        return 1

    finally:
        await engine.dispose()

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
