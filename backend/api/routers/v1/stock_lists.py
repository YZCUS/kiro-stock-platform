"""
股票清單管理 API 路由
"""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from typing import List
from datetime import date

# 依賴注入
from app.dependencies import get_database_session
from core.database import AsyncSessionLocal
from core.auth_dependencies import get_current_active_user
from domain.market_data.daily_prices import fetch_latest_daily_price_rows_by_stock
from domain.services.strategy_signal_service import StrategySignalService

# Models
from domain.models.user import User
from domain.models.user_stock_list import UserStockList, UserStockListItem
from domain.models.stock import Stock

# Schemas
from api.schemas.stock_list import (
    StockListCreateRequest,
    StockListUpdateRequest,
    StockListReorderRequest,
    StockListResponse,
    StockListListResponse,
    StockListItemAddRequest,
    StockListItemBatchAddRequest,
    StockListItemResponse,
    StockListItemListResponse,
    StockListStocksResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)


async def _generate_signals_for_added_stock(user_id, stock_id: int) -> None:
    if AsyncSessionLocal is None:
        return

    try:
        async with AsyncSessionLocal() as db:
            await StrategySignalService().generate_signals_for_user_stock(
                db=db,
                user_id=user_id,
                stock_id=stock_id,
            )
    except Exception:
        logger.exception(
            "Failed to generate strategy signals for added stock %s",
            stock_id,
        )


def _build_price_freshness(latest_price, stale_after_days: int = 1) -> dict:
    if not latest_price:
        return {
            "is_stale": True,
            "age_days": None,
            "last_updated_at": None,
            "source": "market_data_bars",
        }

    price_date = (
        latest_price.get("date")
        if isinstance(latest_price, dict)
        else latest_price.date
    )
    updated_at = (
        latest_price.get("updated_at")
        if isinstance(latest_price, dict)
        else getattr(latest_price, "updated_at", None)
    )
    age_days = max((date.today() - price_date).days, 0) if price_date else None
    return {
        "is_stale": age_days is None or age_days > stale_after_days,
        "age_days": age_days,
        "last_updated_at": updated_at.isoformat() if updated_at else None,
        "source": "market_data_bars",
    }


# =============================================================================
# 股票清單管理端點
# =============================================================================


@router.get("/", response_model=StockListListResponse)
async def get_user_stock_lists(
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user),
):
    """獲取用戶的所有股票清單"""
    try:
        query = (
            select(
                UserStockList.id,
                UserStockList.user_id,
                UserStockList.name,
                UserStockList.description,
                UserStockList.is_default,
                UserStockList.sort_order,
                UserStockList.created_at,
                UserStockList.updated_at,
                func.count(UserStockListItem.id).label("stocks_count"),
            )
            .outerjoin(
                UserStockListItem,
                UserStockListItem.list_id == UserStockList.id,
            )
            .where(UserStockList.user_id == current_user.id)
            .group_by(
                UserStockList.id,
                UserStockList.user_id,
                UserStockList.name,
                UserStockList.description,
                UserStockList.is_default,
                UserStockList.sort_order,
                UserStockList.created_at,
                UserStockList.updated_at,
            )
            .order_by(
                UserStockList.sort_order,
                UserStockList.is_default.desc(),
                UserStockList.created_at,
            )
        )
        result = await db.execute(query)
        lists_data = [
            {
                **dict(row),
                "user_id": str(row["user_id"]),
            }
            for row in result.mappings().all()
        ]

        return StockListListResponse(
            items=[StockListResponse(**lst_data) for lst_data in lists_data],
            total=len(lists_data),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取清單失敗: {str(e)}")


@router.post("/", response_model=StockListResponse)
async def create_stock_list(
    request: StockListCreateRequest,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user),
):
    """創建新的股票清單"""
    try:
        from sqlalchemy import select

        # 檢查清單名稱是否已存在
        query = select(UserStockList).where(
            UserStockList.user_id == current_user.id, UserStockList.name == request.name
        )
        result = await db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            raise HTTPException(status_code=400, detail="清單名稱已存在")

        # 如果設置為預設清單，先取消其他預設清單
        if request.is_default:
            update_query = select(UserStockList).where(
                UserStockList.user_id == current_user.id,
                UserStockList.is_default == True,
            )
            result = await db.execute(update_query)
            default_lists = result.scalars().all()
            for lst in default_lists:
                lst.is_default = False

        # 創建新清單
        new_list = UserStockList(
            user_id=current_user.id,
            name=request.name,
            description=request.description,
            is_default=request.is_default,
        )
        db.add(new_list)
        await db.commit()
        await db.refresh(new_list)

        return StockListResponse(
            id=new_list.id,
            user_id=str(new_list.user_id),
            name=new_list.name,
            description=new_list.description,
            is_default=new_list.is_default,
            sort_order=new_list.sort_order,
            stocks_count=0,
            created_at=new_list.created_at,
            updated_at=new_list.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"創建清單失敗: {str(e)}")


