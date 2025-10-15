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
    get_stock_repository
)
from domain.services.data_validation_service import DataValidationService
from domain.services.stock_service import StockService

router = APIRouter()


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
            from api.schemas.stocks import StockResponse
            stock_data = StockResponse.model_validate(existing_stock).model_dump()

            return {
                "exists": True,
                "created": False,
                "stock": stock_data
            }

        # 股票不存在，先驗證股票代號有效性
        yf_wrapper = YFinanceWrapper()
        ticker = yf_wrapper.get_ticker(formatted_symbol)
        info = ticker.info

        if not info or 'symbol' not in info:
            raise HTTPException(
                status_code=404,
                detail=f"股票代號 {formatted_symbol} 無效或不存在"
            )

        # 創建新股票
        from api.schemas.stocks import StockCreateRequest

        company_name = info.get('longName') or info.get('shortName') or formatted_symbol
        stock_create = StockCreateRequest(
            symbol=formatted_symbol,
            name=company_name,
            market=market
        )
        new_stock = await stock_repo.create(db, obj_in=stock_create)

        # 抓取歷史價格（最近90天）
        try:
            await data_collection_service.collect_stock_prices(
                db=db,
                stock_id=new_stock.id,
                days=90
            )
        except Exception as price_error:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"抓取股票價格失敗，但股票已創建: {str(price_error)}")

        # 重新獲取股票以包含最新價格
        await db.refresh(new_stock)
        from api.schemas.stocks import StockResponse
        stock_data = StockResponse.model_validate(new_stock).model_dump()

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
        raise HTTPException(
            status_code=400,
            detail=f"確保股票存在失敗: {str(e)}"
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