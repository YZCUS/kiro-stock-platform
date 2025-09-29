"""
數據驗證相關API端點
負責: /{stock_id}/validate
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.dependencies import (
    get_database_session,
    get_stock_service,
    get_data_validation_service_clean
)
from domain.services.data_validation_service import DataValidationService
from domain.services.stock_service import StockService

router = APIRouter()


@router.get("/{stock_id}/validate", response_model=Dict[str, Any])
async def validate_stock_data(
    stock_id: int,
    db: AsyncSession = Depends(get_database_session),
    stock_service: StockService = Depends(get_stock_service),
    validation_service: DataValidationService = Depends(get_data_validation_service_clean)
):
    """
    驗證股票數據完整性和質量
    """
    try:
        # 檢查股票是否存在
        stock = await stock_service.get_stock_by_id(db, stock_id)

        report = await validation_service.validate_stock_data(db, stock_id)

        return {
            "stock_id": report.stock_id,
            "symbol": report.symbol,
            "market": report.market,
            "quality_score": report.quality_score,
            "is_valid": report.is_valid,
            "total_records": report.total_records,
            "issues": [
                {"message": issue.message, "context": issue.context}
                for issue in report.issues
            ],
            "recommendations": report.recommendations
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"數據驗證失敗: {str(e)}")