# OpenStock-inspired feature integration

This project borrows product patterns from OpenStock without copying its
AGPL-licensed implementation or changing the core platform architecture.

## Added surfaces

- Market info API:
  - `GET /api/v1/market/search`
  - `GET /api/v1/market/stocks/{market}/{symbol}/profile`
  - `GET /api/v1/market/stocks/{market}/{symbol}/quote`
  - `GET /api/v1/market/news`
  - `GET /api/v1/market/stocks/{market}/{symbol}/news`
  - `GET /api/v1/market/watchlist/news`
- Price alerts API:
  - `GET /api/v1/price-alerts/`
  - `POST /api/v1/price-alerts/`
  - `PATCH /api/v1/price-alerts/{id}`
  - `DELETE /api/v1/price-alerts/{id}`
  - `POST /api/v1/internal/price-alerts/check`
- Qlib data readiness:
  - `GET /api/v1/qlib/readiness`

## Data sources

The platform treats local `market_data_bars` as the canonical OHLCV source.
Finnhub is used for product metadata, quote snapshots, valuation metrics, news,
and the optional realtime stream path:

- symbol search
- quote fallback
- company profile
- valuation metrics
- market and company news
- realtime trade stream for 5-minute bar aggregation

Provider interfaces are intentionally split by responsibility:

- `IPriceDataSource`: historical OHLCV and bars for ingestion pipelines.
- `IQuoteDataSource`: near-real-time quote snapshots for interactive UI and
  alerts.
- `IMarketInfoProvider`: symbol search, company profile, and news metadata.
- `MarketStreamProvider`: WebSocket trade stream used by `/ws/market`.

Finnhub currently implements `IQuoteDataSource`, `IMarketInfoProvider`, and the
market stream provider. Yahoo Finance remains the default historical
`IPriceDataSource`.

Configure it with:

```env
FINNHUB_API_KEY=...
FINNHUB_BASE_URL=https://finnhub.io/api/v1
FINNHUB_WS_URL=wss://ws.finnhub.io
INTERNAL_API_TOKEN=...
NEXT_PUBLIC_MARKET_WS_URL=ws://localhost:8000/ws/market
```

## Qlib data readiness

`/api/v1/qlib/readiness` reports whether local daily OHLCV data is broad and
deep enough for meaningful Qlib ranking experiments. It checks active universe
size, daily bar coverage, median history length, and adjusted-row availability.

The Qlib prediction service export now includes:

- `adjusted_close`
- `factor`
- `is_adjusted`

Those fields preserve enough adjustment context for a production pyqlib data
converter, while the current service can continue to run the deterministic
bootstrap scorer.
