"""Daily price repository backed by market_data_bars."""

from typing import List, Optional, Tuple
from datetime import date, datetime, time
from zoneinfo import ZoneInfo
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from domain.repositories.daily_price_repository_interface import (
    IDailyPriceRepository,
)
from domain.market_data.daily_prices import (
    DailyPriceBar,
    fetch_daily_prices,
    fetch_latest_daily_price,
)
from domain.models.market_data_bar import MarketDataBar
from domain.models.stock import Stock


class DailyPriceRepository(IDailyPriceRepository):
    """日線價格儲存庫實現。"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_by_stock(
        self, db: AsyncSession, stock_id: int, limit: int = 100
    ) -> List[DailyPriceBar]:
        """取得指定股票的日線資料。"""
        return await fetch_daily_prices(db, stock_id=stock_id, limit=limit)

    async def get_by_stock_and_date_range(
        self,
        db: AsyncSession,
        stock_id: int,
        start_date: date,
        end_date: date,
        limit: int = 1000,
    ) -> List[DailyPriceBar]:
        """取得指定股票在特定日期範圍的日線資料。"""
        return await fetch_daily_prices(
            db,
            stock_id=stock_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )

    async def get_latest_price(
        self, db: AsyncSession, stock_id: int
    ) -> Optional[DailyPriceBar]:
        """取得最新日線收盤價。"""
        return await fetch_latest_daily_price(db, stock_id)

    async def get_stock_price_range(
        self,
        db: AsyncSession,
        stock_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 1000,
    ) -> List[DailyPriceBar]:
        """取得指定日期範圍內的日線資料。"""
        return await fetch_daily_prices(
            db,
            stock_id=stock_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )

    async def create_batch(
        self, db: AsyncSession, price_data: List[dict]
    ) -> List[DailyPriceBar]:
        """批量儲存日線資料到 canonical market_data_bars。"""
        from sqlalchemy.dialects.postgresql import insert

        if not price_data:
            return []

        stock_ids = sorted({data["stock_id"] for data in price_data})
        stock_result = await db.execute(
            select(Stock.id, Stock.symbol, Stock.market).where(Stock.id.in_(stock_ids))
        )
        stocks_by_id = {
            row.id: {"symbol": row.symbol, "market": row.market}
            for row in stock_result.all()
        }

        bars = []
        for data in price_data:
            stock = stocks_by_id.get(data["stock_id"])
            symbol = data.get("symbol") or (stock["symbol"] if stock else None)
            market = data.get("market") or (stock["market"] if stock else None)
            if not symbol or not market:
                continue

            open_price = data.get("open_price")
            high_price = data.get("high_price")
            low_price = data.get("low_price")
            close_price = data.get("close_price")
            if not all([open_price, high_price, low_price, close_price]):
                continue

            bar_date = data["date"]
            market_timezone = ZoneInfo(
                "Asia/Taipei" if market == "TW" else "America/New_York"
            )
            bars.append(
                {
                    "stock_id": data["stock_id"],
                    "symbol": symbol,
                    "market": market,
                    "timeframe": "1d",
                    "timestamp": datetime.combine(
                        bar_date,
                        time.min,
                        tzinfo=market_timezone,
                    ),
                    "open_price": open_price,
                    "high_price": high_price,
                    "low_price": low_price,
                    "close_price": close_price,
                    "volume": data.get("volume") or 0,
                    "source": self._canonical_source_name(
                        data.get("source") or "daily_price_adapter"
                    ),
                    "source_type": "source",
                    "is_adjusted": False,
                    "generated_from_timeframe": None,
                    "quality_status": data.get("quality_status") or "backfilled",
                }
            )

        if not bars:
            return []

        stmt = insert(MarketDataBar).values(bars)
        stmt = stmt.on_conflict_do_update(
            index_elements=[
                "stock_id",
                "timeframe",
                "timestamp",
                "source",
                "is_adjusted",
            ],
            set_={
                "open_price": stmt.excluded.open_price,
                "high_price": stmt.excluded.high_price,
                "low_price": stmt.excluded.low_price,
                "close_price": stmt.excluded.close_price,
                "volume": stmt.excluded.volume,
                "source_type": stmt.excluded.source_type,
                "quality_status": stmt.excluded.quality_status,
                "updated_at": func.now(),
            },
        )

        await db.execute(stmt)
        await db.commit()

        dates = [data["date"] for data in price_data]
        created: list[DailyPriceBar] = []
        for stock_id in stock_ids:
            stock_dates = [data["date"] for data in price_data if data["stock_id"] == stock_id]
            if not stock_dates:
                continue
            created.extend(
                await fetch_daily_prices(
                    db,
                    stock_id=stock_id,
                    start_date=min(stock_dates),
                    end_date=max(stock_dates),
                    limit=len(stock_dates),
                )
            )
        return [price for price in created if price.date in dates]

    @staticmethod
    def _canonical_source_name(source: str) -> str:
        return "_".join(source.strip().lower().replace("-", "_").split())

    async def get_price_changes(
        self, db: AsyncSession, stock_id: int, periods: int = 1
    ) -> List[Tuple[date, float]]:
        """計算價格變化 (日期, 變化百分比)"""
        prices = await self.get_by_stock(db, stock_id, limit=periods + 1)

        changes = []
        for i in range(len(prices) - 1):
            current = prices[i]
            previous = prices[i + 1]

            if previous.close_price > 0:
                change_percent = (
                    (float(current.close_price) - float(previous.close_price))
                    / float(previous.close_price)
                ) * 100
                changes.append((current.date, change_percent))

        return changes

    async def get_volume_stats(
        self, db: AsyncSession, stock_id: int, days: int = 30
    ) -> dict:
        """取得成交量統計"""
        from datetime import datetime, timedelta

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        prices = await fetch_daily_prices(
            db,
            stock_id=stock_id,
            start_date=start_date,
            end_date=end_date,
            limit=days * 2,
        )
        volumes = [int(price.volume) for price in prices if price.volume and price.volume > 0]
        if volumes:
            return {
                "avg_volume": sum(volumes) / len(volumes),
                "max_volume": max(volumes),
                "min_volume": min(volumes),
                "trading_days": len(volumes),
            }

        return {"avg_volume": 0, "max_volume": 0, "min_volume": 0, "trading_days": 0}

    async def get_missing_dates(
        self, db: AsyncSession, stock_id: int, start_date: date, end_date: date
    ) -> List[date]:
        """取得缺失的交易日期"""
        from datetime import timedelta

        prices = await fetch_daily_prices(
            db,
            stock_id=stock_id,
            start_date=start_date,
            end_date=end_date,
            limit=10000,
            ascending=True,
        )
        existing_dates = {price.date for price in prices}

        # 生成所有工作日（週一到週五）
        all_dates = []
        current_date = start_date
        while current_date <= end_date:
            # 只包含工作日
            if current_date.weekday() < 5:
                all_dates.append(current_date)
            current_date += timedelta(days=1)

        # 找出缺失的日期
        missing_dates = [d for d in all_dates if d not in existing_dates]
        return missing_dates
