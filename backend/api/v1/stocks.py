"""
股票相關API端點
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel

from core.database import get_db_session
from services.data.collection import data_collection_service
from services.data.validation import data_validation_service
from models.repositories.crud_stock import stock_crud
from models.repositories.crud_price_history import price_history_crud
from models.repositories.crud_trading_signal import trading_signal_crud

router = APIRouter(prefix="/stocks", tags=["stocks"])


# Pydantic模型
class StockResponse(BaseModel):
    id: int
    symbol: str
    market: str
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PriceDataResponse(BaseModel):
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


class StockCreateRequest(BaseModel):
    symbol: str
    market: str
    name: Optional[str] = None


class StockBatchCreateRequest(BaseModel):
    stocks: List[StockCreateRequest]


class TradingSignalResponse(BaseModel):
    id: int
    stock_id: int
    symbol: str
    signal_type: str
    strength: str
    confidence: float
    price: float
    generated_at: datetime
    description: Optional[str] = None

    class Config:
        from_attributes = True
    

class StockUpdateRequest(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None


class DataCollectionRequest(BaseModel):
    symbol: str
    market: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class DataCollectionResponse(BaseModel):
    success: bool
    message: str
    data_points: int
    errors: List[str] = []


@router.get("/", response_model=List[StockResponse])
async def get_stocks(
    market: Optional[str] = Query(None, description="市場代碼"),
    active_only: bool = Query(True, description="只返回活躍股票"),
    limit: int = Query(100, description="返回數量限制"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    取得股票清單
    """
    try:
        stocks = await stock_crud.get_multi(db, limit=limit)
        
        # 過濾條件
        filtered_stocks = []
        for stock in stocks:
            if market and stock.market != market:
                continue
            if active_only and not stock.is_active:
                continue
            filtered_stocks.append(stock)
        
        return filtered_stocks
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得股票清單失敗: {str(e)}")


