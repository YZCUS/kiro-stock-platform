"""
技術指標相關API端點
負責: /indicators, /indicators/calculate, /summary, /specific, /batch
"""

from typing import List, Optional, Dict, Any
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    get_database_session,
    get_stock_service,
    get_technical_analysis_service_clean,
)
from domain.models.technical_indicator import TechnicalIndicator
from api.schemas.stocks import (
    IndicatorCalculateRequest,
    IndicatorBatchCalculateRequest,
    IndicatorSummaryResponse,
)
from domain.services.stock_service import StockService
from domain.services.technical_analysis_service import (
    TechnicalAnalysisService,
    IndicatorType,
)

router = APIRouter()


def _extract_period_from_indicator(indicator_type: str) -> int:
    """
    從指標類型名稱中提取週期參數

    支援的格式：
    - SMA_5, SMA_20, SMA_60 -> 5, 20, 60
    - EMA_12, EMA_26 -> 12, 26
    - RSI, MACD, KD_K, KD_D -> 14（預設）
    """
    try:
        indicator_upper = indicator_type.upper()

        # 從指標名稱中提取數字（如 SMA_20 -> 20）
        if "_" in indicator_upper:
            parts = indicator_upper.split("_")
            if len(parts) >= 2:
                try:
                    return int(parts[-1])  # 取最後一個數字部分
                except ValueError:
                    pass

        # 預設週期對應表
        default_periods = {
            "RSI": 14,
            "MACD": 26,  # MACD 使用較長週期
            "MACD_SIGNAL": 9,
            "MACD_HISTOGRAM": 9,
            "BB_UPPER": 20,
            "BB_MIDDLE": 20,
            "BB_LOWER": 20,
            "KD_K": 14,
            "KD_D": 14,
            "ATR": 14,
            "CCI": 20,
            "WILLIAMS_R": 14,
            "VOLUME_SMA": 20,
        }

        return default_periods.get(indicator_upper, 14)  # 預設使用 14

    except Exception:
        return 14  # 發生任何錯誤時使用預設值


def _resolve_indicator_type(indicator_type: str, period: Optional[int] = None) -> IndicatorType:
    """Normalize frontend shorthand names to backend indicator enum values."""
    normalized = indicator_type.upper().replace("-", "_")

    shorthand = {
        "SMA": f"SMA_{period or 20}",
        "EMA": f"EMA_{period or 12}",
        "BOLLINGER": "BB_MIDDLE",
        "BOLLINGER_BANDS": "BB_MIDDLE",
        "BB": "BB_MIDDLE",
        "KD": "KD_K",
        "STOCH": "KD_K",
        "WILLIAMS": "WILLIAMS_R",
    }
    normalized = shorthand.get(normalized, normalized)

    try:
        return IndicatorType(normalized)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"無效的指標類型: {indicator_type}")


