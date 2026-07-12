"""
Order execution worker service.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.settings import Settings
from domain.brokers import BrokerConnectionError, BrokerError, IBrokerAdapter
from domain.execution import (
    IOrderExecutionQueue,
    OrderExecutionCommand,
    OrderQueueFailureDisposition,
)
from domain.models.order_intent import BrokerOrder, OrderIntent
from domain.services.order_intent_service import (
    OrderExecutionClaimBusy,
    OrderExecutionNotExecutable,
    OrderExecutionReconciliationRequired,
    OrderIntentService,
)


class OrderExecutionWorker:
    """Consumes queued order commands and performs broker execution."""

    def __init__(self, order_intent_service: Optional[OrderIntentService] = None):
        self.order_intent_service = order_intent_service or OrderIntentService()
        self._last_recovery_scan: Optional[float] = None

    async def process_next(
        self,
        db: AsyncSession,
        execution_queue: IOrderExecutionQueue,
        broker: IBrokerAdapter,
        settings: Settings,
        timeout: Optional[float] = 0,
    ) -> Optional[tuple[OrderIntent, BrokerOrder]]:
        await self._recover_stale_commands_if_due(db, execution_queue)
        command = await execution_queue.dequeue(timeout=timeout)
        if command is None:
            return None
        if command.metadata.get("reconciliation_required"):
            try:
                await self.order_intent_service.mark_execution_reconciliation_required(
                    db=db,
                    user_id=command.user_id,
                    intent_id=command.order_intent_id,
                    error=OrderExecutionReconciliationRequired(
                        str(
                            command.metadata.get("reconciliation_error")
                            or "Order reconciliation required"
                        ),
                        broker_order_ref=command.metadata.get("broker_order_ref"),
                    ),
                )
            except Exception:
                await self._rollback_safely(db)
                # Keep this non-executable marker pending for XAUTOCLAIM. It must
                # never fall back into the broker execution path.
                raise
            await execution_queue.ack(command)
            return None
        try:
            result = await self.process_command(db, command, broker, settings)
        except OrderExecutionReconciliationRequired as exc:
            await self._rollback_safely(db)
            try:
                await self.order_intent_service.mark_execution_reconciliation_required(
                    db=db,
                    user_id=command.user_id,
                    intent_id=command.order_intent_id,
                    error=exc,
                )
            except Exception:
                await self._rollback_safely(db)
                await execution_queue.quarantine(command, exc)
                raise
            await execution_queue.ack(command)
            raise
        except BrokerConnectionError as exc:
            await self._rollback_safely(db)
            durable_attempt = int(
                getattr(exc, "attempt_count", command.attempt) or command.attempt
            )
            failure_command = replace(
                command,
                attempt=max(command.attempt, durable_attempt),
            )
            disposition = await execution_queue.fail(failure_command, exc)
            await self._mark_if_dead_lettered(
                db, execution_queue, failure_command, exc, disposition
            )
            raise
        except OrderExecutionClaimBusy:
            # The owning worker may still be inside its bounded broker call.
            # Leave this delivery pending; XAUTOCLAIM can retry after the lease.
            await self._rollback_safely(db)
            return None
        except OrderExecutionNotExecutable:
            # A durable outbox may publish twice if the process dies after XADD
            # but before recording dispatch. The intent row is the execution
            # fence, so a command observed after finalization is safe to discard.
            await self._rollback_safely(db)
            await execution_queue.ack(command)
            return None
        except BrokerError:
            # Configuration errors and explicit broker rejections are terminal.
            await execution_queue.ack(command)
            raise
        except Exception as exc:
            await self._rollback_safely(db)
            disposition = await execution_queue.fail(command, exc)
            await self._mark_if_dead_lettered(
                db, execution_queue, command, exc, disposition
            )
            raise

        await execution_queue.ack(command)
        return result

    async def _recover_stale_commands_if_due(
        self,
        db: AsyncSession,
        execution_queue: IOrderExecutionQueue,
    ) -> None:
        now = asyncio.get_running_loop().time()
        if self._last_recovery_scan is not None and now - self._last_recovery_scan < 30:
            return None

        reconcile_expired = getattr(
            self.order_intent_service,
            "reconcile_expired_execution_leases",
            None,
        )
        if reconcile_expired is not None:
            await reconcile_expired(db=db)

        recover = getattr(
            self.order_intent_service, "recover_queued_order_intents", None
        )
        if recover is None:
            self._last_recovery_scan = now
            return None
        recovered = await recover(
            db=db,
            execution_queue=execution_queue,
        )
        # A full one-row claim may indicate more backlog. Scan again on the next
        # loop; only rate-limit after finding no publishable outbox row.
        self._last_recovery_scan = None if recovered else now

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

    async def _mark_if_dead_lettered(
        self,
        db: AsyncSession,
        execution_queue: IOrderExecutionQueue,
        command: OrderExecutionCommand,
        error: Exception,
        disposition: Optional[OrderQueueFailureDisposition],
    ) -> None:
        if disposition != OrderQueueFailureDisposition.DEAD_LETTERED:
            return
        try:
            await self.order_intent_service.mark_execution_reconciliation_required(
                db=db,
                user_id=command.user_id,
                intent_id=command.order_intent_id,
                error=error,
            )
        except Exception:
            await self._rollback_safely(db)
            await execution_queue.quarantine(command, error)
            raise
        # Keep the active message pending until the durable order state is fenced.
        # If either this ACK or the process fails, redelivery sees REQUIRES_REVIEW
        # and is safely discarded without another broker call.
        await execution_queue.ack(command)

    async def _rollback_safely(self, db: AsyncSession) -> None:
        rollback = getattr(db, "rollback", None)
        if rollback is not None:
            await rollback()
