"""
Order execution queue interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from domain.execution.execution_models import OrderExecutionCommand


class IOrderExecutionQueue(ABC):
    """Queue port for broker execution commands."""

    @abstractmethod
    async def enqueue(self, command: OrderExecutionCommand) -> None:
        """Publish a command for asynchronous broker execution."""
        pass

    @abstractmethod
    async def dequeue(
        self, timeout: Optional[float] = None
    ) -> Optional[OrderExecutionCommand]:
        """Fetch the next command, or return None when timeout expires."""
        pass

    @abstractmethod
    async def ack(self, command: OrderExecutionCommand) -> None:
        """Acknowledge successful command processing."""
        pass

    @abstractmethod
    async def fail(self, command: OrderExecutionCommand, error: Exception) -> None:
        """Record command failure and apply retry/dead-letter policy."""
        pass
