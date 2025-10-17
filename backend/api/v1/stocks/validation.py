"""
數據驗證相關API端點
負責: /{stock_id}/validate, /validate
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.dependencies import (
    get_database_session,
    get_stock_service,
    get_data_validation_service_clean,
    get_data_collection_service_clean,
    get_stock_repository,
    get_price_data_source
)
from domain.services.data_validation_service import DataValidationService
from domain.services.stock_service import StockService

router = APIRouter()


@router.post("/validate")
async def validate_stock_symbol(
    symbol: str = Query(..., description="股票代號"),
    market: str = Query(..., description="市場代碼 (TW/US)"),
    price_source=Depends(get_price_data_source)
):
    """
    驗證股票代號是否有效

    通過價格數據源驗證股票代號，返回股票基本信息
    """
    try:
        # 格式化股票代號
        formatted_symbol = symbol.strip().upper()
        if market == 'TW' and not formatted_symbol.endswith('.TW'):
            formatted_symbol = f"{formatted_symbol}.TW"

        # 使用抽象數據源驗證
        is_valid = await price_source.validate_symbol(formatted_symbol, market)

        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"找不到股票代號「{symbol}」，請確認股票代號是否正確"
            )

        # 獲取股票資訊
        stock_info = await price_source.get_stock_info(formatted_symbol, market)

        # 返回股票基本信息
        return {
            "valid": True,
            "symbol": formatted_symbol,
            "name": stock_info.get('long_name') or stock_info.get('short_name') or formatted_symbol,
            "market": market,
            "currency": stock_info.get('currency'),
            "exchange": stock_info.get('exchange'),  # 注意：可能沒有這個欄位
            "quote_type": stock_info.get('quote_type')  # 注意：可能沒有這個欄位
        }

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"驗證股票代號失敗: {str(e)}")

        # 提供友善的錯誤訊息，不要暴露內部錯誤細節
        error_msg = str(e).lower()
        if ('404' in error_msg or
            'no data found' in error_msg or
            'no price data' in error_msg or
            'not found' in error_msg or
            'delisted' in error_msg):
            detail = f"找不到股票代號「{symbol}」，請確認股票代號是否正確"
        else:
            detail = f"驗證股票「{symbol}」時發生錯誤，請稍後再試"

        raise HTTPException(
            status_code=400,
            detail=detail
        )


@router.post("/ensure")
async def ensure_stock_exists(
    symbol: str = Query(..., description="股票代號"),
    market: str = Query(..., description="市場代碼 (TW/US)"),
    db: AsyncSession = Depends(get_database_session),
    stock_repo=Depends(get_stock_repository),
    data_collection_service=Depends(get_data_collection_service_clean)
):
    """
    確保股票存在於資料庫中，如果不存在則創建並抓取價格

    返回股票完整信息，包括最新價格
    """
    try:
        from infrastructure.external.yfinance_wrapper import YFinanceWrapper

        # 格式化股票代號
        formatted_symbol = symbol.strip().upper()
        if market == 'TW' and not formatted_symbol.endswith('.TW'):
            formatted_symbol = f"{formatted_symbol}.TW"

        # 檢查股票是否已存在於資料庫
        existing_stock = await stock_repo.get_by_symbol(db, formatted_symbol)

        if existing_stock:
            # 股票已存在，獲取最新價格
            from api.schemas.stocks import StockResponse, LatestPriceInfo
            from domain.models.price_history import PriceHistory
            from sqlalchemy import select, desc

            stock_data = StockResponse.model_validate(existing_stock).model_dump()

            # 獲取最新兩天的價格數據用於計算漲跌
            price_query = select(PriceHistory).where(
                PriceHistory.stock_id == existing_stock.id
            ).order_by(desc(PriceHistory.date)).limit(2)
            price_result = await db.execute(price_query)
            prices = price_result.scalars().all()

            if prices and len(prices) > 0:
                latest = prices[0]
                close_price = float(latest.close_price) if latest.close_price else None

                # 計算漲跌
                change = None
                change_percent = None
                if close_price and len(prices) > 1:
                    prev_close = float(prices[1].close_price) if prices[1].close_price else None
                    if prev_close and prev_close != 0:
                        change = close_price - prev_close
                        change_percent = (change / prev_close) * 100

                stock_data['latest_price'] = {
                    'close': close_price,
                    'change': change,
                    'change_percent': change_percent,
                    'date': str(latest.date) if latest.date else None,
                    'volume': latest.volume
                }

            return {
                "exists": True,
                "created": False,
                "stock": stock_data
            }

        # 股票不存在，創建新股票（stock_repo.create 已整合驗證邏輯）
        from api.schemas.stocks import StockCreateRequest

        stock_create = StockCreateRequest(
            symbol=formatted_symbol,
            name=None,  # 讓 stock_repo 自動從數據源獲取公司名稱
            market=market
        )

        # stock_repo.create 會自動驗證股票並獲取公司名稱
        try:
            new_stock = await stock_repo.create(db, obj_in=stock_create)
        except ValueError as e:
            # 股票驗證失敗
            raise HTTPException(
                status_code=400,
                detail=str(e)
            )

        # 抓取歷史價格（過去一年）
        try:
            await data_collection_service.collect_stock_prices(
                db=db,
                stock_id=new_stock.id,
                period='1y'  # 使用 yfinance period 參數，獲取完整一年資料
            )
        except Exception as price_error:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"抓取股票價格失敗，但股票已創建: {str(price_error)}")

        # 重新獲取股票以包含最新價格
        await db.refresh(new_stock)
        from api.schemas.stocks import StockResponse, LatestPriceInfo
        from domain.models.price_history import PriceHistory
        from sqlalchemy import select, desc

        stock_data = StockResponse.model_validate(new_stock).model_dump()

        # 獲取最新兩天的價格數據用於計算漲跌
        price_query = select(PriceHistory).where(
            PriceHistory.stock_id == new_stock.id
        ).order_by(desc(PriceHistory.date)).limit(2)
        price_result = await db.execute(price_query)
        prices = price_result.scalars().all()

        if prices and len(prices) > 0:
            latest = prices[0]
            close_price = float(latest.close_price) if latest.close_price else None

            # 計算漲跌
            change = None
            change_percent = None
            if close_price and len(prices) > 1:
                prev_close = float(prices[1].close_price) if prices[1].close_price else None
                if prev_close and prev_close != 0:
                    change = close_price - prev_close
                    change_percent = (change / prev_close) * 100

            stock_data['latest_price'] = {
                'close': close_price,
                'change': change,
                'change_percent': change_percent,
                'date': str(latest.date) if latest.date else None,
                'volume': latest.volume
            }

        return {
            "exists": False,
            "created": True,
            "stock": stock_data
        }

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"確保股票存在失敗: {str(e)}")

        # 提供友善的錯誤訊息，不要暴露內部錯誤細節
        error_msg = str(e).lower()
        if ('404' in error_msg or
            'no data found' in error_msg or
            'no price data' in error_msg or
            'not found' in error_msg or
            'delisted' in error_msg):
            detail = f"找不到股票代號「{symbol}」，請確認股票代號是否正確"
        else:
            detail = f"查詢股票「{symbol}」時發生錯誤，請稍後再試"

        raise HTTPException(
            status_code=400,
            detail=detail
        )


@router.get("/{stock_id}/validate", response_model=Dict[str, Any])
async def validate_stock_data(
    stock_id: int,
    db: AsyncSession = Depends(get_database_session),
    stock_service: StockService = Depends(get_stock_service),
    validation_service: DataValidationService = Depends(get_data_validation_service_clean)
):
    """
    驗證股票數據完整性和質量
    """
    try:
        # 檢查股票是否存在
        stock = await stock_service.get_stock_by_id(db, stock_id)

        report = await validation_service.validate_stock_data(db, stock_id)

        return {
            "stock_id": report.stock_id,
            "symbol": report.symbol,
            "market": report.market,
            "quality_score": report.quality_score,
            "is_valid": report.is_valid,
            "total_records": report.total_records,
            "issues": [
                {"message": issue.message, "context": issue.context}
                for issue in report.issues
            ],
            "recommendations": report.recommendations
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"數據驗證失敗: {str(e)}")