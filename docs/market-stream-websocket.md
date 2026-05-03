# Market Stream WebSocket

## Purpose

The market stream layer supports intraday quote and 5-minute candle updates without making every browser poll REST endpoints. REST remains the source for initial historical data; WebSocket only carries incremental realtime updates.

## Runtime Flow

```text
Finnhub WebSocket or mock provider
  -> backend MarketStreamService
  -> Redis latest quote/current 5m bar cache
  -> /ws/market
  -> realtime chart UI
```

The frontend subscribes only when a realtime chart is mounted:

```json
{
  "type": "subscribe_symbol",
  "market": "US",
  "symbol": "AAPL",
  "intervals": ["quote", "5m"]
}
```

The service fanouts:

- `quote_update`: latest trade/quote snapshot.
- `bar_update`: current or finalized 5-minute candle.
- `signal_update`: observation-only intraday signal generated from 5-minute bars.

Finalized 5-minute candles are upserted into `market_data_bars` using `timeframe = "5m"`.

Historical chart data is still loaded through REST:

```text
GET /api/v1/stocks/{stock_id}/prices?timeframe=1d
GET /api/v1/stocks/{stock_id}/prices?timeframe=5m
```

The realtime chart defaults to daily bars because the current database is
guaranteed to have broad `1d` S&P 500 coverage, while `5m` history is still
incremental. Users can switch the chart between `日線` and `5分K`. If the user
selects `5分K` before 5-minute history exists for that symbol, the UI shows a
clear fallback message and displays daily candles instead of rendering a blank
chart.

## Design Rules

- Do not connect WebSocket globally from navigation.
- Do not expose Finnhub keys to the frontend.
- Do not write raw tick data to Postgres/Supabase.
- Store only finalized 5-minute bars in Postgres.
- Cache latest quote and current in-progress 5-minute bar in Redis, with memory fallback for local development.
- If `FINNHUB_API_KEY` is absent, backend uses `MockMarketStreamProvider`.

## Environment

```env
FINNHUB_API_KEY=
FINNHUB_BASE_URL=https://finnhub.io/api/v1
FINNHUB_WS_URL=wss://ws.finnhub.io
NEXT_PUBLIC_MARKET_WS_URL=ws://localhost:8000/ws/market
```

## Frontend Flow

1. Load historical bars through REST.
2. Open `/ws/market` only on the realtime chart page.
3. Subscribe to the selected symbol.
4. Apply `bar_update` to the last candle only while the chart is displaying
   `5分K`.
5. Keep daily charts on REST data; do not insert 5-minute streaming bars into a
   daily time axis.
6. Keep existing HTTP quote polling as a fallback path.

The navigation bar must not open market WebSocket connections. A connection is
created only by mounted realtime views through `useMarketStream`, and cleaned up
when the symbol/view changes.

## Current Scope

This implementation lays the stream foundation for 5-minute intraday analysis. It does not execute automated intraday orders.

The initial intraday signal runner emits observation-only signals:

- `intraday_ma_cross`: 5m 5MA / 20MA crossover.
- `intraday_volume_spike`: current 5m volume materially above the previous 20-bar average.

These signals are pushed through `signal_update` and displayed in the realtime signal panel. They are not persisted as strategy subscriptions yet; persistence should be added only after evaluation rules and alert UX are stable.

## Operational Notes

- `FINNHUB_API_KEY` enables the real Finnhub stream provider.
- Without a key, local development uses `MockMarketStreamProvider`.
- Latest quote and in-progress 5-minute bars are cache data, not permanent
  records.
- Only finalized 5-minute bars should be written to Postgres/Supabase.
- Intraday signals are currently observation-only and WebSocket-only.
