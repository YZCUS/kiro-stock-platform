#!/usr/bin/env python3
"""Backfill current S&P 500 daily OHLCV bars into market_data_bars."""

from __future__ import annotations

import argparse
import asyncio
import logging
import re
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import yfinance as yf
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from core.database import AsyncSessionLocal  # noqa: E402
from domain.models.market_data_bar import MarketDataBar  # noqa: E402
from domain.models.stock import Stock  # noqa: E402


SOURCE_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
SOURCE_NAME = "yahoo_finance"
MARKET = "US"
MARKET_TZ = ZoneInfo("America/New_York")

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SP500Constituent:
    source_symbol: str
    yahoo_symbol: str
    security: str
    sector: str | None = None
    sub_industry: str | None = None


class WikiTableParser(HTMLParser):
    """Small HTML table parser to avoid requiring lxml in the backend image."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._table_depth = 0
        self._current_table: list[list[str]] | None = None
        self._current_row: list[str] | None = None
        self._current_cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            if self._table_depth == 0:
                self._current_table = []
            self._table_depth += 1
            return

        if self._table_depth != 1:
            return

        if tag == "tr":
            self._current_row = []
        elif tag in {"td", "th"} and self._current_row is not None:
            self._current_cell = []
        elif tag == "br" and self._current_cell is not None:
            self._current_cell.append(" ")

    def handle_data(self, data: str) -> None:
        if self._current_cell is not None:
            self._current_cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._current_cell is not None:
            if self._current_row is not None:
                self._current_row.append(clean_cell_text("".join(self._current_cell)))
            self._current_cell = None
            return

        if tag == "tr" and self._table_depth == 1:
            if self._current_table is not None and self._current_row:
                self._current_table.append(self._current_row)
            self._current_row = None
            return

        if tag == "table" and self._table_depth > 0:
            self._table_depth -= 1
            if self._table_depth == 0 and self._current_table is not None:
                self.tables.append(self._current_table)
                self._current_table = None


def clean_cell_text(value: str) -> str:
    value = re.sub(r"\[[^\]]+\]", "", value)
    return re.sub(r"\s+", " ", value).strip()


def normalize_yahoo_symbol(symbol: str) -> str:
    return clean_cell_text(symbol).upper().replace(".", "-")


def fetch_sp500_constituents(source_url: str) -> list[SP500Constituent]:
    response = requests.get(
        source_url,
        timeout=30,
        headers={
            "User-Agent": "kiro-stock-platform/1.0 (+https://local.dev)",
        },
    )
    response.raise_for_status()

    parser = WikiTableParser()
    parser.feed(response.text)

    for table in parser.tables:
        if not table:
            continue

        header = [cell.lower() for cell in table[0]]
        if "symbol" not in header or "security" not in header:
            continue

        symbol_idx = header.index("symbol")
        security_idx = header.index("security")
        sector_idx = header.index("gics sector") if "gics sector" in header else None
        sub_idx = (
            header.index("gics sub-industry")
            if "gics sub-industry" in header
            else None
        )

        constituents: list[SP500Constituent] = []
        for row in table[1:]:
            if len(row) <= max(symbol_idx, security_idx):
                continue

            source_symbol = clean_cell_text(row[symbol_idx]).upper()
            if not source_symbol:
                continue

            security = clean_cell_text(row[security_idx])[:100] or source_symbol
            sector = (
                clean_cell_text(row[sector_idx])
                if sector_idx is not None and len(row) > sector_idx
                else None
            )
            sub_industry = (
                clean_cell_text(row[sub_idx])
                if sub_idx is not None and len(row) > sub_idx
                else None
            )
            constituents.append(
                SP500Constituent(
                    source_symbol=source_symbol,
                    yahoo_symbol=normalize_yahoo_symbol(source_symbol),
                    security=security,
                    sector=sector,
                    sub_industry=sub_industry,
                )
            )

        if constituents:
            return constituents

    raise RuntimeError("Could not find S&P 500 constituent table in source HTML")


def subtract_years(value: date, years: int) -> date:
    try:
        return value.replace(year=value.year - years)
    except ValueError:
        return value.replace(year=value.year - years, month=2, day=28)


def chunked(values: list[str], chunk_size: int) -> Iterable[list[str]]:
    for start in range(0, len(values), chunk_size):
        yield values[start : start + chunk_size]


async def upsert_stocks(
    constituents: list[SP500Constituent],
) -> dict[str, int]:
    if AsyncSessionLocal is None:
        raise RuntimeError("Database session factory is unavailable")

    rows = [
        {
            "symbol": constituent.yahoo_symbol,
            "market": MARKET,
            "name": constituent.security,
            "is_active": True,
        }
        for constituent in constituents
    ]

    async with AsyncSessionLocal() as db:
        stmt = insert(Stock).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "market"],
            set_={
                "name": stmt.excluded.name,
                "is_active": True,
                "updated_at": func.now(),
            },
        )
        await db.execute(stmt)
        await db.commit()

        result = await db.execute(
            select(Stock.id, Stock.symbol).where(
                Stock.market == MARKET,
                Stock.symbol.in_([row["symbol"] for row in rows]),
            )
        )
        return {symbol: stock_id for stock_id, symbol in result.all()}


async def verify_db_coverage(symbols: list[str]) -> None:
    if AsyncSessionLocal is None:
        raise RuntimeError("Database session factory is unavailable")

    async with AsyncSessionLocal() as db:
        stock_result = await db.execute(
            select(Stock.id, Stock.symbol).where(
                Stock.market == MARKET,
                Stock.symbol.in_(symbols),
            )
        )
        stock_rows = stock_result.all()
        stock_ids_by_symbol = {symbol: stock_id for stock_id, symbol in stock_rows}
        symbols_by_stock_id = {stock_id: symbol for symbol, stock_id in stock_ids_by_symbol.items()}

        if not stock_ids_by_symbol:
            logger.info("Verification: no requested symbols exist in stocks")
            return

        bar_result = await db.execute(
            select(
                MarketDataBar.stock_id,
                func.count(MarketDataBar.id),
                func.min(MarketDataBar.timestamp),
                func.max(MarketDataBar.timestamp),
            )
            .where(
                MarketDataBar.stock_id.in_(stock_ids_by_symbol.values()),
                MarketDataBar.market == MARKET,
                MarketDataBar.timeframe == "1d",
                MarketDataBar.source == SOURCE_NAME,
            )
            .group_by(MarketDataBar.stock_id)
        )
        bar_rows = bar_result.all()

    counts_by_symbol = {
        symbols_by_stock_id[stock_id]: int(count)
        for stock_id, count, _min_ts, _max_ts in bar_rows
    }
    counts = sorted(counts_by_symbol.values())
    missing_stocks = sorted(set(symbols) - set(stock_ids_by_symbol))
    no_bars = sorted(set(symbols) - set(counts_by_symbol))
    min_ts = min((row[2] for row in bar_rows), default=None)
    max_ts = max((row[3] for row in bar_rows), default=None)
    median_count = counts[len(counts) // 2] if counts else 0

    logger.info(
        "Verification: symbols=%s stocks_in_db=%s stocks_with_bars=%s rows=%s",
        len(symbols),
        len(stock_ids_by_symbol),
        len(counts_by_symbol),
        sum(counts),
    )
    logger.info(
        "Verification: min_ts=%s max_ts=%s per_stock_min=%s median=%s max=%s",
        min_ts,
        max_ts,
        counts[0] if counts else 0,
        median_count,
        counts[-1] if counts else 0,
    )
    if missing_stocks:
        logger.warning("Verification: missing stocks: %s", ", ".join(missing_stocks))
    if no_bars:
        logger.warning("Verification: stocks without bars: %s", ", ".join(no_bars))


def download_daily_bars(
    symbols: list[str],
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    return yf.download(
        tickers=" ".join(symbols),
        start=start_date.isoformat(),
        end=(end_date + timedelta(days=1)).isoformat(),
        interval="1d",
        group_by="ticker",
        auto_adjust=False,
        actions=False,
        progress=False,
        threads=True,
    )


def dataframe_for_symbol(downloaded: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if downloaded.empty:
        return pd.DataFrame()

    if isinstance(downloaded.columns, pd.MultiIndex):
        if symbol in downloaded.columns.get_level_values(0):
            return downloaded[symbol]
        if symbol in downloaded.columns.get_level_values(1):
            return downloaded.xs(symbol, axis=1, level=1)
        return pd.DataFrame()

    return downloaded


def to_decimal(value: object) -> Decimal | None:
    if value is None or pd.isna(value):
        return None
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if decimal <= 0:
        return None
    return decimal


def build_bar_records(
    downloaded: pd.DataFrame,
    symbols: list[str],
    stock_ids_by_symbol: dict[str, int],
) -> tuple[list[dict], dict[str, str]]:
    records: list[dict] = []
    failures: dict[str, str] = {}

    for symbol in symbols:
        stock_id = stock_ids_by_symbol.get(symbol)
        if stock_id is None:
            failures[symbol] = "stock id missing"
            continue

        frame = dataframe_for_symbol(downloaded, symbol)
        if frame.empty:
            failures[symbol] = "no downloaded rows"
            continue

        valid_count = 0
        for index, row in frame.iterrows():
            open_price = to_decimal(row.get("Open"))
            high_price = to_decimal(row.get("High"))
            low_price = to_decimal(row.get("Low"))
            close_price = to_decimal(row.get("Close"))
            if not all([open_price, high_price, low_price, close_price]):
                continue

            high_price = max(high_price, open_price, low_price, close_price)
            low_price = min(low_price, open_price, high_price, close_price)
            volume = row.get("Volume")
            timestamp = (
                index.to_pydatetime() if hasattr(index, "to_pydatetime") else index
            )
            if timestamp.tzinfo is not None:
                timestamp = timestamp.astimezone(MARKET_TZ)
            timestamp = datetime.combine(
                timestamp.date(),
                datetime.min.time(),
                tzinfo=MARKET_TZ,
            )

            records.append(
                {
                    "stock_id": stock_id,
                    "symbol": symbol,
                    "market": MARKET,
                    "timeframe": "1d",
                    "timestamp": timestamp,
                    "open_price": open_price,
                    "high_price": high_price,
                    "low_price": low_price,
                    "close_price": close_price,
                    "volume": int(volume or 0) if not pd.isna(volume) else 0,
                    "source": SOURCE_NAME,
                    "source_type": "source",
                    "is_adjusted": False,
                    "generated_from_timeframe": None,
                    "quality_status": "complete",
                }
            )
            valid_count += 1

        if valid_count == 0:
            failures[symbol] = "no valid OHLCV rows"

    return records, failures


async def upsert_bars(records: list[dict], insert_batch_size: int) -> int:
    if not records:
        return 0
    if AsyncSessionLocal is None:
        raise RuntimeError("Database session factory is unavailable")

    written = 0
    async with AsyncSessionLocal() as db:
        for batch in chunked_records(records, insert_batch_size):
            stmt = insert(MarketDataBar).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=[
                    "stock_id",
                    "timeframe",
                    "timestamp",
                    "source",
                    "is_adjusted",
                ],
                set_={
                    "symbol": stmt.excluded.symbol,
                    "market": stmt.excluded.market,
                    "open_price": stmt.excluded.open_price,
                    "high_price": stmt.excluded.high_price,
                    "low_price": stmt.excluded.low_price,
                    "close_price": stmt.excluded.close_price,
                    "volume": stmt.excluded.volume,
                    "source_type": stmt.excluded.source_type,
                    "generated_from_timeframe": stmt.excluded.generated_from_timeframe,
                    "quality_status": stmt.excluded.quality_status,
                    "updated_at": func.now(),
                },
            )
            await db.execute(stmt)
            written += len(batch)
        await db.commit()
    return written


def chunked_records(values: list[dict], chunk_size: int) -> Iterable[list[dict]]:
    for start in range(0, len(values), chunk_size):
        yield values[start : start + chunk_size]


async def run_backfill(args: argparse.Namespace) -> None:
    end_date = (
        datetime.strptime(args.end_date, "%Y-%m-%d").date()
        if args.end_date
        else date.today()
    )
    start_date = (
        datetime.strptime(args.start_date, "%Y-%m-%d").date()
        if args.start_date
        else subtract_years(end_date, args.years)
    )

    constituents = fetch_sp500_constituents(args.source_url)
    if args.symbols:
        requested = {
            normalize_yahoo_symbol(symbol)
            for symbol in args.symbols.split(",")
        }
        constituents = [
            constituent
            for constituent in constituents
            if constituent.yahoo_symbol in requested
            or normalize_yahoo_symbol(constituent.source_symbol) in requested
        ]
    if args.max_symbols:
        constituents = constituents[: args.max_symbols]

    symbols = [constituent.yahoo_symbol for constituent in constituents]
    class_share_mappings = [
        f"{constituent.source_symbol}->{constituent.yahoo_symbol}"
        for constituent in constituents
        if constituent.source_symbol != constituent.yahoo_symbol
    ]
    logger.info(
        "Loaded %s S&P 500 symbols from %s (%s mapped for Yahoo)",
        len(symbols),
        args.source_url,
        len(class_share_mappings),
    )
    if class_share_mappings:
        logger.info("Class share mappings: %s", ", ".join(class_share_mappings))

    if args.verify_db:
        await verify_db_coverage(symbols)
        return

    if args.dry_run:
        logger.info("Dry run only; no database writes or Yahoo downloads")
        return

    stock_ids_by_symbol = await upsert_stocks(constituents)
    missing_stocks = sorted(set(symbols) - set(stock_ids_by_symbol))
    if missing_stocks:
        raise RuntimeError(f"Stocks missing after upsert: {', '.join(missing_stocks)}")

    total_written = 0
    failures: dict[str, str] = {}
    chunks = list(chunked(symbols, args.chunk_size))
    logger.info(
        "Backfilling %s symbols from %s through %s in %s chunks",
        len(symbols),
        start_date,
        end_date,
        len(chunks),
    )

    for index, symbols_chunk in enumerate(chunks, start=1):
        logger.info(
            "Downloading chunk %s/%s: %s",
            index,
            len(chunks),
            ", ".join(symbols_chunk[:5]) + ("..." if len(symbols_chunk) > 5 else ""),
        )
        downloaded = await asyncio.to_thread(
            download_daily_bars,
            symbols_chunk,
            start_date,
            end_date,
        )
        records, chunk_failures = build_bar_records(
            downloaded,
            symbols_chunk,
            stock_ids_by_symbol,
        )
        written = await upsert_bars(records, args.insert_batch_size)
        total_written += written
        failures.update(chunk_failures)
        logger.info(
            "Chunk %s/%s wrote %s rows (%s cumulative)",
            index,
            len(chunks),
            written,
            total_written,
        )
        if args.pause_seconds and index < len(chunks):
            time.sleep(args.pause_seconds)

    logger.info(
        "Completed S&P 500 backfill: symbols=%s rows_upserted=%s failures=%s",
        len(symbols),
        total_written,
        len(failures),
    )
    if failures:
        for symbol, reason in sorted(failures.items()):
            logger.warning("No data for %s: %s", symbol, reason)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill current S&P 500 daily bars into market_data_bars"
    )
    parser.add_argument("--source-url", default=SOURCE_URL)
    parser.add_argument("--years", type=int, default=3)
    parser.add_argument("--start-date", help="Inclusive YYYY-MM-DD start date")
    parser.add_argument("--end-date", help="Inclusive YYYY-MM-DD end date")
    parser.add_argument("--chunk-size", type=int, default=50)
    parser.add_argument("--insert-batch-size", type=int, default=1000)
    parser.add_argument("--pause-seconds", type=float, default=1.0)
    parser.add_argument("--symbols", help="Comma-separated Yahoo/source symbols")
    parser.add_argument("--max-symbols", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify-db", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    asyncio.run(run_backfill(args))


if __name__ == "__main__":
    main()
