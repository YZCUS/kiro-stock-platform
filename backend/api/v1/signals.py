"""
交易信號相關API端點
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel
from enum import Enum

from core.database import get_db_session
from services.analysis.signal_detector import trading_signal_detector, SignalType, SignalStrength
from services.trading.buy_sell_generator import buy_sell_signal_generator
from models.repositories.crud_stock import stock_crud
from models.repositories.crud_trading_signal import trading_signal_crud

router = APIRouter(prefix="/signals", tags=["signals"])


# Pydantic模型
class SignalTypeEnum(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    GOLDEN_CROSS = "GOLDEN_CROSS"
    DEATH_CROSS = "DEATH_CROSS"


class SignalStrengthEnum(str, Enum):
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"


class TradingSignalResponse(BaseModel):
    id: int
    stock_id: int
    symbol: str
    signal_type: str
    strength: str
    price: float
    confidence: float
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


@router.get("/", response_model=SignalHistoryResponse)
async def get_all_signals(
    signal_type: Optional[SignalTypeEnum] = Query(None, description="信號類型"),
    market: Optional[str] = Query(None, description="市場代碼"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0, description="最小信心度"),
    start_date: Optional[date] = Query(None, description="開始日期"),
    end_date: Optional[date] = Query(None, description="結束日期"),
    page: int = Query(1, ge=1, description="頁碼"),
    page_size: int = Query(50, ge=1, le=200, description="每頁數量"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    取得所有交易信號
    """
    try:
        # 計算分頁偏移量
        offset = (page - 1) * page_size
        
        # 建立查詢條件
        filters = {}
        if signal_type:
            filters["signal_type"] = signal_type.value
        if min_confidence > 0:
            filters["min_confidence"] = min_confidence
        if start_date:
            filters["start_date"] = start_date
        if end_date:
            filters["end_date"] = end_date
        
        # 取得信號數據
        signals = await trading_signal_crud.get_signals_with_filters(
            db, filters=filters, market=market, offset=offset, limit=page_size
        )
        
        # 取得總數
        total_count = await trading_signal_crud.count_signals_with_filters(
            db, filters=filters, market=market
        )
        
        # 格式化信號數據
        signal_responses = []
        for signal in signals:
            signal_responses.append(TradingSignalResponse(
                id=signal.id,
                stock_id=signal.stock_id,
                symbol=signal.stock.symbol,
                signal_type=signal.signal_type,
                strength=signal.strength or "MODERATE",
                price=float(signal.price),
                confidence=float(signal.confidence),
                date=signal.date,
                description=signal.description or "",
                indicators=signal.indicators or {},
                created_at=signal.created_at
            ))
        
        # 計算統計資訊
        stats = await trading_signal_crud.get_signal_stats(db, filters=filters, market=market)
        
        # 計算分頁資訊
        total_pages = (total_count + page_size - 1) // page_size
        
        return SignalHistoryResponse(
            signals=signal_responses,
            pagination={
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            },
            stats=stats
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得交易信號失敗: {str(e)}")


@router.get("/history", response_model=List[TradingSignalResponse])
async def get_signal_history(
    days: int = Query(30, ge=1, le=365, description="歷史天數"),
    signal_type: Optional[SignalTypeEnum] = Query(None, description="信號類型"),
    market: Optional[str] = Query(None, description="市場代碼"),
    limit: int = Query(100, ge=1, le=500, description="返回數量限制"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    取得歷史交易信號
    """
    try:
        from datetime import timedelta
        
        # 計算日期範圍
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        # 建立查詢條件
        filters = {
            "start_date": start_date,
            "end_date": end_date
        }
        if signal_type:
            filters["signal_type"] = signal_type.value
        
        # 取得信號數據
        signals = await trading_signal_crud.get_signals_with_filters(
            db, filters=filters, market=market, limit=limit
        )
        
        # 格式化響應
        return [
            TradingSignalResponse(
                id=signal.id,
                stock_id=signal.stock_id,
                symbol=signal.stock.symbol,
                signal_type=signal.signal_type,
                strength=signal.strength or "MODERATE",
                price=float(signal.price),
                confidence=float(signal.confidence),
                date=signal.date,
                description=signal.description or "",
                indicators=signal.indicators or {},
                created_at=signal.created_at
            )
            for signal in signals
        ]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得信號歷史失敗: {str(e)}")


@router.get("/stats", response_model=SignalStatsResponse)
async def get_signal_statistics(
    days: int = Query(30, ge=1, le=365, description="統計天數"),
    market: Optional[str] = Query(None, description="市場代碼"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    取得信號統計資訊
    """
    try:
        from datetime import timedelta
        
        # 計算日期範圍
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        filters = {
            "start_date": start_date,
            "end_date": end_date
        }
        
        # 取得統計資訊
        stats = await trading_signal_crud.get_detailed_signal_stats(db, filters=filters, market=market)
        
        return SignalStatsResponse(
            total_signals=stats.get("total_signals", 0),
            buy_signals=stats.get("buy_signals", 0),
            sell_signals=stats.get("sell_signals", 0),
            hold_signals=stats.get("hold_signals", 0),
            cross_signals=stats.get("cross_signals", 0),
            avg_confidence=stats.get("avg_confidence", 0.0),
            top_stocks=stats.get("top_stocks", [])
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得信號統計失敗: {str(e)}")


@router.get("/{stock_id}", response_model=List[TradingSignalResponse])
async def get_stock_signals(
    stock_id: int,
    signal_type: Optional[SignalTypeEnum] = Query(None, description="信號類型"),
    days: int = Query(30, ge=1, le=365, description="歷史天數"),
    limit: int = Query(50, ge=1, le=200, description="返回數量限制"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    取得特定股票的交易信號
    """
    try:
        # 檢查股票是否存在
        stock = await stock_crud.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")
        
        from datetime import timedelta
        
        # 計算日期範圍
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        # 建立查詢條件
        filters = {
            "stock_id": stock_id,
            "start_date": start_date,
            "end_date": end_date
        }
        if signal_type:
            filters["signal_type"] = signal_type.value
        
        # 取得信號數據
        signals = await trading_signal_crud.get_signals_with_filters(
            db, filters=filters, limit=limit
        )
        
        # 格式化響應
        return [
            TradingSignalResponse(
                id=signal.id,
                stock_id=signal.stock_id,
                symbol=stock.symbol,
                signal_type=signal.signal_type,
                strength=signal.strength or "MODERATE",
                price=float(signal.price),
                confidence=float(signal.confidence),
                date=signal.date,
                description=signal.description or "",
                indicators=signal.indicators or {},
                created_at=signal.created_at
            )
            for signal in signals
        ]
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得股票信號失敗: {str(e)}")


@router.post("/{stock_id}/detect", response_model=List[TradingSignalResponse])
async def detect_stock_signals(
    stock_id: int,
    signal_types: List[SignalTypeEnum] = Query([SignalTypeEnum.BUY, SignalTypeEnum.SELL], description="要偵測的信號類型"),
    save_results: bool = Query(True, description="是否保存結果"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    即時偵測股票交易信號
    """
    try:
        # 檢查股票是否存在
        stock = await stock_crud.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")
        
        all_signals = []
        
        # 偵測各種信號類型
        for signal_type_enum in signal_types:
            if signal_type_enum in [SignalTypeEnum.BUY, SignalTypeEnum.SELL, SignalTypeEnum.HOLD]:
                # 使用交易信號偵測器
                signal_type = SignalType(signal_type_enum.value)
                signals = await trading_signal_detector.detect_signals(db, stock_id, signal_type)
                
                for signal in signals:
                    signal_response = TradingSignalResponse(
                        id=0,  # 新偵測的信號還沒有ID
                        stock_id=stock_id,
                        symbol=stock.symbol,
                        signal_type=signal.signal_type.value,
                        strength=signal.strength.value,
                        price=float(signal.price),
                        confidence=signal.confidence,
                        date=date.today(),
                        description=signal.description,
                        indicators=signal.indicators,
                        created_at=datetime.now()
                    )
                    all_signals.append(signal_response)
            
            elif signal_type_enum in [SignalTypeEnum.GOLDEN_CROSS, SignalTypeEnum.DEATH_CROSS]:
                # 使用買賣信號生成器偵測交叉信號
                cross_signals = await buy_sell_signal_generator.detect_cross_signals(db, stock_id)
                
                for signal in cross_signals:
                    if (signal_type_enum == SignalTypeEnum.GOLDEN_CROSS and signal.signal_type == "GOLDEN_CROSS") or \
                       (signal_type_enum == SignalTypeEnum.DEATH_CROSS and signal.signal_type == "DEATH_CROSS"):
                        signal_response = TradingSignalResponse(
                            id=0,
                            stock_id=stock_id,
                            symbol=stock.symbol,
                            signal_type=signal.signal_type,
                            strength="MODERATE",
                            price=float(signal.price),
                            confidence=signal.confidence,
                            date=signal.date,
                            description=signal.description,
                            indicators=signal.indicators,
                            created_at=datetime.now()
                        )
                        all_signals.append(signal_response)
        
        # 如果需要保存結果
        if save_results and all_signals:
            for signal in all_signals:
                signal_data = {
                    "stock_id": signal.stock_id,
                    "signal_type": signal.signal_type,
                    "strength": signal.strength,
                    "price": signal.price,
                    "confidence": signal.confidence,
                    "date": signal.date,
                    "description": signal.description,
                    "indicators": signal.indicators
                }
                saved_signal = await trading_signal_crud.create(db, obj_in=signal_data)
                signal.id = saved_signal.id
        
        return all_signals
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"信號偵測失敗: {str(e)}")


@router.delete("/{signal_id}")
async def delete_signal(
    signal_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """
    刪除交易信號
    """
    try:
        # 檢查信號是否存在
        signal = await trading_signal_crud.get(db, signal_id)
        if not signal:
            raise HTTPException(status_code=404, detail="交易信號不存在")
        
        # 刪除信號
        await trading_signal_crud.remove(db, id=signal_id)
        
        return {"message": f"交易信號 {signal_id} 已成功刪除"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除交易信號失敗: {str(e)}")