"""
股票價格相關API端點
負責: /{stock_id}/data, /prices, /price-history, /price/latest, /price/backfill
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional, Dict, Any
from datetime import date

from core.database import get_db_session
from services.data.collection import data_collection_service
from models.repositories.crud_stock import stock_crud
from models.repositories.crud_price_history import price_history_crud
from models.domain.price_history import PriceHistory
from api.schemas.stocks import PriceDataResponse

router = APIRouter()


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
            db, stock.symbol, stock.market, start_date, end_date
        )

        return {
            "success": result.success,
            "message": result.message,
            "data_points": result.data_points_collected,
            "errors": result.errors
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"數據回填失敗: {str(e)}")