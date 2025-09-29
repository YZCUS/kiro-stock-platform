"""
股票價格相關API端點
負責: /{stock_id}/data, /prices, /price-history, /price/latest, /price/backfill
"""
from typing import List, Optional, Dict, Any
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    get_database_session,
    get_stock_service,
    get_data_collection_service_clean
)
from api.schemas.stocks import PriceDataResponse
from domain.services.stock_service import StockService
from domain.services.data_collection_service import DataCollectionService

router = APIRouter()


@router.get("/{stock_id}/prices", response_model=List[PriceDataResponse])
async def get_stock_prices(
    stock_id: int,
    start_date: Optional[date] = Query(None, description="開始日期"),
    end_date: Optional[date] = Query(None, description="結束日期"),
    limit: int = Query(100, description="返回數量限制"),
    db: AsyncSession = Depends(get_database_session),
    stock_service: StockService = Depends(get_stock_service)
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
        prices = await stock_service.get_stock_prices(
            db=db,
            stock_id=stock_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )

        return [PriceDataResponse(**price) for price in prices]

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
    db: AsyncSession = Depends(get_database_session),
    stock_service: StockService = Depends(get_stock_service)
):
    """
    取得股票價格歷史（前端兼容端點）
    """
    try:
        # 注意：interval 參數暫未實現，目前統一返回日線數據
        _ = interval  # 消除未使用警告

        return await stock_service.get_price_history(
            db=db,
            stock_id=stock_id,
            start_date=start_date,
            end_date=end_date,
            limit=1000
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得價格歷史失敗: {str(e)}")


@router.get("/{stock_id}/price/latest", response_model=Dict[str, Any])
async def get_stock_latest_price(
    stock_id: int,
    db: AsyncSession = Depends(get_database_session),
    stock_service: StockService = Depends(get_stock_service)
):
    """
    取得股票最新價格（前端兼容端點）
    """
    try:
        try:
            return await stock_service.get_latest_price_with_change(db, stock_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

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
    db: AsyncSession = Depends(get_database_session),
    data_collection_service: DataCollectionService = Depends(get_data_collection_service_clean)
):
    """
    觸發股票數據回填（前端兼容端點）

    注意：force 參數目前暫未實現，數據收集服務會自動處理重複數據
    """
    try:
        # 注意：force 參數暫未實現，預留供未來功能
        _ = force  # 消除未使用警告

        try:
            result = await data_collection_service.collect_stock_data(
                db=db,
                stock_id=stock_id,
                start_date=start_date,
                end_date=end_date
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

        return {
            "success": result.status == result.status.SUCCESS,
            "message": result.status.value,
            "data_points": result.records_collected,
            "errors": result.errors,
            "warnings": result.warnings,
            "execution_time": result.execution_time_seconds
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"數據回填失敗: {str(e)}")