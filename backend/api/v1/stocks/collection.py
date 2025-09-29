"""
數據收集相關API端點
負責: /refresh, /collect, /collect-all, /collect-batch
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
from datetime import date, timedelta

from app.dependencies import (
    get_database_session,
    get_data_collection_service_clean,
    get_stock_service
)
from domain.services.data_collection_service import DataCollectionService
from domain.services.stock_service import StockService
from api.schemas.stocks import (
    DataCollectionRequest,
    DataCollectionResponse,
    BatchCollectionRequest
)

router = APIRouter()


@router.post("/{stock_id}/refresh", response_model=DataCollectionResponse)
async def refresh_stock_data(
    stock_id: int,
    days: int = 30,
    db: AsyncSession = Depends(get_database_session),
    data_collection_service: DataCollectionService = Depends(get_data_collection_service_clean),
    stock_service: StockService = Depends(get_stock_service)
):
    """
    手動更新股票數據
    """
    try:
        # 檢查股票是否存在
        stock = await stock_service.get_stock_by_id(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")

        # 計算日期範圍
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # 執行數據收集（domain service）
        collect_result = await data_collection_service.collect_stock_data(
            db,
            stock_id=stock_id,
            start_date=start_date,
            end_date=end_date
        )

        return DataCollectionResponse(
            success=collect_result.status == collect_result.status.SUCCESS,
            message="數據刷新完成" if collect_result.status == collect_result.status.SUCCESS else "數據刷新失敗",
            data_points=collect_result.records_collected,
            errors=collect_result.errors
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"數據刷新失敗: {str(e)}")


@router.post("/collect", response_model=DataCollectionResponse)
async def collect_stock_data(
    request: DataCollectionRequest,
    db: AsyncSession = Depends(get_database_session),
    data_collection_service: DataCollectionService = Depends(get_data_collection_service_clean),
    stock_service: StockService = Depends(get_stock_service)
):
    """
    收集指定股票的數據
    """
    try:
        stock = await stock_service.get_stock_by_symbol(db, request.symbol)

        result = await data_collection_service.collect_stock_data(
            db,
            stock_id=stock.id,
            start_date=request.start_date,
            end_date=request.end_date
        )

        return DataCollectionResponse(
            success=result.status == result.status.SUCCESS,
            message="數據收集完成" if result.status == result.status.SUCCESS else "數據收集失敗",
            data_points=result.records_collected,
            errors=result.errors
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"數據收集失敗: {str(e)}")


@router.post("/collect-all", response_model=Dict[str, Any])
async def collect_all_stocks_data(
    days: int = 7,
    db: AsyncSession = Depends(get_database_session),
    data_collection_service: DataCollectionService = Depends(get_data_collection_service_clean)
):
    """
    收集所有活躍股票的數據
    """
    try:
        summary = await data_collection_service.collect_active_stocks_data(
            db,
            days=days
        )

        return {
            "success": summary.successful_stocks == summary.total_stocks,
            "message": f"批次收集完成，處理了 {summary.total_stocks} 隻股票",
            "processed": summary.total_stocks,
            "successful": summary.successful_stocks,
            "failed": summary.failed_stocks,
            "errors": [error for result in summary.results for error in result.errors][:50]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批次收集失敗: {str(e)}")


@router.post("/collect-batch", response_model=Dict[str, Any])
async def collect_batch_stocks_data(
    request: BatchCollectionRequest,
    db: AsyncSession = Depends(get_database_session),
    data_collection_service: DataCollectionService = Depends(get_data_collection_service_clean)
):
    """
    批次收集指定股票的數據
    """
    try:
        if request.use_stock_list and request.stocks:
            stock_entries = request.stocks
        else:
            active_stocks = await data_collection_service.stock_repo.get_active_stocks(db)
            stock_entries = [{"symbol": stock.symbol, "market": stock.market} for stock in active_stocks]

        summary = await data_collection_service.collect_batch_stocks_data(
            db,
            stock_list=stock_entries,
            start_date=request.start_date,
            end_date=request.end_date
        )

        return {
            "success": summary["success"],
            "message": summary["message"],
            "processed": summary["total_stocks"],
            "successful": summary["success_count"],
            "failed": summary["error_count"],
            "errors": summary["collection_errors"][:50]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批次收集失敗: {str(e)}")