"""
分析相關API端點
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.dependencies import (
    get_database_session,
    get_stock_service,
    get_technical_analysis_service_clean,
    get_trading_signal_service_clean,
)
from domain.services.technical_analysis_service import IndicatorType
from domain.services.trading_signal_service import SignalType, TradingSignalService
from domain.services.technical_analysis_service import TechnicalAnalysisService
from domain.services.stock_service import StockService

router = APIRouter(prefix="/analysis", tags=["analysis"])


class IndicatorTypeEnum(str, Enum):
    RSI = "RSI"
    SMA = "SMA_20"
    EMA = "EMA_12"
    MACD = "MACD"
    BOLLINGER = "BB_UPPER"
    STOCHASTIC = "KD_K"


class SignalTypeEnum(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class TechnicalAnalysisRequest(BaseModel):
    stock_id: int
    indicator: IndicatorTypeEnum
    days: int = 30


class TechnicalAnalysisResponse(BaseModel):
    stock_id: int
    indicator: str
    values: List[Dict[str, Any]]
    summary: Dict[str, Any]
    timestamp: datetime


class SignalDetectionRequest(BaseModel):
    stock_id: int
    signal_types: List[SignalTypeEnum] = [SignalTypeEnum.BUY, SignalTypeEnum.SELL]


class SignalResponse(BaseModel):
    stock_id: int
    symbol: str
    signal_type: str
    strength: str
    price: Optional[float]
    timestamp: datetime
    indicators: Dict[str, Any]


@router.post("/technical-analysis", response_model=TechnicalAnalysisResponse)
async def calculate_technical_indicator(
    request: TechnicalAnalysisRequest,
    db: AsyncSession = Depends(get_database_session),
    stock_service: StockService = Depends(get_stock_service),
    technical_service: TechnicalAnalysisService = Depends(get_technical_analysis_service_clean),
):
    try:
        await stock_service.get_stock_by_id(db, request.stock_id)

        indicator = IndicatorType(request.indicator.value)
        result = await technical_service.calculate_indicator(
            db,
            stock_id=request.stock_id,
            indicator=indicator,
            days=request.days,
        )

        values = [
            {"date": date, "value": value}
            for date, value in zip(result["dates"], result["values"])
        ]

        return TechnicalAnalysisResponse(
            stock_id=request.stock_id,
            indicator=request.indicator.value,
            values=values,
            summary=result["summary"],
            timestamp=datetime.now(),
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"技術分析計算失敗: {str(e)}")


@router.get("/technical-analysis/{stock_id}", response_model=List[TechnicalAnalysisResponse])
async def get_all_technical_indicators(
    stock_id: int,
    days: int = Query(30, description="計算天數"),
    db: AsyncSession = Depends(get_database_session),
    stock_service: StockService = Depends(get_stock_service),
    technical_service: TechnicalAnalysisService = Depends(get_technical_analysis_service_clean),
):
    try:
        await stock_service.get_stock_by_id(db, stock_id)

        indicators = [
            IndicatorType.RSI,
            IndicatorType.SMA_20,
            IndicatorType.EMA_12,
            IndicatorType.MACD,
        ]

        responses: List[TechnicalAnalysisResponse] = []
        for indicator in indicators:
            try:
                result = await technical_service.calculate_indicator(
                    db,
                    stock_id=stock_id,
                    indicator=indicator,
                    days=days,
                )
                values = [
                    {"date": date, "value": value}
                    for date, value in zip(result["dates"], result["values"])
                ]
                responses.append(
                    TechnicalAnalysisResponse(
                        stock_id=stock_id,
                        indicator=indicator.value,
                        values=values,
                        summary=result["summary"],
                        timestamp=datetime.now(),
                    )
                )
            except Exception:
                continue

        return responses

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得技術指標失敗: {str(e)}")


@router.post("/signals", response_model=List[SignalResponse])
async def detect_trading_signals(
    request: SignalDetectionRequest,
    db: AsyncSession = Depends(get_database_session),
    stock_service: StockService = Depends(get_stock_service),
    signal_service: TradingSignalService = Depends(get_trading_signal_service_clean),
):
    try:
        stock = await stock_service.get_stock_by_id(db, request.stock_id)

        signals = []
        for signal_type_enum in request.signal_types:
            signal_type = SignalType(signal_type_enum.value)
            signal_analysis = await signal_service.generate_trading_signals(
                db,
                stock_id=request.stock_id,
            )
            if signal_analysis.primary_signal:
                signals.append(signal_analysis.primary_signal)
            signals.extend(signal_analysis.supporting_signals)

        responses: List[SignalResponse] = []
        for signal in signals:
            responses.append(
                SignalResponse(
                    stock_id=request.stock_id,
                    symbol=stock.symbol,
                    signal_type=signal.signal_type.value,
                    strength=signal.signal_strength.value,
                    price=float(signal.metadata.get("price", 0)) if signal.metadata else None,
                    timestamp=signal.signal_date,
                    indicators=signal.metadata or {},
                )
            )

        return responses

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"信號偵測失敗: {str(e)}")


@router.get("/signals/{stock_id}", response_model=List[SignalResponse])
async def get_stock_signals(
    stock_id: int,
    signal_type: Optional[SignalTypeEnum] = Query(None, description="信號類型"),
    limit: int = Query(10, description="返回數量限制"),
    db: AsyncSession = Depends(get_database_session),
    stock_service: StockService = Depends(get_stock_service),
    signal_service: TradingSignalService = Depends(get_trading_signal_service_clean),
):
    try:
        stock = await stock_service.get_stock_by_id(db, stock_id)

        recent_signals = await signal_service.get_recent_signals(
            db,
            stock_id=stock_id,
            limit=limit,
            signal_type=signal_type.value if signal_type else None,
        )

        responses = [
            SignalResponse(
                stock_id=stock_id,
                symbol=stock.symbol,
                signal_type=signal.get("signal_type", ""),
                strength=signal.get("signal_strength", ""),
                price=signal.get("price"),
                timestamp=signal.get("created_at", datetime.now()),
                indicators=signal.get("metadata", {}),
            )
            for signal in recent_signals
        ]

        return responses

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得交易信號失敗: {str(e)}")


@router.get("/batch-analysis", response_model=Dict[str, Any])
async def batch_technical_analysis(
    market: Optional[str] = Query(None, description="市場代碼"),
    indicator: IndicatorTypeEnum = Query(IndicatorTypeEnum.RSI, description="技術指標"),
    days: int = Query(30, description="計算天數"),
    limit: int = Query(20, description="股票數量限制"),
    db: AsyncSession = Depends(get_database_session),
    stock_service: StockService = Depends(get_stock_service),
    technical_service: TechnicalAnalysisService = Depends(get_technical_analysis_service_clean),
):
    try:
        stock_list = await stock_service.get_stock_list(
            db,
            market=market,
            is_active=True,
            page=1,
            per_page=limit,
        )

        results = []
        indicator_type = IndicatorType(indicator.value)

        for item in stock_list["items"]:
            try:
                result = await technical_service.calculate_indicator(
                    db,
                    stock_id=item["id"],
                    indicator=indicator_type,
                    days=days,
                )
                results.append(
                    {
                        "stock_id": item["id"],
                        "symbol": item["symbol"],
                        "market": item["market"],
                        "indicator": indicator.value,
                        "current_value": result["summary"].get("current_value"),
                        "trend": result["summary"].get("trend"),
                    }
                )
            except Exception:
                continue

        return {
            "indicator": indicator.value,
            "total_analyzed": len(results),
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批次技術分析失敗: {str(e)}")


@router.get("/market-overview", response_model=Dict[str, Any])
async def get_market_overview(
    market: Optional[str] = Query(None, description="市場代碼"),
    db: AsyncSession = Depends(get_database_session),
    stock_service: StockService = Depends(get_stock_service),
    signal_service: TradingSignalService = Depends(get_trading_signal_service_clean),
):
    try:
        stocks = await stock_service.get_stock_list(
            db,
            market=market,
            is_active=True,
            page=1,
            per_page=50,
        )

        signal_stats = {"BUY": 0, "SELL": 0, "HOLD": 0}
        analyzed_stocks = 0

        for item in stocks["items"][:20]:
            try:
                analysis = await signal_service.generate_trading_signals(db, item["id"]) 
                if analysis.primary_signal:
                    signal_type = analysis.primary_signal.signal_type.value.upper()
                    signal_stats[signal_type] = signal_stats.get(signal_type, 0) + 1
                    analyzed_stocks += 1
            except Exception:
                continue

        total_signal = signal_stats["BUY"] + signal_stats["SELL"]
        if total_signal == 0:
            sentiment = "neutral"
        else:
            buy_ratio = signal_stats["BUY"] / total_signal
            sentiment = "bullish" if buy_ratio > 0.6 else "bearish" if buy_ratio < 0.4 else "neutral"

        return {
            "market": market or "ALL",
            "total_stocks": stocks["total"],
            "analyzed_stocks": analyzed_stocks,
            "signal_distribution": signal_stats,
            "market_sentiment": sentiment,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得市場概覽失敗: {str(e)}")