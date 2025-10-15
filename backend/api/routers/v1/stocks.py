"""
股票API路由 - 重構為Clean Architecture版本
只負責HTTP路由、參數驗證和回應格式化，業務邏輯委託給Domain Services
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import date

# 依賴注入
from app.dependencies import (
    get_database_session,
    get_stock_service,
    get_technical_analysis_service_clean,
    get_data_collection_service_clean,
    get_trading_signal_service_clean,
    get_stock_repository,
    get_cache_service,
    get_settings
)

# Schemas
from api.schemas.stocks import (
    StockResponse,
    StockListResponse,
    StockCreateRequest,
    StockUpdateRequest,
    PriceDataResponse,
    IndicatorSummaryResponse,
    DataCollectionResponse
)

router = APIRouter()


# =============================================================================
# 股票清單相關端點
# =============================================================================

@router.get("/", response_model=StockListResponse)
async def get_stocks(
    market: Optional[str] = Query(None, description="市場代碼 (TW/US)"),
    is_active: Optional[bool] = Query(True, description="股票狀態篩選"),
    search: Optional[str] = Query(None, description="搜尋關鍵字"),
    page: int = Query(1, ge=1, description="頁碼"),
    per_page: int = Query(50, ge=1, le=200, description="每頁數量"),
    db: AsyncSession = Depends(get_database_session),
    stock_service=Depends(get_stock_service)
):
    """取得股票清單（支援過濾和分頁，支持可選的用戶認證以顯示自選股和持倉標記）

    注意: 目前版本暫時不支持用戶認證檢查 is_watchlist 和 is_portfolio
    所有股票的 is_watchlist 和 is_portfolio 都返回 False
    後續版本將添加可選認證支持
    """
    try:
        from sqlalchemy import select, desc
        from domain.models.price_history import PriceHistory
        from domain.models.user_watchlist import UserWatchlist
        from domain.models.user_portfolio import UserPortfolio
        from api.schemas.stocks import LatestPriceInfo

        # 暫時設為 None，後續版本將支持可選用戶認證
        current_user = None

        # 使用Domain Service處理業務邏輯
        result = await stock_service.get_stock_list(
            db=db,
            market=market,
            is_active=is_active,
            search=search,
            page=page,
            per_page=per_page
        )

        # 為每個股票獲取最新價格和用戶標記
        import logging
        logger = logging.getLogger(__name__)

        stock_responses = []
        for stock in result["items"]:
            # 查詢最新兩個交易日的價格（用於計算漲跌）
            price_query = select(PriceHistory).where(
                PriceHistory.stock_id == stock.id
            ).order_by(desc(PriceHistory.date)).limit(2)

            price_result = await db.execute(price_query)
            prices = price_result.scalars().all()

            # 構建股票響應
            stock_data = StockResponse.model_validate(stock).model_dump()

            # 檢查是否在自選股和持倉中（僅當用戶已認證時）
            if current_user:
                # 檢查自選股
                watchlist_query = select(UserWatchlist).where(
                    UserWatchlist.user_id == current_user.id,
                    UserWatchlist.stock_id == stock.id
                )
                watchlist_result = await db.execute(watchlist_query)
                stock_data['is_watchlist'] = watchlist_result.scalar_one_or_none() is not None

                # 檢查持倉
                portfolio_query = select(UserPortfolio).where(
                    UserPortfolio.user_id == current_user.id,
                    UserPortfolio.stock_id == stock.id
                )
                portfolio_result = await db.execute(portfolio_query)
                stock_data['is_portfolio'] = portfolio_result.scalar_one_or_none() is not None
            else:
                # 未認證用戶，標記為 False
                stock_data['is_watchlist'] = False
                stock_data['is_portfolio'] = False

            if prices and len(prices) > 0:
                latest = prices[0]
                close_price = float(latest.close_price) if latest.close_price else None

                # 計算漲跌
                change = None
                change_percent = None
                if close_price and len(prices) > 1:
                    prev_close = float(prices[1].close_price) if prices[1].close_price else None
                    if prev_close:
                        change = close_price - prev_close
                        change_percent = (change / prev_close) * 100

                stock_data['latest_price'] = LatestPriceInfo(
                    close=close_price,
                    change=change,
                    change_percent=change_percent,
                    date=latest.date,
                    volume=latest.volume
                )

            stock_responses.append(StockResponse(**stock_data))

        # 轉換為API回應格式
        response_data = {
            "items": stock_responses,
            "total": result["total"],
            "page": result["page"],
            "per_page": result["per_page"],
            "total_pages": result["total_pages"]
        }

        return StockListResponse(**response_data)

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"取得股票清單失敗: {str(e)}")


@router.get("/active", response_model=List[Dict[str, Any]])
async def get_active_stocks(
    market: Optional[str] = Query(None, description="市場代碼"),
    db: AsyncSession = Depends(get_database_session),
    stock_repo=Depends(get_stock_repository),
    cache_service=Depends(get_cache_service)
):
    """取得活躍股票清單"""
    try:
        cache_key = cache_service.get_cache_key("active_stocks", market=market)

        # 嘗試從快取獲取
        cached_data = await cache_service.get(cache_key)
        if cached_data:
            return cached_data

        # 從儲存庫獲取
        stocks = await stock_repo.get_active_stocks(db, market=market)

        result = [
            {
                "id": stock.id,
                "symbol": stock.symbol,
                "name": stock.name,
                "market": stock.market
            }
            for stock in stocks
        ]

        # 設置快取
        await cache_service.set(cache_key, result, ttl=1800)  # 30分鐘

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得活躍股票失敗: {str(e)}")


# =============================================================================
# 股票詳情端點
# =============================================================================

@router.post("/validate")
async def validate_stock_symbol(
    symbol: str = Query(..., description="股票代號"),
    market: str = Query(..., description="市場代碼 (TW/US)"),
    data_collection_service=Depends(get_data_collection_service_clean)
):
    """
    驗證股票代號是否有效

    通過 Yahoo Finance API 驗證股票代號，返回股票基本信息
    """
    try:
        from infrastructure.external.yfinance_wrapper import YFinanceWrapper

        # 格式化股票代號
        formatted_symbol = symbol.strip().upper()
        if market == 'TW' and not formatted_symbol.endswith('.TW'):
            formatted_symbol = f"{formatted_symbol}.TW"

        # 使用 YFinance 驗證
        yf_wrapper = YFinanceWrapper()
        ticker = yf_wrapper.get_ticker(formatted_symbol)

        # 獲取股票信息
        info = ticker.info

        # 檢查是否有效
        if not info or 'symbol' not in info:
            raise HTTPException(
                status_code=404,
                detail=f"股票代號 {formatted_symbol} 無效或不存在"
            )

        # 返回股票基本信息
        return {
            "valid": True,
            "symbol": formatted_symbol,
            "name": info.get('longName') or info.get('shortName') or formatted_symbol,
            "market": market,
            "currency": info.get('currency'),
            "exchange": info.get('exchange'),
            "quote_type": info.get('quoteType')
        }

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"驗證股票代號失敗: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"驗證股票代號失敗: {str(e)}"
        )


@router.get("/{stock_id}", response_model=StockResponse)
async def get_stock(
    stock_id: int,
    db: AsyncSession = Depends(get_database_session),
    stock_repo=Depends(get_stock_repository)
):
    """取得單個股票詳情"""
    try:
        stock = await stock_repo.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")

        return StockResponse.model_validate(stock)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得股票詳情失敗: {str(e)}")


# =============================================================================
# 價格相關端點
# =============================================================================

@router.get("/{stock_id}/prices", response_model=List[PriceDataResponse])
async def get_stock_prices(
    stock_id: int,
    start_date: Optional[date] = Query(None, description="開始日期"),
    end_date: Optional[date] = Query(None, description="結束日期"),
    limit: int = Query(100, description="返回數量限制"),
    db: AsyncSession = Depends(get_database_session),
    stock_repo=Depends(get_stock_repository)
):
    """取得股票價格數據"""
    try:
        # 檢查股票是否存在
        stock = await stock_repo.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")

        # 取得價格數據
        from sqlalchemy import select, and_, desc
        from domain.models.price_history import PriceHistory

        query = select(PriceHistory).where(PriceHistory.stock_id == stock_id)

        if start_date and end_date:
            query = query.where(
                and_(
                    PriceHistory.date >= start_date,
                    PriceHistory.date <= end_date
                )
            )

        query = query.order_by(desc(PriceHistory.date)).limit(limit)
        result = await db.execute(query)
        prices = result.scalars().all()

        # 過濾掉有 NULL 值的價格數據並轉換
        valid_prices = []
        for price in prices:
            try:
                # 檢查必要欄位是否存在且不為 None
                if all([
                    price.date is not None,
                    price.open_price is not None,
                    price.high_price is not None,
                    price.low_price is not None,
                    price.close_price is not None
                ]):
                    valid_prices.append(
                        PriceDataResponse(
                            date=price.date,
                            open=float(price.open_price),
                            high=float(price.high_price),
                            low=float(price.low_price),
                            close=float(price.close_price),
                            volume=price.volume if price.volume is not None else 0
                        )
                    )
            except (ValueError, TypeError) as e:
                # 跳過無法轉換的數據
                continue

        return valid_prices

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得價格數據失敗: {str(e)}")


# =============================================================================
# 技術指標端點
# =============================================================================

@router.get("/{stock_id}/indicators/summary", response_model=IndicatorSummaryResponse)
async def get_indicators_summary(
    stock_id: int,
    indicator_types: Optional[str] = Query(None, description="指標類型（逗號分隔）"),
    timeframe: str = Query("1d", description="時間框架"),
    period: Optional[int] = Query(None, description="週期參數"),
    db: AsyncSession = Depends(get_database_session),
    stock_repo=Depends(get_stock_repository),
    analysis_service=Depends(get_technical_analysis_service_clean),
    settings=Depends(get_settings)
):
    """取得技術指標摘要"""
    try:
        # 檢查股票是否存在
        stock = await stock_repo.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")

        # 解析指標類型
        if indicator_types:
            indicator_list = [t.strip().upper() for t in indicator_types.split(',')]
        else:
            indicator_list = ["RSI", "SMA_20", "MACD", "SMA_5"]  # 預設指標

        # 呼叫Domain Service處理業務邏輯
        # 這裡需要調整TechnicalAnalysisService的接口來支援新的參數格式
        indicators_data = await analysis_service.get_stock_indicators(
            db_session=db,
            stock_id=stock_id,
            indicator_types=indicator_list,
            days=100  # 暫時使用固定值，後續可根據period調整
        )

        # 格式化響應
        indicators_summary = {}
        for indicator_type in indicator_list:
            if indicator_type in indicators_data:
                raw_data = indicators_data[indicator_type]
                if raw_data:
                    # 建立標準化的指標響應格式
                    latest_value = raw_data[-1] if isinstance(raw_data, list) else raw_data

                    formatted_response = {
                        "symbol": stock.symbol,
                        "indicators": {indicator_type.lower(): latest_value},
                        "period": period or 14,
                        "timestamp": "2024-01-01T12:00:00Z",  # 暫時使用固定時間
                        "success": True,
                        "data_points": len(raw_data) if isinstance(raw_data, list) else 1
                    }

                    indicators_summary[indicator_type] = formatted_response

        return IndicatorSummaryResponse(
            stock_id=stock_id,
            symbol=stock.symbol,
            timeframe=timeframe,
            indicators=indicators_summary
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得指標摘要失敗: {str(e)}")


# =============================================================================
# 數據收集端點
# =============================================================================

@router.post("/{stock_id}/refresh", response_model=DataCollectionResponse)
async def refresh_stock_data(
    stock_id: int,
    days: int = Query(30, ge=1, le=365, description="回補天數"),
    db: AsyncSession = Depends(get_database_session),
    stock_repo=Depends(get_stock_repository),
    collection_service=Depends(get_data_collection_service_clean)
):
    """手動更新股票數據"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"=== ENTERING refresh_stock_data endpoint, stock_id={stock_id}, days={days} ===")
    try:
        logger.info("Checking if stock exists...")
        # 檢查股票是否存在
        stock = await stock_repo.get(db, stock_id)
        logger.info(f"Stock found: {stock}")
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")

        # 計算日期範圍
        from datetime import timedelta
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # 呼叫Domain Service
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Calling collect_stock_data with stock_id={stock.id}, start={start_date}, end={end_date}")

        result = await collection_service.collect_stock_data(
            db, stock_id=stock.id, start_date=start_date, end_date=end_date
        )

        logger.info(f"Collection result type: {type(result)}, result: {result}")

        # 檢查結果狀態 (result.status 是 DataCollectionStatus enum)
        from domain.services.data_collection_service import DataCollectionStatus
        success = result.status == DataCollectionStatus.SUCCESS
        message = f"成功收集 {result.records_collected} 筆數據" if success else "數據收集失敗"

        return DataCollectionResponse(
            success=success,
            message=message,
            data_points=result.records_collected,
            errors=result.errors
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"數據刷新失敗: {str(e)}")


