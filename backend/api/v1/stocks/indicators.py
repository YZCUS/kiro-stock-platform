"""
技術指標相關API端點
負責: /indicators, /indicators/calculate, /summary, /specific, /batch
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from pydantic import Field

from core.database import get_db_session
from services.analysis.technical_analysis import TechnicalAnalysisService, IndicatorType
from models.repositories.crud_stock import stock_crud
from models.repositories.crud_technical_indicator import technical_indicator_crud
from api.schemas.stocks import (
    IndicatorCalculateRequest,
    IndicatorBatchCalculateRequest,
    IndicatorSummaryResponse
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
        if '_' in indicator_upper:
            parts = indicator_upper.split('_')
            if len(parts) >= 2:
                try:
                    return int(parts[-1])  # 取最後一個數字部分
                except ValueError:
                    pass

        # 預設週期對應表
        default_periods = {
            'RSI': 14,
            'MACD': 26,  # MACD 使用較長週期
            'MACD_SIGNAL': 9,
            'MACD_HISTOGRAM': 9,
            'BB_UPPER': 20,
            'BB_MIDDLE': 20,
            'BB_LOWER': 20,
            'KD_K': 14,
            'KD_D': 14,
            'ATR': 14,
            'CCI': 20,
            'WILLIAMS_R': 14,
            'VOLUME_SMA': 20
        }

        return default_periods.get(indicator_upper, 14)  # 預設使用 14

    except Exception:
        return 14  # 發生任何錯誤時使用預設值


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

        # 計算分頁
        offset = (page - 1) * page_size

        # 取得指標數據
        if indicator_type:
            indicators = await technical_indicator_crud.get_by_stock_and_type(
                db,
                stock_id=stock_id,
                indicator_type=indicator_type,
                start_date=start_date,
                end_date=end_date,
                offset=offset,
                limit=page_size
            )
            total = await technical_indicator_crud.count_by_stock_and_type(
                db, stock_id=stock_id, indicator_type=indicator_type,
                start_date=start_date, end_date=end_date
            )
        else:
            indicators = await technical_indicator_crud.get_by_stock(
                db,
                stock_id=stock_id,
                start_date=start_date,
                end_date=end_date,
                offset=offset,
                limit=page_size
            )
            total = await technical_indicator_crud.count_by_stock(
                db, stock_id=stock_id, start_date=start_date, end_date=end_date
            )

        # 計算總頁數
        total_pages = (total + page_size - 1) // page_size

        return {
            "items": [
                {
                    "id": indicator.id,
                    "indicator_type": indicator.indicator_type,
                    "value": indicator.value,
                    "period": indicator.period,
                    "date": indicator.date.isoformat(),
                    "parameters": indicator.parameters
                }
                for indicator in indicators
            ],
            "total": total,
            "page": page,
            "per_page": page_size,
            "total_pages": total_pages,
            "stock_id": stock_id,
            "symbol": stock.symbol
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
    db: AsyncSession = Depends(get_db_session)
):
    """
    計算股票技術指標（GET版本，用於快速查詢）
    """
    try:
        # 檢查股票是否存在
        stock = await stock_crud.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")

        # 解析指標類型
        if indicators:
            indicator_list = [t.strip().upper() for t in indicators.split(',')]
        else:
            indicator_list = ["RSI", "SMA_20", "MACD"]  # 預設指標

        # 使用技術分析服務
        analysis_service = TechnicalAnalysisService()

        # 決定使用的週期和天數
        if period:
            days = max(period * 3, 30)  # 至少需要週期*3的數據
        else:
            days = 100  # 預設天數

        # 計算指標
        analysis_result = await analysis_service.calculate_stock_indicators(
            db_session=db,
            stock_id=stock_id,
            indicators=indicator_list,
            days=days,
            save_to_db=True
        )

        return {
            "success": True,
            "data": analysis_result,
            "indicators_calculated": len(indicator_list),
            "timeframe": timeframe,
            "message": "指標計算完成"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"計算技術指標失敗: {str(e)}")


@router.post("/{stock_id}/indicators/calculate", response_model=Dict[str, Any])
async def calculate_stock_indicators_post(
    stock_id: int,
    request: IndicatorCalculateRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    計算股票技術指標（POST版本，支援詳細參數）
    """
    try:
        # 檢查股票是否存在
        stock = await stock_crud.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")

        # 解析要計算的指標
        requested_indicators = [request.indicator_type.upper()]

        # 決定週期和所需天數
        period = request.period or _extract_period_from_indicator(request.indicator_type)
        buffer_size = max(period * 2, 50)  # 緩衝區大小

        # 使用技術分析服務
        analysis_service = TechnicalAnalysisService()

        analysis_result = await analysis_service.calculate_stock_indicators(
            db_session=db,
            stock_id=stock_id,
            indicators=requested_indicators,
            days=period + buffer_size,
            save_to_db=True
        )

        return {
            "success": True,
            "data": analysis_result,
            "indicator_type": request.indicator_type,
            "period": period,
            "timeframe": request.timeframe,
            "message": "指標計算完成"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"計算技術指標失敗: {str(e)}")


