"""
Order execution queue interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional

from domain.execution.execution_models import OrderExecutionCommand


class OrderQueueFailureDisposition(str, Enum):
    """Durable result of applying the queue retry policy."""

    REQUEUED = "requeued"
    DEAD_LETTERED = "dead_lettered"


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
    async def fail(
        self, command: OrderExecutionCommand, error: Exception
    ) -> OrderQueueFailureDisposition:
        """Apply retry policy and report whether durable DB fencing is required."""
        pass

    @abstractmethod
    async def quarantine(
        self, command: OrderExecutionCommand, error: Exception
    ) -> None:
        """Replace an executable command with reconciliation-only work."""
        pass
