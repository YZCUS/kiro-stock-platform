"""
Order execution worker service.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.settings import Settings
from domain.brokers import IBrokerAdapter
from domain.execution import IOrderExecutionQueue, OrderExecutionCommand
from domain.models.order_intent import BrokerOrder, OrderIntent
from domain.services.order_intent_service import OrderIntentService


class OrderExecutionWorker:
    """Consumes queued order commands and performs broker execution."""

    def __init__(self, order_intent_service: Optional[OrderIntentService] = None):
        self.order_intent_service = order_intent_service or OrderIntentService()

    async def process_next(
        self,
        db: AsyncSession,
        execution_queue: IOrderExecutionQueue,
        broker: IBrokerAdapter,
        settings: Settings,
        timeout: Optional[float] = 0,
    ) -> Optional[tuple[OrderIntent, BrokerOrder]]:
        command = await execution_queue.dequeue(timeout=timeout)
        if command is None:
            return None
        try:
            result = await self.process_command(db, command, broker, settings)
        except Exception as exc:
            await execution_queue.fail(command, exc)
            raise

        await execution_queue.ack(command)
        return result

    async def process_command(
        self,
        db: AsyncSession,
        command: OrderExecutionCommand,
        broker: IBrokerAdapter,
        settings: Settings,
    ) -> tuple[OrderIntent, BrokerOrder]:
        return await self.order_intent_service.execute_order_intent(
            db=db,
            user_id=command.user_id,
            intent_id=command.order_intent_id,
            broker=broker,
            settings=settings,
        )
