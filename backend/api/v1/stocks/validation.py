"""
數據驗證相關API端點
負責: /{stock_id}/validate
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from core.database import get_db_session
from services.data.validation import data_validation_service
from models.repositories.crud_stock import stock_crud

router = APIRouter()


@router.get("/{stock_id}/validate", response_model=Dict[str, Any])
async def validate_stock_data(
    stock_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """
    驗證股票數據完整性和質量
    """
    try:
        # 檢查股票是否存在
        stock = await stock_crud.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")

        # 執行數據驗證
        validation_result = await data_validation_service.validate_stock_data(
            db, stock_id=stock_id
        )

        return {
            "stock_id": stock_id,
            "symbol": stock.symbol,
            "validation_result": validation_result,
            "is_valid": validation_result.get("is_valid", False),
            "issues_found": len(validation_result.get("issues", [])),
            "recommendations": validation_result.get("recommendations", [])
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"數據驗證失敗: {str(e)}")