@router.get("/{list_id}", response_model=StockListResponse)
async def get_stock_list(
    list_id: int,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user),
):
    """獲取單個股票清單"""
    try:
        from sqlalchemy import select

        query = select(UserStockList).where(
            UserStockList.id == list_id, UserStockList.user_id == current_user.id
        )
        result = await db.execute(query)
        stock_list = result.scalar_one_or_none()

        if not stock_list:
            raise HTTPException(status_code=404, detail="清單不存在")

        # 在同步上下文中獲取股票數量
        def _get_stocks_count(session):
            lst = session.query(UserStockList).filter_by(id=list_id).first()
            return len(lst.list_items) if lst else 0

        stocks_count = await db.run_sync(_get_stocks_count)

        return StockListResponse(
            id=stock_list.id,
            user_id=str(stock_list.user_id),
            name=stock_list.name,
            description=stock_list.description,
            is_default=stock_list.is_default,
            sort_order=stock_list.sort_order,
            stocks_count=stocks_count,
            created_at=stock_list.created_at,
            updated_at=stock_list.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取清單失敗: {str(e)}")


@router.put("/{list_id}", response_model=StockListResponse)
async def update_stock_list(
    list_id: int,
    request: StockListUpdateRequest,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user),
):
    """更新股票清單"""
    try:
        from sqlalchemy import select

        # 獲取清單
        query = select(UserStockList).where(
            UserStockList.id == list_id, UserStockList.user_id == current_user.id
        )
        result = await db.execute(query)
        stock_list = result.scalar_one_or_none()

        if not stock_list:
            raise HTTPException(status_code=404, detail="清單不存在")

        # 更新欄位
        if request.name is not None:
            # 檢查新名稱是否與其他清單衝突
            check_query = select(UserStockList).where(
                UserStockList.user_id == current_user.id,
                UserStockList.name == request.name,
                UserStockList.id != list_id,
            )
            check_result = await db.execute(check_query)
            if check_result.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="清單名稱已存在")
            stock_list.name = request.name

        if request.description is not None:
            stock_list.description = request.description

        if request.is_default is not None:
            if request.is_default:
                # 取消其他預設清單
                update_query = select(UserStockList).where(
                    UserStockList.user_id == current_user.id,
                    UserStockList.is_default == True,
                    UserStockList.id != list_id,
                )
                result = await db.execute(update_query)
                default_lists = result.scalars().all()
                for lst in default_lists:
                    lst.is_default = False
            stock_list.is_default = request.is_default

        await db.commit()
        await db.refresh(stock_list)

        # 在同步上下文中獲取股票數量
        def _get_stocks_count(session):
            # 重新獲取以確保有關聯數據
            lst = session.query(UserStockList).filter_by(id=list_id).first()
            return len(lst.list_items) if lst else 0

        stocks_count = await db.run_sync(_get_stocks_count)

        return StockListResponse(
            id=stock_list.id,
            user_id=str(stock_list.user_id),
            name=stock_list.name,
            description=stock_list.description,
            is_default=stock_list.is_default,
            sort_order=stock_list.sort_order,
            stocks_count=stocks_count,
            created_at=stock_list.created_at,
            updated_at=stock_list.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"更新清單失敗: {str(e)}")


