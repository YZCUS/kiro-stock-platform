"""
持倉管理API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal

# 依賴注入
from app.dependencies import get_database_session
from core.auth_dependencies import get_current_active_user

# Models
from domain.models.user import User
from domain.models.user_portfolio import UserPortfolio
from domain.models.transaction import Transaction
from domain.models.stock import Stock

# Schemas
from api.schemas.portfolio import (
    PortfolioResponse,
    PortfolioListResponse,
    PortfolioSummaryResponse,
    TransactionCreateRequest,
    TransactionResponse,
    TransactionListResponse,
    TransactionSummaryResponse,
    BatchTransactionRequest,
    BatchTransactionResponse
)

router = APIRouter()


# =============================================================================
# 持倉管理端點
# =============================================================================

@router.get("/", response_model=PortfolioListResponse)
async def get_user_portfolio(
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user)
):
    """取得用戶持倉列表"""
    try:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        # 查詢用戶持倉 (使用 eager loading 避免 lazy loading 問題)
        query = select(UserPortfolio).where(
            UserPortfolio.user_id == current_user.id
        ).options(selectinload(UserPortfolio.stock))
        result = await db.execute(query)
        portfolios = result.scalars().all()

        # 獲取每個持倉的詳細資訊
        portfolio_responses = []
        total_cost = Decimal(0)
        total_current_value = Decimal(0)

        for portfolio in portfolios:
            # 使用已經 eager loaded 的股票資訊
            stock = portfolio.stock

            if not stock:
                continue

            # 獲取最新價格
            from domain.models.price_history import PriceHistory
            price_query = select(PriceHistory).where(
                PriceHistory.stock_id == stock.id
            ).order_by(PriceHistory.date.desc()).limit(1)
            price_result = await db.execute(price_query)
            latest_price = price_result.scalar_one_or_none()

            current_price = None
            current_value = None
            profit_loss = None
            profit_loss_percent = None

            if latest_price:
                current_price = float(latest_price.close_price)
                profit_loss_data = portfolio.calculate_profit_loss(Decimal(str(current_price)))
                current_value = float(profit_loss_data['current_value'])
                profit_loss = float(profit_loss_data['profit_loss'])
                profit_loss_percent = float(profit_loss_data['profit_loss_percent'])

                total_cost += portfolio.total_cost
                total_current_value += profit_loss_data['current_value']

            portfolio_responses.append(PortfolioResponse(
                id=portfolio.id,
                user_id=str(portfolio.user_id),
                stock_id=portfolio.stock_id,
                stock_symbol=stock.symbol,
                stock_name=stock.name,
                quantity=float(portfolio.quantity),
                avg_cost=float(portfolio.avg_cost),
                total_cost=float(portfolio.total_cost),
                current_price=current_price,
                current_value=current_value,
                profit_loss=profit_loss,
                profit_loss_percent=profit_loss_percent,
                created_at=portfolio.created_at,
                updated_at=portfolio.updated_at
            ))

        # 計算總體盈虧（確保類型一致）
        total_profit_loss = total_current_value - total_cost
        total_profit_loss_percent = (total_profit_loss / total_cost * 100) if total_cost > 0 else Decimal(0)

        return PortfolioListResponse(
            items=portfolio_responses,
            total=len(portfolio_responses),
            total_cost=float(total_cost),
            total_current_value=float(total_current_value),
            total_profit_loss=float(total_profit_loss),
            total_profit_loss_percent=float(total_profit_loss_percent)
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"取得持倉列表失敗: {str(e)}")


@router.get("/summary", response_model=PortfolioSummaryResponse)
async def get_portfolio_summary(
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user)
):
    """取得持倉摘要"""
    try:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from domain.models.price_history import PriceHistory

        # 查詢用戶持倉（使用 eager loading）
        query = select(UserPortfolio).where(
            UserPortfolio.user_id == current_user.id
        ).options(selectinload(UserPortfolio.stock))
        result = await db.execute(query)
        portfolios = result.scalars().all()

        total_cost = Decimal(0)
        total_current_value = Decimal(0)

        for portfolio in portfolios:
            stock = portfolio.stock
            if not stock:
                continue

            # 獲取最新價格
            price_query = select(PriceHistory).where(
                PriceHistory.stock_id == stock.id
            ).order_by(PriceHistory.date.desc()).limit(1)
            price_result = await db.execute(price_query)
            latest_price = price_result.scalar_one_or_none()

            if latest_price:
                current_price = Decimal(str(latest_price.close_price))
                total_cost += portfolio.total_cost
                total_current_value += portfolio.calculate_current_value(current_price)

        total_profit_loss = total_current_value - total_cost
        total_profit_loss_percent = (total_profit_loss / total_cost * 100) if total_cost > 0 else Decimal(0)

        return PortfolioSummaryResponse(
            total_cost=float(total_cost),
            total_current_value=float(total_current_value),
            total_profit_loss=float(total_profit_loss),
            total_profit_loss_percent=float(total_profit_loss_percent),
            portfolio_count=len(portfolios)
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"取得持倉摘要失敗: {str(e)}")


@router.get("/{portfolio_id}", response_model=PortfolioResponse)
async def get_portfolio_detail(
    portfolio_id: int,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user)
):
    """取得單個持倉詳情"""
    try:
        from sqlalchemy import select

        query = select(UserPortfolio).where(
            UserPortfolio.id == portfolio_id,
            UserPortfolio.user_id == current_user.id
        )
        result = await db.execute(query)
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            raise HTTPException(status_code=404, detail="持倉不存在")

        # 獲取股票和價格資訊（同上面的邏輯）
        stock_query = select(Stock).where(Stock.id == portfolio.stock_id)
        stock_result = await db.execute(stock_query)
        stock = stock_result.scalar_one_or_none()

        current_price = None
        if stock:
            from domain.models.price_history import PriceHistory
            price_query = select(PriceHistory).where(
                PriceHistory.stock_id == stock.id
            ).order_by(PriceHistory.date.desc()).limit(1)
            price_result = await db.execute(price_query)
            latest_price = price_result.scalar_one_or_none()
            if latest_price:
                current_price = float(latest_price.close_price)

        profit_loss_data = None
        if current_price:
            profit_loss_data = portfolio.calculate_profit_loss(Decimal(str(current_price)))

        return PortfolioResponse(
            id=portfolio.id,
            user_id=str(portfolio.user_id),
            stock_id=portfolio.stock_id,
            stock_symbol=stock.symbol if stock else None,
            stock_name=stock.name if stock else None,
            quantity=float(portfolio.quantity),
            avg_cost=float(portfolio.avg_cost),
            total_cost=float(portfolio.total_cost),
            current_price=current_price,
            current_value=float(profit_loss_data['current_value']) if profit_loss_data else None,
            profit_loss=float(profit_loss_data['profit_loss']) if profit_loss_data else None,
            profit_loss_percent=float(profit_loss_data['profit_loss_percent']) if profit_loss_data else None,
            created_at=portfolio.created_at,
            updated_at=portfolio.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得持倉詳情失敗: {str(e)}")


@router.delete("/{portfolio_id}")
async def delete_portfolio(
    portfolio_id: int,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user)
):
    """刪除持倉（清倉）"""
    try:
        from sqlalchemy import select, delete

        # 檢查持倉是否存在且屬於當前用戶
        query = select(UserPortfolio).where(
            UserPortfolio.id == portfolio_id,
            UserPortfolio.user_id == current_user.id
        )
        result = await db.execute(query)
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            raise HTTPException(status_code=404, detail="持倉不存在")

        # 刪除持倉
        delete_query = delete(UserPortfolio).where(UserPortfolio.id == portfolio_id)
        await db.execute(delete_query)
        await db.commit()

        return {"message": f"持倉已刪除", "portfolio_id": portfolio_id}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"刪除持倉失敗: {str(e)}")


# =============================================================================
# 交易記錄端點
# =============================================================================

@router.post("/transactions", response_model=TransactionResponse)
async def create_transaction(
    transaction_req: TransactionCreateRequest,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user)
):
    """創建交易記錄（買入/賣出）"""
    try:
        from sqlalchemy import select

        # 檢查股票是否存在
        stock_query = select(Stock).where(Stock.id == transaction_req.stock_id)
        stock_result = await db.execute(stock_query)
        stock = stock_result.scalar_one_or_none()

        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")

        # 查詢或創建持倉
        portfolio_query = select(UserPortfolio).where(
            UserPortfolio.user_id == current_user.id,
            UserPortfolio.stock_id == transaction_req.stock_id
        )
        portfolio_result = await db.execute(portfolio_query)
        portfolio = portfolio_result.scalar_one_or_none()

        # 更新持倉（使用同步方法）
        def update_portfolio_sync(session):
            return UserPortfolio.create_or_update_position(
                session=session,
                user_id=current_user.id,
                stock_id=transaction_req.stock_id,
                quantity=Decimal(str(transaction_req.quantity)),
                price=Decimal(str(transaction_req.price)),
                transaction_type=transaction_req.transaction_type
            )

        portfolio = await db.run_sync(update_portfolio_sync)
        await db.commit()

        # 獲取 portfolio_id（清倉時為 None）
        if portfolio is None:
            portfolio_id = None
        else:
            # 重新查詢持倉以獲取ID
            portfolio_query = select(UserPortfolio).where(
                UserPortfolio.user_id == current_user.id,
                UserPortfolio.stock_id == transaction_req.stock_id
            )
            portfolio_result = await db.execute(portfolio_query)
            portfolio = portfolio_result.scalar_one_or_none()
            portfolio_id = portfolio.id if portfolio else None

        # 創建交易記錄（使用同步方法）
        def create_transaction_sync(session):
            return Transaction.create_transaction(
                session=session,
                user_id=current_user.id,
                portfolio_id=portfolio_id,
                stock_id=transaction_req.stock_id,
                transaction_type=transaction_req.transaction_type,
                quantity=Decimal(str(transaction_req.quantity)),
                price=Decimal(str(transaction_req.price)),
                transaction_date=transaction_req.transaction_date,
                fee=Decimal(str(transaction_req.fee)),
                tax=Decimal(str(transaction_req.tax)),
                note=transaction_req.note
            )

        transaction = await db.run_sync(create_transaction_sync)
        await db.commit()

        return TransactionResponse(
            id=transaction.id,
            user_id=str(transaction.user_id),
            portfolio_id=transaction.portfolio_id,
            stock_id=transaction.stock_id,
            stock_symbol=stock.symbol,
            stock_name=stock.name,
            transaction_type=transaction.transaction_type,
            quantity=float(transaction.quantity),
            price=float(transaction.price),
            fee=float(transaction.fee),
            tax=float(transaction.tax),
            total=float(transaction.total),
            transaction_date=transaction.transaction_date,
            note=transaction.note,
            created_at=transaction.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"創建交易失敗: {str(e)}")


@router.get("/transactions", response_model=TransactionListResponse)
async def get_transactions(
    stock_id: Optional[int] = Query(None, description="股票ID過濾"),
    transaction_type: Optional[str] = Query(None, pattern="^(BUY|SELL)$", description="交易類型過濾"),
    start_date: Optional[date] = Query(None, description="開始日期"),
    end_date: Optional[date] = Query(None, description="結束日期"),
    page: int = Query(1, ge=1, description="頁碼"),
    per_page: int = Query(50, ge=1, le=200, description="每頁數量"),
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user)
):
    """取得用戶交易記錄列表"""
    try:
        from sqlalchemy import select, and_

        # 構建查詢
        query = select(Transaction).where(Transaction.user_id == current_user.id)

        if stock_id:
            query = query.where(Transaction.stock_id == stock_id)

        if transaction_type:
            query = query.where(Transaction.transaction_type == transaction_type)

        if start_date:
            query = query.where(Transaction.transaction_date >= start_date)

        if end_date:
            query = query.where(Transaction.transaction_date <= end_date)

        # 計算總數
        from sqlalchemy import func
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # 分頁
        query = query.order_by(Transaction.transaction_date.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)

        result = await db.execute(query)
        transactions = result.scalars().all()

        # 構建響應
        transaction_responses = []
        for txn in transactions:
            stock_query = select(Stock).where(Stock.id == txn.stock_id)
            stock_result = await db.execute(stock_query)
            stock = stock_result.scalar_one_or_none()

            transaction_responses.append(TransactionResponse(
                id=txn.id,
                user_id=str(txn.user_id),
                portfolio_id=txn.portfolio_id,
                stock_id=txn.stock_id,
                stock_symbol=stock.symbol if stock else None,
                stock_name=stock.name if stock else None,
                transaction_type=txn.transaction_type,
                quantity=float(txn.quantity),
                price=float(txn.price),
                fee=float(txn.fee),
                tax=float(txn.tax),
                total=float(txn.total),
                transaction_date=txn.transaction_date,
                note=txn.note,
                created_at=txn.created_at
            ))

        total_pages = (total + per_page - 1) // per_page

        return TransactionListResponse(
            items=transaction_responses,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"取得交易記錄失敗: {str(e)}")


@router.get("/transactions/summary", response_model=TransactionSummaryResponse)
async def get_transaction_summary(
    start_date: Optional[date] = Query(None, description="開始日期"),
    end_date: Optional[date] = Query(None, description="結束日期"),
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user)
):
    """取得交易統計摘要"""
    try:
        summary = await db.run_sync(
            lambda session: Transaction.calculate_transaction_summary(
                session, current_user.id, start_date, end_date
            )
        )
        return TransactionSummaryResponse(**summary)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得交易摘要失敗: {str(e)}")
