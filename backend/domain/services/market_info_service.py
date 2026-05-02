"""
Market information orchestration service.
"""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models.market_data_bar import MarketDataBar
from domain.models.price_history import PriceHistory
from domain.models.stock import Stock
from domain.models.user_stock_list import UserStockList, UserStockListItem
from domain.repositories.market_info_provider_interface import IMarketInfoProvider
from domain.repositories.quote_data_source_interface import IQuoteDataSource
from domain.services.symbol_mapping_service import SymbolMappingService
from infrastructure.external.finnhub_client import unix_timestamp_to_datetime


class MarketInfoService:
    """Combines local canonical data with optional Finnhub product data."""

    def __init__(
        self,
        market_info_provider: IMarketInfoProvider,
        quote_data_source: Optional[IQuoteDataSource] = None,
        symbol_mapping_service: Optional[SymbolMappingService] = None,
    ):
        self.market_info_provider = market_info_provider
        self.quote_data_source = quote_data_source
        self.symbol_mapping = symbol_mapping_service or SymbolMappingService()

    async def search(
        self,
        db: AsyncSession,
        query: str,
        market: Optional[str] = None,
        limit: int = 15,
        include_external: bool = True,
    ) -> list[dict[str, Any]]:
        trimmed = query.strip()
        if not trimmed:
            return []

        items_by_key: dict[tuple[str, str], dict[str, Any]] = {}
        local_result = await db.execute(
            select(Stock)
            .where(
                Stock.is_active == True,
                or_(
                    Stock.symbol.ilike(f"%{trimmed}%"),
                    Stock.name.ilike(f"%{trimmed}%"),
                ),
                *([Stock.market == market] if market else []),
            )
            .order_by(Stock.symbol)
            .limit(limit)
        )
        for stock in local_result.scalars().all():
            mapping = self.symbol_mapping.build_mapping(stock.symbol, stock.market)
            items_by_key[(stock.symbol, stock.market)] = {
                "symbol": stock.symbol,
                "market": stock.market,
                "name": stock.name,
                "exchange": mapping.exchange_code,
                "type": "Stock",
                "provider": "local",
                "stock_id": stock.id,
                "is_local": True,
                "tradingview_symbol": mapping.tradingview_symbol,
            }

        if (
            include_external
            and self.market_info_provider.is_available()
            and len(items_by_key) < limit
        ):
            external_items = await self.market_info_provider.search_symbols(trimmed)
            for item in external_items:
                symbol = str(item.get("symbol") or "").upper()
                if not symbol:
                    continue
                detected_market = self._market_from_symbol(symbol)
                if market and detected_market != market:
                    continue
                key = (symbol, detected_market)
                if key in items_by_key:
                    continue
                mapping = self.symbol_mapping.build_mapping(symbol, detected_market)
                items_by_key[key] = {
                    "symbol": symbol,
                    "market": detected_market,
                    "name": item.get("description") or symbol,
                    "exchange": item.get("displaySymbol") or mapping.exchange_code,
                    "type": item.get("type") or "Stock",
                    "provider": "finnhub",
                    "stock_id": None,
                    "is_local": False,
                    "tradingview_symbol": mapping.tradingview_symbol,
                }
                if len(items_by_key) >= limit:
                    break

        if (
            include_external
            and len(items_by_key) < limit
            and self._is_symbol_like(trimmed)
        ):
            symbol = trimmed.upper()
            detected_market = market or self._market_from_symbol(symbol)
            mapping = self.symbol_mapping.build_mapping(symbol, detected_market)
            display_symbol = (
                mapping.yahoo_symbol
                if detected_market == "TW"
                else mapping.internal_symbol
            )
            key = (display_symbol, detected_market)
            if key not in items_by_key:
                items_by_key[key] = {
                    "symbol": display_symbol,
                    "market": detected_market,
                    "name": display_symbol,
                    "exchange": mapping.exchange_code,
                    "type": "Stock",
                    "provider": "symbol",
                    "stock_id": None,
                    "is_local": False,
                    "tradingview_symbol": mapping.tradingview_symbol,
                }

        return list(items_by_key.values())[:limit]

    async def get_profile(
        self,
        db: AsyncSession,
        symbol: str,
        market: str,
    ) -> dict[str, Any]:
        stock = await self._find_stock(db, symbol, market)
        mapping = self.symbol_mapping.build_mapping(symbol, market)
        profile: dict[str, Any] = {}
        provider = "local"
        if self.market_info_provider.is_available():
            try:
                profile = await self.market_info_provider.get_company_profile(
                    mapping.finnhub_symbol
                )
                provider = self.market_info_provider.get_source_name()
            except Exception:
                profile = {}

        return {
            "symbol": stock.symbol if stock else mapping.internal_symbol,
            "market": market,
            "name": profile.get("name") or (stock.name if stock else None),
            "exchange": profile.get("exchange") or mapping.exchange_code,
            "currency": profile.get("currency"),
            "logo": profile.get("logo"),
            "market_cap": profile.get("marketCapitalization"),
            "provider": provider,
            "stock_id": stock.id if stock else None,
            "tradingview_symbol": mapping.tradingview_symbol,
        }

    async def get_quote(
        self,
        db: AsyncSession,
        symbol: str,
        market: str,
        stock_id: Optional[int] = None,
        prefer_realtime: bool = False,
    ) -> dict[str, Any]:
        stock = (
            await db.get(Stock, stock_id)
            if stock_id
            else await self._find_stock(db, symbol, market)
        )
        mapping = self.symbol_mapping.build_mapping(symbol, market)

        if prefer_realtime:
            realtime_quote = await self._realtime_quote_or_none(
                mapping.finnhub_symbol, symbol, market
            )
            if realtime_quote and realtime_quote.get("price") is not None:
                return realtime_quote

        if stock:
            local_quote = await self._latest_local_quote(db, stock)
            if local_quote:
                return local_quote

        realtime_quote = await self._realtime_quote_or_none(
            mapping.finnhub_symbol, symbol, market
        )
        if realtime_quote:
            return realtime_quote

        return {
            "symbol": symbol,
            "market": market,
            "price": None,
            "change": None,
            "change_percent": None,
            "timestamp": None,
            "source": "unavailable",
            "is_realtime": False,
        }

    async def market_news(self, category: str = "general", limit: int = 12) -> list[dict[str, Any]]:
        if not self.market_info_provider.is_available():
            return []
        articles = await self.market_info_provider.get_market_news(category)
        return [self._format_news_article(article) for article in articles[:limit]]

    async def stock_news(
        self,
        symbol: str,
        market: str,
        days: int = 5,
        limit: int = 12,
    ) -> list[dict[str, Any]]:
        if not self.market_info_provider.is_available():
            return []
        mapping = self.symbol_mapping.build_mapping(symbol, market)
        end = date.today()
        start = end - timedelta(days=days)
        articles = await self.market_info_provider.get_company_news(
            mapping.finnhub_symbol,
            start.isoformat(),
            end.isoformat(),
        )
        return [
            {**self._format_news_article(article), "symbol": symbol}
            for article in articles[:limit]
        ]

    async def watchlist_news(
        self,
        db: AsyncSession,
        user_id,
        days: int = 5,
        limit: int = 12,
    ) -> tuple[list[str], list[dict[str, Any]]]:
        result = await db.execute(
            select(Stock)
            .join(UserStockListItem, UserStockListItem.stock_id == Stock.id)
            .join(UserStockList, UserStockList.id == UserStockListItem.list_id)
            .where(UserStockList.user_id == user_id)
            .order_by(UserStockListItem.sort_order, Stock.symbol)
            .limit(20)
        )
        stocks = result.scalars().all()
        symbols = [stock.symbol for stock in stocks]
        articles: list[dict[str, Any]] = []
        if not stocks:
            return symbols, await self.market_news(limit=limit)

        per_symbol = max(1, limit // max(len(stocks), 1))
        for stock in stocks:
            stock_articles = await self.stock_news(
                stock.symbol,
                stock.market,
                days=days,
                limit=per_symbol,
            )
            articles.extend(stock_articles)
            if len(articles) >= limit:
                break
        articles.sort(key=lambda item: item.get("published_at") or "", reverse=True)
        return symbols, articles[:limit]

    async def _find_stock(
        self,
        db: AsyncSession,
        symbol: str,
        market: str,
    ) -> Optional[Stock]:
        result = await db.execute(
            select(Stock)
            .where(Stock.symbol == symbol.upper(), Stock.market == market.upper())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _latest_local_quote(
        self, db: AsyncSession, stock: Stock
    ) -> Optional[dict[str, Any]]:
        bar_result = await db.execute(
            select(MarketDataBar)
            .where(MarketDataBar.stock_id == stock.id, MarketDataBar.timeframe == "1d")
            .order_by(desc(MarketDataBar.timestamp))
            .limit(2)
        )
        bars = bar_result.scalars().all()
        if bars:
            latest = bars[0]
            previous = bars[1] if len(bars) > 1 else None
            price = float(latest.close_price)
            prev_close = float(previous.close_price) if previous else None
            change = price - prev_close if prev_close else None
            return {
                "symbol": stock.symbol,
                "market": stock.market,
                "price": price,
                "change": change,
                "change_percent": (change / prev_close * 100) if change is not None and prev_close else None,
                "timestamp": latest.timestamp,
                "source": "market_data_bars",
                "is_realtime": False,
            }

        price_result = await db.execute(
            select(PriceHistory)
            .where(PriceHistory.stock_id == stock.id)
            .order_by(desc(PriceHistory.date))
            .limit(2)
        )
        prices = price_result.scalars().all()
        if not prices:
            return None
        latest = prices[0]
        previous = prices[1] if len(prices) > 1 else None
        if latest.close_price is None:
            return None
        price = float(latest.close_price)
        prev_close = float(previous.close_price) if previous and previous.close_price else None
        change = price - prev_close if prev_close else None
        return {
            "symbol": stock.symbol,
            "market": stock.market,
            "price": price,
            "change": change,
            "change_percent": (
                (change / prev_close * 100)
                if change is not None and prev_close
                else None
            ),
            "timestamp": datetime.combine(
                latest.date, time.min, tzinfo=timezone.utc
            ),
            "source": "price_history",
            "is_realtime": False,
        }

    async def _realtime_quote_or_none(
        self, provider_symbol: str, symbol: str, market: str
    ) -> Optional[dict[str, Any]]:
        if self.quote_data_source is None or not self.quote_data_source.is_available():
            return None

        try:
            quote = await self.quote_data_source.fetch_quote(
                provider_symbol,
                market=market,
            )
        except Exception:
            return None

        price = quote.get("c")
        return {
            "symbol": symbol,
            "market": market,
            "price": float(price) if price is not None else None,
            "change": self._float_or_none(quote.get("d")),
            "change_percent": self._float_or_none(quote.get("dp")),
            "timestamp": unix_timestamp_to_datetime(quote.get("t")),
            "source": self.quote_data_source.get_source_name(),
            "is_realtime": True,
        }

    def _format_news_article(self, article: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(article.get("id")) if article.get("id") is not None else None,
            "headline": article.get("headline") or article.get("title") or "",
            "summary": article.get("summary"),
            "source": article.get("source"),
            "url": article.get("url"),
            "image": article.get("image"),
            "published_at": unix_timestamp_to_datetime(article.get("datetime")),
            "provider": "finnhub",
        }

    def _market_from_symbol(self, symbol: str) -> str:
        upper = symbol.upper()
        if upper.endswith(".TW") or upper.endswith(".TWO") or upper.isdigit():
            return "TW"
        return "US"

    def _is_symbol_like(self, query: str) -> bool:
        upper = query.strip().upper()
        return bool(
            re.fullmatch(r"\d{4,6}(\.(TW|TWO))?", upper)
            or re.fullmatch(r"[A-Z]{1,5}([.-][A-Z])?", upper)
        )

    def _float_or_none(self, value: Any) -> Optional[float]:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
