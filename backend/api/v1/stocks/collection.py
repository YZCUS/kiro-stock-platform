"""
數據收集相關API端點
負責: /refresh, /collect, /collect-all, /collect-batch
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
from datetime import date, timedelta

from app.dependencies import (
    get_database_session,
    get_data_collection_service_clean,
    get_stock_service
)
from domain.services.data_collection_service import DataCollectionService, DataCollectionStatus
from domain.services.stock_service import StockService
from api.schemas.stocks import (
    DataCollectionRequest,
    DataCollectionResponse,
    BatchCollectionRequest
)

router = APIRouter()


@router.post("/{stock_id}/refresh", response_model=DataCollectionResponse)
async def refresh_stock_data(
    stock_id: int,
    days: int = 30,
    db: AsyncSession = Depends(get_database_session),
    data_collection_service: DataCollectionService = Depends(get_data_collection_service_clean),
    stock_service: StockService = Depends(get_stock_service)
):
    """
    手動更新股票數據
    """
    try:
        # 檢查股票是否存在
        stock = await stock_service.get_stock_by_id(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")

        # 計算日期範圍
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # 執行數據收集（domain service）
        collect_result = await data_collection_service.collect_stock_data(
            db,
            stock_id=stock_id,
            start_date=start_date,
            end_date=end_date
        )

        return DataCollectionResponse(
            success=collect_result.status == DataCollectionStatus.SUCCESS,
            message="數據刷新完成" if collect_result.status == DataCollectionStatus.SUCCESS else "數據刷新失敗",
            data_points=collect_result.records_collected,
            errors=collect_result.errors
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"數據刷新失敗: {str(e)}")


@router.post("/collect", response_model=DataCollectionResponse)
async def collect_stock_data(
    request: DataCollectionRequest,
    db: AsyncSession = Depends(get_database_session),
    data_collection_service: DataCollectionService = Depends(get_data_collection_service_clean),
    stock_service: StockService = Depends(get_stock_service)
):
    """
    收集指定股票的數據
    """
    try:
        stock = await stock_service.get_stock_by_symbol(db, request.symbol)

        result = await data_collection_service.collect_stock_data(
            db,
            stock_id=stock.id,
            start_date=request.start_date,
            end_date=request.end_date
        )

        return DataCollectionResponse(
            success=result.status == DataCollectionStatus.SUCCESS,
            message="數據收集完成" if result.status == DataCollectionStatus.SUCCESS else "數據收集失敗",
            data_points=result.records_collected,
            errors=result.errors
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"數據收集失敗: {str(e)}")


@router.post("/collect-all", response_model=Dict[str, Any])
async def collect_all_stocks_data(
    days: int = 7,
    db: AsyncSession = Depends(get_database_session),
    data_collection_service: DataCollectionService = Depends(get_data_collection_service_clean)
):
    """
    收集所有活躍股票的數據
    """
    try:
        summary = await data_collection_service.collect_active_stocks_data(
            db,
            days=days
        )

        return {
            "success": summary.successful_stocks == summary.total_stocks,
            "message": f"批次收集完成，處理了 {summary.total_stocks} 隻股票",
            "processed": summary.total_stocks,
            "successful": summary.successful_stocks,
            "failed": summary.failed_stocks,
            "errors": [error for result in summary.results for error in result.errors][:50]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批次收集失敗: {str(e)}")


@router.post("/collect-batch", response_model=Dict[str, Any])
async def collect_batch_stocks_data(
    request: BatchCollectionRequest,
    db: AsyncSession = Depends(get_database_session),
    data_collection_service: DataCollectionService = Depends(get_data_collection_service_clean)
):
    """
    批次收集指定股票的數據
    """
    try:
        if request.use_stock_list and request.stocks:
            stock_entries = request.stocks
        else:
            active_stocks = await data_collection_service.stock_repo.get_active_stocks(db)
            stock_entries = [{"symbol": stock.symbol, "market": stock.market} for stock in active_stocks]

        summary = await data_collection_service.collect_batch_stocks_data(
            db,
            stock_list=stock_entries,
            start_date=request.start_date,
            end_date=request.end_date
        )

        return {
            "success": summary["success"],
            "message": summary["message"],
            "processed": summary["total_stocks"],
            "successful": summary["success_count"],
            "failed": summary["error_count"],
            "errors": summary["collection_errors"][:50]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批次收集失敗: {str(e)}")


@router.post("/{stock_id}/backfill-full", response_model=Dict[str, Any])
async def backfill_full_history(
    stock_id: int,
    period: str = "1y",
    db: AsyncSession = Depends(get_database_session),
    data_collection_service: DataCollectionService = Depends(get_data_collection_service_clean),
    stock_service: StockService = Depends(get_stock_service)
):
    """
    補齊單一股票的完整歷史資料

    支援的 period 參數:
    - 1d, 5d, 1mo, 3mo, 6mo - 短期資料
    - 1y, 2y, 5y, 10y - 中長期資料
    - max - 所有可用的歷史資料（從上市日開始）
    - ytd - 年初至今

    建議:
    - 新股票首次加入: period="1y"
    - 重點追蹤股票: period="5y" 或 "max"
    - 日常更新: 使用 /refresh 端點即可
    """
    try:
        # 檢查股票是否存在
        stock = await stock_service.get_stock_by_id(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")

        # 驗證 period 參數
        valid_periods = ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max']
        if period not in valid_periods:
            raise HTTPException(
                status_code=400,
                detail=f"無效的 period 參數。支援的值: {', '.join(valid_periods)}"
            )

        # 執行歷史資料收集
        records_count = await data_collection_service.collect_stock_prices(
            db,
            stock_id=stock_id,
            period=period
        )

        return {
            "success": True,
            "message": f"成功補齊 {stock.symbol} 的歷史資料",
            "stock_id": stock_id,
            "symbol": stock.symbol,
            "period": period,
            "records_collected": records_count
        }

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.error(f"Backfill full history failed for stock {stock_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"歷史資料補齊失敗: {str(e)}")


@router.post("/backfill-missing", response_model=Dict[str, Any])
async def backfill_missing_data(
    days: int = 365,
    market: str = None,
    db: AsyncSession = Depends(get_database_session),
    data_collection_service: DataCollectionService = Depends(get_data_collection_service_clean)
):
    """
    智慧補齊所有股票的缺漏資料

    邏輯:
    1. 查詢所有活躍股票
    2. 檢查每支股票的最新資料日期
    3. 如果資料落後超過 2 天，自動補齊
    4. 批次處理並回報結果

    參數:
    - days: 最多回溯天數（預設 365 天）
    - market: 指定市場 (TW/US)，不指定則處理所有市場
    """
    try:
        from datetime import date

        # 取得活躍股票清單
        active_stocks = await data_collection_service.stock_repo.get_active_stocks(db, market=market)

        if not active_stocks:
            return {
                "success": True,
                "message": "沒有需要處理的股票",
                "processed": 0,
                "updated": 0,
                "skipped": 0,
                "errors": []
            }

        results = []
        updated_count = 0
        skipped_count = 0
        error_count = 0
        errors = []

        for stock in active_stocks:
            try:
                # 檢查最新資料日期
                latest_price = await data_collection_service.price_repo.get_latest_price(db, stock.id)

                if latest_price:
                    days_behind = (date.today() - latest_price.date).days

                    # 如果資料是最新的，跳過
                    if days_behind <= 2:
                        skipped_count += 1
                        continue

                    # 計算需要補齊的天數
                    backfill_days = min(days_behind + 7, days)  # 多抓 7 天以確保完整
                else:
                    # 沒有任何資料，抓取指定天數
                    backfill_days = days

                # 執行補齊
                records = await data_collection_service.collect_stock_prices(
                    db,
                    stock_id=stock.id,
                    days=backfill_days
                )

                if records > 0:
                    updated_count += 1
                    results.append(f"{stock.symbol}: 補齊 {records} 筆")
                else:
                    skipped_count += 1

            except Exception as e:
                error_count += 1
                error_msg = f"{stock.symbol}: {str(e)}"
                errors.append(error_msg)
                import logging
                logging.error(f"Failed to backfill {stock.symbol}: {str(e)}")

        return {
            "success": error_count == 0,
            "message": f"補齊完成，處理了 {len(active_stocks)} 支股票",
            "processed": len(active_stocks),
            "updated": updated_count,
            "skipped": skipped_count,
            "failed": error_count,
            "results": results[:20],  # 只顯示前 20 個結果
            "errors": errors[:10]  # 只顯示前 10 個錯誤
        }

    except Exception as e:
        import logging
        logging.error(f"Backfill missing data failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批次補齊失敗: {str(e)}")