@router.post("/{stock_id}/indicators/calculate/batch", response_model=Dict[str, Any])
async def calculate_stock_indicators_batch(
    stock_id: int,
    request: IndicatorBatchCalculateRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    批次計算股票技術指標
    """
    try:
        # 檢查股票是否存在
        stock = await stock_crud.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")

        # 解析要計算的指標
        requested_indicators = [item.type.upper() for item in request.indicators]

        # 計算最大所需天數
        max_period = 0
        for item in request.indicators:
            period = item.period or _extract_period_from_indicator(item.type)
            max_period = max(max_period, period)

        buffer_size = max(max_period * 2, 100)

        # 使用技術分析服務
        analysis_service = TechnicalAnalysisService()

        analysis_result = await analysis_service.calculate_stock_indicators(
            db_session=db,
            stock_id=stock_id,
            indicators=requested_indicators,
            days=max_period + buffer_size,
            save_to_db=True
        )

        return {
            "success": True,
            "data": analysis_result,
            "indicators_calculated": len(requested_indicators),
            "timeframe": request.timeframe,
            "message": f"批次計算完成，共處理 {len(requested_indicators)} 個指標"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批次計算技術指標失敗: {str(e)}")


@router.get("/{stock_id}/indicators/{indicator_type}", response_model=Dict[str, Any])
async def get_specific_indicator(
    stock_id: int,
    indicator_type: str,
    period: Optional[int] = Query(None, description="週期"),
    limit: int = Query(100, ge=1, le=1000, description="返回數量"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    取得特定類型的技術指標
    """
    try:
        # 檢查股票是否存在
        stock = await stock_crud.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")

        # 檢查指標類型是否有效
        try:
            indicator_enum = IndicatorType(indicator_type.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"無效的指標類型: {indicator_type}")

        # 使用技術分析服務獲取指標數據
        analysis_service = TechnicalAnalysisService()

        # 決定週期和所需天數
        used_period = period or _extract_period_from_indicator(indicator_type)
        required_days = max(used_period * 4, 50)

        indicator_data = await analysis_service.get_stock_indicators(
            db_session=db,
            stock_id=stock_id,
            indicator_types=[indicator_type.upper()],
            days=required_days
        )

        if indicator_data and indicator_type.upper() in indicator_data:
            raw_data = indicator_data[indicator_type.upper()]

            if raw_data and len(raw_data) > 0:
                # 格式化為標準響應
                formatted_response = {
                    "symbol": stock.symbol,
                    "indicators": {indicator_type.lower(): raw_data},
                    "period": used_period,
                    "timestamp": datetime.now().isoformat(),
                    "success": True,
                    "data_points": len(raw_data) if isinstance(raw_data, list) else 1
                }

                return {
                    "success": True,
                    "data": formatted_response,
                    "indicator_type": indicator_type,
                    "period": used_period
                }

        # 如果沒有數據，返回空響應
        return {
            "success": False,
            "data": {
                "symbol": stock.symbol,
                "indicators": {},
                "period": used_period,
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "data_points": 0
            },
            "indicator_type": indicator_type,
            "period": used_period,
            "message": "沒有找到指標數據"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得特定指標失敗: {str(e)}")


@router.get("/{stock_id}/indicators/summary", response_model=IndicatorSummaryResponse)
async def get_stock_indicators_summary(
    stock_id: int,
    indicator_types: Optional[str] = Query(None, description="指標類型（逗號分隔）"),
    timeframe: str = Query("1d", description="時間框架"),
    period: Optional[int] = Query(None, description="週期參數（覆蓋指標預設週期）"),
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
                # 決定使用的週期
                indicator_period = period if period is not None else _extract_period_from_indicator(indicator_type.value)

                # 計算需要的數據天數（週期 × 4 以確保有足夠數據進行計算）
                required_days = max(indicator_period * 4, 50)

                indicator_data = await analysis_service.get_stock_indicators(
                    db_session=db,
                    stock_id=stock_id,
                    indicator_types=[indicator_type.value],
                    days=required_days
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
                            "period": indicator_period,  # 使用實際計算的週期
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
                error_period = period if period is not None else _extract_period_from_indicator(indicator_type.value)
                indicators_summary[indicator_type.value] = {
                    "symbol": stock.symbol,
                    "indicators": {},
                    "period": error_period,
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