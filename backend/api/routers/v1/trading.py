"""
交易整合 API
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.trading import (
    BrokerOrderResponse,
    BrokerStatusResponse,
    OrderIntentCreateRequest,
    OrderIntentListResponse,
    OrderIntentResponse,
    RiskCheckResponse,
)
from app.dependencies import (
    get_broker_adapter,
    get_database_session,
    get_order_intent_service,
    get_risk_engine,
)
from app.settings import Settings, get_settings
from core.auth_dependencies import get_current_active_user
from domain.brokers import BrokerError, IBrokerAdapter
from domain.models.order_intent import OrderIntent
from domain.models.user import User
from domain.orders import OrderIntentRequest, OrderSide, OrderType, TimeInForce
from domain.risk import IRiskEngine
from domain.services.order_intent_service import OrderIntentService


router = APIRouter(prefix="/trading", tags=["trading"])


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


@router.post("/order-intents/{intent_id}/submit", response_model=BrokerOrderResponse)
async def submit_order_intent(
    intent_id: int,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user),
    service: OrderIntentService = Depends(get_order_intent_service),
    risk_engine: IRiskEngine = Depends(get_risk_engine),
    broker: IBrokerAdapter = Depends(get_broker_adapter),
    settings: Settings = Depends(get_settings),
):
    """
    送出下單意圖。

    若尚未通過風控，會先執行風控；未通過則不會送 broker。
    """
    try:
        _, broker_order = await service.submit_order_intent(
            db, current_user.id, intent_id, risk_engine, broker, settings
        )
        return BrokerOrderResponse(
            id=broker_order.id,
            order_intent_id=broker_order.order_intent_id,
            broker_order_ref=broker_order.broker_order_ref,
            status=broker_order.status,
            submitted_quantity=broker_order.submitted_quantity,
            filled_quantity=broker_order.filled_quantity,
            avg_fill_price=broker_order.avg_fill_price,
            submitted_at=broker_order.submitted_at,
            raw_payload=broker_order.raw_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except BrokerError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


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
