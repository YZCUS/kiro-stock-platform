"""
Market data bar domain models.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import List, Optional


class BarTimeframe(str, Enum):
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "1h"
    ONE_DAY = "1d"
    ONE_WEEK = "1w"


class BarSourceType(str, Enum):
    SOURCE = "source"
    DERIVED = "derived"


class BarQualityStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    BACKFILLED = "backfilled"
    CORRECTED = "corrected"
    MISSING = "missing"


TIMEFRAME_SECONDS = {
    BarTimeframe.ONE_MINUTE.value: 60,
    BarTimeframe.FIVE_MINUTES.value: 5 * 60,
    BarTimeframe.FIFTEEN_MINUTES.value: 15 * 60,
    BarTimeframe.THIRTY_MINUTES.value: 30 * 60,
    BarTimeframe.ONE_HOUR.value: 60 * 60,
    BarTimeframe.ONE_DAY.value: 24 * 60 * 60,
    BarTimeframe.ONE_WEEK.value: 7 * 24 * 60 * 60,
}


@dataclass(frozen=True)
class MarketDataBarDTO:
    """Normalized OHLCV bar used by data and strategy services."""

    stock_id: int
    timeframe: str
    timestamp: datetime
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: int = 0
    source: str = "unknown"
    source_type: str = BarSourceType.SOURCE.value
    is_adjusted: bool = False
    generated_from_timeframe: Optional[str] = None
    quality_status: str = BarQualityStatus.COMPLETE.value


@dataclass(frozen=True)
class MarketDataCompletenessReport:
    """Completeness result for a stock/timeframe/date window."""

    stock_id: int
    symbol: str
    market: str
    timeframe: str
    source: Optional[str]
    start_at: datetime
    end_at: datetime
    expected_count: int
    actual_count: int
    missing_timestamps: List[datetime]
    partial_timestamps: List[datetime]
    duplicate_count: int
    invalid_ohlcv_count: int
    partial_count: int
    first_timestamp: Optional[datetime]
    last_timestamp: Optional[datetime]

    @property
    def completeness_percentage(self) -> float:
        if self.expected_count == 0:
            return 100.0 if self.actual_count == 0 else 0.0
        present_count = max(self.expected_count - len(self.missing_timestamps), 0)
        return round((present_count / self.expected_count) * 100, 2)

    @property
    def is_complete(self) -> bool:
        return (
            self.expected_count == self.actual_count
            and not self.missing_timestamps
            and not self.partial_timestamps
            and self.duplicate_count == 0
            and self.invalid_ohlcv_count == 0
        )

    def to_dict(self) -> dict:
        return {
            "stock_id": self.stock_id,
            "symbol": self.symbol,
            "market": self.market,
            "timeframe": self.timeframe,
            "source": self.source,
            "start_at": self.start_at.isoformat(),
            "end_at": self.end_at.isoformat(),
            "expected_count": self.expected_count,
            "actual_count": self.actual_count,
            "missing_count": len(self.missing_timestamps),
            "missing_timestamps": [
                timestamp.isoformat() for timestamp in self.missing_timestamps
            ],
            "partial_timestamps": [
                timestamp.isoformat() for timestamp in self.partial_timestamps
            ],
            "duplicate_count": self.duplicate_count,
            "invalid_ohlcv_count": self.invalid_ohlcv_count,
            "partial_count": self.partial_count,
            "first_timestamp": (
                self.first_timestamp.isoformat() if self.first_timestamp else None
            ),
            "last_timestamp": (
                self.last_timestamp.isoformat() if self.last_timestamp else None
            ),
            "completeness_percentage": self.completeness_percentage,
            "is_complete": self.is_complete,
        }


def timeframe_to_timedelta(timeframe: str) -> timedelta:
    seconds = TIMEFRAME_SECONDS.get(timeframe)
    if seconds is None:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    return timedelta(seconds=seconds)


def is_supported_timeframe(timeframe: str) -> bool:
    return timeframe in TIMEFRAME_SECONDS
