"""
Timeframe-aware market data access service.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from domain.repositories.market_data_bar_repository_interface import (
    IMarketDataBarRepository,
)

STRATEGY_USABLE_QUALITY_STATUSES = {"complete", "backfilled", "corrected"}


@dataclass(frozen=True)
class MarketDataRequirement:
    """Data requirement declared by a strategy or worker."""

    stock_id: int
    timeframe: str
    lookback_bars: int
    source: Optional[str] = None


@dataclass(frozen=True)
class MarketDataAvailability:
    """Availability result for a timeframe requirement."""

    requirement: MarketDataRequirement
    available_bars: int
    latest_timestamp: Optional[datetime]

    @property
    def is_satisfied(self) -> bool:
        return self.available_bars >= self.requirement.lookback_bars


class MarketDataAccessService:
    """Provides a single access path for strategy market data needs."""

    def __init__(self, bar_repository: IMarketDataBarRepository):
        self.bar_repository = bar_repository

    async def get_required_bars(
        self, db: AsyncSession, requirement: MarketDataRequirement
    ):
        bars = await self.bar_repository.get_bars(
            db=db,
            stock_id=requirement.stock_id,
            timeframe=requirement.timeframe,
            source=requirement.source,
            limit=requirement.lookback_bars * 3,
            ascending=True,
        )
        usable_bars = [
            bar
            for bar in bars
            if bar.quality_status in STRATEGY_USABLE_QUALITY_STATUSES
        ]
        return usable_bars[-requirement.lookback_bars :]

    async def check_availability(
        self, db: AsyncSession, requirements: List[MarketDataRequirement]
    ) -> Dict[str, MarketDataAvailability]:
        results: Dict[str, MarketDataAvailability] = {}
        for requirement in requirements:
            bars = await self.get_required_bars(db, requirement)
            latest_timestamp = bars[-1].timestamp if bars else None
            key = self._requirement_key(requirement)
            results[key] = MarketDataAvailability(
                requirement=requirement,
                available_bars=len(bars),
                latest_timestamp=latest_timestamp,
            )
        return results

    def _requirement_key(self, requirement: MarketDataRequirement) -> str:
        source = requirement.source or "any"
        return f"{requirement.stock_id}:{requirement.timeframe}:{source}"
