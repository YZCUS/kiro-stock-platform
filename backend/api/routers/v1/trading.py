"""
交易整合 API
"""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.trading import (
    BrokerStatusResponse,
    OrderExecutionCommandResponse,
    OrderIntentCreateRequest,
    OrderIntentListResponse,
    OrderIntentQueuedResponse,
    OrderIntentResponse,
    RiskCheckResponse,
)
from app.dependencies import (
    get_broker_adapter,
    get_database_session,
    get_order_execution_queue,
    get_order_execution_worker,
    get_order_intent_service,
    get_risk_engine,
)
from app.settings import Settings, get_settings
from core.auth_dependencies import get_current_active_user
from domain.brokers import IBrokerAdapter
from domain.execution import IOrderExecutionQueue, OrderExecutionCommand
from domain.models.order_intent import OrderIntent
from domain.models.risk import RiskCheckResult
from domain.models.user import User
from domain.orders import OrderIntentRequest, OrderSide, OrderType, TimeInForce
from domain.risk import IRiskEngine
from domain.services.order_intent_service import OrderIntentService


router = APIRouter(prefix="/trading", tags=["trading"])
logger = logging.getLogger(__name__)


@router.get("/broker/status", response_model=BrokerStatusResponse)
async def get_broker_status(
    broker: IBrokerAdapter = Depends(get_broker_adapter),
):
    """取得目前 broker adapter 狀態。"""
    status = await broker.get_status()
    return BrokerStatusResponse(
        provider=status.provider,
        mode=status.mode,
        available=status.available,
        read_only=status.read_only,
        message=status.message,
        metadata=status.metadata,
    )


@router.post("/order-intents", response_model=OrderIntentResponse, status_code=201)
async def create_order_intent(
    request: OrderIntentCreateRequest,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user),
    service: OrderIntentService = Depends(get_order_intent_service),
):
    """建立下單意圖。此動作不會送單到 broker。"""
    try:
        intent = await service.create_order_intent(
            db,
            OrderIntentRequest(
                user_id=current_user.id,
                stock_id=request.stock_id,
                strategy_signal_id=request.strategy_signal_id,
                broker_account_id=request.broker_account_id,
                side=OrderSide(request.side),
                order_type=OrderType(request.order_type),
                time_in_force=TimeInForce(request.time_in_force),
                quantity=request.quantity,
                limit_price=request.limit_price,
                stop_price=request.stop_price,
                notional=request.notional,
                source=request.source,
                reason=request.reason,
                idempotency_key=request.idempotency_key,
                metadata=request.metadata,
                expires_at=request.expires_at,
            ),
        )
        return _serialize_order_intent(intent)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/order-intents", response_model=OrderIntentListResponse)
async def list_order_intents(
    status: str | None = Query(None, description="依狀態篩選"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user),
):
    """列出目前使用者的下單意圖。"""
    query = select(OrderIntent).where(OrderIntent.user_id == current_user.id)
    if status:
        query = query.where(OrderIntent.status == status)
    query = query.order_by(OrderIntent.requested_at.desc()).limit(limit)

    result = await db.execute(query)
    items = [_serialize_order_intent(intent) for intent in result.scalars().all()]
    return OrderIntentListResponse(items=items, total=len(items))


