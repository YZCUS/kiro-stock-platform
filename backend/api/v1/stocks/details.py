"""
股票詳情相關API端點
負責: GET /{stock_id}, /{symbol}/signals
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

from core.database import get_db_session
from models.repositories.crud_stock import stock_crud
from models.repositories.crud_trading_signal import trading_signal_crud
from api.schemas.stocks import StockResponse, TradingSignalResponse

router = APIRouter()


@router.get("/{stock_id}", response_model=StockResponse)
async def get_stock(
    stock_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """
    取得單個股票詳細資訊
    """
    try:
        stock = await stock_crud.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")

        return StockResponse.model_validate(stock)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得股票詳情失敗: {str(e)}")


@router.get("/{stock_id}/data", response_model=Dict[str, Any])
async def get_stock_data(
    stock_id: int,
    include_prices: bool = Query(True, description="是否包含價格數據"),
    include_indicators: bool = Query(True, description="是否包含技術指標"),
    include_signals: bool = Query(True, description="是否包含交易信號"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    取得股票完整數據（包含價格、指標、信號等）
    """
    try:
        # 檢查股票是否存在
        stock = await stock_crud.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")

        result = {
            "stock": StockResponse.model_validate(stock)
        }

        # 根據請求參數添加相關數據
        if include_prices:
            # 這裡可以添加價格數據邏輯
            result["prices"] = {"message": "價格數據將在後續版本實現"}

        if include_indicators:
            # 這裡可以添加指標數據邏輯
            result["indicators"] = {"message": "指標數據將在後續版本實現"}

        if include_signals:
            # 獲取最近的交易信號
            signals = await trading_signal_crud.get_by_stock_id(
                db, stock_id=stock_id, limit=10
            )
            result["signals"] = [
                TradingSignalResponse.model_validate(signal) for signal in signals
            ]

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得股票數據失敗: {str(e)}")


@router.get("/{symbol}/signals", response_model=List[TradingSignalResponse])
async def get_stock_signals_by_symbol(
    symbol: str,
    limit: int = Query(50, ge=1, le=200, description="返回信號數量"),
    signal_type: str = Query(None, description="信號類型過濾"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    根據股票代號取得交易信號
    """
    try:
        # 先根據symbol找到股票
        stock = await stock_crud.get_by_symbol(db, symbol=symbol)
        if not stock:
            raise HTTPException(status_code=404, detail=f"股票代號 {symbol} 不存在")

        # 取得交易信號
        signals = await trading_signal_crud.get_by_stock_id(
            db,
            stock_id=stock.id,
            signal_type=signal_type,
            limit=limit
        )

        return [TradingSignalResponse.model_validate(signal) for signal in signals]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得交易信號失敗: {str(e)}")