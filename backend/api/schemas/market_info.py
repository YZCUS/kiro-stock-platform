"""
Market information schemas.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MarketSearchResult(BaseModel):
    symbol: str
    market: str
    name: Optional[str] = None
    exchange: Optional[str] = None
    type: Optional[str] = None
    provider: str = "local"
    stock_id: Optional[int] = None
    is_local: bool = False
    tradingview_symbol: Optional[str] = None


class StockProfileResponse(BaseModel):
    symbol: str
    market: str
    name: Optional[str] = None
    exchange: Optional[str] = None
    currency: Optional[str] = None
    logo: Optional[str] = None
    market_cap: Optional[float] = None
    provider: str
    stock_id: Optional[int] = None
    tradingview_symbol: Optional[str] = None


class QuoteResponse(BaseModel):
    symbol: str
    market: str
    price: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
    timestamp: Optional[datetime] = None
    source: str
    is_realtime: bool = False


class NewsArticleResponse(BaseModel):
    id: Optional[str] = None
    symbol: Optional[str] = None
    headline: str
    summary: Optional[str] = None
    source: Optional[str] = None
    url: Optional[str] = None
    image: Optional[str] = None
    published_at: Optional[datetime] = None
    provider: str = "finnhub"


class WatchlistNewsResponse(BaseModel):
    articles: list[NewsArticleResponse]
    symbols: list[str] = Field(default_factory=list)
