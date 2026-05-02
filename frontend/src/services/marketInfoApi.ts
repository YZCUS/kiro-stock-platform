import { ApiService, API_ENDPOINTS } from '@/lib/api';

const marketInfoInFlight = new Map<string, Promise<unknown>>();

const dedupeInFlight = <T>(
  key: string,
  requestFactory: () => Promise<T>
): Promise<T> => {
  const existingRequest = marketInfoInFlight.get(key);
  if (existingRequest) {
    return existingRequest as Promise<T>;
  }

  const request = requestFactory().finally(() => {
    marketInfoInFlight.delete(key);
  });
  marketInfoInFlight.set(key, request);
  return request;
};

export interface MarketSearchResult {
  symbol: string;
  market: string;
  name?: string | null;
  exchange?: string | null;
  type?: string | null;
  provider: string;
  stock_id?: number | null;
  is_local: boolean;
  tradingview_symbol?: string | null;
}

export interface NewsArticle {
  id?: string | null;
  symbol?: string | null;
  headline: string;
  summary?: string | null;
  source?: string | null;
  url?: string | null;
  image?: string | null;
  published_at?: string | null;
  provider: string;
}

export interface StockProfile {
  symbol: string;
  market: string;
  name?: string | null;
  exchange?: string | null;
  currency?: string | null;
  logo?: string | null;
  market_cap?: number | null;
  provider: string;
  stock_id?: number | null;
  tradingview_symbol?: string | null;
}

export interface MarketQuote {
  symbol: string;
  market: string;
  price?: number | null;
  change?: number | null;
  change_percent?: number | null;
  timestamp?: string | null;
  source: string;
  is_realtime: boolean;
}

export async function searchMarketSymbols(params: {
  q: string;
  market?: string;
  include_external?: boolean;
  limit?: number;
}): Promise<MarketSearchResult[]> {
  return ApiService.get(API_ENDPOINTS.MARKET.SEARCH, params);
}

export async function getStockProfile(
  market: string,
  symbol: string
): Promise<StockProfile> {
  return ApiService.get(API_ENDPOINTS.MARKET.PROFILE(market, symbol));
}

export async function getStockQuote(
  market: string,
  symbol: string,
  stockId?: number,
  preferRealtime = false
): Promise<MarketQuote> {
  const key = `quote:${market}:${symbol}:${stockId ?? ''}:${preferRealtime}`;
  return dedupeInFlight(key, () =>
    ApiService.get(API_ENDPOINTS.MARKET.QUOTE(market, symbol), {
      stock_id: stockId,
      prefer_realtime: preferRealtime,
    })
  );
}

export async function getMarketNews(limit = 8): Promise<NewsArticle[]> {
  return dedupeInFlight(`market-news:${limit}`, () =>
    ApiService.get(API_ENDPOINTS.MARKET.NEWS, { limit })
  );
}

export async function getStockNews(
  market: string,
  symbol: string,
  limit = 8
): Promise<NewsArticle[]> {
  return dedupeInFlight(`stock-news:${market}:${symbol}:${limit}`, () =>
    ApiService.get(API_ENDPOINTS.MARKET.STOCK_NEWS(market, symbol), {
      limit,
    })
  );
}

export async function getWatchlistNews(limit = 8): Promise<{
  symbols: string[];
  articles: NewsArticle[];
}> {
  return ApiService.get(API_ENDPOINTS.MARKET.WATCHLIST_NEWS, { limit });
}
