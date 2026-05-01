"""
Run long-lived background workers.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal

from app.dependencies import (
    get_broker_adapter,
    get_order_execution_queue,
    get_order_execution_worker,
    get_redis_client,
)
from app.settings import get_settings
from core.database import AsyncSessionLocal
from domain.services.market_data_access_service import MarketDataAccessService
from domain.services.task_worker_runtime import TaskWorkerRuntime
from domain.services.worker_task_handlers import (
    BarAggregationTaskHandler,
    DataValidationTaskHandler,
    LoggingTaskHandler,
    MarketDataTaskHandler,
    StrategyTaskHandler,
)
from infrastructure.persistence.market_data_bar_repository import (
    MarketDataBarRepository,
)
from infrastructure.workers import RedisStreamTaskQueue

# Importing this package registers built-in strategies.
import domain.strategies  # noqa: F401

logger = logging.getLogger(__name__)


WORKER_STREAMS = {
    "market-data": "market_data_tasks",
    "bar-aggregation": "bar_aggregation_tasks",
    "data-validation": "data_validation_tasks",
    "indicator": "indicator_tasks",
    "strategy": "strategy_tasks",
    "broker-sync": "broker_sync_tasks",
    "notification": "notification_tasks",
}


async def run_order_execution_worker(stop_event: asyncio.Event) -> None:
    settings = get_settings()
    queue = get_order_execution_queue()
    broker = get_broker_adapter(settings)
    worker = get_order_execution_worker()

    if AsyncSessionLocal is None:
        raise RuntimeError("Database session factory is unavailable")

    while not stop_event.is_set():
        async with AsyncSessionLocal() as db:
            try:
                processed = await worker.process_next(
                    db=db,
                    execution_queue=queue,
                    broker=broker,
                    settings=settings,
                    timeout=5,
                )
            except Exception:
                await db.rollback()
                logger.exception("Order execution command failed")
                processed = True

        if not processed:
            await asyncio.sleep(1)


async def run_generic_worker(worker_type: str, stop_event: asyncio.Event) -> None:
    settings = get_settings()
    redis_client = get_redis_client(settings)
    if redis_client is None:
        raise RuntimeError("Redis is required for background workers")
    if AsyncSessionLocal is None:
        raise RuntimeError("Database session factory is unavailable")

    stream_name = WORKER_STREAMS[worker_type]
    queue = RedisStreamTaskQueue(
        redis_client=redis_client,
        stream_name=stream_name,
        consumer_group=f"{worker_type}_workers",
        consumer_name=settings.order_execution_queue.consumer_name,
        dead_letter_stream=f"{stream_name}_dead",
        max_attempts=settings.order_execution_queue.max_attempts,
        pending_idle_ms=settings.order_execution_queue.pending_idle_ms,
    )
    handler = build_handler(worker_type)
    runtime = TaskWorkerRuntime(queue=queue, handler=handler)

    while not stop_event.is_set():
        async with AsyncSessionLocal() as db:
            try:
                processed = await runtime.process_next(
                    db=db,
                    settings=settings,
                    timeout=5,
                )
            except Exception:
                await db.rollback()
                logger.exception("%s worker task failed", worker_type)
                processed = True

        if not processed:
            await asyncio.sleep(1)


def build_handler(worker_type: str):
    if worker_type == "market-data":
        from infrastructure.external.price_data_sources import create_price_data_source
        from infrastructure.persistence.stock_repository import StockRepository
        from domain.services.market_data_ingestion_service import (
            MarketDataIngestionService,
        )
        from domain.services.market_data_validation_service import (
            MarketDataValidationService,
        )

        settings = get_settings()
        stock_repo = StockRepository(db_session=None)
        bar_repo = MarketDataBarRepository()
        return MarketDataTaskHandler(
            ingestion_service=MarketDataIngestionService(
                stock_repository=stock_repo,
                bar_repository=bar_repo,
                price_data_source=create_price_data_source(
                    settings.external_api.price_data_source
                ),
            ),
            validation_service=MarketDataValidationService(
                stock_repository=stock_repo,
                bar_repository=bar_repo,
            ),
        )
    if worker_type == "bar-aggregation":
        return BarAggregationTaskHandler(MarketDataBarRepository())
    if worker_type == "data-validation":
        from infrastructure.persistence.stock_repository import StockRepository
        from domain.services.market_data_validation_service import (
            MarketDataValidationService,
        )

        return DataValidationTaskHandler(
            MarketDataValidationService(
                stock_repository=StockRepository(db_session=None),
                bar_repository=MarketDataBarRepository(),
            )
        )
    if worker_type == "strategy":
        repo = MarketDataBarRepository()
        return StrategyTaskHandler(MarketDataAccessService(repo))
    return LoggingTaskHandler(worker_type)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run a backend background worker")
    parser.add_argument(
        "worker_type",
        choices=["order-execution", *WORKER_STREAMS.keys()],
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    stop_event = asyncio.Event()

    def request_stop() -> None:
        logger.info("Stopping %s worker", args.worker_type)
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, request_stop)

    logger.info("Starting %s worker", args.worker_type)
    if args.worker_type == "order-execution":
        await run_order_execution_worker(stop_event)
    else:
        await run_generic_worker(args.worker_type, stop_event)


if __name__ == "__main__":
    asyncio.run(main())
