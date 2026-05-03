"""
下單意圖服務
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.settings import Settings
from domain.brokers import (
    BrokerError,
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
        self, db: AsyncSession, user_id: UUID, intent_id: int
    ) -> OrderIntent:
        result = await db.execute(
            select(OrderIntent).where(
                OrderIntent.id == intent_id, OrderIntent.user_id == user_id
            )
        )
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
        intent = await self.get_user_order_intent(db, user_id, intent_id)
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
        intent = await self.get_user_order_intent(db, user_id, intent_id)
        risk_result: Optional[RiskCheckResult] = None

        if intent.status in self._EXECUTION_LOCKED_STATUSES:
            raise ValueError(f"Order intent is already {intent.status}")

        if intent.status != OrderIntentStatus.RISK_APPROVED.value:
            intent, decision, risk_result = await self.evaluate_risk(
                db, user_id, intent_id, risk_engine, settings
            )
            if not decision.is_approved:
                raise ValueError(decision.reason_message)

        if not intent.client_order_id:
            intent.client_order_id = str(uuid4())

        intent.status = OrderIntentStatus.QUEUED_FOR_EXECUTION.value
        await db.commit()
        await db.refresh(intent)

        command = OrderExecutionCommand.from_intent(intent)
        try:
            await execution_queue.enqueue(command)
        except Exception as exc:
            intent.status = OrderIntentStatus.FAILED.value
            await db.commit()
            raise RuntimeError(
                "Failed to enqueue order execution command"
            ) from exc

        return intent, command, risk_result

    async def submit_order_intent(
        self,
        db: AsyncSession,
        user_id: UUID,
        intent_id: int,
        risk_engine: IRiskEngine,
        broker: IBrokerAdapter,
        settings: Settings,
    ) -> tuple[OrderIntent, BrokerOrder]:
        intent = await self.get_user_order_intent(db, user_id, intent_id)

        if intent.status in self._EXECUTION_LOCKED_STATUSES:
            raise ValueError(f"Order intent is already {intent.status}")

        if intent.status != OrderIntentStatus.RISK_APPROVED.value:
            intent, decision, _ = await self.evaluate_risk(
                db, user_id, intent_id, risk_engine, settings
            )
            if not decision.is_approved:
                raise ValueError(decision.reason_message)

        intent.status = OrderIntentStatus.QUEUED_FOR_EXECUTION.value
        await db.commit()
        await db.refresh(intent)

        return await self.execute_order_intent(
            db, user_id, intent_id, broker, settings
        )

    async def execute_order_intent(
        self,
        db: AsyncSession,
        user_id: UUID,
        intent_id: int,
        broker: IBrokerAdapter,
        settings: Settings,
    ) -> tuple[OrderIntent, BrokerOrder]:
        intent = await self.get_user_order_intent(db, user_id, intent_id)

        if intent.status not in self._EXECUTABLE_STATUSES:
            raise ValueError(
                f"Order intent must be queued before execution, got {intent.status}"
            )

        stock = await db.get(Stock, intent.stock_id)
        if stock is None:
            raise ValueError(f"Stock not found: {intent.stock_id}")

        broker_connection = await self._get_active_broker_connection(
            db, user_id, settings
        )

        if not intent.client_order_id:
            intent.client_order_id = str(uuid4())

        intent.status = OrderIntentStatus.SUBMITTING.value
        await db.commit()
        await db.refresh(intent)

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

        try:
            order_result = await broker.place_order(order_request)
        except BrokerError:
            intent.status = OrderIntentStatus.FAILED.value
            await db.commit()
            raise

        broker_order = BrokerOrder(
            order_intent_id=intent.id,
            broker_connection_id=broker_connection.id if broker_connection else None,
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
                occurred_at=order_result.submitted_at or datetime.now(timezone.utc),
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

        await db.commit()
        await db.refresh(intent)
        await db.refresh(broker_order)
        return intent, broker_order

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
