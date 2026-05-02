"""
Price alert API routes.
"""

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.price_alerts import (
    PriceAlertCheckResponse,
    PriceAlertCreateRequest,
    PriceAlertResponse,
    PriceAlertUpdateRequest,
)
from app.dependencies import (
    get_database_session,
    get_price_alert_service,
    get_settings,
)
from app.settings import Settings
from core.auth_dependencies import get_current_active_user
from domain.models.price_alert import PriceAlert
from domain.models.user import User
from domain.services.price_alert_service import PriceAlertService

router = APIRouter(prefix="/price-alerts", tags=["price-alerts"])
internal_router = APIRouter(prefix="/internal/price-alerts", tags=["internal"])


def serialize_price_alert(alert: PriceAlert) -> PriceAlertResponse:
    return PriceAlertResponse(
        id=alert.id,
        user_id=str(alert.user_id),
        stock_id=alert.stock_id,
        symbol=alert.symbol,
        market=alert.market,
        condition=alert.condition,
        target_price=float(alert.target_price),
        source_timeframe=alert.source_timeframe,
        active=alert.active,
        triggered=alert.triggered,
        triggered_at=alert.triggered_at,
        expires_at=alert.expires_at,
        last_checked_at=alert.last_checked_at,
        last_price=float(alert.last_price) if alert.last_price is not None else None,
        last_source=alert.last_source,
        created_at=alert.created_at,
        updated_at=alert.updated_at,
    )


def require_internal_token(
    x_internal_token: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    expected = (
        settings.INTERNAL_API_TOKEN
        or settings.QLIB_INTERNAL_TOKEN
        or "dev-internal-token"
    )
    if x_internal_token != expected:
        raise HTTPException(status_code=401, detail="invalid internal token")


@router.get("/", response_model=list[PriceAlertResponse])
async def list_price_alerts(
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user),
    service: PriceAlertService = Depends(get_price_alert_service),
):
    alerts = await service.list_alerts(db, current_user.id, active_only=active_only)
    return [serialize_price_alert(alert) for alert in alerts]


@router.post("/", response_model=PriceAlertResponse)
async def create_price_alert(
    request: PriceAlertCreateRequest,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user),
    service: PriceAlertService = Depends(get_price_alert_service),
):
    try:
        alert = await service.create_alert(
            db,
            user_id=current_user.id,
            stock_id=request.stock_id,
            condition=request.condition,
            target_price=request.target_price,
            source_timeframe=request.source_timeframe,
            expires_at=request.expires_at,
        )
        return serialize_price_alert(alert)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.patch("/{alert_id}", response_model=PriceAlertResponse)
async def update_price_alert(
    alert_id: int,
    request: PriceAlertUpdateRequest,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user),
):
    alert = await db.get(PriceAlert, alert_id)
    if alert is None or alert.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="price alert not found")

    if request.active is not None:
        alert.active = request.active
    if request.target_price is not None:
        alert.target_price = request.target_price
    if request.condition is not None:
        alert.condition = request.condition
    if request.expires_at is not None:
        alert.expires_at = request.expires_at

    await db.commit()
    await db.refresh(alert)
    return serialize_price_alert(alert)


@router.delete("/{alert_id}")
async def delete_price_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user),
):
    alert = await db.get(PriceAlert, alert_id)
    if alert is None or alert.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="price alert not found")
    await db.delete(alert)
    await db.commit()
    return {"message": "price alert deleted", "id": alert_id}


@internal_router.post(
    "/check",
    response_model=PriceAlertCheckResponse,
    dependencies=[Depends(require_internal_token)],
)
async def check_price_alerts(
    limit: int = Query(500, ge=1, le=5000),
    db: AsyncSession = Depends(get_database_session),
    service: PriceAlertService = Depends(get_price_alert_service),
):
    return await service.check_alerts(db, limit=limit)
