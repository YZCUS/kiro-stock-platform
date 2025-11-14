"""
股票價格相關API端點
負責: /{stock_id}/data, /prices, /price-history, /price/latest, /price/backfill
"""

from typing import List, Optional, Dict, Any
from datetime import date
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.dependencies import (
    get_database_session,
    get_stock_service,
    get_data_collection_service_clean,
)
from api.schemas.stocks import PriceDataResponse
from domain.services.stock_service import StockService
from domain.services.data_collection_service import DataCollectionService
from domain.models.stock import Stock
from domain.models.price_history import PriceHistory

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/prices/data-exists")
async def check_price_data_exists(
    date: str = Query(..., description="檢查日期 (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_database_session),
) -> Dict[str, Any]:
    """
    檢查指定日期是否有價格數據

    Args:
        date: 日期字串 (YYYY-MM-DD 格式)
        db: 資料庫會話

    Returns:
        Dict: 包含 has_data 和 stock_count 的字典
    """
    try:
        from datetime import datetime

        # 解析日期
        check_date = datetime.strptime(date, "%Y-%m-%d").date()

        # 查詢該日期的價格數據數量
        query = select(func.count(PriceHistory.id)).where(
            PriceHistory.date == check_date
        )

        result = await db.execute(query)
        count = result.scalar()

        logger.info(f"檢查日期 {check_date} 的價格數據: {count} 筆")

        return {
            "success": True,
            "date": date,
            "has_data": count > 0,
            "stock_count": count,
        }

    except ValueError as e:
        logger.error(f"日期格式錯誤: {date}")
        raise HTTPException(
            status_code=400, detail=f"日期格式錯誤，請使用 YYYY-MM-DD 格式"
        )
    except Exception as e:
        logger.error(f"檢查價格數據時發生錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"檢查失敗: {str(e)}")


@router.get("/{stock_id}/prices", response_model=List[PriceDataResponse])
async def get_stock_prices(
    stock_id: int,
    start_date: Optional[date] = Query(None, description="開始日期"),
    end_date: Optional[date] = Query(None, description="結束日期"),
    limit: int = Query(100, description="返回數量限制"),
    db: AsyncSession = Depends(get_database_session),
    stock_service: StockService = Depends(get_stock_service),
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
            limit=limit,
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
    stock_service: StockService = Depends(get_stock_service),
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
            limit=1000,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得價格歷史失敗: {str(e)}")


@router.get("/{stock_id}/price/latest", response_model=Dict[str, Any])
async def get_stock_latest_price(
    stock_id: int,
    db: AsyncSession = Depends(get_database_session),
    stock_service: StockService = Depends(get_stock_service),
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
    data_collection_service: DataCollectionService = Depends(
        get_data_collection_service_clean
    ),
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
                db=db, stock_id=stock_id, start_date=start_date, end_date=end_date
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

        return {
            "success": result.status == result.status.SUCCESS,
            "message": result.status.value,
            "data_points": result.records_collected,
            "errors": result.errors,
            "warnings": result.warnings,
            "execution_time": result.execution_time_seconds,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"數據回填失敗: {str(e)}")


@router.post("/refresh-all", response_model=Dict[str, Any])
async def refresh_all_stock_prices(
    db: AsyncSession = Depends(get_database_session),
    data_collection_service: DataCollectionService = Depends(
        get_data_collection_service_clean
    ),
):
    """
    刷新所有活躍股票的最新價格數據

    此端點會：
    1. 找出所有活躍股票
    2. 逐一更新它們的最新價格數據（最近30天）
    3. 返回處理結果摘要

    適用場景：
    - 每日定時更新所有股票價格
    - 手動刷新所有股票的最新數據
    """
    try:
        from datetime import datetime, timedelta

        logger.info("開始刷新所有活躍股票的最新價格數據")

        # 查找所有活躍股票
        query = select(Stock).where(Stock.is_active == True)
        result = await db.execute(query)
        active_stocks = result.scalars().all()

        logger.info(f"找到 {len(active_stocks)} 個活躍股票")

        if not active_stocks:
            return {
                "success": True,
                "message": "沒有活躍股票需要更新",
                "total_stocks": 0,
                "successful": 0,
                "failed": 0,
                "results": [],
            }

        # 計算開始日期（最近30天）
        start_date = (datetime.now() - timedelta(days=30)).date()

        # 逐一刷新數據
        results = []
        successful = 0
        failed = 0

        for stock in active_stocks:
            try:
                logger.info(f"正在刷新股票: {stock.symbol} ({stock.name})")

                collect_result = await data_collection_service.collect_stock_data(
                    db=db,
                    stock_id=stock.id,
                    start_date=start_date,
                    end_date=None,  # 到今天
                )

                if collect_result.status == collect_result.status.SUCCESS:
                    successful += 1
                    results.append(
                        {
                            "stock_id": stock.id,
                            "symbol": stock.symbol,
                            "name": stock.name,
                            "success": True,
                            "data_points": collect_result.records_collected,
                            "message": "成功刷新數據",
                        }
                    )
                else:
                    failed += 1
                    results.append(
                        {
                            "stock_id": stock.id,
                            "symbol": stock.symbol,
                            "name": stock.name,
                            "success": False,
                            "data_points": 0,
                            "message": f"刷新失敗: {collect_result.status.value}",
                            "errors": collect_result.errors,
                        }
                    )

            except Exception as e:
                failed += 1
                logger.error(f"刷新股票 {stock.symbol} 時發生錯誤: {str(e)}")
                results.append(
                    {
                        "stock_id": stock.id,
                        "symbol": stock.symbol,
                        "name": stock.name,
                        "success": False,
                        "data_points": 0,
                        "message": f"錯誤: {str(e)}",
                    }
                )

        logger.info(f"批量刷新完成: 成功 {successful}, 失敗 {failed}")

        return {
            "success": True,
            "message": f"批量刷新完成：成功 {successful} 個，失敗 {failed} 個",
            "total_stocks": len(active_stocks),
            "successful": successful,
            "failed": failed,
            "results": results,
        }

    except Exception as e:
        logger.error(f"批量刷新失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批量刷新失敗: {str(e)}")


@router.post("/backfill-missing", response_model=Dict[str, Any])
async def backfill_missing_prices(
    db: AsyncSession = Depends(get_database_session),
    data_collection_service: DataCollectionService = Depends(
        get_data_collection_service_clean
    ),
):
    """
    自動回填所有缺失價格的股票數據（僅針對完全沒有數據的股票）

    此端點會：
    1. 找出所有沒有價格數據的活躍股票
    2. 逐一抓取它們的歷史價格數據
    3. 返回處理結果摘要

    注意：此端點只處理完全沒有價格數據的股票。
    如需更新已有數據的股票，請使用 /refresh-all 端點。
    """
    try:
        logger.info("開始批量回填缺失的股票價格數據")

        # 查找所有沒有價格數據的活躍股票
        # 使用 LEFT JOIN 找出 price_history 表中沒有記錄的股票
        query = (
            select(Stock)
            .outerjoin(PriceHistory, Stock.id == PriceHistory.stock_id)
            .where(Stock.is_active == True)
            .group_by(Stock.id)
            .having(func.count(PriceHistory.id) == 0)
        )

        result = await db.execute(query)
        stocks_without_prices = result.scalars().all()

        logger.info(f"找到 {len(stocks_without_prices)} 個沒有價格數據的股票")

        if not stocks_without_prices:
            return {
                "success": True,
                "message": "所有活躍股票都已有價格數據",
                "total_stocks": 0,
                "successful": 0,
                "failed": 0,
                "results": [],
            }

        # 逐一回填數據
        results = []
        successful = 0
        failed = 0

        for stock in stocks_without_prices:
            try:
                logger.info(f"正在回填股票: {stock.symbol} ({stock.name})")

                collect_result = await data_collection_service.collect_stock_data(
                    db=db,
                    stock_id=stock.id,
                    start_date=None,  # 使用預設日期範圍
                    end_date=None,
                )

                if collect_result.status == collect_result.status.SUCCESS:
                    successful += 1
                    results.append(
                        {
                            "stock_id": stock.id,
                            "symbol": stock.symbol,
                            "name": stock.name,
                            "success": True,
                            "data_points": collect_result.records_collected,
                            "message": "成功回填數據",
                        }
                    )
                else:
                    failed += 1
                    results.append(
                        {
                            "stock_id": stock.id,
                            "symbol": stock.symbol,
                            "name": stock.name,
                            "success": False,
                            "data_points": 0,
                            "message": f"回填失敗: {collect_result.status.value}",
                            "errors": collect_result.errors,
                        }
                    )

            except Exception as e:
                failed += 1
                logger.error(f"回填股票 {stock.symbol} 時發生錯誤: {str(e)}")
                results.append(
                    {
                        "stock_id": stock.id,
                        "symbol": stock.symbol,
                        "name": stock.name,
                        "success": False,
                        "data_points": 0,
                        "message": f"錯誤: {str(e)}",
                    }
                )

        logger.info(f"批量回填完成: 成功 {successful}, 失敗 {failed}")

        return {
            "success": True,
            "message": f"批量回填完成：成功 {successful} 個，失敗 {failed} 個",
            "total_stocks": len(stocks_without_prices),
            "successful": successful,
            "failed": failed,
            "results": results,
        }

    except Exception as e:
        logger.error(f"批量回填失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批量回填失敗: {str(e)}")
