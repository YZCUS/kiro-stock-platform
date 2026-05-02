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

The platform still treats local `market_data_bars` and `price_history` as the
canonical OHLCV source. Finnhub is only used for product metadata and fallback
market information:

- symbol search
- quote fallback
- company profile
- market and company news

Provider interfaces are intentionally split by responsibility:

- `IPriceDataSource`: historical OHLCV and bars for ingestion pipelines.
- `IQuoteDataSource`: near-real-time quote snapshots for interactive UI and
  alerts.
- `IMarketInfoProvider`: symbol search, company profile, and news metadata.

Finnhub currently implements `IQuoteDataSource` and `IMarketInfoProvider`.
Yahoo Finance remains the default `IPriceDataSource`.

Configure it with:

```env
FINNHUB_API_KEY=...
FINNHUB_BASE_URL=https://finnhub.io/api/v1
INTERNAL_API_TOKEN=...
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
