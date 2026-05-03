# Market Data Pipeline

This project now keeps strategy-facing OHLCV data in `market_data_bars`.
The old `price_history` table and compatibility view have been dropped. All
daily OHLCV reads and writes should use `market_data_bars`.

## Timeframes

Source timeframes:

- `1d`: daily bars fetched from the configured price provider.
- `5m`: intraday bars fetched from the configured price provider or finalized
  by the market stream service from realtime trades.

Derived timeframes:

- `15m`, `30m`, `1h`: aggregated from `5m`.
- `1w`: aggregated from `1d`.

Each bar is uniquely identified by `stock_id`, `timeframe`, `timestamp`,
`source`, and `is_adjusted`, so reruns upsert instead of duplicating rows.

## API Workflow

Run the full synchronous pipeline for active TW stocks:

```bash
curl -X POST http://localhost:8000/api/v1/stocks/market-data/orchestrate \
  -H 'Content-Type: application/json' \
  -d '{"market":"TW","days":7,"limit":100}'
```

Queue one ordered pipeline command per stock:

```bash
curl -X POST http://localhost:8000/api/v1/stocks/market-data/orchestrate \
  -H 'Content-Type: application/json' \
  -d '{"stock_ids":[1],"days":7,"enqueue":true}'
```

Check completeness for one window:

```bash
curl 'http://localhost:8000/api/v1/stocks/market-data/completeness?stock_id=1&timeframe=1d&start_at=2026-04-24T00:00:00%2B08:00&end_at=2026-05-01T00:00:00%2B08:00'
```

## Worker Workflow

Redis Streams are used for durable background work:

- `market_data_tasks`: ordered source collect -> aggregate -> validate pipeline
  commands, or source-only collect commands.
- `bar_aggregation_tasks`: manual derived-bar aggregation tasks.
- `data_validation_tasks`: manual completeness validation tasks.

Start workers locally:

```bash
docker compose --profile workers up market-data-worker bar-aggregation-worker data-validation-worker
```

Airflow calls the synchronous `orchestrate` endpoint after daily source
collection. For production, switch the Airflow task to enqueue mode only when
workers are always running and monitored.

## Realtime 5-Minute Bars

The market stream service can build current 5-minute candles from Finnhub trade
events. In-progress candles are cache state only. Finalized 5-minute candles are
upserted to `market_data_bars` with source `finnhub_stream` or `mock_stream`.

REST remains responsible for initial chart history. The frontend can request:

```text
GET /api/v1/stocks/{stock_id}/prices?timeframe=1d
GET /api/v1/stocks/{stock_id}/prices?timeframe=5m
```

The realtime chart defaults to `1d` and lets users switch to `5m`. When `5m`
history is unavailable, the UI explicitly falls back to daily bars instead of
showing an empty chart.

## Completeness Rules

Validation compares actual bars to expected timestamps for the market calendar.
The first version uses weekday trading days with regular sessions:

- TW: `Asia/Taipei`, 09:00-13:30.
- US: `America/New_York`, 09:30-16:00.

Reports include expected count, actual count, missing timestamps, duplicate
count, invalid OHLCV count, partial bars, partial timestamps, first/last
timestamp, and completeness percentage. Holiday and half-day calendars should be
added before production use.

## Missing Bar Policy

Missing lower-timeframe bars are not interpolated. The pipeline follows this
order:

1. Fetch source `1d` and `5m` bars from the provider.
2. Aggregate derived bars from source data.
3. Mark derived buckets as `partial` when their source bars are incomplete.
4. For incomplete derived timeframes, directly fetch the affected `15m`, `30m`,
   `1h`, or `1w` bars from the provider.
5. Replace only the affected derived timestamps with provider bars marked
   `quality_status = backfilled`.

This does not fill the missing `5m` bar. It only makes the higher timeframe
usable for strategies that operate on that timeframe. Strategies should use only
`complete`, `backfilled`, or `corrected` bars and exclude `partial` or `missing`
bars. Linear interpolation and backward-looking fills are intentionally not used
for trading data.
