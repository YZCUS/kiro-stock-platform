"""
Market information API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.market_info import (
    MarketSearchResult,
    NewsArticleResponse,
    QuoteResponse,
    StockProfileResponse,
    WatchlistNewsResponse,
)
from app.dependencies import get_database_session, get_market_info_service
from core.auth_dependencies import get_current_active_user
from domain.models.user import User
from domain.services.market_info_service import MarketInfoService

router = APIRouter(prefix="/market", tags=["market-info"])


@router.get("/search", response_model=list[MarketSearchResult])
async def search_market_symbols(
    q: str = Query(..., min_length=1, max_length=50),
    market: str | None = Query(None, pattern="^(TW|US)$"),
    include_external: bool = Query(True),
    limit: int = Query(15, ge=1, le=50),
    db: AsyncSession = Depends(get_database_session),
    service: MarketInfoService = Depends(get_market_info_service),
):
    return await service.search(
        db,
        query=q,
        market=market,
        limit=limit,
        include_external=include_external,
    )


@router.get("/stocks/{market}/{symbol}/profile", response_model=StockProfileResponse)
async def get_stock_profile(
    market: str,
    symbol: str,
    db: AsyncSession = Depends(get_database_session),
    service: MarketInfoService = Depends(get_market_info_service),
):
    return await service.get_profile(db, symbol=symbol.upper(), market=market.upper())


@router.get("/stocks/{market}/{symbol}/quote", response_model=QuoteResponse)
async def get_stock_quote(
    market: str,
    symbol: str,
    stock_id: int | None = Query(None, ge=1),
    prefer_realtime: bool = Query(False),
    db: AsyncSession = Depends(get_database_session),
    service: MarketInfoService = Depends(get_market_info_service),
):
    return await service.get_quote(
        db,
        symbol=symbol.upper(),
        market=market.upper(),
        stock_id=stock_id,
        prefer_realtime=prefer_realtime,
    )


@router.get("/news", response_model=list[NewsArticleResponse])
async def get_market_news(
    category: str = Query("general", max_length=30),
    limit: int = Query(12, ge=1, le=50),
    service: MarketInfoService = Depends(get_market_info_service),
):
    try:
        return await service.market_news(category=category, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/stocks/{market}/{symbol}/news", response_model=list[NewsArticleResponse])
async def get_stock_news(
    market: str,
    symbol: str,
    days: int = Query(5, ge=1, le=30),
    limit: int = Query(12, ge=1, le=50),
    service: MarketInfoService = Depends(get_market_info_service),
):
    try:
        return await service.stock_news(
            symbol=symbol.upper(),
            market=market.upper(),
            days=days,
            limit=limit,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/watchlist/news", response_model=WatchlistNewsResponse)
async def get_watchlist_news(
    days: int = Query(5, ge=1, le=30),
    limit: int = Query(12, ge=1, le=50),
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_active_user),
    service: MarketInfoService = Depends(get_market_info_service),
):
    symbols, articles = await service.watchlist_news(
        db,
        user_id=current_user.id,
        days=days,
        limit=limit,
    )
    return {"symbols": symbols, "articles": articles}
