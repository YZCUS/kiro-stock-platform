/**
 * 股票分析平台 - TypeScript 類型定義
 */

// 最新價格資訊
export interface LatestPriceInfo {
  close: number | null;
  change: number | null;
  change_percent: number | null;
  date: string | null;
  volume: number | null;
}

// 基礎類型
export interface Stock {
  id: number;
  symbol: string;
  market: string;
  name: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  latest_price?: LatestPriceInfo | null;
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

// 交易信號類型（與後端 SignalType 枚舉對應）
export type TradingSignalType =
  // 基本交易信號
  | 'BUY' | 'SELL' | 'HOLD'
  // 黃金交叉和死亡交叉
  | 'GOLDEN_CROSS' | 'DEATH_CROSS'
  | 'golden_cross' | 'death_cross'
  // RSI 信號
  | 'rsi_oversold' | 'rsi_overbought'
  // MACD 信號
  | 'macd_bullish' | 'macd_bearish'
  // 布林帶信號
  | 'bollinger_breakout' | 'bollinger_squeeze'
  | 'bb_squeeze' | 'bb_breakout'
  // KD 信號
  | 'kd_golden_cross' | 'kd_death_cross'
  // 成交量信號
  | 'volume_breakout' | 'volume_spike'
  // 支撐阻力信號
  | 'support_resistance' | 'support_break' | 'resistance_break';

// 信號強度類型（與後端 SignalStrength 枚舉對應）
export type TradingSignalStrength = 'WEAK' | 'MODERATE' | 'STRONG' | 'weak' | 'moderate' | 'strong';

export interface TradingSignal {
  id: number;
  stock_id: number;
  symbol: string;
  market: string;
  signal_type: TradingSignalType;
  strength: TradingSignalStrength;
  price: number;
  confidence: number;
  date: string;
  description: string;
  indicators: Record<string, any>;
  created_at: string;
}

// 信號類型轉換和正規化工具函數
export const SignalTypeUtils = {
  /**
   * 將後端信號類型轉換為前端顯示文字
   */
  getDisplayName(signalType: TradingSignalType): string {
    const displayNames: Record<string, string> = {
      'BUY': '買入',
      'SELL': '賣出',
      'HOLD': '持有',
      'GOLDEN_CROSS': '黃金交叉',
      'DEATH_CROSS': '死亡交叉',
      'golden_cross': '黃金交叉',
      'death_cross': '死亡交叉',
      'rsi_oversold': 'RSI超賣',
      'rsi_overbought': 'RSI超買',
      'macd_bullish': 'MACD看漲',
      'macd_bearish': 'MACD看跌',
      'bollinger_breakout': '布林帶突破',
      'bollinger_squeeze': '布林帶收縮',
      'bb_squeeze': '布林帶收縮',
      'bb_breakout': '布林帶突破',
      'kd_golden_cross': 'KD黃金交叉',
      'kd_death_cross': 'KD死亡交叉',
      'volume_breakout': '成交量突破',
      'volume_spike': '成交量激增',
      'support_resistance': '支撐阻力',
      'support_break': '支撐突破',
      'resistance_break': '阻力突破'
    };
    return displayNames[signalType] || signalType;
  },

  /**
   * 根據信號類型判斷是否為買入信號
   */
  isBuySignal(signalType: TradingSignalType): boolean {
    const buySignals: TradingSignalType[] = [
      'BUY', 'golden_cross', 'GOLDEN_CROSS', 'rsi_oversold',
      'macd_bullish', 'bollinger_breakout', 'bb_breakout',
      'kd_golden_cross', 'volume_breakout', 'support_break'
    ];
    return buySignals.includes(signalType);
  },

  /**
   * 根據信號類型判斷是否為賣出信號
   */
  isSellSignal(signalType: TradingSignalType): boolean {
    const sellSignals: TradingSignalType[] = [
      'SELL', 'death_cross', 'DEATH_CROSS', 'rsi_overbought',
      'macd_bearish', 'kd_death_cross', 'resistance_break'
    ];
    return sellSignals.includes(signalType);
  },

  /**
   * 獲取信號類型的顏色主題
   */
  getSignalColor(signalType: TradingSignalType): 'green' | 'red' | 'yellow' | 'gray' {
    if (this.isBuySignal(signalType)) return 'green';
    if (this.isSellSignal(signalType)) return 'red';
    if (signalType === 'HOLD') return 'gray';
    return 'yellow'; // 中性信號
  }
};

// API 響應類型
export interface ApiResponse<T> {
  data?: T;
  message?: string;
  success?: boolean;
  error?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
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