# =============================================================================
# CRUD 端點
# =============================================================================

@router.post("/", response_model=StockResponse)
async def create_stock(
    stock: StockCreateRequest,
    db: AsyncSession = Depends(get_database_session),
    stock_repo=Depends(get_stock_repository)
):
    """創建新股票"""
    try:
        # 檢查股票是否已存在
        existing_stock = await stock_repo.get_by_symbol(db, symbol=stock.symbol)
        if existing_stock:
            raise HTTPException(
                status_code=400,
                detail=f"股票代號 {stock.symbol} 已存在"
            )

        # 創建股票
        created_stock = await stock_repo.create(db, obj_in=stock)
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
    stock_repo=Depends(get_stock_repository)
):
    """更新股票資訊"""
    try:
        # 檢查股票是否存在
        stock = await stock_repo.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")

        # 更新股票
        updated_stock = await stock_repo.update(db, db_obj=stock, obj_in=stock_update)
        return StockResponse.model_validate(updated_stock)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新股票失敗: {str(e)}")


@router.delete("/{stock_id}")
async def delete_stock(
    stock_id: int,
    db: AsyncSession = Depends(get_database_session),
    stock_repo=Depends(get_stock_repository)
):
    """刪除股票"""
    try:
        # 檢查股票是否存在
        stock = await stock_repo.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")

        # 刪除股票
        await stock_repo.remove(db, id=stock_id)

        return {"message": f"股票 {stock.symbol} 已刪除"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除股票失敗: {str(e)}")