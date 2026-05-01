"""
Bar aggregation service.
"""

from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Iterable, List, Optional
from zoneinfo import ZoneInfo

from domain.market_data import (
    BarQualityStatus,
    BarSourceType,
    MarketDataBarDTO,
    timeframe_to_timedelta,
)
from domain.services.market_calendar_service import MarketCalendarService


class BarAggregationService:
    """Aggregates lower-timeframe OHLCV bars into higher timeframes."""

    def aggregate(
        self,
        bars: Iterable[MarketDataBarDTO],
        target_timeframe: str,
        source: str = "internal_aggregation",
        market: Optional[str] = None,
    ) -> List[MarketDataBarDTO]:
        sorted_bars = sorted(bars, key=lambda bar: bar.timestamp)
        if not sorted_bars:
            return []

        source_timeframe = sorted_bars[0].timeframe
        self._validate_timeframes(source_timeframe, target_timeframe)

        grouped: OrderedDict[datetime, list[MarketDataBarDTO]] = OrderedDict()
        default_expected_bars = int(
            timeframe_to_timedelta(target_timeframe).total_seconds()
            / timeframe_to_timedelta(source_timeframe).total_seconds()
        )
        for bar in sorted_bars:
            if bar.timeframe != source_timeframe:
                raise ValueError("All source bars must use the same timeframe")
            bucket_start = self._floor_timestamp(
                bar.timestamp,
                target_timeframe,
                market=market,
            )
            grouped.setdefault(bucket_start, []).append(bar)

        aggregated = []
        for bucket_start, group in grouped.items():
            first = group[0]
            last = group[-1]
            expected_bars = self._expected_source_bars_for_bucket(
                market=market,
                source_timeframe=source_timeframe,
                target_timeframe=target_timeframe,
                bucket_start=bucket_start,
                fallback_count=default_expected_bars,
            )
            aggregated.append(
                MarketDataBarDTO(
                    stock_id=first.stock_id,
                    timeframe=target_timeframe,
                    timestamp=bucket_start,
                    open_price=first.open_price,
                    high_price=max(bar.high_price for bar in group),
                    low_price=min(bar.low_price for bar in group),
                    close_price=last.close_price,
                    volume=sum(int(bar.volume or 0) for bar in group),
                    source=source,
                    source_type=BarSourceType.DERIVED.value,
                    is_adjusted=first.is_adjusted,
                    generated_from_timeframe=source_timeframe,
                    quality_status=self._quality_for_group(group, expected_bars),
                )
            )
        return aggregated

    def _validate_timeframes(
        self, source_timeframe: str, target_timeframe: str
    ) -> None:
        source_delta = timeframe_to_timedelta(source_timeframe)
        target_delta = timeframe_to_timedelta(target_timeframe)
        if source_delta >= target_delta:
            raise ValueError("Target timeframe must be larger than source timeframe")
        if target_delta.total_seconds() % source_delta.total_seconds() != 0:
            raise ValueError("Target timeframe must be divisible by source timeframe")

    def _floor_timestamp(
        self,
        timestamp: datetime,
        timeframe: str,
        market: Optional[str] = None,
    ) -> datetime:
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        if timeframe == "1w":
            if market is not None:
                timestamp = timestamp.astimezone(self._market_timezone(market))
            week_start = timestamp.date() - timedelta(days=timestamp.weekday())
            return datetime.combine(
                week_start,
                datetime.min.time(),
                tzinfo=timestamp.tzinfo,
            )

        delta = timeframe_to_timedelta(timeframe)
        seconds = int(delta.total_seconds())
        epoch_seconds = int(timestamp.timestamp())
        floored = epoch_seconds - (epoch_seconds % seconds)
        return datetime.fromtimestamp(floored, tz=timestamp.tzinfo)

    def _market_timezone(self, market: str) -> ZoneInfo:
        if market == "TW":
            return ZoneInfo("Asia/Taipei")
        return ZoneInfo("America/New_York")

    def _expected_source_bars_for_bucket(
        self,
        market: Optional[str],
        source_timeframe: str,
        target_timeframe: str,
        bucket_start: datetime,
        fallback_count: int,
    ) -> int:
        if market is None:
            return fallback_count

        try:
            calendar = MarketCalendarService()
            bucket_end = bucket_start + timeframe_to_timedelta(target_timeframe)
            expected_timestamps = calendar.expected_timestamps(
                market=market,
                timeframe=source_timeframe,
                start_at=bucket_start,
                end_at=bucket_end,
            )
        except Exception:
            return fallback_count

        return len(expected_timestamps) or fallback_count

    def _quality_for_group(
        self, bars: list[MarketDataBarDTO], expected_bars: int
    ) -> str:
        statuses = {bar.quality_status for bar in bars}
        if len(bars) < expected_bars:
            return BarQualityStatus.PARTIAL.value
        if statuses == {BarQualityStatus.COMPLETE.value}:
            return BarQualityStatus.COMPLETE.value
        if BarQualityStatus.MISSING.value in statuses:
            return BarQualityStatus.MISSING.value
        return BarQualityStatus.PARTIAL.value

    def to_record_dicts(
        self,
        bars: Iterable[MarketDataBarDTO],
        symbol: str,
        market: str,
    ) -> List[dict]:
        records = []
        for bar in bars:
            records.append(
                {
                    "stock_id": bar.stock_id,
                    "symbol": symbol,
                    "market": market,
                    "timeframe": bar.timeframe,
                    "timestamp": bar.timestamp,
                    "open_price": Decimal(bar.open_price),
                    "high_price": Decimal(bar.high_price),
                    "low_price": Decimal(bar.low_price),
                    "close_price": Decimal(bar.close_price),
                    "volume": int(bar.volume or 0),
                    "source": bar.source,
                    "source_type": bar.source_type,
                    "is_adjusted": bar.is_adjusted,
                    "generated_from_timeframe": bar.generated_from_timeframe,
                    "quality_status": bar.quality_status,
                }
            )
        return records
