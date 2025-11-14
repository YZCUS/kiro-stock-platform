"""
股票CRUD操作相關API端點
負責: POST /, PUT /{stock_id}, DELETE /{stock_id}, /batch
"""

from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_database_session, get_stock_service
from api.schemas.stocks import (
    StockResponse,
    StockCreateRequest,
    StockUpdateRequest,
    StockBatchCreateRequest,
)
from domain.services.stock_service import StockService

router = APIRouter()


@router.post("/", response_model=StockResponse)
async def create_stock(
    stock: StockCreateRequest,
    db: AsyncSession = Depends(get_database_session),
    stock_service: StockService = Depends(get_stock_service),
):
    """
    創建新股票

    在創建前會驗證股票代號是否有效（透過 Yahoo Finance）
    """
    try:
        # 驗證股票代號是否有效
        from infrastructure.external.yfinance_wrapper import YFinanceWrapper

        yf_wrapper = YFinanceWrapper()
        ticker = yf_wrapper.get_ticker(stock.symbol)
        info = ticker.info

        # 檢查股票代號是否有效（必須有公司名稱或市場價格）
        if not info or "symbol" not in info:
            raise HTTPException(
                status_code=400,
                detail=f"股票代號 {stock.symbol} 無效或不存在於 Yahoo Finance",
            )

        # 進一步驗證：有效股票應該有公司名稱或市場價格
        has_name = info.get("longName") or info.get("shortName")
        has_price = info.get("regularMarketPrice") or info.get("currentPrice")

        if not has_name and not has_price:
            raise HTTPException(
                status_code=400,
                detail=f"股票代號 {stock.symbol} 無法取得有效資訊，可能是無效或已下市的股票",
            )

        # 如果未提供公司名稱，從 Yahoo Finance 獲取
        if not stock.name or stock.name == stock.symbol:
            stock.name = info.get("longName") or info.get("shortName") or stock.symbol

        created_stock = await stock_service.create_stock(db, stock)
        return StockResponse.model_validate(created_stock)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"創建股票失敗: {str(e)}")


@router.put("/{stock_id}", response_model=StockResponse)
async def update_stock(
    stock_id: int,
    stock_update: StockUpdateRequest,
    db: AsyncSession = Depends(get_database_session),
    stock_service: StockService = Depends(get_stock_service),
):
    """
    更新股票資訊
    """
    try:
        updated_stock = await stock_service.update_stock(db, stock_id, stock_update)
        return StockResponse.model_validate(updated_stock)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新股票失敗: {str(e)}")


@router.delete("/{stock_id}")
async def delete_stock(
    stock_id: int,
    db: AsyncSession = Depends(get_database_session),
    stock_service: StockService = Depends(get_stock_service),
):
    """
    刪除股票
    """
    try:
        return await stock_service.delete_stock(db, stock_id)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除股票失敗: {str(e)}")


@router.post("/batch", response_model=Dict[str, Any])
async def create_stocks_batch(
    request: StockBatchCreateRequest,
    db: AsyncSession = Depends(get_database_session),
    stock_service: StockService = Depends(get_stock_service),
):
    """
    批次創建股票
    """
    try:
        result = await stock_service.create_stocks_batch(db, request.stocks)

        created_items = [
            StockResponse.model_validate(item) for item in result["created_stocks"]
        ]
        result["created_stocks"] = [item.model_dump() for item in created_items]

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批次創建失敗: {str(e)}")
