"""
股票相關API端點

性能優化說明：
- 所有過濾條件都在資料庫層執行，避免不必要的數據傳輸
- 實現了真正的分頁機制，支援大數據量查詢
- 使用索引建議：在 symbol, market, is_active 欄位上創建組合索引
  CREATE INDEX idx_stocks_market_active ON stocks(market, is_active);
  CREATE INDEX idx_stocks_symbol_search ON stocks(symbol);
  CREATE INDEX idx_stocks_name_search ON stocks(name);
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel
import redis
import json
import hashlib
from core.config import settings

from core.database import get_db_session
from services.data.collection import data_collection_service
from services.data.validation import data_validation_service
from services.analysis.technical_analysis import TechnicalAnalysisService, IndicatorType
from models.repositories.crud_stock import stock_crud
from models.repositories.crud_price_history import price_history_crud
from models.repositories.crud_trading_signal import trading_signal_crud

router = APIRouter(prefix="/stocks", tags=["stocks"])

# Redis 連接配置
try:
    redis_client = redis.Redis(
        host=getattr(settings, 'REDIS_HOST', 'localhost'),
        port=getattr(settings, 'REDIS_PORT', 6379),
        db=getattr(settings, 'REDIS_DB', 0),
        decode_responses=True,
        socket_timeout=5
    )
    # 測試連接
    redis_client.ping()
except Exception as e:
    print(f"Redis 連接失敗，快取將被禁用: {e}")
    redis_client = None


def _get_cache_key(prefix: str, market: Optional[str] = None) -> str:
    """生成快取鍵"""
    key_parts = [prefix]
    if market:
        key_parts.append(f"market:{market}")
    return ":".join(key_parts)


def _get_cached_data(cache_key: str) -> Optional[List[Dict[str, Any]]]:
    """從快取獲取數據"""
    if not redis_client:
        return None

    try:
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)
    except Exception as e:
        print(f"快取讀取失敗: {e}")

    return None


def _set_cached_data(cache_key: str, data: List[Dict[str, Any]], ttl: int = 300) -> None:
    """設置快取數據"""
    if not redis_client:
        return

    try:
        redis_client.setex(cache_key, ttl, json.dumps(data, ensure_ascii=False))
    except Exception as e:
        print(f"快取設置失敗: {e}")


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


class BatchCollectionRequest(BaseModel):
    stocks: List[Dict[str, str]]  # [{"symbol": "2330", "market": "TW"}, ...]
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    use_stock_list: Optional[bool] = True


class DataCollectionResponse(BaseModel):
    success: bool
    message: str
    data_points: int
    errors: List[str] = []


class StockListResponse(BaseModel):
    """股票清單響應模型（與前端PaginatedResponse兼容）"""
    items: List[StockResponse]
    total: int
    page: int
    per_page: int  # 改為 per_page 以匹配前端期望
    total_pages: int


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
        skip = (page - 1) * per_page

        # 在資料庫層進行過濾和分頁
        stocks = await stock_crud.get_stocks_with_filters(
            db,
            market=market,
            is_active=is_active,
            search_term=search,
            skip=skip,
            limit=per_page
        )

        # 計算總數（用於分頁信息）
        total_count = await stock_crud.count_stocks_with_filters(
            db,
            market=market,
            is_active=is_active,
            search_term=search
        )

        # 計算總頁數
        total_pages = (total_count + per_page - 1) // per_page

        return StockListResponse(
            items=[StockResponse.model_validate(stock) for stock in stocks],
            total=total_count,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得股票清單失敗: {str(e)}")


@router.get("/active", response_model=List[Dict[str, Any]])
async def get_active_stocks(
    market: Optional[str] = Query(None, description="市場代碼 (TW/US)"),
    force_refresh: bool = Query(False, description="強制刷新快取"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    取得所有活躍股票清單（用於數據收集，不分頁）
    支援快取機制以提升性能
    """
    try:
        # 生成快取鍵
        cache_key = _get_cache_key("active_stocks", market)

        # 嘗試從快取獲取數據（除非強制刷新）
        if not force_refresh:
            cached_data = _get_cached_data(cache_key)
            if cached_data:
                print(f"從快取返回活躍股票清單，數量: {len(cached_data)}")
                return cached_data

        # 獲取所有活躍股票，添加安全限制
        stocks = await stock_crud.get_stocks_with_filters(
            db,
            market=market,
            is_active=True,
            search_term=None,
            skip=0,
            limit=None  # 不限制數量
        )

        # 安全檢查：防止意外返回過多數據
        MAX_STOCKS = 10000  # 設置合理的上限
        if len(stocks) > MAX_STOCKS:
            raise HTTPException(
                status_code=500,
                detail=f"活躍股票數量過多 ({len(stocks)})，超過安全限制 ({MAX_STOCKS})"
            )

        # 回傳簡化的股票清單，僅包含收集所需的欄位
        stock_list = []
        for stock in stocks:
            stock_list.append({
                'id': stock.id,
                'symbol': stock.symbol,
                'market': stock.market,
                'name': stock.name
            })

        # 設置快取（TTL: 5分鐘）
        _set_cached_data(cache_key, stock_list, ttl=300)

        print(f"從資料庫返回活躍股票清單，數量: {len(stock_list)}")
        return stock_list

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得活躍股票清單失敗: {str(e)}")


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
    per_page: int = Query(100, ge=1, le=1000, description="每頁數量"),
    include_indicators: bool = Query(False, description="包含技術指標"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    取得股票完整數據（價格 + 可選技術指標）

    ## 回傳結構
    ```json
    {
        "stock": {"id": int, "symbol": str, "market": str, "name": str},
        "price_data": {
            "items": [{"date": str, "open": float, "high": float, "low": float, "close": float, "volume": int}],
            "pagination": {"total": int, "page": int, "per_page": int, "total_pages": int}
        },
        "indicators": {"RSI": [...], "SMA": [...]} // 僅當 include_indicators=true 時
    }
    ```

    ## 與 /prices 端點差異
    - `/data`: 包含分頁資訊、股票基本資料、可選技術指標（適合複雜查詢）
    - `/prices`: 僅返回價格陣列（適合輕量級查詢）
    - `/price-history`: 返回與前端期望格式兼容的結構
    """
    try:
        # 檢查股票是否存在
        stock = await stock_crud.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")
        
        # 計算分頁偏移量
        offset = (page - 1) * per_page

        # 取得價格數據
        if start_date and end_date:
            prices = await price_history_crud.get_stock_price_range(
                db, stock_id=stock_id, start_date=start_date, end_date=end_date, limit=per_page
            )
            # 簡化計算總數 - 使用已有方法
            all_prices = await price_history_crud.get_stock_price_range(
                db, stock_id=stock_id, start_date=start_date, end_date=end_date
            )
            total_count = len(all_prices)
        else:
            prices = await price_history_crud.get_stock_price_range(
                db, stock_id=stock_id, limit=per_page
            )
            all_prices = await price_history_crud.get_stock_price_range(
                db, stock_id=stock_id
            )
            total_count = len(all_prices)
        
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
        total_pages = (total_count + per_page - 1) // per_page

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
                    "per_page": per_page,
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
    取得股票價格數據（輕量級版本）

    ## 回傳結構
    ```json
    [
        {"date": "2024-01-01", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0, "volume": 1000000}
    ]
    ```

    ## 使用場景
    - 僅需要價格數據時使用
    - 無分頁功能，使用 limit 參數控制數量
    - 無額外資訊（股票基本資料、技術指標）
    - 適合圖表顯示、輕量級查詢

    ## 相關端點
    - 如需分頁資訊：使用 `/data` 端點
    - 如需技術指標：使用 `/data?include_indicators=true`
    - 如需前端兼容格式：使用 `/price-history`
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


# 新增前端期望的價格歷史端點
@router.get("/{stock_id}/price-history", response_model=Dict[str, Any])
async def get_stock_price_history(
    stock_id: int,
    start_date: Optional[date] = Query(None, description="開始日期"),
    end_date: Optional[date] = Query(None, description="結束日期"),
    interval: Optional[str] = Query("1d", description="時間間隔"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    取得股票價格歷史（前端兼容端點）
    """
    try:
        # 檢查股票是否存在
        stock = await stock_crud.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")

        # 取得價格數據
        prices = await price_history_crud.get_stock_price_range(
            db,
            stock_id=stock_id,
            start_date=start_date,
            end_date=end_date,
            limit=1000  # 合理的默認限制
        )

        return {
            "symbol": stock.symbol,
            "data": [
                {
                    "date": price.date.isoformat(),
                    "open": float(price.open_price),
                    "high": float(price.high_price),
                    "low": float(price.low_price),
                    "close": float(price.close_price),
                    "volume": price.volume,
                    "adjusted_close": float(price.adjusted_close or price.close_price)
                }
                for price in prices
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得價格歷史失敗: {str(e)}")


# 新增前端期望的最新價格端點
@router.get("/{stock_id}/price/latest", response_model=Dict[str, Any])
async def get_stock_latest_price(
    stock_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """
    取得股票最新價格（前端兼容端點）
    """
    try:
        # 檢查股票是否存在
        stock = await stock_crud.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")

        # 取得最新價格
        latest_price = await price_history_crud.get_latest_price(db, stock_id=stock_id)
        if not latest_price:
            raise HTTPException(status_code=404, detail="沒有價格數據")

        # 計算變動
        previous_prices = await price_history_crud.get_stock_price_range(
            db, stock_id=stock_id, limit=2
        )

        change = 0.0
        change_percent = 0.0
        if len(previous_prices) >= 2:
            prev_close = float(previous_prices[1].close_price)
            current_close = float(latest_price.close_price)
            change = current_close - prev_close
            change_percent = (change / prev_close) * 100 if prev_close != 0 else 0.0

        return {
            "symbol": stock.symbol,
            "price": float(latest_price.close_price),
            "change": change,
            "change_percent": change_percent,
            "volume": latest_price.volume,
            "timestamp": latest_price.date.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得最新價格失敗: {str(e)}")


# 新增前端期望的數據回填端點
@router.post("/{stock_id}/price/backfill", response_model=Dict[str, Any])
async def backfill_stock_data(
    stock_id: int,
    start_date: Optional[date] = Query(None, description="開始日期"),
    end_date: Optional[date] = Query(None, description="結束日期"),
    force: bool = Query(False, description="強制回填（暫未實現，預留參數）"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    觸發股票數據回填（前端兼容端點）

    注意：force 參數目前暫未實現，數據收集服務會自動處理重複數據
    """
    try:
        # 檢查股票是否存在
        stock = await stock_crud.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")

        # 調用數據收集服務（同步完成）
        result = await data_collection_service.collect_stock_data(
            db_session=db,
            symbol=stock.symbol,
            market=stock.market,
            start_date=start_date,
            end_date=end_date
        )

        if result["success"]:
            # 實際上是同步完成的，不需要 task_id
            return {
                "message": result.get("message", "數據回填已完成"),
                "completed": True,
                "success": True,
                "symbol": stock.symbol,
                "records_processed": result.get("records_processed", 0),
                "records_saved": result.get("records_saved", 0),
                "date_range": result.get("date_range", {}),
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("message", "數據回填失敗"))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"啟動數據回填失敗: {str(e)}")


# 新增前端期望的指標計算端點
@router.get("/{stock_id}/indicators/calculate", response_model=Dict[str, Any])
async def calculate_stock_indicators(
    stock_id: int,
    indicator_types: Optional[str] = Query(None, description="指標類型（逗號分隔）"),
    period: int = Query(30, description="計算週期"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    計算股票技術指標（前端兼容端點）
    """
    try:
        # 檢查股票是否存在
        stock = await stock_crud.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")

        # 取得價格數據
        prices = await price_history_crud.get_stock_price_range(
            db, stock_id=stock_id, limit=period + 50  # 額外數據確保計算準確
        )

        if not prices:
            raise HTTPException(status_code=404, detail="沒有價格數據")

        # 使用真實的技術分析服務進行計算
        analysis_service = TechnicalAnalysisService()

        # 解析指標類型
        requested_indicators = []
        if indicator_types:
            indicator_list = [t.strip().upper() for t in indicator_types.split(',')]
            for indicator_type in indicator_list:
                try:
                    requested_indicators.append(IndicatorType(indicator_type))
                except ValueError:
                    # 忽略不支援的指標類型
                    continue

        # 如果沒有指定或無效的指標類型，使用預設指標
        if not requested_indicators:
            requested_indicators = [IndicatorType.RSI, IndicatorType.SMA, IndicatorType.MACD]

        # 調用分析服務計算指標
        analysis_result = await analysis_service.calculate_stock_indicators(
            db_session=db,
            stock_id=stock_id,
            indicators=requested_indicators,
            days=period + 50,  # 額外數據確保計算準確
            save_to_db=False  # 不保存到資料庫，僅用於API回傳
        )

        # 轉換結果格式以匹配前端期望，即使部分失敗也嘗試返回可用數據
        indicators = {}
        errors = []
        warnings = []

        # 收集錯誤和警告信息
        if analysis_result.errors:
            errors.extend(analysis_result.errors)
        if analysis_result.warnings:
            warnings.extend(analysis_result.warnings)

        # 處理指標數據，即使 success=False 也檢查是否有部分可用數據
        if analysis_result.indicators:
            for indicator_name, values in analysis_result.indicators.items():
                if values:  # 確保有數值
                    # 修正：使用更精確的指標類型匹配
                    indicator_upper = indicator_name.upper()

                    if 'RSI' in indicator_upper and len(values) > 0:
                        indicators["rsi"] = values[-1]  # 取最新值
                    elif 'SMA' in indicator_upper and len(values) > 0:
                        # 處理不同週期的 SMA (SMA_20, SMA_50 等)
                        if 'SMA_20' in indicator_upper:
                            indicators["sma_20"] = values[-1]
                        elif 'SMA_50' in indicator_upper:
                            indicators["sma_50"] = values[-1]
                        else:
                            indicators["sma"] = values[-1]  # 通用 SMA
                    elif 'EMA' in indicator_upper and len(values) > 0:
                        # 處理不同週期的 EMA
                        if 'EMA_12' in indicator_upper:
                            indicators["ema_12"] = values[-1]
                        elif 'EMA_26' in indicator_upper:
                            indicators["ema_26"] = values[-1]
                        else:
                            indicators["ema"] = values[-1]  # 通用 EMA
                    elif 'MACD' in indicator_upper and isinstance(values, dict):
                        # MACD 返回字典格式
                        indicators["macd"] = {
                            "macd": values.get('macd', [0])[-1] if values.get('macd') else 0,
                            "signal": values.get('signal', [0])[-1] if values.get('signal') else 0,
                            "histogram": values.get('histogram', [0])[-1] if values.get('histogram') else 0
                        }
                    elif 'BOLLINGER' in indicator_upper and isinstance(values, dict):
                        # 布林帶返回字典格式
                        indicators["bollinger"] = {
                            "upper": values.get('upper', [0])[-1] if values.get('upper') else 0,
                            "middle": values.get('middle', [0])[-1] if values.get('middle') else 0,
                            "lower": values.get('lower', [0])[-1] if values.get('lower') else 0
                        }

        # 如果沒有任何指標數據且有錯誤，提供詳細錯誤信息
        if not indicators and not analysis_result.success:
            if not errors:
                errors.append("無法計算技術指標，可能由於數據不足")

        result = {
            "symbol": stock.symbol,
            "indicators": indicators,
            "period": period,
            "timestamp": datetime.now().isoformat(),
            "success": analysis_result.success,
            "data_points": len(prices) if prices else 0
        }

        # 只在有錯誤或警告時才加入這些欄位
        if errors:
            result["errors"] = errors
        if warnings:
            result["warnings"] = warnings

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"計算技術指標失敗: {str(e)}")


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
            data_points=result.get('records_saved', 0),
            errors=[result.get('error')] if result.get('error') else []
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

        # 直接回傳服務層的成功狀態，而非固定為 True
        service_success = result.get('success', False)

        # 詳細錯誤資訊（保持向後兼容）
        collection_errors = result.get('collection_errors', [])
        save_errors = result.get('save_errors', [])
        all_errors = collection_errors + save_errors

        return {
            'success': service_success,
            'message': '批次數據收集完成' if service_success else '批次數據收集部分失敗',
            'total_stocks': result.get('total_stocks', 0),
            'success_count': result.get('success_count', 0),
            'error_count': result.get('error_count', 0),
            'total_data_saved': result.get('total_data_saved', 0),
            'errors': all_errors,  # 向後兼容的聚合錯誤
            'error_details': {
                'collection_errors': collection_errors,
                'save_errors': save_errors,
                'failed_symbols': [error.split(':')[0] for error in collection_errors if ':' in error]
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批次數據收集失敗: {str(e)}")


@router.post("/collect-batch", response_model=Dict[str, Any])
async def collect_batch_stocks_data(
    request: BatchCollectionRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    批次收集指定股票數據
    """
    try:
        result = await data_collection_service.collect_batch_stocks_data(
            db,
            request.stocks,
            request.start_date,
            request.end_date
        )

        # 直接回傳服務層的成功狀態
        service_success = result.get('success', False)

        # 詳細錯誤資訊（保持向後兼容）
        collection_errors = result.get('collection_errors', [])
        save_errors = result.get('save_errors', [])
        all_errors = collection_errors + save_errors

        return {
            'success': service_success,
            'message': result.get('message', '批次收集完成' if service_success else '批次收集部分失敗'),
            'total_stocks': result.get('total_stocks', 0),
            'success_count': result.get('success_count', 0),
            'error_count': result.get('error_count', 0),
            'total_data_saved': result.get('total_data_saved', 0),
            'errors': all_errors,  # 向後兼容的聚合錯誤
            'error_details': {
                'collection_errors': collection_errors,
                'save_errors': save_errors,
                'failed_symbols': [error.split(':')[0] for error in collection_errors if ':' in error]
            }
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


@router.get("/search", response_model=StockListResponse)
async def search_stocks(
    q: str = Query(..., description="搜尋關鍵字（股票代號或名稱）", min_length=1),
    market: Optional[str] = Query(None, description="市場代碼 (TW/US)"),
    is_active: Optional[bool] = Query(True, description="股票狀態篩選"),
    page: int = Query(1, ge=1, description="頁碼"),
    per_page: int = Query(20, ge=1, le=100, description="每頁數量"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    搜尋股票（支援分頁）
    """
    try:
        # 計算分頁偏移量
        skip = (page - 1) * per_page

        # 在資料庫層進行搜尋和分頁
        stocks = await stock_crud.get_stocks_with_filters(
            db,
            market=market,
            is_active=is_active,
            search_term=q,
            skip=skip,
            limit=per_page
        )

        # 計算總數
        total_count = await stock_crud.count_stocks_with_filters(
            db,
            market=market,
            is_active=is_active,
            search_term=q
        )

        # 計算總頁數
        total_pages = (total_count + per_page - 1) // per_page

        return StockListResponse(
            items=[StockResponse.model_validate(stock) for stock in stocks],
            total=total_count,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜尋股票失敗: {str(e)}")


@router.get("/simple", response_model=List[StockResponse])
async def get_stocks_simple(
    market: Optional[str] = Query(None, description="市場代碼 (TW/US)"),
    is_active: bool = Query(True, description="只返回活躍股票"),
    limit: int = Query(100, ge=1, le=1000, description="返回數量限制"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    取得股票清單（簡化版本，向後兼容）
    """
    try:
        # 使用優化後的資料庫查詢
        stocks = await stock_crud.get_stocks_with_filters(
            db,
            market=market,
            is_active=is_active,
            skip=0,
            limit=limit
        )

        return [StockResponse.model_validate(stock) for stock in stocks]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得股票清單失敗: {str(e)}")


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