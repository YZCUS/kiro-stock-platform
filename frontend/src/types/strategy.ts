// ==================== 策略類型 ====================
export type StrategyParameterType = 'number' | 'text' | 'boolean';
export type StrategyParameterValue = string | number | boolean | null;
export type StrategyParameterMap = Record<string, StrategyParameterValue>;

export interface StrategyParameterSchema {
  key: string;
  label: string;
  type: StrategyParameterType;
  min?: number;
  max?: number;
  step?: number;
  description?: string;
}

export interface StrategyInfo {
  type: string;
  name: string;
  description: string;
  default_params: StrategyParameterMap;
  parameter_schema?: StrategyParameterSchema[];
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
  strategy_name?: string;
  is_active: boolean;
  parameters?: StrategyParameterMap | null;
  monitor_all_lists: boolean;
  monitor_portfolio: boolean;
  monitor_all_stocks: boolean;
  monitored_lists?: number[];
  selected_list_ids: number[];
  stock_lists?: StockListInfo[];
  created_at: string;
  updated_at: string;
}

export interface SubscriptionCreateRequest {
  strategy_type: string;
  parameters?: StrategyParameterMap;
  monitor_all_lists?: boolean;
  monitor_portfolio?: boolean;
  monitor_all_stocks?: boolean;
  selected_list_ids?: number[];
}

export interface SubscriptionUpdateRequest {
  parameters?: StrategyParameterMap;
  monitor_all_lists?: boolean;
  monitor_portfolio?: boolean;
  monitor_all_stocks?: boolean;
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
  stock_symbol?: string | null;
  stock_name?: string | null;
  strategy_type: string;
  strategy_name?: string;
  signal_horizon?: string;
  direction: SignalDirection;
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
  status: SignalStatus;
  signal_date: string;
  valid_until?: string | null;
  reason?: string | null;
  extra_data?: Record<string, unknown>;
  is_valid?: boolean;
  created_at: string;
}

export interface SignalListResponse {
  signals: TradingSignal[];
  total: number;
  limit?: number;
  offset?: number;
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
  direction?: SignalDirection;
  stock_id?: number;
  date_from?: string;
  date_to?: string;
  sort_by?: 'signal_date' | 'confidence';
  sort_order?: 'asc' | 'desc';
  limit?: number;
  offset?: number;
}

export interface StrategyReliabilityScore {
  strategy_type: string;
  horizon: string;
  reliability_score: number;
  target_score: number;
  backtest_score: number;
  recent_score: number;
  stability_score: number;
  regime_fit_score: number;
  sample_size: number;
  validation_status: string;
  min_weight: number;
  max_weight: number;
  metrics?: Record<string, unknown> | null;
  last_evaluated_at: string;
}

export interface StrategyReliabilityScoreListResponse {
  items: StrategyReliabilityScore[];
  total: number;
}

export interface StockCompositeScore {
  stock_id: number;
  symbol: string;
  market: string;
  score_date: string;
  composite_score: number;
  direction: 'bullish' | 'neutral' | 'bearish';
  confidence: number;
  weight_version_id?: number | null;
  horizon_breakdown?: Record<string, number> | null;
  strategy_contributions?: Array<Record<string, unknown>> | null;
  positive_count: number;
  negative_count: number;
  neutral_count: number;
  data_quality_weight: number;
}

export interface StockCompositeScoreListResponse {
  items: StockCompositeScore[];
  total: number;
}
