"""
股票清單相關API端點
負責: GET /, /active, /search, /simple
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any

from core.database import get_db_session
from models.repositories.crud_stock import stock_crud
from api.schemas.stocks import StockResponse, StockListResponse
from api.utils.cache import get_cache_key, get_cached_data, set_cached_data

router = APIRouter()


@router.get("/", response_model=StockListResponse)
async def get_stocks(
    market: Optional[str] = Query(None, description="市場代碼 (TW/US)"),
    is_active: Optional[bool] = Query(True, description="股票狀態篩選"),
    search: Optional[str] = Query(None, description="搜尋關鍵字（股票代號或名稱）"),
    page: int = Query(1, ge=1, description="頁碼"),
    per_page: int = Query(50, ge=1, le=200, description="每頁數量"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    取得股票清單（支援過濾和分頁）
    """
    try:
        # 計算分頁偏移量
        offset = (page - 1) * per_page

        # 構建快取鍵
        cache_key = get_cache_key("stocks_list", market)

        # 如果沒有搜尋條件且頁數為1，嘗試從快取獲取
        if not search and page == 1 and per_page == 50:
            cached_data = get_cached_data(cache_key)
            if cached_data:
                return StockListResponse(**cached_data)

        # 從資料庫獲取
        stocks, total = await stock_crud.get_multi_with_filter(
            db,
            market=market,
            is_active=is_active,
            search=search,
            offset=offset,
            limit=per_page
        )

        # 計算總頁數
        total_pages = (total + per_page - 1) // per_page

        result = {
            "items": [StockResponse.model_validate(stock) for stock in stocks],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages
        }

        # 如果是第一頁且沒有搜尋條件，設置快取
        if not search and page == 1 and per_page == 50:
            set_cached_data(cache_key, result, ttl=300)

        return StockListResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得股票清單失敗: {str(e)}")


@router.get("/active", response_model=List[Dict[str, Any]])
async def get_active_stocks(
    market: Optional[str] = Query(None, description="市場代碼 (TW/US)"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    取得活躍股票清單（快速API，用於下拉選單等）
    """
    try:
        cache_key = get_cache_key("active_stocks", market)

        # 嘗試從快取獲取
        cached_data = get_cached_data(cache_key)
        if cached_data:
            return cached_data

        # 從資料庫獲取活躍股票
        stocks = await stock_crud.get_active_stocks(db, market=market)

        # 轉換為簡化格式
        result = [
            {
                "id": stock.id,
                "symbol": stock.symbol,
                "name": stock.name,
                "market": stock.market
            }
            for stock in stocks
        ]

        # 設置快取（較長時間，因為活躍狀態變化較少）
        set_cached_data(cache_key, result, ttl=1800)  # 30分鐘

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得活躍股票失敗: {str(e)}")


@router.get("/search", response_model=StockListResponse)
async def search_stocks(
    q: str = Query(..., description="搜尋關鍵字"),
    market: Optional[str] = Query(None, description="市場代碼 (TW/US)"),
    page: int = Query(1, ge=1, description="頁碼"),
    per_page: int = Query(20, ge=1, le=100, description="每頁數量"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    搜尋股票（支援股票代號和名稱模糊搜尋）
    """
    try:
        offset = (page - 1) * per_page

        # 使用通用搜尋功能
        stocks, total = await stock_crud.get_multi_with_filter(
            db,
            market=market,
            is_active=True,  # 搜尋時只顯示活躍股票
            search=q,
            offset=offset,
            limit=per_page
        )

        total_pages = (total + per_page - 1) // per_page

        return StockListResponse(
            items=[StockResponse.model_validate(stock) for stock in stocks],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜尋股票失敗: {str(e)}")


@router.get("/simple", response_model=List[StockResponse])
async def get_simple_stocks(
    market: Optional[str] = Query(None, description="市場代碼 (TW/US)"),
    limit: int = Query(100, ge=1, le=1000, description="返回數量限制"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    取得簡化股票清單（不分頁，用於快速載入）
    """
    try:
        cache_key = get_cache_key(f"simple_stocks_{limit}", market)

        # 嘗試從快取獲取
        cached_data = get_cached_data(cache_key)
        if cached_data:
            return [StockResponse(**item) for item in cached_data]

        # 從資料庫獲取
        stocks = await stock_crud.get_active_stocks(db, market=market, limit=limit)

        result = [StockResponse.model_validate(stock) for stock in stocks]

        # 轉換為可序列化的格式
        serializable_result = [stock.model_dump() for stock in result]
        set_cached_data(cache_key, serializable_result, ttl=600)  # 10分鐘

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得簡化股票清單失敗: {str(e)}")