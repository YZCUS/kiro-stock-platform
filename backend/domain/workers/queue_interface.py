"""
Generic worker queue interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from domain.workers.task_models import StreamTaskCommand


class IStreamTaskQueue(ABC):
    """Queue port for background worker task commands."""

    @abstractmethod
    async def enqueue(self, command: StreamTaskCommand) -> None:
        """Publish a task command."""
        pass

    @abstractmethod
    async def dequeue(
        self, timeout: Optional[float] = None
    ) -> Optional[StreamTaskCommand]:
        """Fetch the next task command, or return None when timeout expires."""
        pass

    @abstractmethod
    async def ack(self, command: StreamTaskCommand) -> None:
        """Acknowledge successful task processing."""
        pass

    @abstractmethod
    async def fail(self, command: StreamTaskCommand, error: Exception) -> None:
        """Record task failure and apply retry/dead-letter policy."""
        pass
