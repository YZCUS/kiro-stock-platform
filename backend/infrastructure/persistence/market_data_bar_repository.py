"""
Market data bar repository implementation.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, asc, delete, desc, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models.market_data_bar import MarketDataBar
from domain.repositories.market_data_bar_repository_interface import (
    IMarketDataBarRepository,
)


class MarketDataBarRepository(IMarketDataBarRepository):
    """PostgreSQL-backed repository for multi-timeframe bars."""

    async def upsert_batch(self, db: AsyncSession, bars: List[dict]):
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
                "symbol": stmt.excluded.symbol,
                "market": stmt.excluded.market,
                "open_price": stmt.excluded.open_price,
                "high_price": stmt.excluded.high_price,
                "low_price": stmt.excluded.low_price,
                "close_price": stmt.excluded.close_price,
                "volume": stmt.excluded.volume,
                "source_type": stmt.excluded.source_type,
                "generated_from_timeframe": stmt.excluded.generated_from_timeframe,
                "quality_status": stmt.excluded.quality_status,
                "updated_at": func.now(),
            },
        )
        await db.execute(stmt)
        await db.commit()

        stock_ids = [bar["stock_id"] for bar in bars]
        timeframes = [bar["timeframe"] for bar in bars]
        timestamps = [bar["timestamp"] for bar in bars]
        sources = [bar["source"] for bar in bars]

        result = await db.execute(
            select(MarketDataBar).where(
                MarketDataBar.stock_id.in_(stock_ids),
                MarketDataBar.timeframe.in_(timeframes),
                MarketDataBar.timestamp.in_(timestamps),
                MarketDataBar.source.in_(sources),
            )
        )
        return list(result.scalars().all())

    async def get_bars(
        self,
        db: AsyncSession,
        stock_id: int,
        timeframe: str,
        start_at: Optional[datetime] = None,
        end_at: Optional[datetime] = None,
        source: Optional[str] = None,
        limit: int = 1000,
        ascending: bool = True,
    ):
        filters = [
            MarketDataBar.stock_id == stock_id,
            MarketDataBar.timeframe == timeframe,
        ]
        if start_at is not None:
            filters.append(MarketDataBar.timestamp >= start_at)
        if end_at is not None:
            filters.append(MarketDataBar.timestamp < end_at)
        if source is not None:
            filters.append(MarketDataBar.source == source)

        order_by = asc(MarketDataBar.timestamp) if ascending else desc(MarketDataBar.timestamp)
        result = await db.execute(
            select(MarketDataBar)
            .where(and_(*filters))
            .order_by(order_by)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_latest_bar(
        self,
        db: AsyncSession,
        stock_id: int,
        timeframe: str,
        source: Optional[str] = None,
    ):
        filters = [
            MarketDataBar.stock_id == stock_id,
            MarketDataBar.timeframe == timeframe,
        ]
        if source is not None:
            filters.append(MarketDataBar.source == source)

        result = await db.execute(
            select(MarketDataBar)
            .where(and_(*filters))
            .order_by(desc(MarketDataBar.timestamp))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def delete_window(
        self,
        db: AsyncSession,
        stock_id: int,
        timeframe: str,
        start_at: datetime,
        end_at: datetime,
        source: Optional[str] = None,
        source_type: Optional[str] = None,
    ) -> int:
        filters = [
            MarketDataBar.stock_id == stock_id,
            MarketDataBar.timeframe == timeframe,
            MarketDataBar.timestamp >= start_at,
            MarketDataBar.timestamp < end_at,
        ]
        if source is not None:
            filters.append(MarketDataBar.source == source)
        if source_type is not None:
            filters.append(MarketDataBar.source_type == source_type)

        result = await db.execute(delete(MarketDataBar).where(and_(*filters)))
        await db.commit()
        return result.rowcount or 0

    async def delete_timestamps(
        self,
        db: AsyncSession,
        stock_id: int,
        timeframe: str,
        timestamps: list[datetime],
        source: Optional[str] = None,
        source_type: Optional[str] = None,
    ) -> int:
        if not timestamps:
            return 0

        filters = [
            MarketDataBar.stock_id == stock_id,
            MarketDataBar.timeframe == timeframe,
            MarketDataBar.timestamp.in_(timestamps),
        ]
        if source is not None:
            filters.append(MarketDataBar.source == source)
        if source_type is not None:
            filters.append(MarketDataBar.source_type == source_type)

        result = await db.execute(delete(MarketDataBar).where(and_(*filters)))
        await db.commit()
        return result.rowcount or 0
