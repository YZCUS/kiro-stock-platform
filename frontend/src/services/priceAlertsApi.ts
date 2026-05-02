import { ApiService, API_ENDPOINTS } from '@/lib/api';

export interface PriceAlert {
  id: number;
  user_id: string;
  stock_id: number;
  symbol: string;
  market: string;
  condition: 'ABOVE' | 'BELOW';
  target_price: number;
  source_timeframe: string;
  active: boolean;
  triggered: boolean;
  triggered_at?: string | null;
  expires_at: string;
  last_checked_at?: string | null;
  last_price?: number | null;
  last_source?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PriceAlertCreateData {
  stock_id: number;
  condition: 'ABOVE' | 'BELOW';
  target_price: number;
  source_timeframe?: string;
  expires_at?: string;
}

export async function getPriceAlerts(activeOnly = false): Promise<PriceAlert[]> {
  return ApiService.get(API_ENDPOINTS.PRICE_ALERTS.LIST, {
    active_only: activeOnly,
  });
}

export async function createPriceAlert(
  data: PriceAlertCreateData
): Promise<PriceAlert> {
  return ApiService.post(API_ENDPOINTS.PRICE_ALERTS.CREATE, data);
}

export async function deletePriceAlert(id: number): Promise<void> {
  await ApiService.delete(API_ENDPOINTS.PRICE_ALERTS.DETAIL(id));
}
