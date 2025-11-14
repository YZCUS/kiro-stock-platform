// ==================== 策略類型 ====================
export interface StrategyInfo {
  type: string;
  name: string;
  description: string;
  default_params: Record<string, any>;
}

export interface StrategyListResponse {
  strategies: StrategyInfo[];
}

// ==================== 訂閱類型 ====================
export interface StockListInfo {
  id: number;
  name: string;
  stocks_count: number;
}

export interface Subscription {
  id: number;
  user_id: string;
  strategy_type: string;
  strategy_name: string;
  is_active: boolean;
  parameters: Record<string, any>;
  monitor_all_lists: boolean;
  monitor_portfolio: boolean;
  selected_list_ids: number[];
  stock_lists?: StockListInfo[];
  created_at: string;
  updated_at: string;
}

export interface SubscriptionCreateRequest {
  strategy_type: string;
  parameters?: Record<string, any>;
  monitor_all_lists?: boolean;
  monitor_portfolio?: boolean;
  selected_list_ids?: number[];
}

export interface SubscriptionUpdateRequest {
  parameters?: Record<string, any>;
  monitor_all_lists?: boolean;
  monitor_portfolio?: boolean;
  selected_list_ids?: number[];
}

export interface SubscriptionListResponse {
  subscriptions: Subscription[];
  total: number;
}

// ==================== 信號類型 ====================
export type SignalDirection = 'LONG' | 'SHORT' | 'NEUTRAL';
export type SignalStatus = 'active' | 'expired' | 'triggered' | 'cancelled';

export interface TradingSignal {
  id: number;
  stock_id: number;
  stock_symbol: string;
  stock_name: string;
  strategy_type: string;
  strategy_name: string;
  direction: SignalDirection;
  confidence: number;
  entry_min: number;
  entry_max: number;
  stop_loss: number;
  take_profit_targets: number[];
  status: SignalStatus;
  signal_date: string;
  valid_until: string;
  reason: string;
  extra_data?: Record<string, any>;
  created_at: string;
}

export interface SignalListResponse {
  signals: TradingSignal[];
  total: number;
  limit: number;
  offset: number;
}

export interface SignalStatistics {
  active_count: number;
  total_count: number;
  by_strategy: Record<string, Record<SignalStatus, number>>;
  by_status: Record<SignalStatus, number>;
  by_direction: Record<SignalDirection, number>;
  avg_confidence: number;
  this_week_count: number;
  date_range: {
    from: string;
    to: string;
  };
}

export interface UpdateSignalStatusRequest {
  status: SignalStatus;
}

// ==================== 查詢參數 ====================
export interface SignalQueryParams {
  strategy_type?: string;
  status?: SignalStatus;
  stock_id?: number;
  date_from?: string;
  date_to?: string;
  sort_by?: 'signal_date' | 'confidence';
  sort_order?: 'asc' | 'desc';
  limit?: number;
  offset?: number;
}
