"""
股票CRUD操作相關API端點
負責: POST /, PUT /{stock_id}, DELETE /{stock_id}, /batch
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from core.database import get_db_session
from models.repositories.crud_stock import stock_crud
from api.schemas.stocks import (
    StockResponse,
    StockCreateRequest,
    StockUpdateRequest,
    StockBatchCreateRequest
)

router = APIRouter()


@router.post("/", response_model=StockResponse)
async def create_stock(
    stock: StockCreateRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    創建新股票
    """
    try:
        # 檢查股票是否已存在
        existing_stock = await stock_crud.get_by_symbol(db, symbol=stock.symbol)
        if existing_stock:
            raise HTTPException(
                status_code=400,
                detail=f"股票代號 {stock.symbol} 已存在"
            )

        # 創建股票
        created_stock = await stock_crud.create(db, obj_in=stock)
        return StockResponse.model_validate(created_stock)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"創建股票失敗: {str(e)}")


@router.put("/{stock_id}", response_model=StockResponse)
async def update_stock(
    stock_id: int,
    stock_update: StockUpdateRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    更新股票資訊
    """
    try:
        # 檢查股票是否存在
        stock = await stock_crud.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")

        # 更新股票
        updated_stock = await stock_crud.update(db, db_obj=stock, obj_in=stock_update)
        return StockResponse.model_validate(updated_stock)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新股票失敗: {str(e)}")


@router.delete("/{stock_id}")
async def delete_stock(
    stock_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """
    刪除股票
    """
    try:
        # 檢查股票是否存在
        stock = await stock_crud.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")

        # 刪除股票
        await stock_crud.remove(db, id=stock_id)

        return {"message": f"股票 {stock.symbol} 已刪除"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除股票失敗: {str(e)}")


@router.post("/batch", response_model=Dict[str, Any])
async def create_stocks_batch(
    request: StockBatchCreateRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    批次創建股票
    """
    try:
        created_stocks = []
        failed_stocks = []
        skipped_stocks = []

        for stock_data in request.stocks:
            try:
                # 檢查股票是否已存在
                existing_stock = await stock_crud.get_by_symbol(
                    db, symbol=stock_data.symbol
                )
                if existing_stock:
                    skipped_stocks.append({
                        "symbol": stock_data.symbol,
                        "reason": "股票已存在"
                    })
                    continue

                # 創建股票
                created_stock = await stock_crud.create(db, obj_in=stock_data)
                created_stocks.append(StockResponse.model_validate(created_stock))

            except Exception as e:
                failed_stocks.append({
                    "symbol": stock_data.symbol,
                    "error": str(e)
                })

        return {
            "success": True,
            "created": len(created_stocks),
            "skipped": len(skipped_stocks),
            "failed": len(failed_stocks),
            "created_stocks": created_stocks,
            "skipped_stocks": skipped_stocks,
            "failed_stocks": failed_stocks,
            "message": f"批次處理完成：創建 {len(created_stocks)} 隻，跳過 {len(skipped_stocks)} 隻，失敗 {len(failed_stocks)} 隻"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批次創建失敗: {str(e)}")