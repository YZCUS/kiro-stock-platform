"""Daily OHLCV helpers backed by market_data_bars."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Iterable, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import Date, and_, asc, case, cast, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models.market_data_bar import MarketDataBar

GOOD_QUALITY_STATUSES = ("complete", "backfilled", "corrected")


@dataclass
class DailyPriceBar:
    """Compatibility shape for one daily OHLCV bar."""

    id: int
    stock_id: int
    date: date
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: int
    adjusted_close: Decimal
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def price_change(self) -> Optional[Decimal]:
        if self.close_price is not None and self.open_price is not None:
            return self.close_price - self.open_price
        return None

    @property
    def price_change_percent(self) -> Optional[Decimal]:
        if self.open_price and self.open_price != 0 and self.price_change is not None:
            return (self.price_change / self.open_price) * 100
        return None

    @property
    def daily_range(self) -> Optional[Decimal]:
        if self.high_price is not None and self.low_price is not None:
            return self.high_price - self.low_price
        return None

    def get_ohlc_data(self) -> Dict[str, Any]:
        return {
            "date": self.date.isoformat() if self.date else None,
            "open": float(self.open_price) if self.open_price else None,
            "high": float(self.high_price) if self.high_price else None,
            "low": float(self.low_price) if self.low_price else None,
            "close": float(self.close_price) if self.close_price else None,
            "volume": int(self.volume) if self.volume else None,
        }


def market_bar_date_expr() -> Any:
    """Return the market-local date expression for a stored daily bar."""
    return cast(
        case(
            (
                MarketDataBar.market == "TW",
                func.timezone("Asia/Taipei", MarketDataBar.timestamp),
            ),
            else_=func.timezone("America/New_York", MarketDataBar.timestamp),
        ),
        Date,
    )


def market_local_date(timestamp: datetime, market: str) -> date:
    timezone_name = "Asia/Taipei" if market == "TW" else "America/New_York"
    if timestamp.tzinfo is None:
        return timestamp.date()
    return timestamp.astimezone(ZoneInfo(timezone_name)).date()


def daily_price_from_bar(
    bar: MarketDataBar,
    bar_date: Optional[date] = None,
) -> DailyPriceBar:
    local_date = bar_date or market_local_date(bar.timestamp, bar.market)
    return DailyPriceBar(
        id=bar.id,
        stock_id=bar.stock_id,
        date=local_date,
        open_price=bar.open_price,
        high_price=bar.high_price,
        low_price=bar.low_price,
        close_price=bar.close_price,
        volume=bar.volume,
        adjusted_close=bar.close_price,
        created_at=getattr(bar, "created_at", None),
        updated_at=getattr(bar, "updated_at", None),
    )


def _daily_bar_preference_order():
    return (
        case((MarketDataBar.source_type == "source", 0), else_=1),
        case((MarketDataBar.quality_status.in_(GOOD_QUALITY_STATUSES), 0), else_=1),
        asc(MarketDataBar.is_adjusted),
        desc(MarketDataBar.updated_at),
        desc(MarketDataBar.id),
    )


def _ranked_daily_bars_subquery(filters: list[Any]):
    bar_date = market_bar_date_expr().label("bar_date")
    daily_rank = (
        func.row_number()
        .over(
            partition_by=(MarketDataBar.stock_id, bar_date),
            order_by=_daily_bar_preference_order(),
        )
        .label("daily_rank")
    )
    return (
        select(
            MarketDataBar.id.label("bar_id"),
            MarketDataBar.stock_id.label("stock_id"),
            bar_date,
            daily_rank,
        )
        .where(and_(*filters))
        .subquery()
    )


def _daily_filters(
    stock_id: Optional[int] = None,
    stock_ids: Optional[Iterable[int]] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> list[Any]:
    bar_date = market_bar_date_expr()
    filters = [
        MarketDataBar.timeframe == "1d",
        MarketDataBar.close_price.is_not(None),
    ]
    if stock_id is not None:
        filters.append(MarketDataBar.stock_id == stock_id)
    if stock_ids is not None:
        ids = list(stock_ids)
        filters.append(MarketDataBar.stock_id.in_(ids if ids else [-1]))
    if start_date is not None:
        filters.append(bar_date >= start_date)
    if end_date is not None:
        filters.append(bar_date <= end_date)
    return filters


async def fetch_daily_prices(
    db: AsyncSession,
    stock_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 1000,
    ascending: bool = False,
) -> list[DailyPriceBar]:
    ranked = _ranked_daily_bars_subquery(
        _daily_filters(
            stock_id=stock_id,
            start_date=start_date,
            end_date=end_date,
        )
    )
    order_by = asc(ranked.c.bar_date) if ascending else desc(ranked.c.bar_date)
    result = await db.execute(
        select(MarketDataBar, ranked.c.bar_date)
        .join(ranked, MarketDataBar.id == ranked.c.bar_id)
        .where(ranked.c.daily_rank == 1)
        .order_by(order_by)
        .limit(limit)
    )
    return [daily_price_from_bar(bar, bar_date) for bar, bar_date in result.all()]


async def fetch_latest_daily_price(
    db: AsyncSession,
    stock_id: int,
) -> Optional[DailyPriceBar]:
    prices = await fetch_daily_prices(db, stock_id=stock_id, limit=1)
    return prices[0] if prices else None


async def fetch_latest_daily_price_rows_by_stock(
    db: AsyncSession,
    stock_ids: Iterable[int],
    rows_per_stock: int = 2,
) -> dict[int, list[dict[str, Any]]]:
    ids = list(stock_ids)
    if not ids:
        return {}

    ranked = _ranked_daily_bars_subquery(_daily_filters(stock_ids=ids))
    price_rank = (
        func.row_number()
        .over(
            partition_by=ranked.c.stock_id,
            order_by=desc(ranked.c.bar_date),
        )
        .label("price_rank")
    )
    deduped = (
        select(
            ranked.c.bar_id,
            ranked.c.stock_id,
            ranked.c.bar_date,
            price_rank,
        )
        .where(ranked.c.daily_rank == 1)
        .subquery()
    )
    result = await db.execute(
        select(
            MarketDataBar.stock_id.label("stock_id"),
            deduped.c.bar_date.label("date"),
            MarketDataBar.close_price.label("close_price"),
            MarketDataBar.volume.label("volume"),
            MarketDataBar.updated_at.label("updated_at"),
            deduped.c.price_rank,
        )
        .join(deduped, MarketDataBar.id == deduped.c.bar_id)
        .where(deduped.c.price_rank <= rows_per_stock)
        .order_by(MarketDataBar.stock_id, desc(deduped.c.bar_date))
    )

    prices_by_stock: dict[int, list[dict[str, Any]]] = {}
    for row in result.mappings().all():
        prices_by_stock.setdefault(row["stock_id"], []).append(dict(row))
    return prices_by_stock
