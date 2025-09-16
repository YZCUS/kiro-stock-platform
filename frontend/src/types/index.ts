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
  error?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface StockDataResponse {
  stock: Stock;
  price_data: PaginatedResponse<PriceData>;
  indicators?: Record<string, TechnicalIndicator[]>;
}

export interface SignalHistoryResponse {
  signals: TradingSignal[];
  pagination: {
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  };
  stats: Record<string, any>;
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
  };
}

// 圖表相關類型
export interface ChartData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

export interface IndicatorSeries {
  name: string;
  type: 'line' | 'histogram' | 'area';
  data: Array<{
    time: string;
    value: number;
  }>;
  color?: string;
}

export interface ChartConfig {
  symbol: string;
  timeRange: '1D' | '1W' | '1M' | '3M' | '6M' | '1Y' | 'ALL';
  indicators: string[];
  showVolume: boolean;
  showSignals: boolean;
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
  market: string;
  is_open: boolean;
  next_open?: string;
  next_close?: string;
  timezone: string;
}

// 統計數據類型
export interface MarketStats {
  total_stocks: number;
  active_stocks: number;
  total_signals: number;
  buy_signals: number;
  sell_signals: number;
  avg_confidence: number;
}

// 錯誤類型
export interface ApiError {
  status: number;
  message: string;
  details?: string;
}

// 用戶設定類型
export interface UserPreferences {
  theme: 'light' | 'dark';
  language: 'zh-TW' | 'en-US';
  defaultMarket: 'TW' | 'US';
  autoRefresh: boolean;
  refreshInterval: number;
  notifications: {
    signals: boolean;
    dataUpdates: boolean;
    errors: boolean;
  };
}

// Types are already exported via interface declarations above