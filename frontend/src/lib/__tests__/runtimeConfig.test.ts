import {
  getMarketWebSocketUrl,
  getWebSocketUrl,
} from '../runtimeConfig';

describe('runtime WebSocket configuration', () => {
  const originalWebSocketUrl = process.env.NEXT_PUBLIC_WS_URL;
  const originalMarketWebSocketUrl = process.env.NEXT_PUBLIC_MARKET_WS_URL;

  afterEach(() => {
    if (originalWebSocketUrl === undefined) {
      delete process.env.NEXT_PUBLIC_WS_URL;
    } else {
      process.env.NEXT_PUBLIC_WS_URL = originalWebSocketUrl;
    }
    if (originalMarketWebSocketUrl === undefined) {
      delete process.env.NEXT_PUBLIC_MARKET_WS_URL;
    } else {
      process.env.NEXT_PUBLIC_MARKET_WS_URL = originalMarketWebSocketUrl;
    }
  });

  it('derives production WebSocket paths from the browser origin', () => {
    process.env.NEXT_PUBLIC_WS_URL = 'same-origin';
    process.env.NEXT_PUBLIC_MARKET_WS_URL = 'same-origin';

    expect(getWebSocketUrl()).toBe('ws://localhost/ws');
    expect(getMarketWebSocketUrl()).toBe('ws://localhost/ws/market');
  });

  it('preserves explicit development WebSocket URLs', () => {
    process.env.NEXT_PUBLIC_WS_URL = 'ws://localhost:8000/ws';
    process.env.NEXT_PUBLIC_MARKET_WS_URL = 'ws://localhost:8000/ws/market';

    expect(getWebSocketUrl()).toBe('ws://localhost:8000/ws');
    expect(getMarketWebSocketUrl()).toBe('ws://localhost:8000/ws/market');
  });
});
