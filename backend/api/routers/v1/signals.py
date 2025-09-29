"""
交易信號API路由 - Clean Architecture版本
只負責HTTP路由、參數驗證和回應格式化，業務邏輯委託給Domain Services
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.dependencies import (
    get_database_session,
    get_trading_signal_service_clean,
)

router = APIRouter()


@router.get("/generate/{stock_id}")
async def generate_trading_signals(
    stock_id: int,
    analysis_days: int = Query(60, ge=20, le=365, description="分析天數"),
    db: AsyncSession = Depends(get_database_session),
    signal_service=Depends(get_trading_signal_service_clean)
):
    """生成股票交易信號"""
    try:
        analysis = await signal_service.generate_trading_signals(
            db=db,
            stock_id=stock_id,
            analysis_days=analysis_days
        )

        response = {
            "stock_id": analysis.stock_id,
            "symbol": analysis.symbol,
            "analysis_date": analysis.analysis_date,
            "signals_generated": analysis.signals_generated,
            "primary_signal": None,
            "supporting_signals": [],
            "risk_score": analysis.risk_score,
            "recommendation": analysis.recommendation,
            "reasoning": analysis.reasoning,
        }

        if analysis.primary_signal:
            response["primary_signal"] = {
                "signal_type": analysis.primary_signal.signal_type.value,
                "signal_strength": analysis.primary_signal.signal_strength.value,
                "signal_source": analysis.primary_signal.signal_source.value,
                "confidence": analysis.primary_signal.confidence,
                "target_price": analysis.primary_signal.target_price,
                "stop_loss": analysis.primary_signal.stop_loss,
                "description": analysis.primary_signal.description,
            }

        response["supporting_signals"] = [
            {
                "signal_type": signal.signal_type.value,
                "signal_strength": signal.signal_strength.value,
                "signal_source": signal.signal_source.value,
                "confidence": signal.confidence,
                "description": signal.description,
            }
            for signal in analysis.supporting_signals
        ]

        return response

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成交易信號失敗: {str(e)}")


@router.get("/market-scan")
async def scan_market_signals(
    market: Optional[str] = Query(None, description="市場代碼 (TW/US)"),
    min_confidence: float = Query(0.8, ge=0.0, le=1.0, description="最低信心度"),
    db: AsyncSession = Depends(get_database_session),
    signal_service=Depends(get_trading_signal_service_clean)
):
    """掃描市場交易信號"""
    try:
        portfolio_signals = await signal_service.scan_market_signals(
            db=db,
            market=market,
            min_confidence=min_confidence
        )

        high_confidence_signals = [
            {
                "stock_id": signal.stock_id,
                "symbol": signal.symbol,
                "signal_type": signal.signal_type.value,
                "signal_strength": signal.signal_strength.value,
                "signal_source": signal.signal_source.value,
                "confidence": signal.confidence,
                "target_price": signal.target_price,
                "stop_loss": signal.stop_loss,
                "description": signal.description,
            }
            for signal in portfolio_signals.high_confidence_signals
        ]

        return {
            "analysis_date": portfolio_signals.analysis_date,
            "total_stocks_analyzed": portfolio_signals.total_stocks_analyzed,
            "buy_signals": portfolio_signals.buy_signals,
            "sell_signals": portfolio_signals.sell_signals,
            "hold_signals": portfolio_signals.hold_signals,
            "high_confidence_signals": high_confidence_signals,
            "risk_alerts": portfolio_signals.risk_alerts,
            "market_sentiment": portfolio_signals.market_sentiment,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"市場信號掃描失敗: {str(e)}")


@router.get("/performance")
async def get_signal_performance(
    days: int = Query(30, ge=7, le=365, description="分析天數"),
    db: AsyncSession = Depends(get_database_session),
    signal_service=Depends(get_trading_signal_service_clean)
):
    """取得信號表現統計"""
    try:
        performance = await signal_service.get_signal_performance(
            db=db,
            days=days
        )

        return performance

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得信號表現失敗: {str(e)}")


@router.get("/test")
async def test_signals():
    return {"message": "Trading Signals API working with Clean Architecture"}