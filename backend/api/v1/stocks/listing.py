"""
股票清單相關API端點
負責: GET /, /active, /search, /simple
"""

from typing import List, Optional, Dict, Any
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.dependencies import get_database_session, get_stock_service
from api.schemas.stocks import StockResponse, StockListResponse, LatestPriceInfo
from domain.services.stock_service import StockService
from domain.models.price_history import PriceHistory

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=StockListResponse)
async def get_stocks(
    market: Optional[str] = Query(None, description="市場代碼 (TW/US)"),
    is_active: Optional[bool] = Query(True, description="股票狀態篩選"),
    search: Optional[str] = Query(None, description="搜尋關鍵字（股票代號或名稱）"),
    page: int = Query(1, ge=1, description="頁碼"),
    per_page: int = Query(50, ge=1, le=200, description="每頁數量"),
    db: AsyncSession = Depends(get_database_session),
    stock_service: StockService = Depends(get_stock_service),
):
    """
    取得股票清單（支援過濾和分頁）
    """
    try:
        result = await stock_service.get_stock_list(
            db=db,
            market=market,
            is_active=is_active,
            search=search,
            page=page,
            per_page=per_page,
        )

        stock_ids = [
            stock.id if hasattr(stock, "id") else stock["id"]
            for stock in result["items"]
        ]
        prices_by_stock = {}

        if stock_ids:
            price_rank = (
                func.row_number()
                .over(
                    partition_by=PriceHistory.stock_id,
                    order_by=PriceHistory.date.desc(),
                )
                .label("price_rank")
            )
            ranked_prices = (
                select(
                    PriceHistory.stock_id.label("stock_id"),
                    PriceHistory.date.label("date"),
                    PriceHistory.close_price.label("close_price"),
                    PriceHistory.volume.label("volume"),
                    PriceHistory.updated_at.label("updated_at"),
                    price_rank,
                )
                .where(PriceHistory.stock_id.in_(stock_ids))
                .subquery()
            )
            prices_query = (
                select(ranked_prices)
                .where(ranked_prices.c.price_rank <= 2)
                .order_by(ranked_prices.c.stock_id, ranked_prices.c.date.desc())
            )
            prices_result = await db.execute(prices_query)

            for price in prices_result.mappings().all():
                prices_by_stock.setdefault(price["stock_id"], []).append(dict(price))

        # 為每個股票加入本地最新價格資訊
        stock_responses = []
        for stock in result["items"]:
            # stock_service 返回的是 dict，需要用 ['id'] 訪問
            stock_id = stock.id if hasattr(stock, "id") else stock["id"]
            prices = prices_by_stock.get(stock_id, [])

            # 轉換股票資料
            stock_data = StockResponse.model_validate(stock).model_dump()

            # 如果有價格資料，計算最新價格和漲跌
            if prices and len(prices) > 0:
                latest = prices[0]
                close_price = (
                    float(latest["close_price"])
                    if latest["close_price"] is not None
                    else None
                )

                change = None
                change_percent = None
                if close_price is not None and len(prices) > 1:
                    prev_close = (
                        float(prices[1]["close_price"])
                        if prices[1]["close_price"] is not None
                        else None
                    )
                    if prev_close and prev_close != 0:
                        change = close_price - prev_close
                        change_percent = (change / prev_close) * 100

                stock_data["latest_price"] = {
                    "close": close_price,
                    "change": change,
                    "change_percent": change_percent,
                    "date": latest["date"].isoformat() if latest["date"] else None,
                    "volume": latest["volume"],
                    **stock_service.build_price_freshness(latest),
                }

            stock_responses.append(StockResponse(**stock_data))

        return StockListResponse(
            items=stock_responses,
            total=result["total"],
            page=result["page"],
            per_page=result["per_page"],
            total_pages=result["total_pages"],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得股票清單失敗: {str(e)}")


@router.get("/active", response_model=List[Dict[str, Any]])
async def get_active_stocks(
    market: Optional[str] = Query(None, description="市場代碼 (TW/US)"),
    db: AsyncSession = Depends(get_database_session),
    stock_service: StockService = Depends(get_stock_service),
):
    """
    取得活躍股票清單（快速API，用於下拉選單等）
    """
    try:
        result = await stock_service.get_active_stocks(db, market=market)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得活躍股票失敗: {str(e)}")


@router.get("/search", response_model=StockListResponse)
async def search_stocks(
    q: str = Query(..., description="搜尋關鍵字"),
    market: Optional[str] = Query(None, description="市場代碼 (TW/US)"),
    page: int = Query(1, ge=1, description="頁碼"),
    per_page: int = Query(20, ge=1, le=100, description="每頁數量"),
    db: AsyncSession = Depends(get_database_session),
    stock_service: StockService = Depends(get_stock_service),
):
    """
    搜尋股票（支援股票代號和名稱模糊搜尋）
    """
    try:
        result = await stock_service.get_stock_list(
            db=db, market=market, is_active=True, search=q, page=page, per_page=per_page
        )

        items = [StockResponse.model_validate(item) for item in result["items"]]

        return StockListResponse(
            items=items,
            total=result["total"],
            page=result["page"],
            per_page=result["per_page"],
            total_pages=result["total_pages"],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜尋股票失敗: {str(e)}")


@router.get("/simple", response_model=List[StockResponse])
async def get_simple_stocks(
    market: Optional[str] = Query(None, description="市場代碼 (TW/US)"),
    limit: int = Query(100, ge=1, le=1000, description="返回數量限制"),
    db: AsyncSession = Depends(get_database_session),
    stock_service: StockService = Depends(get_stock_service),
):
    """
    取得簡化股票清單（不分頁，用於快速載入）
    """
    try:
        result = await stock_service.get_stock_list(
            db=db, market=market, is_active=True, search=None, page=1, per_page=limit
        )

        items = [StockResponse.model_validate(item) for item in result["items"]]
        return items

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得簡化股票清單失敗: {str(e)}")
