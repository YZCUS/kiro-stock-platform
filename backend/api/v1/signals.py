"""
交易信號相關API端點
"""

from datetime import date, datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.dependencies import (
    get_database_session,
    get_stock_service,
    get_trading_signal_service_clean,
)
from domain.services.stock_service import StockService
from domain.services.trading_signal_service import (
    TradingSignalService,
    SignalType,
    SignalStrength,
)

router = APIRouter(prefix="/signals", tags=["signals"])


class SignalTypeEnum(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    GOLDEN_CROSS = "golden_cross"
    DEATH_CROSS = "death_cross"


class SignalStrengthEnum(str, Enum):
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


class TradingSignalResponse(BaseModel):
    id: Optional[int] = None
    stock_id: int
    symbol: str
    signal_type: str
    strength: str
    price: Optional[float]
    confidence: Optional[float]
    date: date
    description: str
    indicators: Dict[str, Any]
    created_at: datetime


class SignalStatsResponse(BaseModel):
    total_signals: int
    buy_signals: int
    sell_signals: int
    hold_signals: int
    cross_signals: int
    avg_confidence: float
    top_stocks: List[Dict[str, Any]]


class SignalHistoryResponse(BaseModel):
    signals: List[TradingSignalResponse]
    pagination: Dict[str, int]
    stats: Dict[str, Any]


def _serialize_signal(signal: Dict[str, Any], symbol: str) -> TradingSignalResponse:
    return TradingSignalResponse(
        id=signal.get("id"),
        stock_id=signal.get("stock_id"),
        symbol=symbol,
        signal_type=signal.get("signal_type", ""),
        strength=signal.get("strength", SignalStrength.MODERATE.value),
        price=signal.get("price"),
        confidence=signal.get("confidence"),
        date=signal.get("date", date.today()),
        description=signal.get("description", ""),
        indicators=signal.get("indicators", {}),
        created_at=signal.get("created_at", datetime.now()),
    )


@router.get("/", response_model=SignalHistoryResponse)
async def get_all_signals(
    signal_type: Optional[SignalTypeEnum] = Query(None, description="信號類型"),
    market: Optional[str] = Query(None, description="市場代碼"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0, description="最小信心度"),
    start_date: Optional[date] = Query(None, description="開始日期"),
    end_date: Optional[date] = Query(None, description="結束日期"),
    page: int = Query(1, ge=1, description="頁碼"),
    page_size: int = Query(50, ge=1, le=200, description="每頁數量"),
    db: AsyncSession = Depends(get_database_session),
    stock_service: StockService = Depends(get_stock_service),
    signal_service: TradingSignalService = Depends(get_trading_signal_service_clean),
):
    try:
        offset = (page - 1) * page_size
        filters: Dict[str, Any] = {}

        if signal_type:
            filters["signal_type"] = signal_type.value
        if min_confidence > 0:
            filters["min_confidence"] = min_confidence
        if start_date:
            filters["start_date"] = start_date
        if end_date:
            filters["end_date"] = end_date

        signals = await signal_service.list_signals(
            db,
            filters=filters,
            market=market,
            offset=offset,
            limit=page_size,
        )
        total_count = await signal_service.count_signals(
            db,
            filters=filters,
            market=market,
        )
        stats = await signal_service.get_signal_stats(
            db, filters=filters, market=market
        )

        signal_responses = []
        for signal in signals:
            stock = await stock_service.get_stock_by_id(db, signal["stock_id"])
            signal_responses.append(_serialize_signal(signal, stock.symbol))

        total_pages = (total_count + page_size - 1) // page_size

        return SignalHistoryResponse(
            signals=signal_responses,
            pagination={
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            },
            stats=stats,
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得交易信號失敗: {str(e)}")


@router.get("/history", response_model=List[TradingSignalResponse])
async def get_signal_history(
    days: int = Query(30, ge=1, le=365, description="歷史天數"),
    signal_type: Optional[SignalTypeEnum] = Query(None, description="信號類型"),
    market: Optional[str] = Query(None, description="市場代碼"),
    limit: int = Query(100, ge=1, le=500, description="返回數量限制"),
    db: AsyncSession = Depends(get_database_session),
    stock_service: StockService = Depends(get_stock_service),
    signal_service: TradingSignalService = Depends(get_trading_signal_service_clean),
):
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        filters = {
            "start_date": start_date,
            "end_date": end_date,
        }
        if signal_type:
            filters["signal_type"] = signal_type.value

        signals = await signal_service.list_signals(
            db,
            filters=filters,
            market=market,
            limit=limit,
        )

        responses = []
        for signal in signals:
            stock = await stock_service.get_stock_by_id(db, signal["stock_id"])
            responses.append(_serialize_signal(signal, stock.symbol))

        return responses

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得信號歷史失敗: {str(e)}")


@router.get("/stats", response_model=SignalStatsResponse)
async def get_signal_statistics(
    days: int = Query(30, ge=1, le=365, description="統計天數"),
    market: Optional[str] = Query(None, description="市場代碼"),
    db: AsyncSession = Depends(get_database_session),
    signal_service: TradingSignalService = Depends(get_trading_signal_service_clean),
):
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        filters = {
            "start_date": start_date,
            "end_date": end_date,
        }

        stats = await signal_service.get_detailed_signal_stats(
            db, filters=filters, market=market
        )

        return SignalStatsResponse(
            total_signals=stats.get("total_signals", 0),
            buy_signals=stats.get("buy_signals", 0),
            sell_signals=stats.get("sell_signals", 0),
            hold_signals=stats.get("hold_signals", 0),
            cross_signals=stats.get("cross_signals", 0),
            avg_confidence=stats.get("avg_confidence", 0.0),
            top_stocks=stats.get("top_stocks", []),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得信號統計失敗: {str(e)}")


@router.get("/{stock_id}", response_model=List[TradingSignalResponse])
async def get_stock_signals(
    stock_id: int,
    signal_type: Optional[SignalTypeEnum] = Query(None, description="信號類型"),
    days: int = Query(30, ge=1, le=365, description="歷史天數"),
    limit: int = Query(50, ge=1, le=200, description="返回數量限制"),
    db: AsyncSession = Depends(get_database_session),
    stock_service: StockService = Depends(get_stock_service),
    signal_service: TradingSignalService = Depends(get_trading_signal_service_clean),
):
    try:
        stock = await stock_service.get_stock_by_id(db, stock_id)

        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        filters = {
            "stock_id": stock_id,
            "start_date": start_date,
            "end_date": end_date,
        }
        if signal_type:
            filters["signal_type"] = signal_type.value

        signals = await signal_service.list_signals(
            db,
            filters=filters,
            limit=limit,
        )

        return [_serialize_signal(signal, stock.symbol) for signal in signals]

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得股票信號失敗: {str(e)}")


@router.post("/{stock_id}/detect", response_model=List[TradingSignalResponse])
async def detect_stock_signals(
    stock_id: int,
    signal_types: List[SignalTypeEnum] = Query(
        [SignalTypeEnum.BUY, SignalTypeEnum.SELL], description="要偵測的信號類型"
    ),
    save_results: bool = Query(True, description="是否保存結果"),
    db: AsyncSession = Depends(get_database_session),
    stock_service: StockService = Depends(get_stock_service),
    signal_service: TradingSignalService = Depends(get_trading_signal_service_clean),
):
    try:
        stock = await stock_service.get_stock_by_id(db, stock_id)

        analysis = await signal_service.generate_trading_signals(db, stock_id)
        signals = []

        if analysis.primary_signal:
            signals.append(analysis.primary_signal)
        signals.extend(analysis.supporting_signals)

        responses = []
        for signal in signals:
            if SignalTypeEnum(signal.signal_type.value) in signal_types:
                response = TradingSignalResponse(
                    id=None,
                    stock_id=stock_id,
                    symbol=stock.symbol,
                    signal_type=signal.signal_type.value,
                    strength=signal.signal_strength.value,
                    price=(
                        float(signal.metadata.get("price", 0))
                        if signal.metadata
                        else None
                    ),
                    confidence=signal.confidence,
                    date=date.today(),
                    description=signal.description,
                    indicators=signal.metadata or {},
                    created_at=datetime.now(),
                )
                responses.append(response)

        if save_results:
            for response in responses:
                saved = await signal_service.create_signal(
                    db,
                    {
                        "stock_id": response.stock_id,
                        "signal_type": response.signal_type,
                        "strength": response.strength,
                        "price": response.price,
                        "confidence": response.confidence,
                        "date": response.date,
                        "description": response.description,
                        "indicators": response.indicators,
                    },
                )
                response.id = saved.get("id")

        return responses

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"信號偵測失敗: {str(e)}")


@router.delete("/{signal_id}")
async def delete_signal(
    signal_id: int,
    db: AsyncSession = Depends(get_database_session),
    signal_service: TradingSignalService = Depends(get_trading_signal_service_clean),
):
    try:
        signal = await signal_service.get_signal(db, signal_id)
        if not signal:
            raise HTTPException(status_code=404, detail="交易信號不存在")

        await signal_service.delete_signal(db, signal_id)
        return {"message": f"交易信號 {signal_id} 已成功刪除"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除交易信號失敗: {str(e)}")
