"""
In-process order execution queue.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional

from domain.execution import IOrderExecutionQueue, OrderExecutionCommand


class InMemoryOrderExecutionQueue(IOrderExecutionQueue):
    """Process-local queue for development and tests.

    Production deployments can replace this adapter with Redis Streams, a DB outbox,
    or a managed message broker without changing the domain service contract.
    """

    def __init__(self, max_attempts: int = 3) -> None:
        self._queue: asyncio.Queue[OrderExecutionCommand] = asyncio.Queue()
        self.max_attempts = max_attempts

    async def enqueue(self, command: OrderExecutionCommand) -> None:
        await self._queue.put(command)

    async def dequeue(
        self, timeout: Optional[float] = None
    ) -> Optional[OrderExecutionCommand]:
        if timeout is None:
            return await self._queue.get()

        if timeout <= 0:
            try:
                return self._queue.get_nowait()
            except asyncio.QueueEmpty:
                return None

        try:
            return await asyncio.wait_for(self._queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    @property
    def size(self) -> int:
        return self._queue.qsize()

    async def ack(self, command: OrderExecutionCommand) -> None:
        return None

    async def fail(self, command: OrderExecutionCommand, error: Exception) -> None:
        if command.attempt >= self.max_attempts:
            return None

        retry_metadata = {
            **command.metadata,
            "last_error": str(error),
            "last_failed_at": datetime.now(timezone.utc).isoformat(),
        }
        await self.enqueue(
            OrderExecutionCommand(
                order_intent_id=command.order_intent_id,
                user_id=command.user_id,
                idempotency_key=command.idempotency_key,
                attempt=command.attempt + 1,
                metadata=retry_metadata,
            )
        )
