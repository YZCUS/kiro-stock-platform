"""
Market data ingestion and derived timeframe orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Iterable, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from domain.market_data import (
    BarQualityStatus,
    BarSourceType,
    MarketDataBarDTO,
    timeframe_to_timedelta,
    is_supported_timeframe,
)
from domain.repositories.market_data_bar_repository_interface import (
    IMarketDataBarRepository,
)
from domain.repositories.price_data_source_interface import IPriceDataSource
from domain.repositories.stock_repository_interface import IStockRepository
from domain.services.bar_aggregation_service import BarAggregationService
from domain.services.market_calendar_service import MarketCalendarService


SOURCE_TIMEFRAMES = {"1d", "5m"}
DERIVED_TIMEFRAME_SOURCES = {
    "15m": "5m",
    "30m": "5m",
    "1h": "5m",
    "1w": "1d",
}


@dataclass(frozen=True)
class MarketDataWriteResult:
    """Summary for a market data write or aggregation operation."""

    stock_id: int
    symbol: str
    market: str
    timeframe: str
    records_written: int
    source: str
    source_type: str
    quality_status: str = BarQualityStatus.COMPLETE.value
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        return {
            "stock_id": self.stock_id,
            "symbol": self.symbol,
            "market": self.market,
            "timeframe": self.timeframe,
            "records_written": self.records_written,
            "source": self.source,
            "source_type": self.source_type,
            "quality_status": self.quality_status,
            "success": self.success,
            "errors": self.errors,
        }


class MarketDataIngestionService:
    """Writes source bars and aggregates derived bars into market_data_bars."""

    def __init__(
        self,
        stock_repository: IStockRepository,
        bar_repository: IMarketDataBarRepository,
        price_data_source: IPriceDataSource,
        aggregation_service: Optional[BarAggregationService] = None,
        calendar_service: Optional[MarketCalendarService] = None,
    ) -> None:
        self.stock_repository = stock_repository
        self.bar_repository = bar_repository
        self.price_data_source = price_data_source
        self.aggregation_service = aggregation_service or BarAggregationService()
        self.calendar_service = calendar_service or MarketCalendarService()

    async def collect_source_bars(
        self,
        db: AsyncSession,
        stock_id: int,
        timeframe: str,
        start_at: datetime,
        end_at: datetime,
        source: Optional[str] = None,
    ) -> MarketDataWriteResult:
        """Fetch source bars from the configured provider and upsert them."""
        if timeframe not in SOURCE_TIMEFRAMES:
            raise ValueError(
                f"{timeframe} must be derived from source data; supported source "
                f"timeframes are {sorted(SOURCE_TIMEFRAMES)}"
            )

        stock = await self.stock_repository.get(db, stock_id)
        if stock is None:
            raise ValueError(f"Stock ID {stock_id} does not exist")

        provider_source = self.storage_source_name(source)
        raw_bars = await self.price_data_source.fetch_bars(
            symbol=stock.symbol,
            timeframe=timeframe,
            start_at=start_at,
            end_at=end_at,
            market=stock.market,
        )
        records = [
            self.raw_bar_to_record(
                raw_bar,
                stock_id=stock.id,
                symbol=stock.symbol,
                market=stock.market,
                timeframe=timeframe,
                source=provider_source,
            )
            for raw_bar in raw_bars
        ]
        saved = await self.bar_repository.upsert_batch(db, records)
        return MarketDataWriteResult(
            stock_id=stock.id,
            symbol=stock.symbol,
            market=stock.market,
            timeframe=timeframe,
            records_written=len(saved),
            source=provider_source,
            source_type=BarSourceType.SOURCE.value,
        )

    async def collect_backfilled_bars(
        self,
        db: AsyncSession,
        stock_id: int,
        timeframe: str,
        start_at: datetime,
        end_at: datetime,
        target_timestamps: Optional[Iterable[datetime]] = None,
        source: Optional[str] = None,
    ) -> MarketDataWriteResult:
        """Fetch provider bars for a higher timeframe without filling lower bars."""
        if not is_supported_timeframe(timeframe):
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        stock = await self.stock_repository.get(db, stock_id)
        if stock is None:
            raise ValueError(f"Stock ID {stock_id} does not exist")

        provider_source = self.storage_source_name(source)
        raw_bars = await self.price_data_source.fetch_bars(
            symbol=stock.symbol,
            timeframe=timeframe,
            start_at=start_at,
            end_at=end_at,
            market=stock.market,
        )
        target_keys = (
            {self._timestamp_key(timestamp) for timestamp in target_timestamps}
            if target_timestamps is not None
            else None
        )

        records = []
        for raw_bar in raw_bars:
            record = self.raw_bar_to_record(
                raw_bar,
                stock_id=stock.id,
                symbol=stock.symbol,
                market=stock.market,
                timeframe=timeframe,
                source=provider_source,
                quality_status=BarQualityStatus.BACKFILLED.value,
            )
            record_timestamp = self._timestamp_key(record["timestamp"])
            if target_keys is None or record_timestamp in target_keys:
                records.append(record)

        timestamps = [record["timestamp"] for record in records]
        await self.bar_repository.delete_timestamps(
            db=db,
            stock_id=stock.id,
            timeframe=timeframe,
            timestamps=timestamps,
            source_type=BarSourceType.DERIVED.value,
        )
        saved = await self.bar_repository.upsert_batch(db, records)
        return MarketDataWriteResult(
            stock_id=stock.id,
            symbol=stock.symbol,
            market=stock.market,
            timeframe=timeframe,
            records_written=len(saved),
            source=provider_source,
            source_type=BarSourceType.SOURCE.value,
            quality_status=BarQualityStatus.BACKFILLED.value,
        )

    async def backfill_incomplete_derived_reports(
        self,
        db: AsyncSession,
        reports: Iterable,
    ) -> list[MarketDataWriteResult]:
        """Directly backfill incomplete derived timeframe bars from provider data."""
        results = []
        for report in reports:
            if report.timeframe not in DERIVED_TIMEFRAME_SOURCES:
                continue
            affected_timestamps = [
                *report.missing_timestamps,
                *report.partial_timestamps,
            ]
            if not affected_timestamps:
                continue

            start_at = min(affected_timestamps)
            end_at = max(affected_timestamps) + timeframe_to_timedelta(report.timeframe)
            results.append(
                await self.collect_backfilled_bars(
                    db=db,
                    stock_id=report.stock_id,
                    timeframe=report.timeframe,
                    start_at=start_at,
                    end_at=end_at,
                    target_timestamps=affected_timestamps,
                )
            )
        return results

    async def aggregate_derived_bars(
        self,
        db: AsyncSession,
        stock_id: int,
        target_timeframe: str,
        start_at: datetime,
        end_at: datetime,
        source_timeframe: Optional[str] = None,
        source: Optional[str] = None,
        target_source: str = "internal_aggregation",
    ) -> MarketDataWriteResult:
        """Aggregate lower timeframe bars into a target timeframe."""
        if not is_supported_timeframe(target_timeframe):
            raise ValueError(f"Unsupported timeframe: {target_timeframe}")

        source_timeframe = source_timeframe or DERIVED_TIMEFRAME_SOURCES.get(
            target_timeframe
        )
        if source_timeframe is None:
            raise ValueError(f"No default source timeframe for {target_timeframe}")

        stock = await self.stock_repository.get(db, stock_id)
        if stock is None:
            raise ValueError(f"Stock ID {stock_id} does not exist")

        source_filter = source
        if source_timeframe in SOURCE_TIMEFRAMES:
            source_filter = self.storage_source_name(source)

        source_bars = await self.bar_repository.get_bars(
            db=db,
            stock_id=stock.id,
            timeframe=source_timeframe,
            start_at=start_at,
            end_at=end_at,
            source=source_filter,
            limit=100000,
            ascending=True,
        )
        dto_bars = [self.orm_bar_to_dto(bar) for bar in source_bars]
        aggregated = self.aggregation_service.aggregate(
            dto_bars,
            target_timeframe=target_timeframe,
            source=target_source,
            market=stock.market,
        )
        records = self.aggregation_service.to_record_dicts(
            aggregated,
            symbol=stock.symbol,
            market=stock.market,
        )
        await self.bar_repository.delete_window(
            db=db,
            stock_id=stock.id,
            timeframe=target_timeframe,
            start_at=start_at,
            end_at=end_at,
            source=target_source,
            source_type=BarSourceType.DERIVED.value,
        )
        saved = await self.bar_repository.upsert_batch(db, records)
        return MarketDataWriteResult(
            stock_id=stock.id,
            symbol=stock.symbol,
            market=stock.market,
            timeframe=target_timeframe,
            records_written=len(saved),
            source=target_source,
            source_type=BarSourceType.DERIVED.value,
        )

    async def collect_active_stocks_source_bars(
        self,
        db: AsyncSession,
        market: str,
        timeframes: Iterable[str],
        start_at: datetime,
        end_at: datetime,
        limit: int = 100,
    ) -> list[MarketDataWriteResult]:
        stocks = await self.stock_repository.get_active_stocks(
            db,
            market=market,
            limit=limit,
        )
        results = []
        for stock in stocks:
            for timeframe in timeframes:
                try:
                    results.append(
                        await self.collect_source_bars(
                            db=db,
                            stock_id=stock.id,
                            timeframe=timeframe,
                            start_at=start_at,
                            end_at=end_at,
                        )
                    )
                except Exception as exc:
                    results.append(
                        MarketDataWriteResult(
                            stock_id=stock.id,
                            symbol=stock.symbol,
                            market=stock.market,
                            timeframe=timeframe,
                            records_written=0,
                            source=self.storage_source_name(),
                            source_type=BarSourceType.SOURCE.value,
                            errors=[str(exc)],
                        )
                    )
        return results

    def raw_bar_to_record(
        self,
        raw_bar: dict,
        stock_id: int,
        symbol: str,
        market: str,
        timeframe: str,
        source: str,
        quality_status: str = BarQualityStatus.COMPLETE.value,
    ) -> dict:
        timestamp = raw_bar["timestamp"]
        if timeframe in {"1d", "1w"}:
            timestamp = self.normalize_daily_timestamp(timestamp, market)
        return {
            "stock_id": stock_id,
            "symbol": symbol,
            "market": market,
            "timeframe": timeframe,
            "timestamp": timestamp,
            "open_price": Decimal(str(raw_bar["open"])),
            "high_price": Decimal(str(raw_bar["high"])),
            "low_price": Decimal(str(raw_bar["low"])),
            "close_price": Decimal(str(raw_bar["close"])),
            "volume": int(raw_bar.get("volume") or 0),
            "source": self.canonical_source_name(source),
            "source_type": BarSourceType.SOURCE.value,
            "is_adjusted": False,
            "generated_from_timeframe": None,
            "quality_status": quality_status,
        }

    def price_point_to_daily_bar_record(
        self,
        price_point: dict,
        stock_id: int,
        symbol: str,
        market: str,
        source: str,
    ) -> dict:
        timestamp = datetime.combine(
            price_point["date"],
            time.min,
            tzinfo=self.calendar_service.timezone_for_market(market),
        )
        return self.raw_bar_to_record(
            {
                "timestamp": timestamp,
                "open": price_point["open"],
                "high": price_point["high"],
                "low": price_point["low"],
                "close": price_point["close"],
                "volume": price_point.get("volume", 0),
            },
            stock_id=stock_id,
            symbol=symbol,
            market=market,
            timeframe="1d",
            source=source,
        )

    def normalize_daily_timestamp(self, timestamp: datetime, market: str) -> datetime:
        market_tz = self.calendar_service.timezone_for_market(market)
        if timestamp.tzinfo is not None:
            timestamp = timestamp.astimezone(market_tz)
        return datetime.combine(timestamp.date(), time.min, tzinfo=market_tz)

    def orm_bar_to_dto(self, bar) -> MarketDataBarDTO:
        return MarketDataBarDTO(
            stock_id=bar.stock_id,
            timeframe=bar.timeframe,
            timestamp=bar.timestamp,
            open_price=Decimal(bar.open_price),
            high_price=Decimal(bar.high_price),
            low_price=Decimal(bar.low_price),
            close_price=Decimal(bar.close_price),
            volume=int(bar.volume or 0),
            source=bar.source,
            source_type=bar.source_type,
            is_adjusted=bar.is_adjusted,
            generated_from_timeframe=bar.generated_from_timeframe,
            quality_status=bar.quality_status,
        )

    def _timestamp_key(self, timestamp: datetime) -> datetime:
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        return timestamp.astimezone(timezone.utc)

    def storage_source_name(self, source: Optional[str] = None) -> str:
        """Return the canonical source identifier used in market_data_bars."""
        return self.canonical_source_name(
            source or self.price_data_source.get_source_name()
        )

    @staticmethod
    def canonical_source_name(source: str) -> str:
        return "_".join(source.strip().lower().replace("-", "_").split())


def default_market_data_window(days: int = 7) -> tuple[datetime, datetime]:
    end_at = datetime.now().replace(microsecond=0)
    return end_at - timedelta(days=days), end_at