@router.delete("/{list_id}")
async def delete_stock_list(
    list_id: int,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user),
):
    """刪除股票清單"""
    try:
        from sqlalchemy import select, delete

        # 檢查清單是否存在
        query = select(UserStockList).where(
            UserStockList.id == list_id, UserStockList.user_id == current_user.id
        )
        result = await db.execute(query)
        stock_list = result.scalar_one_or_none()

        if not stock_list:
            raise HTTPException(status_code=404, detail="清單不存在")

        # 刪除清單（會自動級聯刪除清單項目）
        delete_query = delete(UserStockList).where(UserStockList.id == list_id)
        await db.execute(delete_query)
        await db.commit()

        return {"message": "清單已刪除", "list_id": list_id}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"刪除清單失敗: {str(e)}")


# =============================================================================
# 清單項目管理端點
# =============================================================================


@router.get("/{list_id}/stocks")
async def get_list_stocks(
    list_id: int,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user),
):
    """獲取清單中的所有股票（包含最新價格和完整股票信息）"""
    try:
        from sqlalchemy.orm import selectinload

        # 驗證清單所有權
        list_query = select(UserStockList).where(
            UserStockList.id == list_id, UserStockList.user_id == current_user.id
        )
        list_result = await db.execute(list_query)
        stock_list = list_result.scalar_one_or_none()

        if not stock_list:
            raise HTTPException(status_code=404, detail="清單不存在")

        # 獲取清單項目（預載入 stock，按 sort_order 排序）
        items_query = (
            select(UserStockListItem)
            .where(UserStockListItem.list_id == list_id)
            .options(selectinload(UserStockListItem.stock))
            .order_by(UserStockListItem.sort_order, UserStockListItem.created_at)
        )
        items_result = await db.execute(items_query)
        items = items_result.scalars().all()

        stock_ids = [item.stock.id for item in items if item.stock]
        prices_by_stock = {}

        if stock_ids:
            prices_by_stock = await fetch_latest_daily_price_rows_by_stock(
                db,
                stock_ids,
                rows_per_stock=2,
            )

        # 為每個股票構建完整的響應（包含本地最新價格）
        stock_responses = []
        for item in items:
            if not item.stock:
                continue

            stock = item.stock
            prices = prices_by_stock.get(stock.id, [])

            # 構建股票響應
            stock_data = {
                "id": stock.id,
                "symbol": stock.symbol,
                "market": stock.market,
                "name": stock.name,
                "is_active": stock.is_active,
                "created_at": stock.created_at,
                "updated_at": stock.updated_at,
                "is_watchlist": False,
                "is_portfolio": False,
                "latest_price": None,
            }

            # 添加最新價格信息
            if prices and len(prices) > 0:
                latest = prices[0]
                close_price = (
                    float(latest["close_price"])
                    if latest["close_price"] is not None
                    else None
                )

                # 計算漲跌
                change = None
                change_percent = None
                if close_price is not None and len(prices) > 1:
                    prev_close = (
                        float(prices[1]["close_price"])
                        if prices[1]["close_price"] is not None
                        else None
                    )
                    if prev_close:
                        change = close_price - prev_close
                        change_percent = (change / prev_close) * 100

                stock_data["latest_price"] = {
                    "close": close_price,
                    "change": change,
                    "change_percent": change_percent,
                    "date": latest["date"].isoformat() if latest["date"] else None,
                    "volume": latest["volume"],
                    **_build_price_freshness(latest),
                }

            stock_responses.append(stock_data)

        # 返回與前端期望的格式一致的響應
        return {
            "items": stock_responses,
            "total": len(stock_responses),
            "list_id": list_id,
            "list_name": stock_list.name,
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"獲取清單股票失敗: {str(e)}")