@router.get("/{stock_id}", response_model=StockResponse)
async def get_stock(
    stock_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """
    取得單支股票資訊
    """
    try:
        stock = await stock_crud.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")
        
        return stock
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得股票資訊失敗: {str(e)}")


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


@router.get("/{stock_id}/data", response_model=Dict[str, Any])
async def get_stock_data(
    stock_id: int,
    start_date: Optional[date] = Query(None, description="開始日期"),
    end_date: Optional[date] = Query(None, description="結束日期"),
    page: int = Query(1, ge=1, description="頁碼"),
    page_size: int = Query(100, ge=1, le=1000, description="每頁數量"),
    include_indicators: bool = Query(False, description="包含技術指標"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    取得股票完整數據（價格 + 可選技術指標）
    """
    try:
        # 檢查股票是否存在
        stock = await stock_crud.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")
        
        # 計算分頁偏移量
        offset = (page - 1) * page_size
        
        # 取得價格數據
        if start_date and end_date:
            prices = await price_history_crud.get_by_stock_and_date_range(
                db, stock_id, start_date, end_date, offset=offset, limit=page_size
            )
            total_count = await price_history_crud.count_by_stock_and_date_range(
                db, stock_id, start_date, end_date
            )
        else:
            prices = await price_history_crud.get_by_stock(db, stock_id, offset=offset, limit=page_size)
            total_count = await price_history_crud.count_by_stock(db, stock_id)
        
        # 格式化價格數據
        price_data = []
        for price in prices:
            price_item = {
                "date": price.date.isoformat(),
                "open": float(price.open_price),
                "high": float(price.high_price),
                "low": float(price.low_price),
                "close": float(price.close_price),
                "volume": price.volume,
                "adjusted_close": float(price.adjusted_close) if price.adjusted_close else None
            }
            price_data.append(price_item)
        
        # 計算分頁資訊
        total_pages = (total_count + page_size - 1) // page_size
        
        result = {
            "stock": {
                "id": stock.id,
                "symbol": stock.symbol,
                "market": stock.market,
                "name": stock.name
            },
            "price_data": {
                "items": price_data,
                "pagination": {
                    "total": total_count,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages
                }
            }
        }
        
        # 如果需要技術指標
        if include_indicators and prices:
            from models.repositories.crud_technical_indicator import technical_indicator_crud
            
            indicators = await technical_indicator_crud.get_by_stock_and_date_range(
                db, stock_id, prices[0].date, prices[-1].date
            )
            
            # 按指標類型組織數據
            indicators_data = {}
            for indicator in indicators:
                indicator_type = indicator.indicator_type
                if indicator_type not in indicators_data:
                    indicators_data[indicator_type] = []
                
                indicators_data[indicator_type].append({
                    "date": indicator.date.isoformat(),
                    "value": float(indicator.value),
                    "parameters": indicator.parameters
                })
            
            result["indicators"] = indicators_data
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得股票數據失敗: {str(e)}")


@router.get("/{stock_id}/prices", response_model=List[PriceDataResponse])
async def get_stock_prices(
    stock_id: int,
    start_date: Optional[date] = Query(None, description="開始日期"),
    end_date: Optional[date] = Query(None, description="結束日期"),
    limit: int = Query(100, description="返回數量限制"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    取得股票價格數據（簡化版本）
    """
    try:
        # 檢查股票是否存在
        stock = await stock_crud.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")
        
        # 取得價格數據
        if start_date and end_date:
            prices = await price_history_crud.get_by_stock_and_date_range(
                db, stock_id, start_date, end_date, limit=limit
            )
        else:
            prices = await price_history_crud.get_by_stock(db, stock_id, limit=limit)
        
        return [
            PriceDataResponse(
                date=price.date,
                open=float(price.open_price),
                high=float(price.high_price),
                low=float(price.low_price),
                close=float(price.close_price),
                volume=price.volume
            )
            for price in prices
        ]
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得價格數據失敗: {str(e)}")


@router.get("/{stock_id}/indicators", response_model=Dict[str, Any])
async def get_stock_indicators(
    stock_id: int,
    indicator_type: Optional[str] = Query(None, description="技術指標類型"),
    start_date: Optional[date] = Query(None, description="開始日期"),
    end_date: Optional[date] = Query(None, description="結束日期"),
    page: int = Query(1, ge=1, description="頁碼"),
    page_size: int = Query(100, ge=1, le=1000, description="每頁數量"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    取得股票技術指標
    """
    try:
        # 檢查股票是否存在
        stock = await stock_crud.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")
        
        from models.repositories.crud_technical_indicator import technical_indicator_crud
        
        # 計算分頁偏移量
        offset = (page - 1) * page_size
        
        # 取得技術指標數據
        if start_date and end_date:
            indicators = await technical_indicator_crud.get_by_stock_and_date_range(
                db, stock_id, start_date, end_date, indicator_type, offset=offset, limit=page_size
            )
            total_count = await technical_indicator_crud.count_by_stock_and_date_range(
                db, stock_id, start_date, end_date, indicator_type
            )
        else:
            indicators = await technical_indicator_crud.get_by_stock(
                db, stock_id, indicator_type, offset=offset, limit=page_size
            )
            total_count = await technical_indicator_crud.count_by_stock(db, stock_id, indicator_type)
        
        # 按指標類型組織數據
        indicators_data = {}
        for indicator in indicators:
            ind_type = indicator.indicator_type
            if ind_type not in indicators_data:
                indicators_data[ind_type] = []
            
            indicators_data[ind_type].append({
                "date": indicator.date.isoformat(),
                "value": float(indicator.value),
                "parameters": indicator.parameters
            })
        
        # 計算分頁資訊
        total_pages = (total_count + page_size - 1) // page_size
        
        return {
            "stock_id": stock_id,
            "symbol": stock.symbol,
            "indicators": indicators_data,
            "pagination": {
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得技術指標失敗: {str(e)}")


@router.post("/{stock_id}/refresh", response_model=DataCollectionResponse)
async def refresh_stock_data(
    stock_id: int,
    days: int = Query(30, ge=1, le=365, description="回補天數"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    手動更新股票數據
    """
    try:
        # 檢查股票是否存在
        stock = await stock_crud.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")
        
        # 計算日期範圍
        from datetime import timedelta
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        # 執行數據收集
        result = await data_collection_service.collect_stock_data(
            db, stock.symbol, stock.market, start_date, end_date
        )
        
        return DataCollectionResponse(
            success=result.get('success', False),
            message=f"股票 {stock.symbol} 數據更新完成",
            data_points=result.get('data_saved', 0),
            errors=result.get('errors', [])
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"數據更新失敗: {str(e)}")


@router.post("/collect", response_model=DataCollectionResponse)
async def collect_stock_data(
    request: DataCollectionRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    收集股票數據
    """
    try:
        result = await data_collection_service.collect_stock_data(
            db, 
            request.symbol, 
            request.market, 
            request.start_date, 
            request.end_date
        )
        
        return DataCollectionResponse(
            success=result.get('success', False),
            message=result.get('message', ''),
            data_points=result.get('data_saved', 0),
            errors=result.get('errors', [])
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"數據收集失敗: {str(e)}")


@router.post("/collect-all", response_model=Dict[str, Any])
async def collect_all_stocks_data(
    db: AsyncSession = Depends(get_db_session)
):
    """
    收集所有股票數據
    """
    try:
        result = await data_collection_service.collect_all_stocks_data(db)
        
        return {
            'success': True,
            'message': '批次數據收集完成',
            'total_stocks': result.get('total_stocks', 0),
            'success_count': result.get('success_count', 0),
            'error_count': result.get('error_count', 0),
            'total_data_saved': result.get('total_data_saved', 0),
            'errors': result.get('collection_errors', []) + result.get('save_errors', [])
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批次數據收集失敗: {str(e)}")


@router.get("/{stock_id}/validate", response_model=Dict[str, Any])
async def validate_stock_data(
    stock_id: int,
    days: int = Query(30, description="檢查天數"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    驗證股票數據品質
    """
    try:
        # 檢查股票是否存在
        stock = await stock_crud.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")
        
        # 執行數據品質分析
        quality_report = await data_validation_service.analyze_stock_data_quality(
            db, stock_id, days
        )
        
        return {
            'stock_id': stock_id,
            'symbol': stock.symbol,
            'quality_score': quality_report.quality_score,
            'total_records': quality_report.total_records,
            'valid_records': quality_report.valid_records,
            'missing_dates': [d.isoformat() for d in quality_report.missing_dates],
            'issues': quality_report.issues,
            'recommendations': quality_report.recommendations
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"數據驗證失敗: {str(e)}")


@router.post("/", response_model=StockResponse)
async def create_stock(
    request: StockCreateRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    新增股票
    """
    try:
        # 檢查股票是否已存在
        existing_stock = await stock_crud.get_by_symbol_and_market(db, request.symbol, request.market)
        if existing_stock:
            raise HTTPException(status_code=400, detail="股票已存在")
        
        # 驗證股票代號格式
        if not _validate_symbol_format(request.symbol, request.market):
            raise HTTPException(status_code=400, detail="股票代號格式不正確")
        
        # 建立股票
        stock_data = {
            "symbol": request.symbol.upper(),
            "market": request.market.upper(),
            "name": request.name or request.symbol,
            "is_active": True
        }
        
        stock = await stock_crud.create(db, obj_in=stock_data)
        return stock
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"新增股票失敗: {str(e)}")


@router.put("/{stock_id}", response_model=StockResponse)
async def update_stock(
    stock_id: int,
    request: StockUpdateRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    更新股票資訊
    """
    try:
        # 檢查股票是否存在
        stock = await stock_crud.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")
        
        # 更新股票
        update_data = {}
        if request.name is not None:
            update_data["name"] = request.name
        if request.is_active is not None:
            update_data["is_active"] = request.is_active
        
        updated_stock = await stock_crud.update(db, db_obj=stock, obj_in=update_data)
        return updated_stock
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新股票失敗: {str(e)}")


@router.delete("/{stock_id}")
async def delete_stock(
    stock_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """
    刪除股票
    """
    try:
        # 檢查股票是否存在
        stock = await stock_crud.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")
        
        # 刪除股票
        await stock_crud.remove(db, id=stock_id)
        
        return {"message": f"股票 {stock.symbol} 已成功刪除"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除股票失敗: {str(e)}")


@router.post("/batch", response_model=Dict[str, Any])
async def batch_create_stocks(
    request: StockBatchCreateRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    批次新增股票
    """
    try:
        results = {
            "total": len(request.stocks),
            "successful": 0,
            "failed": 0,
            "errors": [],
            "created_stocks": []
        }
        
        for stock_request in request.stocks:
            try:
                # 檢查是否已存在
                existing_stock = await stock_crud.get_by_symbol_and_market(
                    db, stock_request.symbol, stock_request.market
                )
                if existing_stock:
                    results["errors"].append(f"{stock_request.symbol}: 股票已存在")
                    results["failed"] += 1
                    continue
                
                # 驗證格式
                if not _validate_symbol_format(stock_request.symbol, stock_request.market):
                    results["errors"].append(f"{stock_request.symbol}: 代號格式不正確")
                    results["failed"] += 1
                    continue
                
                # 建立股票
                stock_data = {
                    "symbol": stock_request.symbol.upper(),
                    "market": stock_request.market.upper(),
                    "name": stock_request.name or stock_request.symbol,
                    "is_active": True
                }
                
                stock = await stock_crud.create(db, obj_in=stock_data)
                results["created_stocks"].append({
                    "id": stock.id,
                    "symbol": stock.symbol,
                    "market": stock.market,
                    "name": stock.name
                })
                results["successful"] += 1
                
            except Exception as e:
                results["errors"].append(f"{stock_request.symbol}: {str(e)}")
                results["failed"] += 1
        
        return results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批次新增股票失敗: {str(e)}")


@router.get("/search/{symbol}", response_model=List[StockResponse])
async def search_stocks(
    symbol: str,
    market: Optional[str] = Query(None, description="市場代碼"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    搜尋股票
    """
    try:
        stocks = await stock_crud.search_by_symbol(db, symbol, market)
        return stocks
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜尋股票失敗: {str(e)}")


@router.get("/{symbol}/signals", response_model=List[TradingSignalResponse])
async def get_stock_signals_by_symbol(
    symbol: str,
    market: Optional[str] = Query(None, description="市場代碼 (TW/US)"),
    signal_type: Optional[str] = Query(None, description="信號類型"),
    days: int = Query(30, ge=1, le=365, description="歷史天數"),
    limit: int = Query(50, ge=1, le=200, description="返回數量限制"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    根據股票代號取得交易信號
    """
    try:
        # 先根據symbol找到股票
        stock = await stock_crud.get_by_symbol_and_market(db, symbol.upper(), market or "TW")
        if not stock:
            raise HTTPException(status_code=404, detail=f"股票 {symbol} 不存在")

        # 建立查詢條件
        filters = {"stock_id": stock.id}
        if signal_type:
            filters["signal_type"] = signal_type

        # 取得交易信號
        signals = await trading_signal_crud.get_stock_signals(
            db,
            stock_id=stock.id,
            filters=filters,
            days=days,
            limit=limit
        )

        # 為每個信號添加股票代號
        response_signals = []
        for signal in signals:
            signal_dict = {
                "id": signal.id,
                "stock_id": signal.stock_id,
                "symbol": stock.symbol,
                "signal_type": signal.signal_type,
                "strength": signal.strength,
                "confidence": signal.confidence,
                "price": float(signal.price),
                "generated_at": signal.generated_at,
                "description": signal.description
            }
            response_signals.append(TradingSignalResponse(**signal_dict))

        return response_signals

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得交易信號失敗: {str(e)}")


def _validate_symbol_format(symbol: str, market: str) -> bool:
    """
    驗證股票代號格式
    """
    import re

    if market.upper() == "TW":
        # 台股格式: 4位數字 + .TW (例如: 2330.TW)
        pattern = r'^\d{4}\.TW$'
        return bool(re.match(pattern, symbol.upper()))
    elif market.upper() == "US":
        # 美股格式: 1-5位英文字母 (例如: AAPL, GOOGL)
        pattern = r'^[A-Z]{1,5}$'
        return bool(re.match(pattern, symbol.upper()))

    return False