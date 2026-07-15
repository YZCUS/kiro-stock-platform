"""
Market data completeness validation.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from domain.market_data import BarQualityStatus, MarketDataCompletenessReport
from domain.repositories.market_data_bar_repository_interface import (
    IMarketDataBarRepository,
)
from domain.repositories.stock_repository_interface import IStockRepository
from domain.services.market_calendar_service import MarketCalendarService

INCOMPLETE_BAR_STATUSES = {
    BarQualityStatus.PARTIAL.value,
    BarQualityStatus.MISSING.value,
}


class MarketDataValidationService:
    """Validates whether market_data_bars is complete and internally consistent."""

    def __init__(
        self,
        stock_repository: IStockRepository,
        bar_repository: IMarketDataBarRepository,
        calendar_service: Optional[MarketCalendarService] = None,
    ) -> None:
        self.stock_repository = stock_repository
        self.bar_repository = bar_repository
        self.calendar_service = calendar_service or MarketCalendarService()

    async def validate_window(
        self,
        db: AsyncSession,
        stock_id: int,
        timeframe: str,
        start_at: datetime,
        end_at: datetime,
        source: Optional[str] = None,
    ) -> MarketDataCompletenessReport:
        stock = await self.stock_repository.get(db, stock_id)
        if stock is None:
            raise ValueError(f"Stock ID {stock_id} does not exist")

        bars = await self.bar_repository.get_bars(
            db=db,
            stock_id=stock.id,
            timeframe=timeframe,
            start_at=start_at,
            end_at=end_at,
            source=source,
            limit=100000,
            ascending=True,
        )
        expected_timestamps = self.calendar_service.expected_timestamps(
            market=stock.market,
            timeframe=timeframe,
            start_at=start_at,
            end_at=end_at,
        )

        normalized_actual = [bar.timestamp for bar in bars]
        actual_counts = {}
        for timestamp in normalized_actual:
            actual_counts[timestamp] = actual_counts.get(timestamp, 0) + 1

        missing_timestamps = [
            timestamp
            for timestamp in expected_timestamps
            if timestamp not in actual_counts
        ]
        duplicate_count = sum(
            count - 1 for count in actual_counts.values() if count > 1
        )
        invalid_count = sum(1 for bar in bars if self._has_invalid_ohlcv(bar))
        partial_count = sum(
            1 for bar in bars if bar.quality_status in INCOMPLETE_BAR_STATUSES
        )
        partial_timestamps = [
            bar.timestamp
            for bar in bars
            if bar.quality_status in INCOMPLETE_BAR_STATUSES
        ]

        return MarketDataCompletenessReport(
            stock_id=stock.id,
            symbol=stock.symbol,
            market=stock.market,
            timeframe=timeframe,
            source=source,
            start_at=start_at,
            end_at=end_at,
            expected_count=len(expected_timestamps),
            actual_count=len(bars),
            missing_timestamps=missing_timestamps,
            partial_timestamps=partial_timestamps,
            duplicate_count=duplicate_count,
            invalid_ohlcv_count=invalid_count,
            partial_count=partial_count,
            first_timestamp=bars[0].timestamp if bars else None,
            last_timestamp=bars[-1].timestamp if bars else None,
        )

    def _has_invalid_ohlcv(self, bar) -> bool:
        try:
            open_price = Decimal(bar.open_price)
            high_price = Decimal(bar.high_price)
            low_price = Decimal(bar.low_price)
            close_price = Decimal(bar.close_price)
            volume = int(bar.volume or 0)
        except (ArithmeticError, TypeError, ValueError):
            return True

        prices = (open_price, high_price, low_price, close_price)
        if not all(price.is_finite() for price in prices):
            return True

        return (
            open_price <= 0
            or high_price <= 0
            or low_price <= 0
            or close_price <= 0
            or volume < 0
            or high_price < max(open_price, low_price, close_price)
            or low_price > min(open_price, high_price, close_price)
        )