@router.get("/order-intents/{intent_id}", response_model=OrderIntentResponse)
async def get_order_intent(
    intent_id: int,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user),
    service: OrderIntentService = Depends(get_order_intent_service),
):
    """取得單一下單意圖。"""
    try:
        intent = await service.get_user_order_intent(db, current_user.id, intent_id)
        return _serialize_order_intent(intent)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/order-intents/{intent_id}/risk-check", response_model=RiskCheckResponse
)
async def evaluate_order_intent_risk(
    intent_id: int,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user),
    service: OrderIntentService = Depends(get_order_intent_service),
    risk_engine: IRiskEngine = Depends(get_risk_engine),
    settings: Settings = Depends(get_settings),
):
    """對下單意圖執行風控評估。"""
    try:
        _, _, result = await service.evaluate_risk(
            db, current_user.id, intent_id, risk_engine, settings
        )
        return RiskCheckResponse(
            id=result.id,
            order_intent_id=result.order_intent_id,
            decision=result.decision,
            reason_code=result.reason_code,
            reason_message=result.reason_message,
            evaluated_by=result.evaluated_by,
            evaluated_at=result.evaluated_at,
            metadata=result.metadata_json,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/order-intents/{intent_id}/submit", response_model=OrderIntentQueuedResponse
)
async def submit_order_intent(
    intent_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user),
    service: OrderIntentService = Depends(get_order_intent_service),
    risk_engine: IRiskEngine = Depends(get_risk_engine),
    execution_queue: IOrderExecutionQueue = Depends(get_order_execution_queue),
    settings: Settings = Depends(get_settings),
):
    """
    送出下單意圖。

    若尚未通過風控，會先執行風控；未通過則不會進入執行佇列。
    實際 broker 送單由 execution worker 處理，
    避免 API request 直接卡在券商連線。
    """
    try:
        intent, command, risk_result = await service.queue_order_intent(
            db,
            current_user.id,
            intent_id,
            risk_engine,
            execution_queue,
            settings,
        )
        if (
            background_tasks is not None
            and settings.broker.provider.lower() == "paper"
        ):
            background_tasks.add_task(_process_next_order_execution_background)

        return OrderIntentQueuedResponse(
            order_intent=_serialize_order_intent(intent),
            command=_serialize_execution_command(command),
            risk_check=(
                _serialize_risk_check_result(risk_result) if risk_result else None
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


async def _process_next_order_execution_background() -> None:
    """Process one queued paper order after the API response is returned."""
    from core.database import AsyncSessionLocal

    if AsyncSessionLocal is None:
        logger.warning(
            "Order execution skipped because database session is unavailable"
        )
        return

    settings = get_settings()
    queue = get_order_execution_queue()
    broker = get_broker_adapter(settings)
    worker = get_order_execution_worker()

    async with AsyncSessionLocal() as db:
        try:
            await worker.process_next(
                db=db,
                execution_queue=queue,
                broker=broker,
                settings=settings,
                timeout=0,
            )
        except Exception:
            await db.rollback()
            logger.exception("Failed to process queued paper order execution")


def _serialize_order_intent(intent: OrderIntent) -> OrderIntentResponse:
    return OrderIntentResponse(
        id=intent.id,
        user_id=str(intent.user_id),
        stock_id=intent.stock_id,
        strategy_signal_id=intent.strategy_signal_id,
        broker_account_id=intent.broker_account_id,
        side=intent.side,
        order_type=intent.order_type,
        time_in_force=intent.time_in_force,
        quantity=intent.quantity,
        limit_price=intent.limit_price,
        stop_price=intent.stop_price,
        notional=intent.notional,
        status=intent.status,
        source=intent.source,
        idempotency_key=intent.idempotency_key,
        client_order_id=intent.client_order_id,
        reason=intent.reason,
        metadata=intent.metadata_json,
        requested_at=intent.requested_at,
        risk_checked_at=intent.risk_checked_at,
        submitted_at=intent.submitted_at,
        expires_at=intent.expires_at,
        created_at=intent.created_at,
        updated_at=intent.updated_at,
    )


def _serialize_risk_check_result(result: RiskCheckResult) -> RiskCheckResponse:
    return RiskCheckResponse(
        id=result.id,
        order_intent_id=result.order_intent_id,
        decision=result.decision,
        reason_code=result.reason_code,
        reason_message=result.reason_message,
        evaluated_by=result.evaluated_by,
        evaluated_at=result.evaluated_at,
        metadata=result.metadata_json,
    )


def _serialize_execution_command(
    command: OrderExecutionCommand,
) -> OrderExecutionCommandResponse:
    return OrderExecutionCommandResponse(
        order_intent_id=command.order_intent_id,
        idempotency_key=command.idempotency_key,
        attempt=command.attempt,
        requested_at=command.requested_at,
        metadata=command.metadata,
    )
