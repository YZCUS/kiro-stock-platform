"""
自選股相關的 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.auth_dependencies import get_current_active_user
from api.schemas.watchlist import (
    WatchlistAdd,
    WatchlistItemResponse,
    WatchlistResponse,
    WatchlistStockDetail,
    PopularStock
)
from domain.models.user import User
from domain.models.user_watchlist import UserWatchlist
from domain.models.stock import Stock
from typing import List

router = APIRouter(prefix="/watchlist", tags=["自選股"])


@router.get("/", response_model=WatchlistResponse)
async def get_my_watchlist(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取得當前用戶的自選股清單

    Args:
        current_user: 當前用戶
        db: 資料庫 session

    Returns:
        WatchlistResponse: 自選股清單
    """
    def _get_watchlist_with_stocks(session):
        items = UserWatchlist.get_user_watchlist(session, current_user.id)
        # Access stock relationship within sync context
        result = []
        for item in items:
            result.append({
                'id': item.id,
                'stock_id': item.stock_id,
                'user_id': str(item.user_id),
                'created_at': item.created_at,
                'stock': item.stock.to_dict() if item.stock else None
            })
        return result

    items_data = await db.run_sync(_get_watchlist_with_stocks)

    items = [WatchlistItemResponse(**item_data) for item_data in items_data]

    return WatchlistResponse(
        total=len(items),
        items=items
    )


@router.get("/detailed", response_model=List[WatchlistStockDetail])
async def get_my_watchlist_detailed(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取得當前用戶的自選股清單（包含最新價格）

    Args:
        current_user: 當前用戶
        db: 資料庫 session

    Returns:
        List[WatchlistStockDetail]: 自選股詳細資訊清單
    """
    def _get_detailed_watchlist(session):
        items = UserWatchlist.get_user_watchlist(session, current_user.id)
        detailed_items = []
        for item in items:
            stock_data = item.get_stock_with_latest_price()
            if stock_data:
                detailed_items.append(stock_data)
        return detailed_items

    detailed_items_data = await db.run_sync(_get_detailed_watchlist)

    return [WatchlistStockDetail(**item_data) for item_data in detailed_items_data]


@router.post("/", response_model=WatchlistItemResponse, status_code=status.HTTP_201_CREATED)
async def add_to_watchlist(
    watchlist_data: WatchlistAdd,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    新增股票到自選股

    Args:
        watchlist_data: 要新增的股票ID
        current_user: 當前用戶
        db: 資料庫 session

    Returns:
        WatchlistItemResponse: 新增的自選股項目

    Raises:
        HTTPException: 如果股票不存在
    """
    # 檢查股票是否存在
    stock = await db.run_sync(
        lambda session: session.query(Stock).filter(Stock.id == watchlist_data.stock_id).first()
    )

    if stock is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="股票不存在"
        )

    # 新增到自選股
    watchlist_item = await db.run_sync(
        lambda session: UserWatchlist.add_to_watchlist(
            session,
            user_id=current_user.id,
            stock_id=watchlist_data.stock_id
        )
    )
    await db.commit()
    await db.refresh(watchlist_item)

    return WatchlistItemResponse(
        id=watchlist_item.id,
        stock_id=watchlist_item.stock_id,
        user_id=str(watchlist_item.user_id),
        created_at=watchlist_item.created_at,
        stock=watchlist_item.stock.to_dict() if watchlist_item.stock else None
    )


@router.delete("/{stock_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_watchlist(
    stock_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    從自選股移除股票

    Args:
        stock_id: 股票ID
        current_user: 當前用戶
        db: 資料庫 session

    Raises:
        HTTPException: 如果股票不在自選股中
    """
    removed = await db.run_sync(
        lambda session: UserWatchlist.remove_from_watchlist(
            session,
            user_id=current_user.id,
            stock_id=stock_id
        )
    )

    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="該股票不在您的自選股中"
        )

    await db.commit()


@router.get("/check/{stock_id}", response_model=dict)
async def check_in_watchlist(
    stock_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    檢查股票是否在自選股中

    Args:
        stock_id: 股票ID
        current_user: 當前用戶
        db: 資料庫 session

    Returns:
        dict: {"in_watchlist": bool, "stock_id": int}
    """
    is_in_watchlist = await db.run_sync(
        lambda session: UserWatchlist.is_in_watchlist(
            session,
            user_id=current_user.id,
            stock_id=stock_id
        )
    )

    return {
        "in_watchlist": is_in_watchlist,
        "stock_id": stock_id
    }


@router.get("/popular", response_model=List[PopularStock])
async def get_popular_stocks(
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    取得熱門自選股（被最多用戶加入的股票）

    Args:
        limit: 返回數量限制
        db: 資料庫 session

    Returns:
        List[PopularStock]: 熱門自選股清單
    """
    popular_stocks = await db.run_sync(
        lambda session: UserWatchlist.get_popular_stocks(session, limit)
    )

    return [
        PopularStock(
            stock=item['stock'].to_dict(),
            watchlist_count=item['watchlist_count']
        )
        for item in popular_stocks
    ]


@router.get("/stats")
async def get_watchlist_stats(
    db: AsyncSession = Depends(get_db)
):
    """
    取得自選股統計資訊（不需要登入）

    Returns:
        dict: 包含不重複股票數量等統計資訊
    """
    from sqlalchemy import select, func, distinct

    # 計算所有 watchlist 中不重複的股票數量
    query = select(func.count(distinct(UserWatchlist.stock_id)))
    result = await db.execute(query)
    unique_stocks_count = result.scalar() or 0

    # 計算總共有多少筆 watchlist 記錄
    total_query = select(func.count(UserWatchlist.id))
    total_result = await db.execute(total_query)
    total_watchlist_entries = total_result.scalar() or 0

    return {
        "unique_stocks_count": unique_stocks_count,
        "total_entries": total_watchlist_entries
    }