@router.post("/{list_id}/stocks", response_model=StockListItemResponse)
async def add_stock_to_list(
    list_id: int,
    request: StockListItemAddRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user),
):
    """添加股票到清單"""
    try:
        from sqlalchemy import select

        # 驗證清單所有權
        list_query = select(UserStockList).where(
            UserStockList.id == list_id, UserStockList.user_id == current_user.id
        )
        list_result = await db.execute(list_query)
        stock_list = list_result.scalar_one_or_none()

        if not stock_list:
            raise HTTPException(status_code=404, detail="清單不存在")

        # 驗證股票是否存在
        stock_query = select(Stock).where(Stock.id == request.stock_id)
        stock_result = await db.execute(stock_query)
        stock = stock_result.scalar_one_or_none()

        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")

        # 檢查是否已存在
        existing_query = select(UserStockListItem).where(
            UserStockListItem.list_id == list_id,
            UserStockListItem.stock_id == request.stock_id,
        )
        existing_result = await db.execute(existing_query)
        existing = existing_result.scalar_one_or_none()

        if existing:
            return StockListItemResponse(
                id=existing.id,
                list_id=existing.list_id,
                stock_id=existing.stock_id,
                stock_symbol=stock.symbol,
                stock_name=stock.name,
                note=existing.note,
                created_at=existing.created_at,
            )

        # 添加新項目
        new_item = UserStockListItem(
            list_id=list_id, stock_id=request.stock_id, note=request.note
        )
        db.add(new_item)
        await db.commit()
        await db.refresh(new_item)
        background_tasks.add_task(
            _generate_signals_for_added_stock,
            current_user.id,
            request.stock_id,
        )

        return StockListItemResponse(
            id=new_item.id,
            list_id=new_item.list_id,
            stock_id=new_item.stock_id,
            stock_symbol=stock.symbol,
            stock_name=stock.name,
            note=new_item.note,
            created_at=new_item.created_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"添加股票失敗: {str(e)}")


@router.post("/{list_id}/stocks/batch")
async def batch_add_stocks_to_list(
    list_id: int,
    request: StockListItemBatchAddRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user),
):
    """批量添加股票到清單"""
    try:
        from sqlalchemy import select

        # 驗證清單所有權
        list_query = select(UserStockList).where(
            UserStockList.id == list_id, UserStockList.user_id == current_user.id
        )
        list_result = await db.execute(list_query)
        stock_list = list_result.scalar_one_or_none()

        if not stock_list:
            raise HTTPException(status_code=404, detail="清單不存在")

        success_count = 0
        failed_count = 0
        errors = []
        added_stock_ids = []

        for stock_id in request.stock_ids:
            try:
                # 驗證股票存在
                stock_query = select(Stock).where(Stock.id == stock_id)
                stock_result = await db.execute(stock_query)
                if not stock_result.scalar_one_or_none():
                    failed_count += 1
                    errors.append(f"股票 ID {stock_id} 不存在")
                    continue

                # 檢查是否已存在
                existing_query = select(UserStockListItem).where(
                    UserStockListItem.list_id == list_id,
                    UserStockListItem.stock_id == stock_id,
                )
                existing_result = await db.execute(existing_query)
                if existing_result.scalar_one_or_none():
                    success_count += 1  # 已存在算成功
                    continue

                # 添加新項目
                new_item = UserStockListItem(list_id=list_id, stock_id=stock_id)
                db.add(new_item)
                added_stock_ids.append(stock_id)
                success_count += 1
            except Exception as e:
                failed_count += 1
                errors.append(f"股票 ID {stock_id}: {str(e)}")

        await db.commit()

        for stock_id in added_stock_ids:
            background_tasks.add_task(
                _generate_signals_for_added_stock,
                current_user.id,
                stock_id,
            )

        return {
            "message": "批量添加完成",
            "success_count": success_count,
            "failed_count": failed_count,
            "errors": errors,
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"批量添加失敗: {str(e)}")


