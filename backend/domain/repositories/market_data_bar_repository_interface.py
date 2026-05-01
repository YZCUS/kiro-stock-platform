"""
Market data bar repository interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession


class IMarketDataBarRepository(ABC):
    """Repository port for multi-timeframe OHLCV bars."""

    @abstractmethod
    async def upsert_batch(self, db: AsyncSession, bars: List[dict]):
        """Create or update bars using the natural unique key."""
        pass

    @abstractmethod
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
        """Fetch bars for a stock/timeframe window."""
        pass

    @abstractmethod
    async def get_latest_bar(
        self,
        db: AsyncSession,
        stock_id: int,
        timeframe: str,
        source: Optional[str] = None,
    ):
        """Fetch the latest bar for a stock/timeframe."""
        pass

    @abstractmethod
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
        """Delete bars in a window before deterministic regeneration."""
        pass

    @abstractmethod
    async def delete_timestamps(
        self,
        db: AsyncSession,
        stock_id: int,
        timeframe: str,
        timestamps: list[datetime],
        source: Optional[str] = None,
        source_type: Optional[str] = None,
    ) -> int:
        """Delete exact bar timestamps before replacing selected bars."""
        pass
