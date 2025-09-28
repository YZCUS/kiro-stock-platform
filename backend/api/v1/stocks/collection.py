"""
數據收集相關API端點
負責: /refresh, /collect, /collect-all, /collect-batch
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
from datetime import date, timedelta

from core.database import get_db_session
from services.data.collection import data_collection_service
from models.repositories.crud_stock import stock_crud
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
    db: AsyncSession = Depends(get_db_session)
):
    """
    手動更新股票數據
    """
    try:
        # 檢查股票是否存在
        stock = await stock_crud.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")

        # 計算日期範圍
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # 執行數據收集
        result = await data_collection_service.collect_stock_data(
            db, stock.symbol, stock.market, start_date, end_date
        )

        return DataCollectionResponse(
            success=result.success,
            message=result.message,
            data_points=result.data_points_collected,
            errors=result.errors
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"數據刷新失敗: {str(e)}")


@router.post("/collect", response_model=DataCollectionResponse)
async def collect_stock_data(
    request: DataCollectionRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    收集指定股票的數據
    """
    try:
        # 執行數據收集
        result = await data_collection_service.collect_stock_data(
            db,
            symbol=request.symbol,
            market=request.market,
            start_date=request.start_date,
            end_date=request.end_date
        )

        return DataCollectionResponse(
            success=result.success,
            message=result.message,
            data_points=result.data_points_collected,
            errors=result.errors
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"數據收集失敗: {str(e)}")


@router.post("/collect-all", response_model=Dict[str, Any])
async def collect_all_stocks_data(
    days: int = 7,
    db: AsyncSession = Depends(get_db_session)
):
    """
    收集所有活躍股票的數據
    """
    try:
        # 獲取所有活躍股票
        active_stocks = await stock_crud.get_active_stocks(db)

        if not active_stocks:
            return {
                "success": True,
                "message": "沒有活躍股票需要收集數據",
                "processed": 0,
                "successful": 0,
                "failed": 0,
                "errors": []
            }

        # 計算日期範圍
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        processed = 0
        successful = 0
        failed = 0
        all_errors = []

        # 逐個處理股票
        for stock in active_stocks:
            processed += 1
            try:
                result = await data_collection_service.collect_stock_data(
                    db, stock.symbol, stock.market, start_date, end_date
                )

                if result.success:
                    successful += 1
                else:
                    failed += 1
                    all_errors.extend(result.errors)

            except Exception as e:
                failed += 1
                all_errors.append(f"{stock.symbol}: {str(e)}")

        return {
            "success": True,
            "message": f"批次收集完成，處理了 {processed} 隻股票",
            "processed": processed,
            "successful": successful,
            "failed": failed,
            "errors": all_errors[:50]  # 限制錯誤數量
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批次收集失敗: {str(e)}")


@router.post("/collect-batch", response_model=Dict[str, Any])
async def collect_batch_stocks_data(
    request: BatchCollectionRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    批次收集指定股票的數據
    """
    try:
        stocks_to_process = []

        if request.use_stock_list and request.stocks:
            # 使用提供的股票列表
            stocks_to_process = [
                {"symbol": stock["symbol"], "market": stock["market"]}
                for stock in request.stocks
            ]
        else:
            # 使用資料庫中的活躍股票
            active_stocks = await stock_crud.get_active_stocks(db)
            stocks_to_process = [
                {"symbol": stock.symbol, "market": stock.market}
                for stock in active_stocks
            ]

        if not stocks_to_process:
            return {
                "success": True,
                "message": "沒有股票需要收集數據",
                "processed": 0,
                "successful": 0,
                "failed": 0,
                "errors": []
            }

        processed = 0
        successful = 0
        failed = 0
        all_errors = []

        # 逐個處理股票
        for stock_info in stocks_to_process:
            processed += 1
            try:
                result = await data_collection_service.collect_stock_data(
                    db,
                    symbol=stock_info["symbol"],
                    market=stock_info["market"],
                    start_date=request.start_date,
                    end_date=request.end_date
                )

                if result.success:
                    successful += 1
                else:
                    failed += 1
                    all_errors.extend(result.errors)

            except Exception as e:
                failed += 1
                all_errors.append(f"{stock_info['symbol']}: {str(e)}")

        return {
            "success": True,
            "message": f"批次收集完成，處理了 {processed} 隻股票",
            "processed": processed,
            "successful": successful,
            "failed": failed,
            "errors": all_errors[:50]  # 限制錯誤數量
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批次收集失敗: {str(e)}")