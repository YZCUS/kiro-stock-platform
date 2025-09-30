"""
價格歷史儲存庫實現 - Infrastructure Layer
實現Domain層的IPriceHistoryRepository介面，封裝具體的ORM操作
"""
from typing import List, Optional, Tuple
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc

from domain.repositories.price_history_repository_interface import IPriceHistoryRepository
from models.domain.price_history import PriceHistory


class PriceHistoryRepository(IPriceHistoryRepository):
    """價格歷史儲存庫實現"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_by_stock(
        self,
        db: AsyncSession,
        stock_id: int,
        limit: int = 100
    ) -> List[PriceHistory]:
        """取得指定股票的價格歷史"""
        result = await db.execute(
            select(PriceHistory)
            .where(PriceHistory.stock_id == stock_id)
            .order_by(desc(PriceHistory.date))
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_stock_and_date_range(
        self,
        db: AsyncSession,
        stock_id: int,
        start_date: date,
        end_date: date,
        limit: int = 1000
    ) -> List[PriceHistory]:
        """取得指定股票在特定日期範圍的價格歷史"""
        result = await db.execute(
            select(PriceHistory)
            .where(
                and_(
                    PriceHistory.stock_id == stock_id,
                    PriceHistory.date >= start_date,
                    PriceHistory.date <= end_date
                )
            )
            .order_by(desc(PriceHistory.date))
            .limit(limit)
        )
        return result.scalars().all()

    async def get_latest_price(
        self,
        db: AsyncSession,
        stock_id: int
    ) -> Optional[PriceHistory]:
        """取得最新價格"""
        result = await db.execute(
            select(PriceHistory)
            .where(PriceHistory.stock_id == stock_id)
            .order_by(desc(PriceHistory.date))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_stock_price_range(
        self,
        db: AsyncSession,
        stock_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 1000
    ) -> List[PriceHistory]:
        """取得指定日期範圍內的價格數據"""
        query = select(PriceHistory).where(PriceHistory.stock_id == stock_id)

        if start_date:
            query = query.where(PriceHistory.date >= start_date)
        if end_date:
            query = query.where(PriceHistory.date <= end_date)

        query = query.order_by(desc(PriceHistory.date)).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    async def create_batch(
        self,
        db: AsyncSession,
        price_data: List[dict]
    ) -> List[PriceHistory]:
        """批量創建價格歷史記錄"""
        price_objects = []

        for data in price_data:
            price_obj = PriceHistory(
                stock_id=data['stock_id'],
                date=data['date'],
                open_price=data['open_price'],
                high_price=data['high_price'],
                low_price=data['low_price'],
                close_price=data['close_price'],
                volume=data.get('volume', 0),
                adj_close=data.get('adj_close')
            )
            price_objects.append(price_obj)

        db.add_all(price_objects)
        await db.commit()

        for obj in price_objects:
            await db.refresh(obj)

        return price_objects

    async def get_price_changes(
        self,
        db: AsyncSession,
        stock_id: int,
        periods: int = 1
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
        self,
        db: AsyncSession,
        stock_id: int,
        days: int = 30
    ) -> dict:
        """取得成交量統計"""
        from datetime import datetime, timedelta

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        result = await db.execute(
            select(
                func.avg(PriceHistory.volume).label('avg_volume'),
                func.max(PriceHistory.volume).label('max_volume'),
                func.min(PriceHistory.volume).label('min_volume'),
                func.count(PriceHistory.id).label('trading_days')
            )
            .where(
                and_(
                    PriceHistory.stock_id == stock_id,
                    PriceHistory.date >= start_date,
                    PriceHistory.date <= end_date,
                    PriceHistory.volume > 0
                )
            )
        )

        row = result.first()
        if row:
            return {
                'avg_volume': float(row.avg_volume) if row.avg_volume else 0,
                'max_volume': int(row.max_volume) if row.max_volume else 0,
                'min_volume': int(row.min_volume) if row.min_volume else 0,
                'trading_days': int(row.trading_days) if row.trading_days else 0
            }

        return {
            'avg_volume': 0,
            'max_volume': 0,
            'min_volume': 0,
            'trading_days': 0
        }

    async def get_missing_dates(
        self,
        db: AsyncSession,
        stock_id: int,
        start_date: date,
        end_date: date
    ) -> List[date]:
        """取得缺失的交易日期"""
        from datetime import timedelta

        # 查詢該股票在期間內的所有日期
        result = await db.execute(
            select(PriceHistory.date)
            .where(
                and_(
                    PriceHistory.stock_id == stock_id,
                    PriceHistory.date >= start_date,
                    PriceHistory.date <= end_date
                )
            )
            .order_by(PriceHistory.date)
        )

        existing_dates = set(row[0] for row in result.fetchall())

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