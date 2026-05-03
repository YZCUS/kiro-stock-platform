"""Realtime market stream data contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class MarketTradeEvent:
    """Normalized trade event from an upstream realtime provider."""

    market: str
    symbol: str
    price: float
    volume: int
    timestamp: datetime
    source: str


@dataclass(frozen=True)
class RealtimeQuote:
    """Latest quote/trade snapshot sent to UI clients."""

    market: str
    symbol: str
    price: float
    volume: int
    timestamp: datetime
    source: str
    change: Optional[float] = None
    change_percent: Optional[float] = None

    def to_message_data(self) -> dict:
        return {
            "market": self.market,
            "symbol": self.symbol,
            "price": self.price,
            "volume": self.volume,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "change": self.change,
            "change_percent": self.change_percent,
        }


@dataclass(frozen=True)
class RealtimeBar:
    """Current or finalized realtime OHLCV bar."""

    market: str
    symbol: str
    interval: str
    bucket_start: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    source: str
    is_final: bool = False

    def to_message_data(self) -> dict:
        return {
            "market": self.market,
            "symbol": self.symbol,
            "interval": self.interval,
            "bucket_start": self.bucket_start.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "source": self.source,
            "is_final": self.is_final,
        }
