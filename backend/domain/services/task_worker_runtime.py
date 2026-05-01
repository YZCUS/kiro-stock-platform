"""
Generic task worker runtime.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.settings import Settings
from domain.workers import IStreamTaskQueue, StreamTaskCommand

logger = logging.getLogger(__name__)


class ITaskHandler(Protocol):
    """Handler contract used by generic background workers."""

    async def handle(
        self,
        db: AsyncSession,
        command: StreamTaskCommand,
        settings: Settings,
    ) -> None:
        """Process a task command."""


class TaskWorkerRuntime:
    """Consumes generic stream tasks with ack/retry/dead-letter semantics."""

    def __init__(self, queue: IStreamTaskQueue, handler: ITaskHandler):
        self.queue = queue
        self.handler = handler

    async def process_next(
        self,
        db: AsyncSession,
        settings: Settings,
        timeout: Optional[float] = 0,
    ) -> bool:
        command = await self.queue.dequeue(timeout=timeout)
        if command is None:
            return False

        try:
            await self.handler.handle(db, command, settings)
        except Exception as exc:
            await self.queue.fail(command, exc)
            raise

        await self.queue.ack(command)
        return True

    async def run_forever(
        self,
        session_factory,
        settings: Settings,
        timeout: float = 5.0,
        idle_sleep_seconds: float = 1.0,
    ) -> None:
        while True:
            async with session_factory() as db:
                try:
                    processed = await self.process_next(
                        db=db,
                        settings=settings,
                        timeout=timeout,
                    )
                except Exception:
                    await db.rollback()
                    logger.exception("Task worker command failed")
                    processed = True

            if not processed:
                await asyncio.sleep(idle_sleep_seconds)
