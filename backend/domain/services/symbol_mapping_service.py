"""
Provider symbol mapping helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models.stock import Stock
from domain.models.stock_symbol_mapping import StockSymbolMapping


FINNHUB_TO_TRADINGVIEW_EXCHANGE = {
    ".TW": "TWSE",
    ".TWO": "TPEX",
    ".T": "TSE",
    ".HK": "HKEX",
    ".SS": "SSE",
    ".SZ": "SZSE",
    ".KS": "KRX",
    ".KQ": "KRX",
    ".SI": "SGX",
    ".AX": "ASX",
    ".NZ": "NZX",
    ".L": "LSE",
    ".DE": "XETR",
    ".F": "FWB",
    ".PA": "EURONEXT",
    ".MI": "MIL",
    ".TO": "TSX",
    ".V": "TSXV",
}


@dataclass(frozen=True)
class SymbolMapping:
    internal_symbol: str
    market: str
    yahoo_symbol: str
    finnhub_symbol: str
    tradingview_symbol: str
    exchange_code: Optional[str] = None


class SymbolMappingService:
    """Normalizes symbols across local, Yahoo, Finnhub, and TradingView formats."""

    async def get_provider_symbol(
        self,
        db: AsyncSession,
        stock: Stock,
        provider: str,
    ) -> str:
        result = await db.execute(
            select(StockSymbolMapping.provider_symbol)
            .where(
                StockSymbolMapping.stock_id == stock.id,
                StockSymbolMapping.provider == provider,
            )
            .limit(1)
        )
        mapped = result.scalar_one_or_none()
        if mapped:
            return mapped
        return self.build_mapping(stock.symbol, stock.market).__dict__[
            f"{provider}_symbol"
        ]

    async def upsert_provider_mapping(
        self,
        db: AsyncSession,
        stock: Stock,
        provider: str,
        provider_symbol: str,
        exchange_code: Optional[str] = None,
        currency: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> StockSymbolMapping:
        result = await db.execute(
            select(StockSymbolMapping).where(
                StockSymbolMapping.stock_id == stock.id,
                StockSymbolMapping.provider == provider,
            )
        )
        mapping = result.scalar_one_or_none()
        if mapping is None:
            mapping = StockSymbolMapping(
                stock_id=stock.id,
                provider=provider,
                provider_symbol=provider_symbol,
            )
            db.add(mapping)
        mapping.provider_symbol = provider_symbol
        mapping.exchange_code = exchange_code
        mapping.currency = currency
        mapping.metadata_json = metadata
        await db.flush()
        return mapping

    def build_mapping(self, symbol: str, market: str) -> SymbolMapping:
        normalized = symbol.strip().upper()
        market = market.strip().upper()
        yahoo_symbol = normalized
        finnhub_symbol = normalized

        if market == "TW":
            if not normalized.endswith(".TW") and not normalized.endswith(".TWO"):
                yahoo_symbol = f"{normalized}.TW"
                finnhub_symbol = yahoo_symbol
            tradingview_symbol = self.to_tradingview_symbol(finnhub_symbol)
            exchange_code = tradingview_symbol.split(":", 1)[0]
        else:
            tradingview_symbol = normalized
            exchange_code = None

        return SymbolMapping(
            internal_symbol=normalized,
            market=market,
            yahoo_symbol=yahoo_symbol,
            finnhub_symbol=finnhub_symbol,
            tradingview_symbol=tradingview_symbol,
            exchange_code=exchange_code,
        )

    def to_tradingview_symbol(self, symbol: str) -> str:
        upper_symbol = symbol.strip().upper()
        for suffix in sorted(FINNHUB_TO_TRADINGVIEW_EXCHANGE, key=len, reverse=True):
            if upper_symbol.endswith(suffix):
                ticker = upper_symbol[: -len(suffix)]
                return f"{FINNHUB_TO_TRADINGVIEW_EXCHANGE[suffix]}:{ticker}"
        return upper_symbol
