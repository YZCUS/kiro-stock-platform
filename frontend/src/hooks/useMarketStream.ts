import { useEffect, useRef, useState } from 'react';
import { getMarketWebSocketUrl } from '../lib/runtimeConfig';

export interface MarketQuoteUpdate {
  market: string;
  symbol: string;
  price: number;
  volume?: number;
  timestamp: string;
  source?: string;
  change?: number | null;
  change_percent?: number | null;
}

export interface MarketBarUpdate {
  market: string;
  symbol: string;
  interval: '5m';
  bucket_start: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  source?: string;
  is_final?: boolean;
}

export interface MarketSignalUpdate {
  id: number;
  stock_id: number;
  stock_symbol?: string | null;
  stock_name?: string | null;
  strategy_type: string;
  strategy_name?: string;
  signal_horizon?: string;
  direction: 'LONG' | 'SHORT' | 'NEUTRAL';
  confidence: number;
  entry_zone?: {
    min: number;
    max: number;
  };
  entry_min?: number;
  entry_max?: number;
  stop_loss: number;
  take_profit?: number[];
  take_profit_targets?: number[];
  status: 'active' | 'expired' | 'triggered' | 'cancelled';
  signal_date: string;
  valid_until?: string | null;
  reason?: string | null;
  extra_data?: Record<string, unknown>;
  is_valid?: boolean;
  created_at: string;
}

type MarketStreamStatus = 'idle' | 'connecting' | 'connected' | 'disconnected' | 'error';

interface UseMarketStreamResult {
  quote: MarketQuoteUpdate | null;
  bar: MarketBarUpdate | null;
  signal: MarketSignalUpdate | null;
  status: MarketStreamStatus;
  error: string | null;
}

interface MarketStreamMessage {
  type?: string;
  market?: string;
  symbol?: string;
  interval?: string;
  data?: unknown;
  message?: string;
}

export function useMarketStream(
  market: string | null | undefined,
  symbol: string | null | undefined,
  enabled = true
): UseMarketStreamResult {
  const [quote, setQuote] = useState<MarketQuoteUpdate | null>(null);
  const [bar, setBar] = useState<MarketBarUpdate | null>(null);
  const [signal, setSignal] = useState<MarketSignalUpdate | null>(null);
  const [status, setStatus] = useState<MarketStreamStatus>('idle');
  const [error, setError] = useState<string | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const closeRequestedRef = useRef(false);

  useEffect(() => {
    if (!enabled || !market || !symbol || typeof window === 'undefined') {
      setStatus('idle');
      setQuote(null);
      setBar(null);
      setSignal(null);
      return;
    }

    const normalizedMarket = market.toUpperCase();
    const normalizedSymbol = symbol.toUpperCase();
    let websocket: WebSocket | null = null;
    let reconnectAttempt = 0;
    closeRequestedRef.current = false;
    setQuote(null);
    setBar(null);
    setSignal(null);

    const clearReconnectTimer = () => {
      if (reconnectTimerRef.current !== null) {
        window.clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    };

    const subscribe = () => {
      websocket?.send(JSON.stringify({
        type: 'subscribe_symbol',
        market: normalizedMarket,
        symbol: normalizedSymbol,
        intervals: ['quote', '5m'],
      }));
    };

    const connect = () => {
      clearReconnectTimer();
      setStatus('connecting');
      setError(null);

      websocket = new WebSocket(getMarketWebSocketUrl());
      websocket.onopen = () => {
        reconnectAttempt = 0;
        setStatus('connected');
        subscribe();
      };

      websocket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as MarketStreamMessage;
          if (message.type === 'quote_update' && isQuoteUpdate(message.data)) {
            setQuote(message.data);
          }
          if (message.type === 'bar_update' && isBarUpdate(message.data)) {
            setBar(message.data);
          }
          if (message.type === 'signal_update' && isSignalUpdate(message.data)) {
            setSignal(message.data);
          }
          if (message.type === 'error') {
            setError(message.message || 'Market stream error');
          }
        } catch {
          setError('Market stream message parse failed');
        }
      };

      websocket.onerror = () => {
        setStatus('error');
        setError('Market stream connection failed');
      };

      websocket.onclose = () => {
        websocket = null;
        if (closeRequestedRef.current) {
          setStatus('disconnected');
          return;
        }
        setStatus('disconnected');
        reconnectAttempt += 1;
        const delay = Math.min(1000 * reconnectAttempt, 10000);
        reconnectTimerRef.current = window.setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      closeRequestedRef.current = true;
      clearReconnectTimer();
      if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.send(JSON.stringify({
          type: 'unsubscribe_symbol',
          market: normalizedMarket,
          symbol: normalizedSymbol,
        }));
      }
      websocket?.close();
    };
  }, [enabled, market, symbol]);

  return { quote, bar, signal, status, error };
}

function isQuoteUpdate(value: unknown): value is MarketQuoteUpdate {
  if (!value || typeof value !== 'object') return false;
  const quote = value as Record<string, unknown>;
  return (
    typeof quote.market === 'string' &&
    typeof quote.symbol === 'string' &&
    typeof quote.price === 'number' &&
    typeof quote.timestamp === 'string'
  );
}

function isBarUpdate(value: unknown): value is MarketBarUpdate {
  if (!value || typeof value !== 'object') return false;
  const bar = value as Record<string, unknown>;
  return (
    typeof bar.market === 'string' &&
    typeof bar.symbol === 'string' &&
    bar.interval === '5m' &&
    typeof bar.bucket_start === 'string' &&
    typeof bar.open === 'number' &&
    typeof bar.high === 'number' &&
    typeof bar.low === 'number' &&
    typeof bar.close === 'number' &&
    typeof bar.volume === 'number'
  );
}

function isSignalUpdate(value: unknown): value is MarketSignalUpdate {
  if (!value || typeof value !== 'object') return false;
  const signal = value as Record<string, unknown>;
  return (
    typeof signal.id === 'number' &&
    typeof signal.strategy_type === 'string' &&
    typeof signal.direction === 'string' &&
    typeof signal.confidence === 'number' &&
    typeof signal.stop_loss === 'number' &&
    typeof signal.signal_date === 'string' &&
    typeof signal.created_at === 'string'
  );
}
