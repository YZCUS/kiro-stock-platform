"""
下單意圖服務
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.settings import Settings
from domain.brokers import (
    BrokerConnectionError,
    BrokerError,
    BrokerOrderRejected,
    BrokerOrderRequest,
    BrokerOrderStatus,
    IBrokerAdapter,
)
from domain.execution import IOrderExecutionQueue, OrderExecutionCommand
from domain.models.broker import BrokerConnection
from domain.models.order_intent import (
    BrokerOrder,
    OrderEvent,
    OrderExecution,
    OrderIntent,
)
from domain.market_data.daily_prices import fetch_latest_daily_price
from domain.models.risk import RiskCheckResult
from domain.models.stock import Stock
from domain.models.transaction import Transaction
from domain.models.user_portfolio import UserPortfolio
from domain.orders import (
    OrderIntentRequest,
    OrderIntentStatus,
    OrderSide,
    OrderType,
    TimeInForce,
)
from domain.risk import IRiskEngine, RiskContext, RiskDecision


class OrderExecutionNotExecutable(ValueError):
    """A duplicate or stale command whose intent is no longer executable."""

    def __init__(self, status: str):
        self.status = status
        super().__init__(f"Order intent must be queued before execution, got {status}")


class OrderExecutionRetryable(BrokerConnectionError):
    """Ambiguous broker failure with a durable per-intent attempt count."""

    def __init__(self, message: str, attempt_count: int):
        self.attempt_count = attempt_count
        super().__init__(message)


class OrderExecutionReconciliationRequired(RuntimeError):
    """The broker replied, but the local order ledger could not be finalized."""

    def __init__(self, message: str, broker_order_ref: Optional[str] = None):
        self.broker_order_ref = broker_order_ref
        super().__init__(message)


class OrderExecutionClaimBusy(RuntimeError):
    """Another worker owns an unexpired durable broker-submission lease."""


class OrderIntentService:
    """管理策略/使用者下單意圖、風控評估與 broker 送單。"""

    _EXECUTION_LOCKED_STATUSES = {
        OrderIntentStatus.QUEUED_FOR_EXECUTION.value,
        OrderIntentStatus.SUBMITTING.value,
        OrderIntentStatus.SUBMITTED.value,
        OrderIntentStatus.PARTIALLY_FILLED.value,
        OrderIntentStatus.FILLED.value,
        OrderIntentStatus.CANCELLED.value,
        OrderIntentStatus.REJECTED.value,
        OrderIntentStatus.FAILED.value,
        OrderIntentStatus.REQUIRES_REVIEW.value,
    }

    _EXECUTABLE_STATUSES = {
        OrderIntentStatus.QUEUED_FOR_EXECUTION.value,
        OrderIntentStatus.RISK_APPROVED.value,
    }

    async def create_order_intent(
        self, db: AsyncSession, request: OrderIntentRequest
    ) -> OrderIntent:
        request.validate()

        stock = await db.get(Stock, request.stock_id)
        if stock is None:
            raise ValueError(f"Stock not found: {request.stock_id}")

        intent = OrderIntent(
            user_id=request.user_id,
            stock_id=request.stock_id,
            strategy_signal_id=request.strategy_signal_id,
            broker_account_id=request.broker_account_id,
            side=request.side.value,
            order_type=request.order_type.value,
            time_in_force=request.time_in_force.value,
            quantity=request.quantity,
            limit_price=request.limit_price,
            stop_price=request.stop_price,
            notional=request.notional,
            status=OrderIntentStatus.DRAFT.value,
            source=request.source,
            idempotency_key=request.idempotency_key or str(uuid4()),
            client_order_id=str(uuid4()),
            reason=request.reason,
            metadata_json=request.metadata,
            expires_at=request.expires_at,
        )
        db.add(intent)
        await db.commit()
        await db.refresh(intent)
        return intent

    async def get_user_order_intent(
        self,
        db: AsyncSession,
        user_id: UUID,
        intent_id: int,
        for_update: bool = False,
    ) -> OrderIntent:
        statement = select(OrderIntent).where(
            OrderIntent.id == intent_id, OrderIntent.user_id == user_id
        )
        if for_update:
            # AsyncSessionLocal keeps identities after commit. Force a locked read
            # to overwrite stale state that another worker may have finalized.
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        result = await db.execute(statement)
        intent = result.scalar_one_or_none()
        if intent is None:
            raise ValueError("Order intent not found")
        return intent

    async def evaluate_risk(
        self,
        db: AsyncSession,
        user_id: UUID,
        intent_id: int,
        risk_engine: IRiskEngine,
        settings: Settings,
    ) -> tuple[OrderIntent, RiskDecision, RiskCheckResult]:
        intent = await self.get_user_order_intent(
            db, user_id, intent_id, for_update=True
        )
        intent.status = OrderIntentStatus.PENDING_RISK_CHECK.value

        decision = await risk_engine.evaluate_order_intent(
            self._to_request(intent), self._build_risk_context(user_id, settings)
        )

        intent.risk_checked_at = datetime.now(timezone.utc)
        if decision.status.value == "APPROVED":
            intent.status = OrderIntentStatus.RISK_APPROVED.value
        elif decision.status.value == "REQUIRES_REVIEW":
            intent.status = OrderIntentStatus.REQUIRES_REVIEW.value
        else:
            intent.status = OrderIntentStatus.RISK_BLOCKED.value

        result = RiskCheckResult(
            order_intent_id=intent.id,
            decision=decision.status.value,
            reason_code=decision.reason_code,
            reason_message=decision.reason_message,
            evaluated_by="system",
            metadata_json={
                "rules": [
                    {
                        "code": rule.code,
                        "passed": rule.passed,
                        "message": rule.message,
                        "severity": rule.severity,
                        "metadata": rule.metadata,
                    }
                    for rule in decision.rule_results
                ],
                "metadata": decision.metadata,
            },
        )
        db.add(result)
        await db.commit()
        await db.refresh(intent)
        await db.refresh(result)
        return intent, decision, result

    async def queue_order_intent(
        self,
        db: AsyncSession,
        user_id: UUID,
        intent_id: int,
        risk_engine: IRiskEngine,
        execution_queue: IOrderExecutionQueue,
        settings: Settings,
    ) -> tuple[OrderIntent, OrderExecutionCommand, Optional[RiskCheckResult]]:
        intent = await self.get_user_order_intent(
            db, user_id, intent_id, for_update=True
        )
        risk_result: Optional[RiskCheckResult] = None

        if intent.status in self._EXECUTION_LOCKED_STATUSES:
            raise ValueError(f"Order intent is already {intent.status}")

        if intent.status != OrderIntentStatus.RISK_APPROVED.value:
            intent, decision, risk_result = await self.evaluate_risk(
                db, user_id, intent_id, risk_engine, settings
            )
            if not decision.is_approved:
                raise ValueError(decision.reason_message)
            intent = await self.get_user_order_intent(
                db, user_id, intent_id, for_update=True
            )
            if intent.status in self._EXECUTION_LOCKED_STATUSES:
                raise ValueError(f"Order intent is already {intent.status}")
            if intent.status != OrderIntentStatus.RISK_APPROVED.value:
                raise ValueError(f"Order intent cannot be queued from {intent.status}")

        if not intent.client_order_id:
            intent.client_order_id = str(uuid4())

        intent.status = OrderIntentStatus.QUEUED_FOR_EXECUTION.value
        # This field is the durable outbox marker. The state transition and the
        # unpublished command are committed atomically before touching Redis.
        intent.execution_dispatched_at = None
        intent.execution_dispatch_claim_token = None
        intent.execution_dispatch_claimed_at = None
        await db.commit()
        await db.refresh(intent)

        # The durable DB transition is the acceptance boundary. Publishing is a
        # worker responsibility so Redis or marker failures cannot turn an
        # accepted order into a client-visible error and invite a resubmit.
        return intent, OrderExecutionCommand.from_intent(intent), risk_result

    async def recover_queued_order_intents(
        self,
        db: AsyncSession,
        execution_queue: IOrderExecutionQueue,
        grace_seconds: int = 0,
        limit: int = 1,
        intent_ids: Optional[list[int]] = None,
        dispatch_claim_timeout_seconds: int = 30,
        stale_dispatched_seconds: int = 300,
    ) -> list[OrderExecutionCommand]:
        """Publish new or conservatively stale durable execution commands."""
        if limit <= 0:
            return []

        claimed_at = datetime.now(timezone.utc)
        cutoff = claimed_at - timedelta(seconds=grace_seconds)
        stale_claim_cutoff = claimed_at - timedelta(
            seconds=max(1, dispatch_claim_timeout_seconds)
        )
        stale_dispatched_cutoff = claimed_at - timedelta(
            seconds=max(1, stale_dispatched_seconds)
        )
        statement = select(OrderIntent).where(
            OrderIntent.status == OrderIntentStatus.QUEUED_FOR_EXECUTION.value,
            or_(
                OrderIntent.execution_dispatched_at.is_(None),
                OrderIntent.execution_dispatched_at <= stale_dispatched_cutoff,
            ),
            or_(
                OrderIntent.execution_dispatch_claim_token.is_(None),
                OrderIntent.execution_dispatch_claimed_at.is_(None),
                OrderIntent.execution_dispatch_claimed_at <= stale_claim_cutoff,
            ),
        )
        if intent_ids is None and grace_seconds > 0:
            statement = statement.where(OrderIntent.updated_at <= cutoff)
        elif intent_ids is not None:
            statement = statement.where(OrderIntent.id.in_(intent_ids))
        statement = (
            statement.order_by(OrderIntent.requested_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await db.execute(statement)
        intents = list(result.scalars().all())
        if not intents:
            # Release the read transaction/connection before the worker blocks
            # waiting on Redis.
            await db.rollback()
            return []

        claims = []
        for intent in intents:
            claim_token = str(uuid4())
            intent.execution_dispatch_claim_token = claim_token
            intent.execution_dispatch_claimed_at = claimed_at
            claims.append(
                (intent.id, claim_token, OrderExecutionCommand.from_intent(intent))
            )
        # Commit the short DB claim before any Redis network call.
        await db.commit()

        recovered: list[OrderExecutionCommand] = []
        for intent_id, claim_token, command in claims:
            try:
                await execution_queue.enqueue(command)
            except Exception as exc:
                await self._finalize_execution_dispatch_claim(
                    db,
                    intent_id,
                    claim_token,
                    error=exc,
                )
                continue

            finalized = await self._finalize_execution_dispatch_claim(
                db,
                intent_id,
                claim_token,
            )
            if finalized:
                recovered.append(command)
        return recovered

    async def reconcile_expired_execution_leases(
        self,
        db: AsyncSession,
        limit: int = 10,
    ) -> list[int]:
        """Fence crashed broker claims even if their Redis delivery was lost."""
        if limit <= 0:
            return []

        statement = (
            select(OrderIntent)
            .where(
                OrderIntent.status == OrderIntentStatus.SUBMITTING.value,
                OrderIntent.execution_lease_expires_at.is_not(None),
                OrderIntent.execution_lease_expires_at <= datetime.now(timezone.utc),
            )
            .order_by(OrderIntent.execution_lease_expires_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
            .execution_options(populate_existing=True)
        )
        result = await db.execute(statement)
        intents = list(result.scalars().all())
        if not intents:
            await db.rollback()
            return []

        reconciled_ids = []
        reconciled_at = datetime.now(timezone.utc).isoformat()
        for intent in intents:
            metadata = dict(intent.metadata_json or {})
            metadata.update(
                {
                    "execution_reconciliation_required_at": reconciled_at,
                    "execution_reconciliation_error": (
                        "Execution lease expired before local finalization"
                    ),
                }
            )
            intent.metadata_json = metadata
            intent.status = OrderIntentStatus.REQUIRES_REVIEW.value
            self._clear_execution_claim(intent)
            reconciled_ids.append(intent.id)

        await db.commit()
        return reconciled_ids

    async def submit_order_intent(
        self,
        db: AsyncSession,
        user_id: UUID,
        intent_id: int,
        risk_engine: IRiskEngine,
        broker: IBrokerAdapter,
        settings: Settings,
    ) -> tuple[OrderIntent, BrokerOrder]:
        intent = await self.get_user_order_intent(
            db, user_id, intent_id, for_update=True
        )

        if intent.status in self._EXECUTION_LOCKED_STATUSES:
            raise ValueError(f"Order intent is already {intent.status}")

        if intent.status != OrderIntentStatus.RISK_APPROVED.value:
            intent, decision, _ = await self.evaluate_risk(
                db, user_id, intent_id, risk_engine, settings
            )
            if not decision.is_approved:
                raise ValueError(decision.reason_message)
            intent = await self.get_user_order_intent(
                db, user_id, intent_id, for_update=True
            )
            if intent.status in self._EXECUTION_LOCKED_STATUSES:
                raise ValueError(f"Order intent is already {intent.status}")
            if intent.status != OrderIntentStatus.RISK_APPROVED.value:
                raise ValueError(
                    f"Order intent cannot be submitted from {intent.status}"
                )

        intent.status = OrderIntentStatus.QUEUED_FOR_EXECUTION.value
        await db.commit()
        await db.refresh(intent)

        return await self.execute_order_intent(db, user_id, intent_id, broker, settings)

    async def execute_order_intent(
        self,
        db: AsyncSession,
        user_id: UUID,
        intent_id: int,
        broker: IBrokerAdapter,
        settings: Settings,
    ) -> tuple[OrderIntent, BrokerOrder]:
        # Lock only long enough to validate and persist a durable execution lease.
        # The broker call runs after that commit, without holding a DB connection.
        intent = await self.get_user_order_intent(
            db, user_id, intent_id, for_update=True
        )

        if intent.status == OrderIntentStatus.SUBMITTING.value:
            lease_expires_at = self._as_utc(intent.execution_lease_expires_at)
            if lease_expires_at and lease_expires_at > datetime.now(timezone.utc):
                raise OrderExecutionClaimBusy(
                    "Order intent already has an active execution lease"
                )

            intent.status = OrderIntentStatus.REQUIRES_REVIEW.value
            metadata = dict(intent.metadata_json or {})
            metadata["execution_reconciliation_error"] = (
                "Execution lease expired before local finalization"
            )
            intent.metadata_json = metadata
            self._clear_execution_claim(intent)
            await db.commit()
            raise OrderExecutionNotExecutable(intent.status)

        if intent.status not in self._EXECUTABLE_STATUSES:
            raise OrderExecutionNotExecutable(intent.status)

        max_attempts = self._max_execution_attempts(settings)
        if int(intent.execution_attempt_count or 0) >= max_attempts:
            intent.status = OrderIntentStatus.REQUIRES_REVIEW.value
            metadata = dict(intent.metadata_json or {})
            metadata["execution_reconciliation_error"] = (
                "Execution attempt budget was already exhausted"
            )
            intent.metadata_json = metadata
            self._clear_execution_claim(intent)
            await db.commit()
            raise OrderExecutionNotExecutable(intent.status)

        stock = await db.get(Stock, intent.stock_id)
        if stock is None:
            raise ValueError(f"Stock not found: {intent.stock_id}")

        broker_connection = await self._get_active_broker_connection(
            db, user_id, settings
        )

        if not intent.client_order_id:
            intent.client_order_id = str(uuid4())

        reference_price = await self._get_latest_reference_price(db, stock.id)
        request_metadata = {"order_intent_id": intent.id}
        if reference_price is not None:
            request_metadata["reference_price"] = str(reference_price)

        order_request = BrokerOrderRequest(
            client_order_id=intent.client_order_id,
            account_ref=settings.broker.default_account_ref,
            symbol=stock.symbol,
            market=stock.market,
            side=OrderSide(intent.side),
            order_type=OrderType(intent.order_type),
            quantity=Decimal(intent.quantity),
            time_in_force=TimeInForce(intent.time_in_force),
            limit_price=(
                Decimal(intent.limit_price) if intent.limit_price is not None else None
            ),
            stop_price=(
                Decimal(intent.stop_price) if intent.stop_price is not None else None
            ),
            metadata=request_metadata,
        )
        claim_token = str(uuid4())
        claimed_at = datetime.now(timezone.utc)
        intent.status = OrderIntentStatus.SUBMITTING.value
        intent.execution_attempt_count = int(intent.execution_attempt_count or 0) + 1
        attempt_count = intent.execution_attempt_count
        intent.execution_claim_token = claim_token
        intent.execution_claimed_at = claimed_at
        intent.execution_lease_expires_at = claimed_at + timedelta(
            seconds=self._execution_lease_seconds(settings)
        )
        # Persist the claim before external I/O. A process death can then be
        # fenced as ambiguous instead of silently rolling back into a resubmit.
        await db.commit()

        try:
            order_result = await asyncio.wait_for(
                broker.place_order(order_request),
                timeout=self._broker_timeout_seconds(settings),
            )
        except asyncio.TimeoutError as exc:
            error = BrokerConnectionError("Broker order submission timed out")
            retry_safe = self._broker_supports_idempotent_retry(broker)
            await self._persist_execution_failure(
                db,
                user_id,
                intent_id,
                claim_token,
                error,
                max_attempts,
                allow_retry=retry_safe,
            )
            if retry_safe:
                raise OrderExecutionRetryable(str(error), attempt_count) from exc
            raise OrderExecutionReconciliationRequired(
                "Broker timeout is ambiguous and automatic retry is not proven safe"
            ) from exc
        except BrokerConnectionError as exc:
            retry_safe = self._broker_supports_idempotent_retry(broker)
            await self._persist_execution_failure(
                db,
                user_id,
                intent_id,
                claim_token,
                exc,
                max_attempts,
                allow_retry=retry_safe,
            )
            if retry_safe:
                raise OrderExecutionRetryable(str(exc), attempt_count) from exc
            raise OrderExecutionReconciliationRequired(
                "Broker connection failure is ambiguous and automatic retry is not proven safe"
            ) from exc
        except BrokerOrderRejected:
            await self._finalize_claim_status(
                db,
                user_id,
                intent_id,
                claim_token,
                OrderIntentStatus.REJECTED.value,
            )
            raise
        except BrokerError:
            await self._finalize_claim_status(
                db,
                user_id,
                intent_id,
                claim_token,
                OrderIntentStatus.FAILED.value,
            )
            raise
        except Exception as exc:
            error = BrokerConnectionError(
                f"Broker submission failed ambiguously: {exc}"
            )
            retry_safe = self._broker_supports_idempotent_retry(broker)
            await self._persist_execution_failure(
                db,
                user_id,
                intent_id,
                claim_token,
                error,
                max_attempts,
                allow_retry=retry_safe,
            )
            if retry_safe:
                raise OrderExecutionRetryable(str(error), attempt_count) from exc
            raise OrderExecutionReconciliationRequired(
                "Broker failure is ambiguous and automatic retry is not proven safe"
            ) from exc

        try:
            intent = await self.get_user_order_intent(
                db, user_id, intent_id, for_update=True
            )
            self._verify_execution_claim(intent, claim_token)
            broker_order = BrokerOrder(
                order_intent_id=intent.id,
                broker_connection_id=(
                    broker_connection.id if broker_connection else None
                ),
                broker_account_id=intent.broker_account_id,
                broker_order_ref=order_result.broker_order_ref,
                status=order_result.status.value,
                submitted_quantity=order_result.submitted_quantity,
                filled_quantity=order_result.filled_quantity,
                avg_fill_price=order_result.avg_fill_price,
                submitted_at=order_result.submitted_at,
                last_event_at=order_result.submitted_at,
                raw_payload=order_result.raw_payload,
            )
            db.add(broker_order)
            await db.flush()

            db.add(
                OrderEvent(
                    broker_order_id=broker_order.id,
                    event_type="ORDER_SUBMITTED",
                    status=order_result.status.value,
                    payload=order_result.raw_payload,
                    occurred_at=(
                        order_result.submitted_at or datetime.now(timezone.utc)
                    ),
                )
            )

            intent.submitted_at = datetime.now(timezone.utc)
            intent.status = self._map_broker_status(order_result.status)

            if self._is_filled_result(order_result):
                await self._record_filled_execution(
                    db=db,
                    intent=intent,
                    broker_order=broker_order,
                    order_result=order_result,
                )
                intent.status = OrderIntentStatus.FILLED.value

            self._clear_execution_claim(intent)
            await db.commit()
            await db.refresh(intent)
            await db.refresh(broker_order)
            return intent, broker_order
        except Exception as exc:
            await db.rollback()
            raise OrderExecutionReconciliationRequired(
                "Broker replied but the local order ledger could not be finalized",
                broker_order_ref=order_result.broker_order_ref,
            ) from exc

    async def mark_execution_reconciliation_required(
        self,
        db: AsyncSession,
        user_id: UUID,
        intent_id: int,
        error: Exception,
    ) -> OrderIntent:
        """Fence an ambiguous, retry-exhausted order from automatic resubmission."""

        intent = await self.get_user_order_intent(
            db, user_id, intent_id, for_update=True
        )
        if intent.status in {
            OrderIntentStatus.SUBMITTED.value,
            OrderIntentStatus.PARTIALLY_FILLED.value,
            OrderIntentStatus.FILLED.value,
            OrderIntentStatus.CANCELLED.value,
            OrderIntentStatus.REJECTED.value,
        }:
            await db.rollback()
            return intent

        metadata = dict(intent.metadata_json or {})
        metadata.update(
            {
                "execution_reconciliation_required_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "execution_reconciliation_error": str(error),
            }
        )
        broker_order_ref = getattr(error, "broker_order_ref", None)
        if broker_order_ref:
            metadata["execution_reconciliation_broker_order_ref"] = str(
                broker_order_ref
            )
        intent.metadata_json = metadata
        intent.status = OrderIntentStatus.REQUIRES_REVIEW.value
        self._clear_execution_claim(intent)
        await db.commit()
        await db.refresh(intent)
        return intent

    async def _get_latest_reference_price(
        self, db: AsyncSession, stock_id: int
    ) -> Optional[Decimal]:
        price = await fetch_latest_daily_price(db, stock_id)
        return Decimal(price.close_price) if price is not None else None

    def _is_filled_result(self, order_result) -> bool:
        return (
            order_result.status == BrokerOrderStatus.FILLED
            and order_result.filled_quantity > 0
            and order_result.avg_fill_price is not None
        )

    async def _record_filled_execution(
        self,
        db: AsyncSession,
        intent: OrderIntent,
        broker_order: BrokerOrder,
        order_result,
    ) -> None:
        executed_at = order_result.submitted_at or datetime.now(timezone.utc)
        execution_ref = f"{order_result.broker_order_ref}-fill-1"
        commission_value = order_result.raw_payload.get("commission") or "0"
        commission = Decimal(str(commission_value))

        broker_order.status = BrokerOrderStatus.FILLED.value
        broker_order.filled_quantity = order_result.filled_quantity
        broker_order.avg_fill_price = order_result.avg_fill_price
        broker_order.last_event_at = executed_at

        db.add(
            OrderExecution(
                broker_order_id=broker_order.id,
                execution_ref=execution_ref,
                side=intent.side,
                quantity=order_result.filled_quantity,
                price=order_result.avg_fill_price,
                commission=commission,
                currency=order_result.raw_payload.get("currency", "USD"),
                executed_at=executed_at,
                payload=order_result.raw_payload,
            )
        )
        db.add(
            OrderEvent(
                broker_order_id=broker_order.id,
                event_type="ORDER_FILLED",
                status=BrokerOrderStatus.FILLED.value,
                payload=order_result.raw_payload,
                occurred_at=executed_at,
            )
        )

        def apply_fill_sync(session):
            portfolio = UserPortfolio.create_or_update_position(
                session=session,
                user_id=intent.user_id,
                stock_id=intent.stock_id,
                quantity=order_result.filled_quantity,
                price=order_result.avg_fill_price,
                transaction_type=intent.side,
            )
            session.flush()

            portfolio_id = portfolio.id if portfolio else None
            Transaction.create_transaction(
                session=session,
                user_id=intent.user_id,
                portfolio_id=portfolio_id,
                stock_id=intent.stock_id,
                transaction_type=intent.side,
                quantity=order_result.filled_quantity,
                price=order_result.avg_fill_price,
                transaction_date=executed_at.date(),
                fee=commission,
                tax=Decimal("0"),
                note=f"Generated from broker order {order_result.broker_order_ref}",
            )
            session.flush()

        await db.run_sync(apply_fill_sync)

    def _to_request(self, intent: OrderIntent) -> OrderIntentRequest:
        return OrderIntentRequest(
            user_id=intent.user_id,
            stock_id=intent.stock_id,
            strategy_signal_id=intent.strategy_signal_id,
            broker_account_id=intent.broker_account_id,
            side=OrderSide(intent.side),
            order_type=OrderType(intent.order_type),
            time_in_force=TimeInForce(intent.time_in_force),
            quantity=Decimal(intent.quantity),
            limit_price=(
                Decimal(intent.limit_price) if intent.limit_price is not None else None
            ),
            stop_price=(
                Decimal(intent.stop_price) if intent.stop_price is not None else None
            ),
            notional=Decimal(intent.notional) if intent.notional is not None else None,
            source=intent.source,
            reason=intent.reason,
            idempotency_key=intent.idempotency_key,
            metadata=intent.metadata_json or {},
            expires_at=intent.expires_at,
        )

    def _record_execution_enqueue_attempt(
        self, intent: OrderIntent, error: Optional[Exception] = None
    ) -> None:
        attempted_datetime = datetime.now(timezone.utc)
        attempted_at = attempted_datetime.isoformat()
        metadata = dict(intent.metadata_json or {})
        metadata["execution_enqueue_attempted_at"] = attempted_at
        if error is None:
            intent.execution_dispatched_at = attempted_datetime
            metadata["execution_enqueued_at"] = attempted_at
            metadata.pop("execution_enqueue_error", None)
            metadata.pop("execution_enqueue_failed_at", None)
        else:
            metadata["execution_enqueue_error"] = str(error)
            metadata["execution_enqueue_failed_at"] = attempted_at
        intent.metadata_json = metadata

    async def _finalize_execution_dispatch_claim(
        self,
        db: AsyncSession,
        intent_id: int,
        claim_token: str,
        error: Optional[Exception] = None,
    ) -> bool:
        statement = (
            select(OrderIntent)
            .where(
                OrderIntent.id == intent_id,
                OrderIntent.execution_dispatch_claim_token == claim_token,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        result = await db.execute(statement)
        intent = result.scalar_one_or_none()
        if intent is None:
            await db.rollback()
            return False

        self._record_execution_enqueue_attempt(intent, error=error)
        intent.execution_dispatch_claim_token = None
        intent.execution_dispatch_claimed_at = None
        await db.commit()
        return True

    def _broker_timeout_seconds(self, settings: Settings) -> float:
        ibkr_settings = getattr(settings, "ibkr", None)
        configured = getattr(ibkr_settings, "timeout_seconds", 30)
        return max(1.0, float(configured or 30))

    def _max_execution_attempts(self, settings: Settings) -> int:
        queue_settings = getattr(settings, "order_execution_queue", None)
        configured = getattr(queue_settings, "max_attempts", 3)
        return max(1, int(configured or 3))

    async def _persist_execution_failure(
        self,
        db: AsyncSession,
        user_id: UUID,
        intent_id: int,
        claim_token: str,
        error: Exception,
        max_attempts: int,
        allow_retry: bool,
    ) -> None:
        try:
            intent = await self.get_user_order_intent(
                db, user_id, intent_id, for_update=True
            )
            self._verify_execution_claim(intent, claim_token)
            failed_at = datetime.now(timezone.utc).isoformat()
            metadata = dict(intent.metadata_json or {})
            metadata.update(
                {
                    "execution_last_error": str(error),
                    "execution_last_failed_at": failed_at,
                    "execution_attempt_count": intent.execution_attempt_count,
                }
            )
            intent.metadata_json = metadata
            intent.status = (
                OrderIntentStatus.REQUIRES_REVIEW.value
                if not allow_retry or intent.execution_attempt_count >= max_attempts
                else OrderIntentStatus.QUEUED_FOR_EXECUTION.value
            )
            self._clear_execution_claim(intent)
            await db.commit()
        except OrderExecutionReconciliationRequired:
            await db.rollback()
            raise
        except Exception as exc:
            await db.rollback()
            raise OrderExecutionReconciliationRequired(
                "Broker outcome is ambiguous and its attempt state could not be saved"
            ) from exc

    def _broker_supports_idempotent_retry(self, broker: IBrokerAdapter) -> bool:
        return bool(getattr(broker, "supports_idempotent_submission", False))

    async def _finalize_claim_status(
        self,
        db: AsyncSession,
        user_id: UUID,
        intent_id: int,
        claim_token: str,
        status: str,
    ) -> None:
        try:
            intent = await self.get_user_order_intent(
                db, user_id, intent_id, for_update=True
            )
            self._verify_execution_claim(intent, claim_token)
            intent.status = status
            self._clear_execution_claim(intent)
            await db.commit()
        except OrderExecutionReconciliationRequired:
            await db.rollback()
            raise
        except Exception as exc:
            await db.rollback()
            raise OrderExecutionReconciliationRequired(
                "Broker result was terminal but local state could not be saved"
            ) from exc

    def _verify_execution_claim(self, intent: OrderIntent, claim_token: str) -> None:
        if (
            intent.status != OrderIntentStatus.SUBMITTING.value
            or intent.execution_claim_token != claim_token
        ):
            raise OrderExecutionReconciliationRequired(
                "Execution claim ownership changed before local finalization"
            )

    def _clear_execution_claim(self, intent: OrderIntent) -> None:
        intent.execution_claim_token = None
        intent.execution_claimed_at = None
        intent.execution_lease_expires_at = None

    def _execution_lease_seconds(self, settings: Settings) -> float:
        queue_settings = getattr(settings, "order_execution_queue", None)
        pending_idle_ms = float(
            getattr(queue_settings, "pending_idle_ms", 60000) or 60000
        )
        return max(
            120.0,
            self._broker_timeout_seconds(settings) + pending_idle_ms / 1000 + 30,
        )

    def _as_utc(self, value: Optional[datetime]) -> Optional[datetime]:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _build_risk_context(self, user_id: UUID, settings: Settings) -> RiskContext:
        provider = settings.broker.provider.lower()
        read_only = (
            False
            if provider == "paper"
            else settings.broker.read_only or settings.ibkr.read_only
        )
        return RiskContext(
            user_id=user_id,
            mode=settings.broker.mode,
            broker_provider=settings.broker.provider,
            trading_enabled=settings.broker.trading_enabled,
            read_only=read_only,
            account_ref=settings.broker.default_account_ref,
        )

    async def _get_active_broker_connection(
        self, db: AsyncSession, user_id: UUID, settings: Settings
    ) -> Optional[BrokerConnection]:
        result = await db.execute(
            select(BrokerConnection)
            .where(
                BrokerConnection.user_id == user_id,
                BrokerConnection.provider == settings.broker.provider,
                BrokerConnection.mode == settings.broker.mode,
                BrokerConnection.is_active == True,
            )
            .order_by(BrokerConnection.created_at.desc())
        )
        return result.scalar_one_or_none()

    def _map_broker_status(self, status: BrokerOrderStatus) -> str:
        if status in {BrokerOrderStatus.ACCEPTED, BrokerOrderStatus.SUBMITTED}:
            return OrderIntentStatus.SUBMITTED.value
        if status == BrokerOrderStatus.PARTIALLY_FILLED:
            return OrderIntentStatus.PARTIALLY_FILLED.value
        if status == BrokerOrderStatus.FILLED:
            return OrderIntentStatus.FILLED.value
        if status == BrokerOrderStatus.CANCELLED:
            return OrderIntentStatus.CANCELLED.value
        if status == BrokerOrderStatus.REJECTED:
            return OrderIntentStatus.REJECTED.value
        return OrderIntentStatus.FAILED.value
