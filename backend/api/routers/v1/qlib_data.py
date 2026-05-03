"""
Qlib data readiness API routes.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.qlib_data import QlibModelOptionsResponse, QlibReadinessResponse
from app.dependencies import get_database_session, get_qlib_data_readiness_service
from domain.services.qlib_data_readiness_service import QlibDataReadinessService
from domain.services.qlib_model_registry import list_qlib_model_options

router = APIRouter(prefix="/qlib", tags=["qlib"])


@router.get("/readiness", response_model=QlibReadinessResponse)
async def get_qlib_readiness(
    market: str = Query("US", pattern="^(TW|US)$"),
    min_stocks: int = Query(200, ge=1, le=10000),
    min_bars: int = Query(504, ge=1, le=10000),
    db: AsyncSession = Depends(get_database_session),
    service: QlibDataReadinessService = Depends(get_qlib_data_readiness_service),
):
    return await service.evaluate(
        db,
        market=market,
        min_stocks=min_stocks,
        min_bars=min_bars,
    )


@router.get("/models", response_model=QlibModelOptionsResponse)
async def get_qlib_models():
    return QlibModelOptionsResponse(
        models=[model_option.as_dict() for model_option in list_qlib_model_options()]
    )