@router.get("/{stock_id}/indicators", response_model=Dict[str, Any])
async def get_stock_indicators(
    stock_id: int,
    indicator_type: Optional[str] = Query(None, description="技術指標類型"),
    start_date: Optional[date] = Query(None, description="開始日期"),
    end_date: Optional[date] = Query(None, description="結束日期"),
    page: int = Query(1, ge=1, description="頁碼"),
    page_size: int = Query(100, ge=1, le=1000, description="每頁數量"),
    db: AsyncSession = Depends(get_database_session),
    stock_service: StockService = Depends(get_stock_service),
    analysis_service: TechnicalAnalysisService = Depends(
        get_technical_analysis_service_clean
    ),
):
    """
    取得股票技術指標
    """
    try:
        stock = await stock_service.get_stock_by_id(db, stock_id)

        normalized_indicator_type = (
            _resolve_indicator_type(indicator_type).value if indicator_type else None
        )

        indicators_data = await analysis_service.get_indicator_series(
            db=db,
            stock_id=stock_id,
            indicator_type=normalized_indicator_type,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size,
        )

        return {
            "items": indicators_data["items"],
            "total": indicators_data["total"],
            "page": indicators_data["page"],
            "per_page": indicators_data["per_page"],
            "total_pages": indicators_data["total_pages"],
            "stock_id": stock_id,
            "symbol": stock.symbol,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得技術指標失敗: {str(e)}")


@router.get("/{stock_id}/indicators/calculate", response_model=Dict[str, Any])
async def calculate_stock_indicators_get(
    stock_id: int,
    indicators: Optional[str] = Query(None, description="指標類型（逗號分隔）"),
    period: Optional[int] = Query(None, description="週期"),
    timeframe: str = Query("1d", description="時間框架"),
    db: AsyncSession = Depends(get_database_session),
    stock_service: StockService = Depends(get_stock_service),
    analysis_service: TechnicalAnalysisService = Depends(
        get_technical_analysis_service_clean
    ),
):
    """
    計算股票技術指標（GET版本，用於快速查詢）
    """
    try:
        stock = await stock_service.get_stock_by_id(db, stock_id)

        if indicators:
            indicator_list = [
                _resolve_indicator_type(t.strip()).value
                for t in indicators.split(",")
            ]
        else:
            indicator_list = ["RSI", "SMA_20", "MACD"]  # 預設指標

        if period:
            days = max(period * 3, 30)  # 至少需要週期*3的數據
        else:
            days = 100  # 預設天數

        analysis_result = await analysis_service.calculate_stock_indicators(
            db=db,
            stock_id=stock_id,
            indicators=[IndicatorType(ind) for ind in indicator_list],
            days=days,
            save_to_db=True,
        )

        return {
            "success": True,
            "data": analysis_result,
            "indicators_calculated": len(indicator_list),
            "timeframe": timeframe,
            "message": "指標計算完成",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"計算技術指標失敗: {str(e)}")


@router.post("/{stock_id}/indicators/calculate", response_model=Dict[str, Any])
async def calculate_stock_indicators_post(
    stock_id: int,
    request: IndicatorCalculateRequest,
    db: AsyncSession = Depends(get_database_session),
    stock_service: StockService = Depends(get_stock_service),
    analysis_service: TechnicalAnalysisService = Depends(
        get_technical_analysis_service_clean
    ),
):
    """
    計算股票技術指標（POST版本，支援詳細參數）
    """
    try:
        stock = await stock_service.get_stock_by_id(db, stock_id)

        # 決定週期和所需天數
        period = request.period or _extract_period_from_indicator(
            request.indicator_type
        )
        requested_indicators = [_resolve_indicator_type(request.indicator_type, period)]
        buffer_size = max(period * 2, 50)  # 緩衝區大小

        analysis_result = await analysis_service.calculate_stock_indicators(
            db=db,
            stock_id=stock_id,
            indicators=requested_indicators,
            days=period + buffer_size,
            save_to_db=True,
        )

        return {
            "success": True,
            "data": analysis_result,
            "indicator_type": request.indicator_type,
            "period": period,
            "timeframe": request.timeframe,
            "message": "指標計算完成",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"計算技術指標失敗: {str(e)}")


@router.post("/{stock_id}/indicators/calculate/batch", response_model=Dict[str, Any])
async def calculate_stock_indicators_batch(
    stock_id: int,
    request: IndicatorBatchCalculateRequest,
    db: AsyncSession = Depends(get_database_session),
    stock_service: StockService = Depends(get_stock_service),
    analysis_service: TechnicalAnalysisService = Depends(
        get_technical_analysis_service_clean
    ),
):
    """
    批次計算股票技術指標
    """
    try:
        stock = await stock_service.get_stock_by_id(db, stock_id)

        # 計算最大所需天數
        max_period = 0
        requested_indicators = []
        for item in request.indicators:
            period = item.period or _extract_period_from_indicator(item.type)
            max_period = max(max_period, period)
            requested_indicators.append(_resolve_indicator_type(item.type, period))

        buffer_size = max(max_period * 2, 100)

        analysis_result = await analysis_service.calculate_stock_indicators(
            db=db,
            stock_id=stock_id,
            indicators=requested_indicators,
            days=max_period + buffer_size,
            save_to_db=True,
        )

        return {
            "success": True,
            "data": analysis_result,
            "indicators_calculated": len(requested_indicators),
            "timeframe": request.timeframe,
            "message": f"批次計算完成，共處理 {len(requested_indicators)} 個指標",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批次計算技術指標失敗: {str(e)}")


@router.post("/{stock_id}/indicators/calculate/recalculate", response_model=Dict[str, Any])
async def recalculate_stock_indicators(
    stock_id: int,
    request: Dict[str, Any],
    db: AsyncSession = Depends(get_database_session),
    stock_service: StockService = Depends(get_stock_service),
    analysis_service: TechnicalAnalysisService = Depends(
        get_technical_analysis_service_clean
    ),
):
    """Compatibility endpoint for frontend-triggered recalculation."""
    try:
        await stock_service.get_stock_by_id(db, stock_id)
        indicator_types = request.get("indicator_types") or ["RSI", "SMA_20", "MACD"]
        requested_indicators = [
            _resolve_indicator_type(str(indicator)).value for indicator in indicator_types
        ]

        result = await analysis_service.calculate_stock_indicators(
            db=db,
            stock_id=stock_id,
            indicators=[IndicatorType(indicator) for indicator in requested_indicators],
            days=120,
            save_to_db=True,
        )

        return {
            "message": "指標重新計算完成",
            "task_id": f"sync-{stock_id}-{date.today().isoformat()}",
            "result": result,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重新計算技術指標失敗: {str(e)}")


@router.get("/{stock_id}/indicators/summary", response_model=IndicatorSummaryResponse)
async def get_stock_indicators_summary_ordered(
    stock_id: int,
    indicator_types: Optional[List[str]] = Query(
        None, description="指標類型（可重複或逗號分隔）"
    ),
    timeframe: str = Query("1d", description="時間框架"),
    period: Optional[int] = Query(None, description="週期參數（覆蓋指標預設週期）"),
    start_date: Optional[date] = Query(None, description="開始日期"),
    end_date: Optional[date] = Query(None, description="結束日期"),
    db: AsyncSession = Depends(get_database_session),
    stock_service: StockService = Depends(get_stock_service),
    analysis_service: TechnicalAnalysisService = Depends(
        get_technical_analysis_service_clean
    ),
):
    """取得股票技術指標摘要。"""
    try:
        _ = start_date
        _ = end_date

        stock = await stock_service.get_stock_by_id(db, stock_id)
        normalized_types = None
        if indicator_types:
            raw_types = []
            for item in indicator_types:
                raw_types.extend(part.strip() for part in item.split(",") if part.strip())
            normalized_types = ",".join(
                _resolve_indicator_type(item, period).value for item in raw_types
            )

        response = await analysis_service.get_indicators_summary(
            db=db, stock_id=stock_id, indicator_types=normalized_types, period=period
        )

        response["symbol"] = stock.symbol
        response["stock_id"] = stock_id
        response["timeframe"] = timeframe

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取指標摘要失敗: {str(e)}")


@router.delete("/{stock_id}/indicators/{indicator_type}", response_model=Dict[str, Any])
async def delete_indicator_data(
    stock_id: int,
    indicator_type: str,
    start_date: Optional[date] = Query(None, description="開始日期"),
    end_date: Optional[date] = Query(None, description="結束日期"),
    db: AsyncSession = Depends(get_database_session),
    stock_service: StockService = Depends(get_stock_service),
):
    """Delete stored indicator rows for a stock and indicator type."""
    try:
        await stock_service.get_stock_by_id(db, stock_id)
        resolved_type = _resolve_indicator_type(indicator_type).value

        conditions = [
            TechnicalIndicator.stock_id == stock_id,
            TechnicalIndicator.indicator_type == resolved_type,
        ]
        if start_date:
            conditions.append(TechnicalIndicator.date >= start_date)
        if end_date:
            conditions.append(TechnicalIndicator.date <= end_date)

        result = await db.execute(delete(TechnicalIndicator).where(and_(*conditions)))
        await db.commit()

        return {
            "message": f"已刪除 {result.rowcount or 0} 筆 {resolved_type} 指標資料",
            "deleted_count": result.rowcount or 0,
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"刪除指標資料失敗: {str(e)}")


@router.get("/{stock_id}/indicators/{indicator_type}", response_model=Dict[str, Any])
async def get_specific_indicator(
    stock_id: int,
    indicator_type: str,
    period: Optional[int] = Query(None, description="週期"),
    limit: int = Query(100, ge=1, le=1000, description="返回數量"),
    db: AsyncSession = Depends(get_database_session),
    stock_service: StockService = Depends(get_stock_service),
    analysis_service: TechnicalAnalysisService = Depends(
        get_technical_analysis_service_clean
    ),
):
    """
    取得特定類型的技術指標
    """
    try:
        # 檢查股票是否存在
        stock = await stock_service.get_stock_by_id(db, stock_id)

        # 檢查指標類型是否有效
        try:
            indicator_enum = _resolve_indicator_type(indicator_type, period)
        except HTTPException:
            raise

        # 決定週期和所需天數
        used_period = period or _extract_period_from_indicator(indicator_type)
        required_days = max(used_period * 4, 50)

        # 使用注入的技術分析服務獲取指標數據
        indicator_data = await analysis_service.get_stock_indicators(
            db_session=db,
            stock_id=stock_id,
            indicator_types=[indicator_enum.value],
            days=required_days,
        )

        if indicator_data and indicator_enum.value in indicator_data:
            raw_data = indicator_data[indicator_enum.value]

            if raw_data and len(raw_data) > 0:
                # 格式化為標準響應
                formatted_response = {
                    "symbol": stock.symbol,
                    "indicators": {indicator_enum.value.lower(): raw_data},
                    "period": used_period,
                    "timestamp": date.today().isoformat(),
                    "success": True,
                    "data_points": len(raw_data) if isinstance(raw_data, list) else 1,
                }

                return {
                    "success": True,
                    "data": formatted_response,
                    "indicator_type": indicator_type,
                    "period": used_period,
                }

        # 如果沒有數據，返回空響應
        return {
            "success": False,
            "data": {
                "symbol": stock.symbol,
                "indicators": {},
                "period": used_period,
                "timestamp": date.today().isoformat(),
                "success": False,
                "data_points": 0,
            },
            "indicator_type": indicator_type,
            "period": used_period,
            "message": "沒有找到指標數據",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得特定指標失敗: {str(e)}")
