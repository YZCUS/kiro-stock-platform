"""
股票清單管理 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

# 依賴注入
from app.dependencies import get_database_session
from core.auth_dependencies import get_current_active_user

# Models
from domain.models.user import User
from domain.models.user_stock_list import UserStockList, UserStockListItem
from domain.models.stock import Stock

# Schemas
from api.schemas.stock_list import (
    StockListCreateRequest,
    StockListUpdateRequest,
    StockListResponse,
    StockListListResponse,
    StockListItemAddRequest,
    StockListItemBatchAddRequest,
    StockListItemResponse,
    StockListItemListResponse,
    StockListStocksResponse
)

router = APIRouter()


# =============================================================================
# 股票清單管理端點
# =============================================================================

@router.get("/", response_model=StockListListResponse)
async def get_user_stock_lists(
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user)
):
    """獲取用戶的所有股票清單"""
    try:
        lists = await db.run_sync(
            lambda session: UserStockList.get_user_lists(session, current_user.id)
        )

        return StockListListResponse(
            items=[StockListResponse(
                id=lst.id,
                user_id=str(lst.user_id),
                name=lst.name,
                description=lst.description,
                is_default=lst.is_default,
                stocks_count=lst.get_stocks_count(),
                created_at=lst.created_at,
                updated_at=lst.updated_at
            ) for lst in lists],
            total=len(lists)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取清單失敗: {str(e)}")


@router.post("/", response_model=StockListResponse)
async def create_stock_list(
    request: StockListCreateRequest,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user)
):
    """創建新的股票清單"""
    try:
        from sqlalchemy import select

        # 檢查清單名稱是否已存在
        query = select(UserStockList).where(
            UserStockList.user_id == current_user.id,
            UserStockList.name == request.name
        )
        result = await db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            raise HTTPException(status_code=400, detail="清單名稱已存在")

        # 如果設置為預設清單，先取消其他預設清單
        if request.is_default:
            update_query = select(UserStockList).where(
                UserStockList.user_id == current_user.id,
                UserStockList.is_default == True
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
            is_default=request.is_default
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
            stocks_count=0,
            created_at=new_list.created_at,
            updated_at=new_list.updated_at
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
    current_user: User = Depends(get_current_active_user)
):
    """獲取單個股票清單"""
    try:
        from sqlalchemy import select

        query = select(UserStockList).where(
            UserStockList.id == list_id,
            UserStockList.user_id == current_user.id
        )
        result = await db.execute(query)
        stock_list = result.scalar_one_or_none()

        if not stock_list:
            raise HTTPException(status_code=404, detail="清單不存在")

        return StockListResponse(
            id=stock_list.id,
            user_id=str(stock_list.user_id),
            name=stock_list.name,
            description=stock_list.description,
            is_default=stock_list.is_default,
            stocks_count=stock_list.get_stocks_count(),
            created_at=stock_list.created_at,
            updated_at=stock_list.updated_at
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
    current_user: User = Depends(get_current_active_user)
):
    """更新股票清單"""
    try:
        from sqlalchemy import select

        # 獲取清單
        query = select(UserStockList).where(
            UserStockList.id == list_id,
            UserStockList.user_id == current_user.id
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
                UserStockList.id != list_id
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
                    UserStockList.id != list_id
                )
                result = await db.execute(update_query)
                default_lists = result.scalars().all()
                for lst in default_lists:
                    lst.is_default = False
            stock_list.is_default = request.is_default

        await db.commit()
        await db.refresh(stock_list)

        return StockListResponse(
            id=stock_list.id,
            user_id=str(stock_list.user_id),
            name=stock_list.name,
            description=stock_list.description,
            is_default=stock_list.is_default,
            stocks_count=stock_list.get_stocks_count(),
            created_at=stock_list.created_at,
            updated_at=stock_list.updated_at
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
    current_user: User = Depends(get_current_active_user)
):
    """刪除股票清單"""
    try:
        from sqlalchemy import select, delete

        # 檢查清單是否存在
        query = select(UserStockList).where(
            UserStockList.id == list_id,
            UserStockList.user_id == current_user.id
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

@router.get("/{list_id}/stocks", response_model=StockListItemListResponse)
async def get_list_stocks(
    list_id: int,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user)
):
    """獲取清單中的所有股票"""
    try:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        # 驗證清單所有權
        list_query = select(UserStockList).where(
            UserStockList.id == list_id,
            UserStockList.user_id == current_user.id
        )
        list_result = await db.execute(list_query)
        stock_list = list_result.scalar_one_or_none()

        if not stock_list:
            raise HTTPException(status_code=404, detail="清單不存在")

        # 獲取清單項目（預載入 stock）
        items_query = select(UserStockListItem).where(
            UserStockListItem.list_id == list_id
        ).options(selectinload(UserStockListItem.stock))
        items_result = await db.execute(items_query)
        items = items_result.scalars().all()

        return StockListItemListResponse(
            items=[StockListItemResponse(
                id=item.id,
                list_id=item.list_id,
                stock_id=item.stock_id,
                stock_symbol=item.stock.symbol if item.stock else None,
                stock_name=item.stock.name if item.stock else None,
                note=item.note,
                created_at=item.created_at
            ) for item in items],
            total=len(items),
            list_id=list_id,
            list_name=stock_list.name
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取清單股票失敗: {str(e)}")


@router.post("/{list_id}/stocks", response_model=StockListItemResponse)
async def add_stock_to_list(
    list_id: int,
    request: StockListItemAddRequest,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user)
):
    """添加股票到清單"""
    try:
        from sqlalchemy import select

        # 驗證清單所有權
        list_query = select(UserStockList).where(
            UserStockList.id == list_id,
            UserStockList.user_id == current_user.id
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
            UserStockListItem.stock_id == request.stock_id
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
                created_at=existing.created_at
            )

        # 添加新項目
        new_item = UserStockListItem(
            list_id=list_id,
            stock_id=request.stock_id,
            note=request.note
        )
        db.add(new_item)
        await db.commit()
        await db.refresh(new_item)

        return StockListItemResponse(
            id=new_item.id,
            list_id=new_item.list_id,
            stock_id=new_item.stock_id,
            stock_symbol=stock.symbol,
            stock_name=stock.name,
            note=new_item.note,
            created_at=new_item.created_at
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
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user)
):
    """批量添加股票到清單"""
    try:
        from sqlalchemy import select

        # 驗證清單所有權
        list_query = select(UserStockList).where(
            UserStockList.id == list_id,
            UserStockList.user_id == current_user.id
        )
        list_result = await db.execute(list_query)
        stock_list = list_result.scalar_one_or_none()

        if not stock_list:
            raise HTTPException(status_code=404, detail="清單不存在")

        success_count = 0
        failed_count = 0
        errors = []

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
                    UserStockListItem.stock_id == stock_id
                )
                existing_result = await db.execute(existing_query)
                if existing_result.scalar_one_or_none():
                    success_count += 1  # 已存在算成功
                    continue

                # 添加新項目
                new_item = UserStockListItem(
                    list_id=list_id,
                    stock_id=stock_id
                )
                db.add(new_item)
                success_count += 1
            except Exception as e:
                failed_count += 1
                errors.append(f"股票 ID {stock_id}: {str(e)}")

        await db.commit()

        return {
            "message": "批量添加完成",
            "success_count": success_count,
            "failed_count": failed_count,
            "errors": errors
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
    current_user: User = Depends(get_current_active_user)
):
    """從清單中移除股票"""
    try:
        from sqlalchemy import select, delete

        # 驗證清單所有權
        list_query = select(UserStockList).where(
            UserStockList.id == list_id,
            UserStockList.user_id == current_user.id
        )
        list_result = await db.execute(list_query)
        stock_list = list_result.scalar_one_or_none()

        if not stock_list:
            raise HTTPException(status_code=404, detail="清單不存在")

        # 刪除項目
        delete_query = delete(UserStockListItem).where(
            UserStockListItem.list_id == list_id,
            UserStockListItem.stock_id == stock_id
        )
        result = await db.execute(delete_query)
        await db.commit()

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="股票不在清單中")

        return {"message": "股票已從清單中移除", "list_id": list_id, "stock_id": stock_id}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"移除股票失敗: {str(e)}")