@router.delete("/{list_id}/stocks/{stock_id}")
async def remove_stock_from_list(
    list_id: int,
    stock_id: int,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user),
):
    """從清單中移除股票"""
    try:
        from sqlalchemy import select, delete

        # 驗證清單所有權
        list_query = select(UserStockList).where(
            UserStockList.id == list_id, UserStockList.user_id == current_user.id
        )
        list_result = await db.execute(list_query)
        stock_list = list_result.scalar_one_or_none()

        if not stock_list:
            raise HTTPException(status_code=404, detail="清單不存在")

        # 刪除項目
        delete_query = delete(UserStockListItem).where(
            UserStockListItem.list_id == list_id, UserStockListItem.stock_id == stock_id
        )
        result = await db.execute(delete_query)
        await db.commit()

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="股票不在清單中")

        return {
            "message": "股票已從清單中移除",
            "list_id": list_id,
            "stock_id": stock_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"移除股票失敗: {str(e)}")


@router.post("/reorder", response_model=dict)
async def reorder_stock_lists(
    request: StockListReorderRequest,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user),
):
    """批量更新清單排序"""
    try:
        from sqlalchemy import select

        # 驗證所有清單都屬於當前用戶
        list_ids = [item["id"] for item in request.list_orders]
        query = select(UserStockList).where(
            UserStockList.id.in_(list_ids), UserStockList.user_id == current_user.id
        )
        result = await db.execute(query)
        lists = result.scalars().all()

        if len(lists) != len(list_ids):
            raise HTTPException(
                status_code=404, detail="部分清單不存在或不屬於當前用戶"
            )

        # 更新每個清單的 sort_order
        for item in request.list_orders:
            list_id = item["id"]
            sort_order = item["sort_order"]

            stock_list = next((lst for lst in lists if lst.id == list_id), None)
            if stock_list:
                stock_list.sort_order = sort_order

        await db.commit()

        return {"message": "清單排序已更新", "updated_count": len(list_ids)}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"更新排序失敗: {str(e)}")


@router.post("/{list_id}/stocks/reorder", response_model=dict)
async def reorder_list_stocks(
    list_id: int,
    request: dict,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user),
):
    """批量更新清單內股票排序"""
    try:
        from sqlalchemy import select

        # 驗證清單所有權
        list_query = select(UserStockList).where(
            UserStockList.id == list_id, UserStockList.user_id == current_user.id
        )
        list_result = await db.execute(list_query)
        stock_list = list_result.scalar_one_or_none()

        if not stock_list:
            raise HTTPException(status_code=404, detail="清單不存在")

        # 獲取 stock_orders
        stock_orders = request.get("stock_orders", [])
        if not stock_orders:
            raise HTTPException(status_code=400, detail="stock_orders 不能為空")

        # 驗證所有股票都在清單中
        stock_ids = [item["stock_id"] for item in stock_orders]
        items_query = select(UserStockListItem).where(
            UserStockListItem.list_id == list_id,
            UserStockListItem.stock_id.in_(stock_ids),
        )
        items_result = await db.execute(items_query)
        items = items_result.scalars().all()

        if len(items) != len(stock_ids):
            raise HTTPException(status_code=404, detail="部分股票不在清單中")

        # 更新每個股票的 sort_order
        for order_item in stock_orders:
            stock_id = order_item["stock_id"]
            sort_order = order_item["sort_order"]

            item = next((i for i in items if i.stock_id == stock_id), None)
            if item:
                item.sort_order = sort_order

        await db.commit()

        return {"message": "股票排序已更新", "updated_count": len(stock_ids)}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"更新排序失敗: {str(e)}")
