"""
分析相關API端點
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel
from enum import Enum

from core.database import get_db_session
from services.analysis.technical_analysis import technical_analysis_service, IndicatorType
from services.analysis.signal_detector import trading_signal_detector, SignalType, SignalStrength
from models.repositories.crud_stock import stock_crud

router = APIRouter(prefix="/analysis", tags=["analysis"])


# Pydantic模型
class IndicatorTypeEnum(str, Enum):
    SMA = "SMA"
    EMA = "EMA"
    RSI = "RSI"
    MACD = "MACD"
    BOLLINGER = "BOLLINGER"
    STOCHASTIC = "STOCHASTIC"


class SignalTypeEnum(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


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
    price: float
    timestamp: datetime
    indicators: Dict[str, Any]


@router.post("/technical-analysis", response_model=TechnicalAnalysisResponse)
async def calculate_technical_indicator(
    request: TechnicalAnalysisRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    計算技術指標
    """
    try:
        # 檢查股票是否存在
        stock = await stock_crud.get(db, request.stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")
        
        # 計算技術指標
        indicator_type = IndicatorType(request.indicator.value)
        result = await technical_analysis_service.calculate_indicator(
            db, request.stock_id, indicator_type, request.days
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="無法計算技術指標，可能缺少足夠的數據")
        
        return TechnicalAnalysisResponse(
            stock_id=request.stock_id,
            indicator=request.indicator.value,
            values=result.values,
            summary=result.summary,
            timestamp=datetime.now()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"技術分析計算失敗: {str(e)}")


@router.get("/technical-analysis/{stock_id}", response_model=List[TechnicalAnalysisResponse])
async def get_all_technical_indicators(
    stock_id: int,
    days: int = Query(30, description="計算天數"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    取得股票的所有技術指標
    """
    try:
        # 檢查股票是否存在
        stock = await stock_crud.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")
        
        # 計算所有指標
        indicators = [IndicatorType.SMA, IndicatorType.EMA, IndicatorType.RSI, IndicatorType.MACD]
        results = []
        
        for indicator_type in indicators:
            try:
                result = await technical_analysis_service.calculate_indicator(
                    db, stock_id, indicator_type, days
                )
                
                if result:
                    results.append(TechnicalAnalysisResponse(
                        stock_id=stock_id,
                        indicator=indicator_type.value,
                        values=result.values,
                        summary=result.summary,
                        timestamp=datetime.now()
                    ))
            except Exception as e:
                # 記錄錯誤但繼續處理其他指標
                print(f"計算 {indicator_type.value} 指標時發生錯誤: {str(e)}")
        
        return results
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得技術指標失敗: {str(e)}")


@router.post("/signals", response_model=List[SignalResponse])
async def detect_trading_signals(
    request: SignalDetectionRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    偵測交易信號
    """
    try:
        # 檢查股票是否存在
        stock = await stock_crud.get(db, request.stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")
        
        # 偵測信號
        all_signals = []
        for signal_type_enum in request.signal_types:
            signal_type = SignalType(signal_type_enum.value)
            signals = await trading_signal_detector.detect_signals(
                db, request.stock_id, signal_type
            )
            
            for signal in signals:
                all_signals.append(SignalResponse(
                    stock_id=request.stock_id,
                    symbol=stock.symbol,
                    signal_type=signal.signal_type.value,
                    strength=signal.strength.value,
                    price=float(signal.price),
                    timestamp=signal.timestamp,
                    indicators=signal.indicators
                ))
        
        return all_signals
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"信號偵測失敗: {str(e)}")


@router.get("/signals/{stock_id}", response_model=List[SignalResponse])
async def get_stock_signals(
    stock_id: int,
    signal_type: Optional[SignalTypeEnum] = Query(None, description="信號類型"),
    limit: int = Query(10, description="返回數量限制"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    取得股票的交易信號
    """
    try:
        # 檢查股票是否存在
        stock = await stock_crud.get(db, stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")
        
        # 取得信號
        if signal_type:
            signal_types = [SignalType(signal_type.value)]
        else:
            signal_types = [SignalType.BUY, SignalType.SELL, SignalType.HOLD]
        
        all_signals = []
        for st in signal_types:
            signals = await trading_signal_detector.detect_signals(db, stock_id, st)
            
            for signal in signals[:limit]:  # 限制每種類型的數量
                all_signals.append(SignalResponse(
                    stock_id=stock_id,
                    symbol=stock.symbol,
                    signal_type=signal.signal_type.value,
                    strength=signal.strength.value,
                    price=float(signal.price),
                    timestamp=signal.timestamp,
                    indicators=signal.indicators
                ))
        
        # 按時間排序
        all_signals.sort(key=lambda x: x.timestamp, reverse=True)
        
        return all_signals[:limit]
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得交易信號失敗: {str(e)}")


@router.get("/batch-analysis", response_model=Dict[str, Any])
async def batch_technical_analysis(
    market: Optional[str] = Query(None, description="市場代碼"),
    indicator: IndicatorTypeEnum = Query(IndicatorTypeEnum.RSI, description="技術指標"),
    days: int = Query(30, description="計算天數"),
    limit: int = Query(20, description="股票數量限制"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    批次技術分析
    """
    try:
        # 取得股票清單
        stocks = await stock_crud.get_multi(db, limit=limit)
        if market:
            stocks = [stock for stock in stocks if stock.market == market]
        
        # 批次計算指標
        results = []
        indicator_type = IndicatorType(indicator.value)
        
        for stock in stocks:
            try:
                result = await technical_analysis_service.calculate_indicator(
                    db, stock.id, indicator_type, days
                )
                
                if result:
                    results.append({
                        'stock_id': stock.id,
                        'symbol': stock.symbol,
                        'market': stock.market,
                        'indicator': indicator.value,
                        'current_value': result.summary.get('current_value'),
                        'trend': result.summary.get('trend'),
                        'signal': result.summary.get('signal')
                    })
            except Exception as e:
                print(f"分析股票 {stock.symbol} 時發生錯誤: {str(e)}")
        
        return {
            'indicator': indicator.value,
            'total_analyzed': len(results),
            'results': results,
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批次技術分析失敗: {str(e)}")


@router.get("/market-overview", response_model=Dict[str, Any])
async def get_market_overview(
    market: Optional[str] = Query(None, description="市場代碼"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    取得市場概覽
    """
    try:
        # 取得股票清單
        stocks = await stock_crud.get_multi(db, limit=50)
        if market:
            stocks = [stock for stock in stocks if stock.market == market]
        
        # 統計信號分佈
        signal_stats = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        analyzed_stocks = 0
        
        for stock in stocks[:20]:  # 限制分析數量
            try:
                # 快速信號檢測
                buy_signals = await trading_signal_detector.detect_signals(
                    db, stock.id, SignalType.BUY
                )
                sell_signals = await trading_signal_detector.detect_signals(
                    db, stock.id, SignalType.SELL
                )
                
                if buy_signals:
                    signal_stats['BUY'] += 1
                elif sell_signals:
                    signal_stats['SELL'] += 1
                else:
                    signal_stats['HOLD'] += 1
                
                analyzed_stocks += 1
                
            except Exception as e:
                print(f"分析股票 {stock.symbol} 信號時發生錯誤: {str(e)}")
        
        return {
            'market': market or 'ALL',
            'total_stocks': len(stocks),
            'analyzed_stocks': analyzed_stocks,
            'signal_distribution': signal_stats,
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得市場概覽失敗: {str(e)}")