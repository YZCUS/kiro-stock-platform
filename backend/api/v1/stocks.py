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
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel, Field
import redis
import json
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
        
        # 計算分頁偏移量（暫未實現偏移式分頁，保留供未來使用）
        # offset = (page - 1) * per_page

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
    interval: Optional[str] = Query("1d", description="時間間隔（暫未實現，保留參數）"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    取得股票價格歷史（前端兼容端點）
    """
    try:
        # 注意：interval 參數暫未實現，目前統一返回日線數據
        _ = interval  # 消除未使用警告

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

        # 計算變動 - 使用更強健的方法直接查詢前一個交易日
        change = 0.0
        change_percent = 0.0

        # 直接查詢小於當前日期的最近一筆價格記錄
        # 優點：
        # 1. 正確處理週末和假日（自動跳過非交易日）
        # 2. 處理資料缺漏情況（找到實際存在的前一個交易日）
        # 3. 避免使用相同結果集推算（确保是真正的前一個交易日）
        # 4. 不依賴固定的日期計算（timedelta 可能跨越多個非交易日）
        from sqlalchemy import select, desc
        from models.domain.price_history import PriceHistory

        previous_price_query = select(PriceHistory).where(
            PriceHistory.stock_id == stock_id,
            PriceHistory.date < latest_price.date
        ).order_by(desc(PriceHistory.date)).limit(1)

        result = await db.execute(previous_price_query)
        previous_price = result.scalar_one_or_none()

        if previous_price:
            prev_close = float(previous_price.close_price)
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
        # 注意：force 參數暫未實現，預留供未來功能
        _ = force  # 消除未使用警告

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

        # 取得價格數據，使用動態 buffer
        # 根據周期動態調整 buffer，最小 20，最大 100
        buffer_size = max(20, min(100, period * 2))
        prices = await price_history_crud.get_stock_price_range(
            db, stock_id=stock_id, limit=period + buffer_size
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
            requested_indicators = [IndicatorType.RSI, IndicatorType.SMA_20, IndicatorType.MACD]

        # 將 IndicatorType 枚舉轉換為字符串列表
        indicator_type_strings = [indicator.value for indicator in requested_indicators]

        # 調用分析服務獲取指標數據
        try:
            indicator_data = await analysis_service.get_stock_indicators(
                db_session=db,
                stock_id=stock_id,
                indicator_types=indicator_type_strings,
                days=period + buffer_size
            )
            success = True
            errors = []
            warnings = []
        except Exception as e:
            # 如果獲取失敗，嘗試重新計算
            try:
                analysis_result = await analysis_service.calculate_stock_indicators(
                    db_session=db,
                    stock_id=stock_id,
                    indicators=requested_indicators,
                    days=period + buffer_size,
                    save_to_db=True  # 保存到資料庫以便下次獲取
                )
                # 重新獲取計算後的數據
                indicator_data = await analysis_service.get_stock_indicators(
                    db_session=db,
                    stock_id=stock_id,
                    indicator_types=indicator_type_strings,
                    days=period + buffer_size
                )
                # 根據成功和失敗的指標數量判斷整體成功與否
                success = analysis_result.indicators_successful > 0 and analysis_result.indicators_failed == 0
                errors = analysis_result.errors or []
                warnings = analysis_result.warnings or []
            except Exception as calc_error:
                indicator_data = {}
                success = False
                errors = [f"計算指標失敗: {str(calc_error)}"]
                warnings = []

        # 轉換結果格式以匹配前端期望
        indicators = {}

        # 處理指標數據
        if indicator_data:
            for indicator_name, value_list in indicator_data.items():
                if value_list and len(value_list) > 0:  # 確保有數值
                    # 獲取最新的指標值
                    latest_value = value_list[-1] if isinstance(value_list, list) else value_list

                    # 修正：使用精確的指標類型匹配
                    indicator_upper = indicator_name.upper()

                    if indicator_upper == 'RSI':
                        indicators["rsi"] = latest_value.get('value') if isinstance(latest_value, dict) else latest_value
                    elif indicator_upper == 'SMA_20':
                        indicators["sma_20"] = latest_value.get('value') if isinstance(latest_value, dict) else latest_value
                    elif indicator_upper == 'SMA_50':
                        indicators["sma_50"] = latest_value.get('value') if isinstance(latest_value, dict) else latest_value
                    elif indicator_upper == 'SMA_5':
                        indicators["sma_5"] = latest_value.get('value') if isinstance(latest_value, dict) else latest_value
                    elif indicator_upper == 'SMA_60':
                        indicators["sma_60"] = latest_value.get('value') if isinstance(latest_value, dict) else latest_value
                    elif indicator_upper == 'EMA_12':
                        indicators["ema_12"] = latest_value.get('value') if isinstance(latest_value, dict) else latest_value
                    elif indicator_upper == 'EMA_26':
                        indicators["ema_26"] = latest_value.get('value') if isinstance(latest_value, dict) else latest_value
                    elif indicator_upper == 'MACD':
                        # MACD 可能返回複雜格式
                        if isinstance(latest_value, dict):
                            indicators["macd"] = {
                                "macd": latest_value.get('macd', 0),
                                "signal": latest_value.get('signal', 0),
                                "histogram": latest_value.get('histogram', 0)
                            }
                        else:
                            indicators["macd"] = latest_value
                    elif indicator_upper == 'BBANDS':
                        # 布林帶返回複雜格式
                        if isinstance(latest_value, dict):
                            indicators["bollinger"] = {
                                "upper": latest_value.get('upper', 0),
                                "middle": latest_value.get('middle', 0),
                                "lower": latest_value.get('lower', 0)
                            }
                        else:
                            indicators["bollinger"] = latest_value
                    elif indicator_upper in ['STOCH', 'KD_K']:
                        # 隨機指標
                        if isinstance(latest_value, dict):
                            indicators["stoch"] = {
                                "k": latest_value.get('k', 0),
                                "d": latest_value.get('d', 0)
                            }
                        else:
                            indicators["stoch"] = latest_value
                    else:
                        # 其他指標使用通用格式
                        indicators[indicator_name.lower()] = latest_value.get('value') if isinstance(latest_value, dict) else latest_value

        # 如果沒有任何指標數據且有錯誤，提供詳細錯誤信息
        if not indicators and not success:
            if not errors:
                errors.append("無法計算技術指標，可能由於數據不足")

        result = {
            "symbol": stock.symbol,
            "indicators": indicators,
            "period": period,
            "timestamp": datetime.now().isoformat(),
            "success": success,
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
        
        # 轉換為標準分頁格式，將指標數據扁平化為陣列
        items = []
        for ind_type, data_list in indicators_data.items():
            for data_point in data_list:
                items.append({
                    "indicator_type": ind_type,
                    "date": data_point["date"],
                    "value": data_point["value"],
                    "parameters": data_point["parameters"],
                    "stock_id": stock_id,
                    "symbol": stock.symbol
                })

        return {
            "items": items,
            "total": total_count,
            "page": page,
            "per_page": page_size,
            "total_pages": total_pages
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得技術指標失敗: {str(e)}")


class IndicatorCalculateRequest(BaseModel):
    """技術指標計算請求模型"""
    indicator_type: str = Field(..., description="技術指標類型，可以是單一指標如 'RSI' 或多個指標如 'RSI,SMA_20,MACD'")
    period: int = Field(default=14, ge=1, le=500, description="計算周期")
    timeframe: str = Field(default="1d", description="時間框架")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="額外參數")
    start_date: Optional[date] = Field(default=None, description="開始日期")
    end_date: Optional[date] = Field(default=None, description="結束日期")


@router.post("/{stock_id}/indicators/calculate", response_model=Dict[str, Any])
async def calculate_stock_indicators_post(
    stock_id: int,
    request: IndicatorCalculateRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    計算股票技術指標 (POST 版本 - 支援即時計算)

    此端點支援前端的即時指標計算需求，可以指定多個指標類型並返回即時計算結果。
    與 GET 版本不同，這個端點著重於即時計算而非歷史數據查詢。
    """
    try:
        # 檢查股票是否存在
        stock = await stock_crud.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")

        # 取得價格數據，使用動態 buffer
        period = request.period
        # 根據周期動態調整 buffer，最小 20，最大 100
        buffer_size = max(20, min(100, period * 2))

        prices = await price_history_crud.get_stock_price_range(
            db, stock_id=stock_id, limit=period + buffer_size
        )

        if not prices:
            raise HTTPException(status_code=404, detail="沒有價格數據")

        # 使用技術分析服務進行計算
        analysis_service = TechnicalAnalysisService()

        # 解析指標類型
        requested_indicators = []
        if request.indicator_type:
            indicator_list = [t.strip().upper() for t in request.indicator_type.split(',')]
            for indicator_type in indicator_list:
                try:
                    requested_indicators.append(IndicatorType(indicator_type))
                except ValueError:
                    # 忽略不支援的指標類型
                    continue

        # 如果沒有指定或無效的指標類型，使用預設指標
        if not requested_indicators:
            requested_indicators = [IndicatorType.RSI, IndicatorType.SMA_20, IndicatorType.MACD]

        # 調用分析服務進行即時計算
        try:
            analysis_result = await analysis_service.calculate_stock_indicators(
                db_session=db,
                stock_id=stock_id,
                indicators=requested_indicators,
                days=period + buffer_size,
                save_to_db=True
            )

            # 判斷計算是否成功
            success = analysis_result.indicators_successful > 0 and analysis_result.indicators_failed == 0
            errors = analysis_result.errors
            warnings = analysis_result.warnings

            # 獲取指標數據用於格式化
            indicator_data = {}
            if hasattr(analysis_result, 'indicator_data') and analysis_result.indicator_data:
                indicator_data = analysis_result.indicator_data
            else:
                # 如果沒有直接數據，嘗試從數據庫獲取最新計算結果
                indicator_type_strings = [indicator.value for indicator in requested_indicators]
                try:
                    indicator_data = await analysis_service.get_stock_indicators(
                        db_session=db,
                        stock_id=stock_id,
                        indicator_types=indicator_type_strings,
                        days=10  # 只需要最新數據
                    )
                except Exception:
                    indicator_data = {}

        except Exception as e:
            # 計算失敗
            success = False
            errors = [f"指標計算失敗: {str(e)}"]
            warnings = []
            indicator_data = {}

        # 格式化指標數據以匹配前端期望的結構
        indicators = {}
        if indicator_data:
            for indicator_name, value_list in indicator_data.items():
                if value_list and len(value_list) > 0:
                    latest_value = value_list[-1] if isinstance(value_list, list) else value_list
                    indicator_upper = indicator_name.upper()

                    if indicator_upper == 'RSI':
                        indicators["rsi"] = latest_value.get('value') if isinstance(latest_value, dict) else latest_value
                    elif indicator_upper == 'SMA_20':
                        indicators["sma_20"] = latest_value.get('value') if isinstance(latest_value, dict) else latest_value
                    elif indicator_upper == 'SMA_5':
                        indicators["sma_5"] = latest_value.get('value') if isinstance(latest_value, dict) else latest_value
                    elif indicator_upper == 'MACD':
                        if isinstance(latest_value, dict):
                            indicators["macd"] = {
                                "macd": latest_value.get('macd', 0),
                                "signal": latest_value.get('signal', 0),
                                "histogram": latest_value.get('histogram', 0)
                            }
                    elif indicator_upper in ['BBANDS', 'BOLLINGER']:
                        if isinstance(latest_value, dict):
                            indicators["bollinger"] = {
                                "upper": latest_value.get('upper', 0),
                                "middle": latest_value.get('middle', 0),
                                "lower": latest_value.get('lower', 0)
                            }
                    elif indicator_upper in ['STOCH', 'KD_K']:
                        if isinstance(latest_value, dict):
                            indicators["stoch"] = {
                                "k": latest_value.get('k', 0),
                                "d": latest_value.get('d', 0)
                            }
                    else:
                        # 其他指標使用通用格式
                        indicators[indicator_name.lower()] = latest_value.get('value') if isinstance(latest_value, dict) else latest_value

        # 構建響應，匹配 IndicatorResponse 接口
        result = {
            "symbol": stock.symbol,
            "indicators": indicators,
            "period": period,
            "timestamp": datetime.now().isoformat(),
            "success": success,
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


class IndicatorBatchItem(BaseModel):
    """批次指標計算項目"""
    type: str = Field(..., description="指標類型")
    period: Optional[int] = Field(default=14, description="計算週期")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="額外參數")


class IndicatorBatchCalculateRequest(BaseModel):
    """批次技術指標計算請求模型"""
    indicators: List[IndicatorBatchItem] = Field(..., description="指標列表")
    timeframe: str = Field(default="1d", description="時間框架")
    start_date: Optional[date] = Field(default=None, description="開始日期")
    end_date: Optional[date] = Field(default=None, description="結束日期")


class IndicatorSummaryResponse(BaseModel):
    """指標摘要響應模型 - 匹配前端 getIndicators 期望格式"""
    stock_id: int = Field(..., description="股票ID")
    symbol: str = Field(..., description="股票代碼")
    timeframe: str = Field(..., description="時間框架")
    indicators: Dict[str, Dict[str, Any]] = Field(..., description="指標數據，格式為 Record<string, IndicatorResponse>")


@router.post("/{stock_id}/indicators/calculate/batch", response_model=Dict[str, Any])
async def batch_calculate_stock_indicators(
    stock_id: int,
    request: IndicatorBatchCalculateRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    批量計算股票技術指標

    此端點支援前端的批量指標計算需求，可以一次計算多個不同類型和周期的指標。
    """
    try:
        # 檢查股票是否存在
        stock = await stock_crud.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")

        # 初始化服務
        analysis_service = TechnicalAnalysisService()

        # 處理每個指標請求
        calculated_indicators = {}
        calculation_errors = []

        for indicator_item in request.indicators:
            try:
                # 解析指標類型
                try:
                    indicator_type = IndicatorType(indicator_item.type.upper())
                except ValueError:
                    calculation_errors.append(f"不支援的指標類型: {indicator_item.type}")
                    continue

                # 計算動態 buffer
                period = indicator_item.period or 14
                buffer_size = max(20, min(100, period * 2))

                # 獲取價格數據
                prices = await price_history_crud.get_stock_price_range(
                    db, stock_id=stock_id, limit=period + buffer_size
                )

                if not prices:
                    calculation_errors.append(f"指標 {indicator_item.type}: 沒有價格數據")
                    continue

                # 計算指標
                analysis_result = await analysis_service.calculate_stock_indicators(
                    db_session=db,
                    stock_id=stock_id,
                    indicators=[indicator_type],
                    days=period + buffer_size,
                    save_to_db=True
                )

                # 獲取計算結果
                if analysis_result.indicators_successful > 0:
                    # 獲取指標數據
                    indicator_data = await analysis_service.get_stock_indicators(
                        db_session=db,
                        stock_id=stock_id,
                        indicator_types=[indicator_type.value],
                        days=10  # 只需要最新數據
                    )

                    if indicator_data and indicator_type.value in indicator_data:
                        # 格式化數據以匹配前端期望
                        raw_data = indicator_data[indicator_type.value]
                        formatted_data = []

                        for item in raw_data:
                            if isinstance(item, dict):
                                formatted_data.append({
                                    "date": item.get("date"),
                                    "value": item.get("value"),
                                    **{k: v for k, v in item.items() if k not in ["date", "value"]}
                                })
                            else:
                                formatted_data.append({"value": item})

                        calculated_indicators[indicator_type.value] = {
                            "data": formatted_data,
                            "parameters": {
                                "period": period,
                                "timeframe": request.timeframe,
                                **(indicator_item.parameters or {})
                            }
                        }
                else:
                    calculation_errors.append(f"指標 {indicator_item.type}: 計算失敗")
                    if analysis_result.errors:
                        calculation_errors.extend(analysis_result.errors)

            except Exception as e:
                calculation_errors.append(f"指標 {indicator_item.type}: {str(e)}")

        # 構建響應
        result = {
            "stock_id": stock_id,
            "symbol": stock.symbol,
            "timeframe": request.timeframe,
            "indicators": calculated_indicators,
            "calculated_at": datetime.now().isoformat()
        }

        # 如果有錯誤，加入錯誤信息
        if calculation_errors:
            result["errors"] = calculation_errors

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量計算技術指標失敗: {str(e)}")


@router.get("/{stock_id}/indicators/{indicator_type}", response_model=Dict[str, Any])
async def get_specific_stock_indicator(
    stock_id: int,
    indicator_type: str,
    period: int = Query(14, ge=1, le=500, description="計算周期"),
    timeframe: str = Query("1d", description="時間框架"),
    start_date: Optional[date] = Query(None, description="開始日期"),
    end_date: Optional[date] = Query(None, description="結束日期"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    取得特定類型的股票技術指標
    """
    try:
        # 檢查股票是否存在
        stock = await stock_crud.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")

        # 解析指標類型
        try:
            indicator_enum = IndicatorType(indicator_type.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"不支援的指標類型: {indicator_type}")

        # 使用技術分析服務
        analysis_service = TechnicalAnalysisService()

        # 獲取指標數據
        try:
            indicator_data = await analysis_service.get_stock_indicators(
                db_session=db,
                stock_id=stock_id,
                indicator_types=[indicator_enum.value],
                days=period + max(20, min(100, period * 2))  # 動態 buffer
            )

            if indicator_data and indicator_enum.value in indicator_data:
                raw_data = indicator_data[indicator_enum.value]

                # 格式化為與單一計算端點一致的結構
                if raw_data and len(raw_data) > 0:
                    latest_value = raw_data[-1] if isinstance(raw_data, list) else raw_data

                    # 根據指標類型格式化數據
                    formatted_indicator = {}
                    indicator_upper = indicator_enum.value.upper()

                    if indicator_upper == 'RSI':
                        formatted_indicator["rsi"] = latest_value.get('value') if isinstance(latest_value, dict) else latest_value
                    elif indicator_upper in ['SMA_5', 'SMA_20', 'SMA_60']:
                        formatted_indicator[indicator_upper.lower()] = latest_value.get('value') if isinstance(latest_value, dict) else latest_value
                    elif indicator_upper == 'MACD':
                        if isinstance(latest_value, dict):
                            formatted_indicator["macd"] = {
                                "macd": latest_value.get('macd', 0),
                                "signal": latest_value.get('signal', 0),
                                "histogram": latest_value.get('histogram', 0)
                            }
                    elif indicator_upper in ['BBANDS', 'BOLLINGER']:
                        if isinstance(latest_value, dict):
                            formatted_indicator["bollinger"] = {
                                "upper": latest_value.get('upper', 0),
                                "middle": latest_value.get('middle', 0),
                                "lower": latest_value.get('lower', 0)
                            }
                    elif indicator_upper in ['STOCH', 'KD_K']:
                        if isinstance(latest_value, dict):
                            formatted_indicator["stoch"] = {
                                "k": latest_value.get('k', 0),
                                "d": latest_value.get('d', 0)
                            }
                    else:
                        # 其他指標使用通用格式
                        formatted_indicator[indicator_type.lower()] = latest_value.get('value') if isinstance(latest_value, dict) else latest_value

                    return {
                        "symbol": stock.symbol,
                        "indicators": formatted_indicator,
                        "period": period,
                        "timestamp": datetime.now().isoformat(),
                        "success": True,
                        "data_points": len(raw_data) if isinstance(raw_data, list) else 1
                    }
                else:
                    # 沒有數據，嘗試計算
                    analysis_result = await analysis_service.calculate_stock_indicators(
                        db_session=db,
                        stock_id=stock_id,
                        indicators=[indicator_enum],
                        days=period + max(20, min(100, period * 2)),
                        save_to_db=True
                    )

                    if analysis_result.indicators_successful > 0:
                        # 重新獲取計算後的數據
                        return await get_specific_stock_indicator(
                            stock_id, indicator_type, period, timeframe, start_date, end_date, db
                        )
                    else:
                        return {
                            "symbol": stock.symbol,
                            "indicators": {},
                            "period": period,
                            "timestamp": datetime.now().isoformat(),
                            "success": False,
                            "data_points": 0,
                            "errors": analysis_result.errors or ["計算指標失敗"]
                        }
            else:
                raise HTTPException(status_code=404, detail=f"找不到指標數據: {indicator_type}")

        except Exception as e:
            return {
                "symbol": stock.symbol,
                "indicators": {},
                "period": period,
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "data_points": 0,
                "errors": [f"獲取指標失敗: {str(e)}"]
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取特定指標失敗: {str(e)}")


@router.get("/{stock_id}/indicators/summary", response_model=IndicatorSummaryResponse)
async def get_stock_indicators_summary(
    stock_id: int,
    indicator_types: Optional[str] = Query(None, description="指標類型（逗號分隔）"),
    timeframe: str = Query("1d", description="時間框架"),
    start_date: Optional[date] = Query(None, description="開始日期"),
    end_date: Optional[date] = Query(None, description="結束日期"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    取得股票技術指標摘要（前端 getIndicators 專用格式）

    返回格式：
    {
      stock_id: number,
      symbol: string,
      timeframe: string,
      indicators: Record<string, IndicatorResponse>
    }
    """
    try:
        # 注意：start_date 和 end_date 參數暫未實現，保留供未來使用
        _ = start_date  # 消除未使用警告
        _ = end_date    # 消除未使用警告

        # 檢查股票是否存在
        stock = await stock_crud.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")

        # 解析要獲取的指標類型
        requested_indicators = []
        if indicator_types:
            indicator_list = [t.strip().upper() for t in indicator_types.split(',')]
            for indicator_type in indicator_list:
                try:
                    requested_indicators.append(IndicatorType(indicator_type))
                except ValueError:
                    continue

        # 如果沒有指定指標，使用常用指標
        if not requested_indicators:
            requested_indicators = [
                IndicatorType.RSI,
                IndicatorType.SMA_20,
                IndicatorType.MACD,
                IndicatorType.SMA_5
            ]

        # 使用技術分析服務
        analysis_service = TechnicalAnalysisService()

        # 獲取指標數據
        indicators_summary = {}

        for indicator_type in requested_indicators:
            try:
                indicator_data = await analysis_service.get_stock_indicators(
                    db_session=db,
                    stock_id=stock_id,
                    indicator_types=[indicator_type.value],
                    days=50  # 獲取最近50天的數據
                )

                if indicator_data and indicator_type.value in indicator_data:
                    raw_data = indicator_data[indicator_type.value]

                    if raw_data and len(raw_data) > 0:
                        # 格式化為 IndicatorResponse 格式
                        latest_value = raw_data[-1] if isinstance(raw_data, list) else raw_data

                        # 創建符合 IndicatorResponse 接口的響應
                        formatted_response = {
                            "symbol": stock.symbol,
                            "indicators": {},
                            "period": 14,  # 預設周期
                            "timestamp": datetime.now().isoformat(),
                            "success": True,
                            "data_points": len(raw_data) if isinstance(raw_data, list) else 1
                        }

                        # 根據指標類型格式化數據
                        indicator_upper = indicator_type.value.upper()
                        if indicator_upper == 'RSI':
                            formatted_response["indicators"]["rsi"] = latest_value.get('value') if isinstance(latest_value, dict) else latest_value
                        elif indicator_upper in ['SMA_5', 'SMA_20', 'SMA_60']:
                            formatted_response["indicators"][indicator_upper.lower()] = latest_value.get('value') if isinstance(latest_value, dict) else latest_value
                        elif indicator_upper == 'MACD':
                            if isinstance(latest_value, dict):
                                formatted_response["indicators"]["macd"] = {
                                    "macd": latest_value.get('macd', 0),
                                    "signal": latest_value.get('signal', 0),
                                    "histogram": latest_value.get('histogram', 0)
                                }
                        else:
                            formatted_response["indicators"][indicator_type.value.lower()] = latest_value.get('value') if isinstance(latest_value, dict) else latest_value

                        indicators_summary[indicator_type.value] = formatted_response

            except Exception as e:
                # 如果單個指標失敗，添加錯誤響應
                indicators_summary[indicator_type.value] = {
                    "symbol": stock.symbol,
                    "indicators": {},
                    "period": 14,
                    "timestamp": datetime.now().isoformat(),
                    "success": False,
                    "data_points": 0,
                    "errors": [f"獲取指標失敗: {str(e)}"]
                }

        return {
            "stock_id": stock_id,
            "symbol": stock.symbol,
            "timeframe": timeframe,
            "indicators": indicators_summary
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取指標摘要失敗: {str(e)}")


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