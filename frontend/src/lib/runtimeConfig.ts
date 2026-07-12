/**
 * Runtime configuration shared by browser and server-side frontend code.
 */

export const DEFAULT_API_BASE_URL = 'http://localhost:8000';
const SAME_ORIGIN_URL = 'same-origin';

export function getApiBaseUrl(): string {
  const configuredApiUrl = process.env.NEXT_PUBLIC_API_URL;

  if (configuredApiUrl === SAME_ORIGIN_URL) {
    if (typeof window !== 'undefined') {
      return window.location.origin;
    }

    return process.env.INTERNAL_API_BASE_URL || DEFAULT_API_BASE_URL;
  }

  return configuredApiUrl || DEFAULT_API_BASE_URL;
}

export function getWebSocketUrl(): string {
  const configuredWebSocketUrl = process.env.NEXT_PUBLIC_WS_URL;
  if (configuredWebSocketUrl && configuredWebSocketUrl !== SAME_ORIGIN_URL) {
    return configuredWebSocketUrl;
  }

  return deriveWebSocketUrl(getWebSocketBaseUrl(configuredWebSocketUrl));
}

export function getMarketWebSocketUrl(): string {
  const configuredWebSocketUrl = process.env.NEXT_PUBLIC_MARKET_WS_URL;
  if (configuredWebSocketUrl && configuredWebSocketUrl !== SAME_ORIGIN_URL) {
    return configuredWebSocketUrl;
  }

  return deriveWebSocketUrl(
    getWebSocketBaseUrl(configuredWebSocketUrl),
    '/ws/market'
  );
}

function getWebSocketBaseUrl(configuredWebSocketUrl?: string): string {
  if (configuredWebSocketUrl === SAME_ORIGIN_URL && typeof window !== 'undefined') {
    return window.location.origin;
  }
  return getApiBaseUrl();
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
