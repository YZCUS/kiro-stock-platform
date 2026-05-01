"""
Multi-timeframe market data endpoints.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    get_database_session,
    get_market_data_ingestion_service,
    get_market_data_validation_service,
    get_redis_client,
    get_settings,
    get_stock_repository,
)
from app.settings import Settings
from domain.services.market_data_ingestion_service import (
    DERIVED_TIMEFRAME_SOURCES,
    SOURCE_TIMEFRAMES,
    MarketDataIngestionService,
)
from domain.services.market_calendar_service import MarketCalendarService
from domain.services.market_data_validation_service import (
    MarketDataValidationService,
)
from domain.workers import StreamTaskCommand
from infrastructure.workers import RedisStreamTaskQueue

router = APIRouter(prefix="/market-data")

WORKER_STREAMS = {
    "market-data": "market_data_tasks",
    "bar-aggregation": "bar_aggregation_tasks",
    "data-validation": "data_validation_tasks",
}


class MarketDataStockSelector(BaseModel):
    stock_ids: Optional[List[int]] = None
    market: str = Field("TW", pattern="^(TW|US)$")
    limit: int = Field(100, ge=1, le=1000)


class MarketDataCollectRequest(MarketDataStockSelector):
    timeframes: List[str] = Field(default_factory=lambda: ["1d", "5m"])
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    days: int = Field(7, ge=1, le=60)
    enqueue: bool = False


class MarketDataAggregateRequest(MarketDataStockSelector):
    target_timeframes: List[str] = Field(
        default_factory=lambda: ["15m", "30m", "1h", "1w"]
    )
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    days: int = Field(7, ge=1, le=365)
    enqueue: bool = False


class MarketDataValidateRequest(MarketDataStockSelector):
    timeframes: List[str] = Field(
        default_factory=lambda: ["1d", "5m", "15m", "30m", "1h", "1w"]
    )
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    days: int = Field(7, ge=1, le=365)
    source: Optional[str] = None
    enqueue: bool = False
    fail_on_incomplete: bool = False


class MarketDataPipelineRequest(MarketDataStockSelector):
    source_timeframes: List[str] = Field(default_factory=lambda: ["1d", "5m"])
    derived_timeframes: List[str] = Field(
        default_factory=lambda: ["15m", "30m", "1h", "1w"]
    )
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    days: int = Field(7, ge=1, le=60)
    enqueue: bool = False
    fail_on_incomplete: bool = False
    backfill_incomplete_derived: bool = True


@router.post("/collect", response_model=Dict[str, Any])
async def collect_market_data(
    request: MarketDataCollectRequest,
    db: AsyncSession = Depends(get_database_session),
    stock_repo=Depends(get_stock_repository),
    ingestion_service: MarketDataIngestionService = Depends(
        get_market_data_ingestion_service
    ),
    settings: Settings = Depends(get_settings),
    redis_client=Depends(get_redis_client),
):
    """Collect source 1d/5m bars into market_data_bars."""
    try:
        start_at, end_at = _resolve_window(
            request.start_at, request.end_at, request.days, request.market
        )
        stocks = await _resolve_stocks(db, stock_repo, request)
        _validate_source_timeframes(request.timeframes)

        if request.enqueue:
            enqueued = await _enqueue_collect_jobs(
                redis_client, settings, stocks, request.timeframes, start_at, end_at
            )
            return {"success": True, "mode": "enqueue", "enqueued": enqueued}

        results = []
        for stock in stocks:
            for timeframe in request.timeframes:
                try:
                    result = await ingestion_service.collect_source_bars(
                        db=db,
                        stock_id=stock.id,
                        timeframe=timeframe,
                        start_at=start_at,
                        end_at=end_at,
                    )
                    results.append(result.to_dict())
                except Exception as exc:
                    results.append(_error_result(stock, timeframe, str(exc), "source"))

        return _summarize_results("sync", results)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/aggregate", response_model=Dict[str, Any])
async def aggregate_market_data(
    request: MarketDataAggregateRequest,
    db: AsyncSession = Depends(get_database_session),
    stock_repo=Depends(get_stock_repository),
    ingestion_service: MarketDataIngestionService = Depends(
        get_market_data_ingestion_service
    ),
    settings: Settings = Depends(get_settings),
    redis_client=Depends(get_redis_client),
):
    """Aggregate 5m->15m/30m/1h and 1d->1w bars."""
    try:
        start_at, end_at = _resolve_window(
            request.start_at, request.end_at, request.days, request.market
        )
        stocks = await _resolve_stocks(db, stock_repo, request)

        if request.enqueue:
            enqueued = await _enqueue_aggregate_jobs(
                redis_client,
                settings,
                stocks,
                request.target_timeframes,
                start_at,
                end_at,
            )
            return {"success": True, "mode": "enqueue", "enqueued": enqueued}

        results = []
        for stock in stocks:
            for target_timeframe in request.target_timeframes:
                try:
                    result = await ingestion_service.aggregate_derived_bars(
                        db=db,
                        stock_id=stock.id,
                        target_timeframe=target_timeframe,
                        start_at=start_at,
                        end_at=end_at,
                    )
                    results.append(result.to_dict())
                except Exception as exc:
                    results.append(
                        _error_result(stock, target_timeframe, str(exc), "derived")
                    )

        return _summarize_results("sync", results)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/validate", response_model=Dict[str, Any])
async def validate_market_data(
    request: MarketDataValidateRequest,
    db: AsyncSession = Depends(get_database_session),
    stock_repo=Depends(get_stock_repository),
    validation_service: MarketDataValidationService = Depends(
        get_market_data_validation_service
    ),
    settings: Settings = Depends(get_settings),
    redis_client=Depends(get_redis_client),
):
    """Validate completeness and OHLCV integrity for market_data_bars."""
    try:
        start_at, end_at = _resolve_window(
            request.start_at, request.end_at, request.days, request.market
        )
        stocks = await _resolve_stocks(db, stock_repo, request)

        if request.enqueue:
            enqueued = await _enqueue_validation_jobs(
                redis_client,
                settings,
                stocks,
                request.timeframes,
                start_at,
                end_at,
                source=request.source,
                fail_on_incomplete=request.fail_on_incomplete,
            )
            return {"success": True, "mode": "enqueue", "enqueued": enqueued}

        reports = []
        for stock in stocks:
            for timeframe in request.timeframes:
                report = await validation_service.validate_window(
                    db=db,
                    stock_id=stock.id,
                    timeframe=timeframe,
                    start_at=start_at,
                    end_at=end_at,
                    source=request.source,
                )
                reports.append(report.to_dict())

        return {
            "success": all(report["is_complete"] for report in reports),
            "mode": "sync",
            "reports": reports,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/orchestrate", response_model=Dict[str, Any])
async def orchestrate_market_data_pipeline(
    request: MarketDataPipelineRequest,
    db: AsyncSession = Depends(get_database_session),
    stock_repo=Depends(get_stock_repository),
    ingestion_service: MarketDataIngestionService = Depends(
        get_market_data_ingestion_service
    ),
    validation_service: MarketDataValidationService = Depends(
        get_market_data_validation_service
    ),
    settings: Settings = Depends(get_settings),
    redis_client=Depends(get_redis_client),
):
    """Run the complete collect -> aggregate -> validate pipeline."""
    try:
        start_at, end_at = _resolve_window(
            request.start_at, request.end_at, request.days, request.market
        )
        stocks = await _resolve_stocks(db, stock_repo, request)
        _validate_source_timeframes(request.source_timeframes)

        if request.enqueue:
            pipeline_count = await _enqueue_pipeline_jobs(
                redis_client,
                settings,
                stocks,
                request.source_timeframes,
                request.derived_timeframes,
                start_at,
                end_at,
                request.fail_on_incomplete,
                request.backfill_incomplete_derived,
            )
            return {
                "success": True,
                "mode": "enqueue",
                "enqueued": {"pipeline": pipeline_count},
            }

        writes = []
        reports = []
        for stock in stocks:
            for timeframe in request.source_timeframes:
                try:
                    writes.append(
                        (
                            await ingestion_service.collect_source_bars(
                                db=db,
                                stock_id=stock.id,
                                timeframe=timeframe,
                                start_at=start_at,
                                end_at=end_at,
                            )
                        ).to_dict()
                    )
                except Exception as exc:
                    writes.append(_error_result(stock, timeframe, str(exc), "source"))

            for timeframe in request.derived_timeframes:
                try:
                    writes.append(
                        (
                            await ingestion_service.aggregate_derived_bars(
                                db=db,
                                stock_id=stock.id,
                                target_timeframe=timeframe,
                                start_at=start_at,
                                end_at=end_at,
                            )
                        ).to_dict()
                    )
                except Exception as exc:
                    writes.append(_error_result(stock, timeframe, str(exc), "derived"))

            stock_reports = []
            for timeframe in [*request.source_timeframes, *request.derived_timeframes]:
                stock_reports.append(
                    await validation_service.validate_window(
                        db=db,
                        stock_id=stock.id,
                        timeframe=timeframe,
                        start_at=start_at,
                        end_at=end_at,
                        source=_validation_source_for_timeframe(
                            timeframe,
                            ingestion_service,
                        ),
                    )
                )

            if request.backfill_incomplete_derived:
                backfill_results = (
                    await ingestion_service.backfill_incomplete_derived_reports(
                        db=db,
                        reports=stock_reports,
                    )
                )
                writes.extend(result.to_dict() for result in backfill_results)
                if backfill_results:
                    stock_reports = []
                    for timeframe in [
                        *request.source_timeframes,
                        *request.derived_timeframes,
                    ]:
                        stock_reports.append(
                            await validation_service.validate_window(
                                db=db,
                                stock_id=stock.id,
                                timeframe=timeframe,
                                start_at=start_at,
                                end_at=end_at,
                                source=_validation_source_for_timeframe(
                                    timeframe,
                                    ingestion_service,
                                ),
                            )
                        )

            reports.extend(report.to_dict() for report in stock_reports)

        return {
            "success": all(item.get("success") for item in writes)
            and (
                not request.fail_on_incomplete
                or all(report["is_complete"] for report in reports)
            ),
            "mode": "sync",
            "validation_success": all(report["is_complete"] for report in reports),
            "writes": writes,
            "reports": reports,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/completeness", response_model=Dict[str, Any])
async def get_market_data_completeness(
    stock_id: int = Query(...),
    timeframe: str = Query(...),
    start_at: datetime = Query(...),
    end_at: datetime = Query(...),
    source: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_database_session),
    validation_service: MarketDataValidationService = Depends(
        get_market_data_validation_service
    ),
):
    """Read-only completeness report for one stock/timeframe window."""
    try:
        report = await validation_service.validate_window(
            db=db,
            stock_id=stock_id,
            timeframe=timeframe,
            start_at=start_at,
            end_at=end_at,
            source=source,
        )
        return report.to_dict()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def _resolve_window(
    start_at: Optional[datetime],
    end_at: Optional[datetime],
    days: int,
    market: str,
) -> tuple[datetime, datetime]:
    if start_at is not None and end_at is not None:
        return start_at, end_at
    calendar = MarketCalendarService()
    market_tz = calendar.timezone_for_market(market)
    now = datetime.now(market_tz)
    session = calendar._session_for_market(market)
    end_date = now.date()
    if now.time() >= session.close_time:
        end_date = end_date + timedelta(days=1)
    resolved_end = datetime.combine(end_date, datetime.min.time(), tzinfo=market_tz)
    resolved_start = resolved_end - timedelta(days=days)
    return start_at or resolved_start, end_at or resolved_end


async def _resolve_stocks(db, stock_repo, selector: MarketDataStockSelector):
    if selector.stock_ids:
        stocks = []
        for stock_id in selector.stock_ids:
            stock = await stock_repo.get(db, stock_id)
            if stock is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Stock {stock_id} not found",
                )
            stocks.append(stock)
        return stocks
    stocks = await stock_repo.get_active_stocks(
        db,
        market=selector.market,
        limit=selector.limit,
    )
    if not stocks:
        raise HTTPException(status_code=404, detail="No active stocks found")
    return stocks


def _validate_source_timeframes(timeframes: List[str]) -> None:
    unsupported = [
        timeframe for timeframe in timeframes if timeframe not in SOURCE_TIMEFRAMES
    ]
    if unsupported:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported source timeframes: {unsupported}",
        )


def _validation_source_for_timeframe(
    timeframe: str,
    ingestion_service: MarketDataIngestionService,
) -> Optional[str]:
    if timeframe in SOURCE_TIMEFRAMES:
        return ingestion_service.storage_source_name()
    return None


async def _enqueue_collect_jobs(
    redis_client,
    settings: Settings,
    stocks,
    timeframes: List[str],
    start_at: datetime,
    end_at: datetime,
) -> int:
    queue = _build_queue(redis_client, settings, "market-data")
    enqueued = 0
    for stock in stocks:
        for timeframe in timeframes:
            await queue.enqueue(
                StreamTaskCommand(
                    task_type="collect_bars",
                    payload={
                        "stock_id": stock.id,
                        "symbol": stock.symbol,
                        "market": stock.market,
                        "timeframe": timeframe,
                        "start_at": start_at.isoformat(),
                        "end_at": end_at.isoformat(),
                    },
                    idempotency_key=(
                        f"collect:{stock.id}:{timeframe}:"
                        f"{start_at.isoformat()}:{end_at.isoformat()}"
                    ),
                )
            )
            enqueued += 1
    return enqueued


async def _enqueue_pipeline_jobs(
    redis_client,
    settings: Settings,
    stocks,
    source_timeframes: List[str],
    derived_timeframes: List[str],
    start_at: datetime,
    end_at: datetime,
    fail_on_incomplete: bool = False,
    backfill_incomplete_derived: bool = True,
) -> int:
    queue = _build_queue(redis_client, settings, "market-data")
    enqueued = 0
    for stock in stocks:
        await queue.enqueue(
            StreamTaskCommand(
                task_type="orchestrate_pipeline",
                payload={
                    "stock_id": stock.id,
                    "symbol": stock.symbol,
                    "market": stock.market,
                    "source_timeframes": source_timeframes,
                    "derived_timeframes": derived_timeframes,
                    "start_at": start_at.isoformat(),
                    "end_at": end_at.isoformat(),
                    "fail_on_incomplete": fail_on_incomplete,
                    "backfill_incomplete_derived": backfill_incomplete_derived,
                },
                idempotency_key=(
                    f"pipeline:{stock.id}:"
                    f"{start_at.isoformat()}:{end_at.isoformat()}"
                ),
            )
        )
        enqueued += 1
    return enqueued


async def _enqueue_aggregate_jobs(
    redis_client,
    settings: Settings,
    stocks,
    target_timeframes: List[str],
    start_at: datetime,
    end_at: datetime,
) -> int:
    queue = _build_queue(redis_client, settings, "bar-aggregation")
    enqueued = 0
    for stock in stocks:
        for target_timeframe in target_timeframes:
            source_timeframe = DERIVED_TIMEFRAME_SOURCES.get(target_timeframe)
            if source_timeframe is None:
                continue
            await queue.enqueue(
                StreamTaskCommand(
                    task_type="aggregate_bars",
                    payload={
                        "stock_id": stock.id,
                        "symbol": stock.symbol,
                        "market": stock.market,
                        "source_timeframe": source_timeframe,
                        "target_timeframe": target_timeframe,
                        "start_at": start_at.isoformat(),
                        "end_at": end_at.isoformat(),
                    },
                    idempotency_key=(
                        f"aggregate:{stock.id}:{source_timeframe}:"
                        f"{target_timeframe}:"
                        f"{start_at.isoformat()}:{end_at.isoformat()}"
                    ),
                )
            )
            enqueued += 1
    return enqueued


async def _enqueue_validation_jobs(
    redis_client,
    settings: Settings,
    stocks,
    timeframes: List[str],
    start_at: datetime,
    end_at: datetime,
    source: Optional[str] = None,
    fail_on_incomplete: bool = False,
) -> int:
    queue = _build_queue(redis_client, settings, "data-validation")
    enqueued = 0
    for stock in stocks:
        for timeframe in timeframes:
            await queue.enqueue(
                StreamTaskCommand(
                    task_type="validate_bars",
                    payload={
                        "stock_id": stock.id,
                        "symbol": stock.symbol,
                        "market": stock.market,
                        "timeframe": timeframe,
                        "start_at": start_at.isoformat(),
                        "end_at": end_at.isoformat(),
                        "source": source,
                        "fail_on_incomplete": fail_on_incomplete,
                    },
                    idempotency_key=(
                        f"validate:{stock.id}:{timeframe}:"
                        f"{start_at.isoformat()}:{end_at.isoformat()}"
                    ),
                )
            )
            enqueued += 1
    return enqueued


def _build_queue(redis_client, settings: Settings, worker_type: str):
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Redis is unavailable")
    stream_name = WORKER_STREAMS[worker_type]
    return RedisStreamTaskQueue(
        redis_client=redis_client,
        stream_name=stream_name,
        consumer_group=f"{worker_type}_workers",
        consumer_name=settings.order_execution_queue.consumer_name,
        dead_letter_stream=f"{stream_name}_dead",
        max_attempts=settings.order_execution_queue.max_attempts,
        pending_idle_ms=settings.order_execution_queue.pending_idle_ms,
    )


def _summarize_results(mode: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "success": all(item.get("success") for item in results),
        "mode": mode,
        "total_tasks": len(results),
        "success_count": sum(1 for item in results if item.get("success")),
        "error_count": sum(1 for item in results if not item.get("success")),
        "total_records": sum(int(item.get("records_written") or 0) for item in results),
        "results": results,
    }


def _error_result(
    stock,
    timeframe: str,
    error: str,
    source_type: str,
) -> Dict[str, Any]:
    return {
        "stock_id": stock.id,
        "symbol": stock.symbol,
        "market": stock.market,
        "timeframe": timeframe,
        "records_written": 0,
        "source": "unknown",
        "source_type": source_type,
        "success": False,
        "errors": [error],
    }
