"""
Background worker task handlers.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.settings import Settings
from domain.market_data import MarketDataBarDTO
from domain.repositories.market_data_bar_repository_interface import (
    IMarketDataBarRepository,
)
from domain.services.bar_aggregation_service import BarAggregationService
from domain.services.market_data_ingestion_service import MarketDataIngestionService
from domain.services.market_data_validation_service import MarketDataValidationService
from domain.services.market_data_access_service import (
    MarketDataAccessService,
    MarketDataRequirement,
)
from domain.strategies import strategy_registry
from domain.strategies.strategy_interface import StrategyType
from domain.workers import StreamTaskCommand

logger = logging.getLogger(__name__)


class LoggingTaskHandler:
    """Placeholder handler for worker types whose business logic is not enabled yet."""

    def __init__(self, worker_type: str):
        self.worker_type = worker_type

    async def handle(
        self,
        db: AsyncSession,
        command: StreamTaskCommand,
        settings: Settings,
    ) -> None:
        logger.info(
            "Handled %s task type=%s idempotency_key=%s",
            self.worker_type,
            command.task_type,
            command.idempotency_key,
        )


class BarAggregationTaskHandler:
    """Aggregates bars from one timeframe into another and persists the result."""

    def __init__(
        self,
        bar_repository: IMarketDataBarRepository,
        aggregation_service: Optional[BarAggregationService] = None,
    ) -> None:
        self.bar_repository = bar_repository
        self.aggregation_service = aggregation_service or BarAggregationService()

    async def handle(
        self,
        db: AsyncSession,
        command: StreamTaskCommand,
        settings: Settings,
    ) -> None:
        payload = command.payload
        stock_id = int(payload["stock_id"])
        symbol = payload["symbol"]
        market = payload["market"]
        source_timeframe = payload["source_timeframe"]
        target_timeframe = payload["target_timeframe"]
        start_at = _parse_datetime(payload.get("start_at"))
        end_at = _parse_datetime(payload.get("end_at"))
        source = payload.get("source")

        source_bars = await self.bar_repository.get_bars(
            db=db,
            stock_id=stock_id,
            timeframe=source_timeframe,
            start_at=start_at,
            end_at=end_at,
            source=source,
            limit=int(payload.get("limit", 5000)),
            ascending=True,
        )
        dto_bars = [
            MarketDataBarDTO(
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
            for bar in source_bars
        ]
        aggregated = self.aggregation_service.aggregate(
            dto_bars,
            target_timeframe=target_timeframe,
            source=payload.get("target_source", "internal_aggregation"),
            market=market,
        )
        records = self.aggregation_service.to_record_dicts(
            aggregated,
            symbol=symbol,
            market=market,
        )
        target_source = payload.get("target_source", "internal_aggregation")
        await self.bar_repository.delete_window(
            db=db,
            stock_id=stock_id,
            timeframe=target_timeframe,
            start_at=start_at,
            end_at=end_at,
            source=target_source,
            source_type="derived",
        )
        await self.bar_repository.upsert_batch(db, records)


class MarketDataTaskHandler:
    """Fetches source market data bars and persists them."""

    def __init__(
        self,
        ingestion_service: MarketDataIngestionService,
        validation_service: Optional[MarketDataValidationService] = None,
    ) -> None:
        self.ingestion_service = ingestion_service
        self.validation_service = validation_service

    async def handle(
        self,
        db: AsyncSession,
        command: StreamTaskCommand,
        settings: Settings,
    ) -> None:
        payload = command.payload
        task_type = command.task_type
        if task_type in {"collect_bars", "ingest_bars"}:
            result = await self.ingestion_service.collect_source_bars(
                db=db,
                stock_id=int(payload["stock_id"]),
                timeframe=payload["timeframe"],
                start_at=_parse_datetime(payload["start_at"]),
                end_at=_parse_datetime(payload["end_at"]),
                source=payload.get("source"),
            )
            logger.info(
                "Collected %s %s bars for %s",
                result.records_written,
                result.timeframe,
                result.symbol,
            )
            return None

        if task_type == "orchestrate_pipeline":
            await self._handle_pipeline(db, payload)
            return None

        else:
            raise ValueError(f"Unsupported market data task: {task_type}")

    async def _handle_pipeline(self, db: AsyncSession, payload: dict) -> None:
        if self.validation_service is None:
            raise RuntimeError("Pipeline task requires validation service")

        stock_id = int(payload["stock_id"])
        start_at = _parse_datetime(payload["start_at"])
        end_at = _parse_datetime(payload["end_at"])

        source_timeframes = payload.get("source_timeframes", ["1d", "5m"])
        derived_timeframes = payload.get(
            "derived_timeframes", ["15m", "30m", "1h", "1w"]
        )

        for timeframe in source_timeframes:
            await self.ingestion_service.collect_source_bars(
                db=db,
                stock_id=stock_id,
                timeframe=timeframe,
                start_at=start_at,
                end_at=end_at,
                source=payload.get("source"),
            )

        for target_timeframe in derived_timeframes:
            await self.ingestion_service.aggregate_derived_bars(
                db=db,
                stock_id=stock_id,
                target_timeframe=target_timeframe,
                start_at=start_at,
                end_at=end_at,
            )

        reports = []
        for timeframe in [*source_timeframes, *derived_timeframes]:
            reports.append(
                await self.validation_service.validate_window(
                    db=db,
                    stock_id=stock_id,
                    timeframe=timeframe,
                    start_at=start_at,
                    end_at=end_at,
                    source=(
                        self.ingestion_service.storage_source_name(
                            payload.get("source")
                        )
                        if timeframe in source_timeframes
                        else None
                    ),
                )
            )

        if payload.get("backfill_incomplete_derived", True):
            backfilled = (
                await self.ingestion_service.backfill_incomplete_derived_reports(
                    db=db,
                    reports=reports,
                )
            )
            if backfilled:
                reports = []
                for timeframe in [*source_timeframes, *derived_timeframes]:
                    reports.append(
                        await self.validation_service.validate_window(
                            db=db,
                            stock_id=stock_id,
                            timeframe=timeframe,
                            start_at=start_at,
                            end_at=end_at,
                            source=(
                                self.ingestion_service.storage_source_name(
                                    payload.get("source")
                                )
                                if timeframe in source_timeframes
                                else None
                            ),
                        )
                    )

        for report in reports:
            if (
                not report.is_complete
                and payload.get("fail_on_incomplete", False)
            ):
                raise ValueError(f"Market data incomplete: {report.to_dict()}")


class DataValidationTaskHandler:
    """Runs market data completeness validation."""

    def __init__(self, validation_service: MarketDataValidationService) -> None:
        self.validation_service = validation_service

    async def handle(
        self,
        db: AsyncSession,
        command: StreamTaskCommand,
        settings: Settings,
    ) -> None:
        payload = command.payload
        report = await self.validation_service.validate_window(
            db=db,
            stock_id=int(payload["stock_id"]),
            timeframe=payload["timeframe"],
            start_at=_parse_datetime(payload["start_at"]),
            end_at=_parse_datetime(payload["end_at"]),
            source=payload.get("source"),
        )
        if not report.is_complete and payload.get("fail_on_incomplete", True):
            raise ValueError(f"Market data incomplete: {report.to_dict()}")
        logger.info("Market data validation report: %s", report.to_dict())


class StrategyTaskHandler:
    """Validates strategy data readiness before strategy execution."""

    def __init__(self, market_data_access: MarketDataAccessService):
        self.market_data_access = market_data_access

    async def handle(
        self,
        db: AsyncSession,
        command: StreamTaskCommand,
        settings: Settings,
    ) -> None:
        payload = command.payload
        stock_id = int(payload["stock_id"])
        strategy_type = StrategyType(payload["strategy_type"])
        strategy = strategy_registry.get_strategy(strategy_type)
        if strategy is None:
            raise ValueError(f"Strategy is not registered: {strategy_type}")

        spec = strategy.get_spec()
        requirements = [
            MarketDataRequirement(
                stock_id=stock_id,
                timeframe=timeframe,
                lookback_bars=spec.lookback_bars[timeframe],
                source=payload.get("source"),
            )
            for timeframe in spec.required_timeframes
        ]
        availability = await self.market_data_access.check_availability(
            db,
            requirements,
        )
        missing = [
            item
            for item in availability.values()
            if not item.is_satisfied
        ]
        if missing:
            details = ", ".join(
                f"{item.requirement.timeframe}:{item.available_bars}/"
                f"{item.requirement.lookback_bars}"
                for item in missing
            )
            raise ValueError(f"Insufficient market data for strategy: {details}")

        logger.info(
            "Strategy %s data requirements satisfied for stock_id=%s",
            strategy_type.value,
            stock_id,
        )


def _parse_datetime(value) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))
