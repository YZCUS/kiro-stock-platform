/**
 * Runtime configuration shared by browser and server-side frontend code.
 */

export const DEFAULT_API_BASE_URL = 'http://localhost:8000';

export function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_BASE_URL;
}

export function getWebSocketUrl(): string {
  if (process.env.NEXT_PUBLIC_WS_URL) {
    return process.env.NEXT_PUBLIC_WS_URL;
  }

  return deriveWebSocketUrl(getApiBaseUrl());
}

export function getMarketWebSocketUrl(): string {
  if (process.env.NEXT_PUBLIC_MARKET_WS_URL) {
    return process.env.NEXT_PUBLIC_MARKET_WS_URL;
  }

  return deriveWebSocketUrl(getApiBaseUrl(), '/ws/market');
}

export function deriveWebSocketUrl(apiUrl: string, pathname = '/ws'): string {
  const baseUrl = typeof window !== 'undefined'
    ? window.location.origin
    : DEFAULT_API_BASE_URL;
  const parsedUrl = new URL(apiUrl, baseUrl);
  parsedUrl.protocol = parsedUrl.protocol === 'https:' ? 'wss:' : 'ws:';
  parsedUrl.pathname = pathname;
  parsedUrl.search = '';
  parsedUrl.hash = '';
  return parsedUrl.toString();
}
