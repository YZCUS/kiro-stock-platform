/**
 * 股票分析平台 - TypeScript 類型定義
 */

// 基礎類型
export interface Stock {
  id: number;
  symbol: string;
  market: string;
  name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PriceData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  adjusted_close?: number;
}

export interface TechnicalIndicator {
  date: string;
  value: number;
  parameters?: Record<string, any>;
}

export interface TradingSignal {
  id: number;
  stock_id: number;
  symbol: string;
  market: string;
  signal_type: 'BUY' | 'SELL' | 'HOLD' | 'GOLDEN_CROSS' | 'DEATH_CROSS';
  strength: 'WEAK' | 'MODERATE' | 'STRONG';
  price: number;
  confidence: number;
  date: string;
  description: string;
  indicators: Record<string, any>;
  created_at: string;
}

// API 響應類型
export interface ApiResponse<T> {
  data?: T;
  message?: string;
  success?: boolean;
  error?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    pageSize: number;
    total: number;
    totalPages: number;
  };
}

// WebSocket 消息類型
export interface WebSocketMessage {
  type: 'welcome' | 'initial_data' | 'price_update' | 'indicator_update' | 'signal_update' | 'market_status' | 'stock_update' | 'market_update' | 'system_notification' | 'error' | 'pong';
  data?: any;
  message?: string;
  timestamp?: string;
}

export interface WebSocketSubscription {
  type: 'subscribe_stock' | 'unsubscribe_stock' | 'subscribe_global' | 'unsubscribe_global' | 'ping';
  data?: {
    stock_id?: number;
    symbol?: string;
  };
}

// 表單類型
export interface StockCreateForm {
  symbol: string;
  market: 'TW' | 'US';
  name?: string;
}

export interface StockBatchCreateForm {
  stocks: StockCreateForm[];
}

// UI 狀態類型
export interface LoadingState {
  isLoading: boolean;
  error?: string;
}

export interface NotificationState {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  timestamp: number;
  autoClose?: boolean;
}

// 篩選和搜尋類型
export interface StockFilter {
  market?: string;
  active_only?: boolean;
  search?: string;
}

export interface SignalFilter {
  signal_type?: string;
  market?: string;
  min_confidence?: number;
  start_date?: string;
  end_date?: string;
}

export interface DateRange {
  start: Date;
  end: Date;
}

// 市場狀態類型
export interface MarketStatus {
  market: 'TW' | 'US';
  is_open: boolean;
  next_open?: string;
  next_close?: string;
}

// Toast 消息類型
export interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message?: string;
  duration?: number;
}

// 即時價格數據類型
export interface RealtimePriceData {
  price: number;
  change: number;
  change_percent: number;
  volume: number;
  timestamp: string;
  ohlc?: {
    open: number;
    high: number;
    low: number;
    close: number;
  };
}

// 技術指標數據類型
export interface IndicatorValue {
  date: string;
  value: number;
}

export interface IndicatorData {
  type: string;
  data: IndicatorValue[];
  last_update?: string;
}

export interface IndicatorsResponse {
  SMA?: IndicatorData;
  EMA?: IndicatorData;
  RSI?: IndicatorData;
  MACD?: {
    type: string;
    data: {
      macd: IndicatorValue[];
      signal: IndicatorValue[];
      histogram: IndicatorValue[];
    };
    last_update?: string;
  };
  bollinger?: {
    type: string;
    data: {
      upper: IndicatorValue[];
      middle: IndicatorValue[];
      lower: IndicatorValue[];
    };
    last_update?: string;
  };
  kd?: {
    type: string;
    data: {
      k: IndicatorValue[];
      d: IndicatorValue[];
    };
    last_update?: string;
  };
}