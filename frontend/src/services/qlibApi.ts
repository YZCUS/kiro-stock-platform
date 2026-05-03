import { ApiService, API_ENDPOINTS } from '@/lib/api';

const qlibInFlight = new Map<string, Promise<unknown>>();

const dedupeInFlight = <T>(
  key: string,
  requestFactory: () => Promise<T>
): Promise<T> => {
  const existingRequest = qlibInFlight.get(key);
  if (existingRequest) {
    return existingRequest as Promise<T>;
  }

  const request = requestFactory().finally(() => {
    qlibInFlight.delete(key);
  });
  qlibInFlight.set(key, request);
  return request;
};

export interface QlibReadiness {
  market: string;
  ready: boolean;
  min_stocks_required: number;
  min_bars_required: number;
  coverage: {
    market: string;
    active_stocks: number;
    stocks_with_daily_bars: number;
    rows: number;
    min_date?: string | null;
    max_date?: string | null;
    min_bars: number;
    median_bars: number;
    max_bars: number;
    adjusted_rows: number;
  };
  issues: string[];
  recommendations: string[];
}

export interface QlibModelOption {
  name: string;
  label: string;
  model_type: string;
  feature_set: string;
  horizon: string;
  min_lookback_days: number;
  description: string;
  portfolio_strategy: string;
  status: string;
  config_uri?: string | null;
}

export interface QlibModelOptionsResponse {
  models: QlibModelOption[];
}

export async function getQlibReadiness(params: {
  market?: 'US' | 'TW';
  min_stocks?: number;
  min_bars?: number;
} = {}): Promise<QlibReadiness> {
  const key = `readiness:${params.market ?? ''}:${params.min_stocks ?? ''}:${params.min_bars ?? ''}`;
  return dedupeInFlight(key, () =>
    ApiService.get(API_ENDPOINTS.QLIB.READINESS, params)
  );
}

export async function getQlibModels(): Promise<QlibModelOptionsResponse> {
  return dedupeInFlight('models', () =>
    ApiService.get<QlibModelOptionsResponse>(API_ENDPOINTS.QLIB.MODELS)
  );
}
