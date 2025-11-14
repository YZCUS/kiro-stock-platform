"""
技術分析API路由 - Clean Architecture版本
只負責HTTP路由、參數驗證和回應格式化，業務邏輯委託給Domain Services
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.dependencies import (
    get_database_session,
    get_technical_analysis_service_clean,
)

router = APIRouter()


@router.get("/technical/{stock_id}")
async def get_technical_analysis(
    stock_id: int,
    analysis_days: int = Query(60, ge=20, le=365, description="分析天數"),
    db: AsyncSession = Depends(get_database_session),
    technical_service=Depends(get_technical_analysis_service_clean),
):
    """取得股票技術分析"""
    try:
        analysis = await technical_service.calculate_stock_indicators(
            db=db, stock_id=stock_id, analysis_days=analysis_days
        )

        return {
            "stock_id": analysis.stock_id,
            "symbol": analysis.symbol,
            "analysis_date": analysis.analysis_date,
            "indicators_calculated": analysis.indicators_calculated,
            "indicators_successful": analysis.indicators_successful,
            "indicators_failed": analysis.indicators_failed,
            "execution_time_seconds": analysis.execution_time_seconds,
            "errors": analysis.errors,
            "warnings": analysis.warnings,
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"技術分析失敗: {str(e)}")


@router.get("/summary/{stock_id}")
async def get_technical_summary(
    stock_id: int,
    timeframe: Optional[str] = Query(None, description="時間框架"),
    db: AsyncSession = Depends(get_database_session),
    technical_service=Depends(get_technical_analysis_service_clean),
):
    """取得股票技術面摘要"""
    try:
        summary = await technical_service.get_stock_technical_summary(
            db=db,
            stock_id=stock_id,
            timeframe=timeframe,
        )

        return summary

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得技術摘要失敗: {str(e)}")


@router.get("/test")
async def test_analysis():
    return {"message": "Technical Analysis API working with Clean Architecture"}
