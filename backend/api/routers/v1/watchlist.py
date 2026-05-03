"""
Watchlist compatibility API.

The active data model is user_stock_lists/user_stock_list_items. These endpoints
preserve the old /watchlist contract by mapping it to the user's default list.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_database_session
from core.auth_dependencies import get_current_active_user
from api.schemas.watchlist import (
    PopularStock,
    WatchlistAdd,
    WatchlistItemResponse,
    WatchlistResponse,
    WatchlistStockDetail,
)
from domain.market_data.daily_prices import fetch_latest_daily_price
from domain.models.stock import Stock
from domain.models.user import User
from domain.models.user_stock_list import UserStockList, UserStockListItem

router = APIRouter(prefix="/watchlist", tags=["自選股"])

DEFAULT_WATCHLIST_NAME = "我的觀察清單"


async def _get_or_create_default_list(db: AsyncSession, user_id) -> UserStockList:
    result = await db.execute(
        select(UserStockList)
        .where(UserStockList.user_id == user_id, UserStockList.is_default == True)
        .order_by(UserStockList.sort_order, UserStockList.created_at, UserStockList.id)
        .limit(1)
    )
    stock_list = result.scalar_one_or_none()
    if stock_list:
        return stock_list

    named_result = await db.execute(
        select(UserStockList)
        .where(
            UserStockList.user_id == user_id,
            UserStockList.name == DEFAULT_WATCHLIST_NAME,
        )
        .order_by(UserStockList.sort_order, UserStockList.created_at, UserStockList.id)
        .limit(1)
    )
    stock_list = named_result.scalar_one_or_none()
    if stock_list:
        stock_list.is_default = True
        await db.flush()
        return stock_list

    stock_list = UserStockList(
        user_id=user_id,
        name=DEFAULT_WATCHLIST_NAME,
        description="預設觀察清單",
        is_default=True,
        sort_order=0,
    )
    db.add(stock_list)
    await db.flush()
    return stock_list


def _item_response(item: UserStockListItem, user_id: str) -> WatchlistItemResponse:
    return WatchlistItemResponse(
        id=item.id,
        stock_id=item.stock_id,
        user_id=user_id,
        created_at=item.created_at,
        stock=item.stock.to_dict() if item.stock else None,
    )


@router.get("/", response_model=WatchlistResponse)
async def get_my_watchlist(
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user),
):
    """Return the current user's default observation list."""
    stock_list = await _get_or_create_default_list(db, current_user.id)
    await db.commit()

    result = await db.execute(
        select(UserStockListItem)
        .where(UserStockListItem.list_id == stock_list.id)
        .options(selectinload(UserStockListItem.stock))
        .order_by(UserStockListItem.sort_order, UserStockListItem.created_at)
    )
    items = result.scalars().all()
    return WatchlistResponse(
        total=len(items),
        items=[_item_response(item, str(current_user.id)) for item in items],
    )


@router.get("/detailed", response_model=list[WatchlistStockDetail])
async def get_my_watchlist_detailed(
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user),
):
    """Return default observation list stocks with latest price data."""
    stock_list = await _get_or_create_default_list(db, current_user.id)
    await db.commit()

    result = await db.execute(
        select(UserStockListItem, Stock)
        .join(Stock, Stock.id == UserStockListItem.stock_id)
        .where(UserStockListItem.list_id == stock_list.id)
        .order_by(UserStockListItem.sort_order, UserStockListItem.created_at)
    )

    response = []
    for item, stock in result.all():
        latest = await fetch_latest_daily_price(db, stock.id)
        latest_price = None
        if latest:
            latest_price = {
                "close": float(latest.close_price) if latest.close_price else None,
                "date": latest.date.isoformat() if latest.date else None,
                "volume": latest.volume,
            }

        response.append(
            WatchlistStockDetail(
                watchlist_id=item.id,
                stock=stock.to_dict(),
                added_at=item.created_at.isoformat() if item.created_at else None,
                latest_price=latest_price,
            )
        )

    return response


@router.post("/", response_model=WatchlistItemResponse)
async def add_to_watchlist(
    watchlist_data: WatchlistAdd,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user),
):
    """Add a stock to the user's default observation list."""
    stock = await db.get(Stock, watchlist_data.stock_id)
    if not stock:
        raise HTTPException(status_code=404, detail="股票不存在")

    stock_list = await _get_or_create_default_list(db, current_user.id)
    result = await db.execute(
        select(UserStockListItem).where(
            UserStockListItem.list_id == stock_list.id,
            UserStockListItem.stock_id == watchlist_data.stock_id,
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        item = UserStockListItem(
            list_id=stock_list.id, stock_id=watchlist_data.stock_id
        )
        db.add(item)
        await db.flush()

    await db.commit()
    await db.refresh(item)
    item.stock = stock
    return _item_response(item, str(current_user.id))


@router.delete("/{stock_id}")
async def remove_from_watchlist(
    stock_id: int,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user),
):
    """Remove a stock from the user's default observation list."""
    stock_list = await _get_or_create_default_list(db, current_user.id)
    result = await db.execute(
        select(UserStockListItem).where(
            UserStockListItem.list_id == stock_list.id,
            UserStockListItem.stock_id == stock_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="股票不在自選股中")

    await db.delete(item)
    await db.commit()
    return {"message": "已從自選股移除", "stock_id": stock_id}


@router.get("/check/{stock_id}")
async def check_in_watchlist(
    stock_id: int,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user),
):
    """Check whether a stock is in the user's default observation list."""
    stock_list = await _get_or_create_default_list(db, current_user.id)
    await db.commit()

    result = await db.execute(
        select(UserStockListItem.id).where(
            UserStockListItem.list_id == stock_list.id,
            UserStockListItem.stock_id == stock_id,
        )
    )
    return {"in_watchlist": result.scalar_one_or_none() is not None, "stock_id": stock_id}


@router.get("/popular", response_model=list[PopularStock])
async def get_popular_stocks(
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_database_session),
):
    """Return stocks most frequently included in user observation lists."""
    watchlist_count = func.count(UserStockListItem.id).label("watchlist_count")
    result = await db.execute(
        select(Stock, watchlist_count)
        .join(UserStockListItem, UserStockListItem.stock_id == Stock.id)
        .group_by(Stock.id)
        .order_by(watchlist_count.desc())
        .limit(limit)
    )
    return [
        PopularStock(stock=stock.to_dict(), watchlist_count=count)
        for stock, count in result.all()
    ]


@router.get("/stats")
async def get_watchlist_stats(db: AsyncSession = Depends(get_database_session)):
    """Return aggregate observation list statistics."""
    distinct_result = await db.execute(
        select(func.count(distinct(UserStockListItem.stock_id)))
    )
    total_result = await db.execute(select(func.count(UserStockListItem.id)))

    unique_stocks_count = distinct_result.scalar() or 0
    return {
        "unique_stocks_count": unique_stocks_count,
        "total_unique_stocks": unique_stocks_count,
        "total_entries": total_result.scalar() or 0,
    }
