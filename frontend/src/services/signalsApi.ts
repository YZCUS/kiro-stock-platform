/**
 * 交易信號 API 服務
 */
import { ApiService, API_ENDPOINTS } from '../lib/api';
import { TradingSignal, SignalFilter, PaginatedResponse } from '../types';

export interface SignalListParams {
  page?: number;
  pageSize?: number;
  filters?: SignalFilter;
}

export interface SignalCreateData {
  stock_id: number;
  signal_type: 'BUY' | 'SELL' | 'HOLD' | 'GOLDEN_CROSS' | 'DEATH_CROSS';
  strength: 'WEAK' | 'MODERATE' | 'STRONG';
  price: number;
  confidence: number;
  description: string;
  indicators: Record<string, any>;
}

export interface SignalUpdateData {
  confidence?: number;
  description?: string;
  indicators?: Record<string, any>;
}

export class SignalsApiService {
  /**
   * 獲取交易信號列表
   */
  static async getSignals(params: SignalListParams = {}): Promise<PaginatedResponse<TradingSignal>> {
    const queryParams = new URLSearchParams();

    if (params.page) {
      queryParams.append('page', params.page.toString());
    }
    if (params.pageSize) {
      queryParams.append('page_size', params.pageSize.toString());
    }
    if (params.filters?.signal_type) {
      queryParams.append('signal_type', params.filters.signal_type);
    }
    if (params.filters?.market) {
      queryParams.append('market', params.filters.market);
    }
    if (params.filters?.min_confidence !== undefined) {
      queryParams.append('min_confidence', params.filters.min_confidence.toString());
    }
    if (params.filters?.start_date) {
      queryParams.append('start_date', params.filters.start_date);
    }
    if (params.filters?.end_date) {
      queryParams.append('end_date', params.filters.end_date);
    }

    const url = `${API_ENDPOINTS.SIGNALS.LIST}?${queryParams.toString()}`;
    return ApiService.get<PaginatedResponse<TradingSignal>>(url);
  }

  /**
   * 獲取單一交易信號詳情
   */
  static async getSignal(id: number): Promise<TradingSignal> {
    return ApiService.get<TradingSignal>(API_ENDPOINTS.SIGNALS.DETAIL(id));
  }

  /**
   * 創建新交易信號
   */
  static async createSignal(data: SignalCreateData): Promise<TradingSignal> {
    return ApiService.post<TradingSignal>(API_ENDPOINTS.SIGNALS.CREATE, data);
  }

  /**
   * 更新交易信號
   */
  static async updateSignal(id: number, data: SignalUpdateData): Promise<TradingSignal> {
    return ApiService.patch<TradingSignal>(API_ENDPOINTS.SIGNALS.UPDATE(id), data);
  }

  /**
   * 刪除交易信號
   */
  static async deleteSignal(id: number): Promise<{ message: string }> {
    return ApiService.delete<{ message: string }>(API_ENDPOINTS.SIGNALS.DELETE(id));
  }

  /**
   * 獲取特定股票的交易信號
   */
  static async getStockSignals(
    stockId: number,
    params: {
      page?: number;
      pageSize?: number;
      signal_type?: string;
      start_date?: string;
      end_date?: string;
    } = {}
  ): Promise<PaginatedResponse<TradingSignal>> {
    const queryParams = new URLSearchParams();

    if (params.page) {
      queryParams.append('page', params.page.toString());
    }
    if (params.pageSize) {
      queryParams.append('page_size', params.pageSize.toString());
    }
    if (params.signal_type) {
      queryParams.append('signal_type', params.signal_type);
    }
    if (params.start_date) {
      queryParams.append('start_date', params.start_date);
    }
    if (params.end_date) {
      queryParams.append('end_date', params.end_date);
    }

    const url = `${API_ENDPOINTS.SIGNALS.BY_STOCK(stockId)}?${queryParams.toString()}`;
    return ApiService.get<PaginatedResponse<TradingSignal>>(url);
  }

  /**
   * 獲取信號統計數據
   */
  static async getSignalStats(params: {
    stock_id?: number;
    market?: string;
    start_date?: string;
    end_date?: string;
  } = {}): Promise<{
    total_signals: number;
    by_type: Record<string, number>;
    by_strength: Record<string, number>;
    avg_confidence: number;
    accuracy?: number; // 如果有回測數據
  }> {
    const queryParams = new URLSearchParams();

    if (params.stock_id) {
      queryParams.append('stock_id', params.stock_id.toString());
    }
    if (params.market) {
      queryParams.append('market', params.market);
    }
    if (params.start_date) {
      queryParams.append('start_date', params.start_date);
    }
    if (params.end_date) {
      queryParams.append('end_date', params.end_date);
    }

    const url = `/api/v1/signals/stats?${queryParams.toString()}`;
    return ApiService.get(url);
  }

  /**
   * 訂閱即時信號推送
   */
  static async subscribeToSignals(stockIds: number[]): Promise<{
    message: string;
    subscription_id: string;
  }> {
    return ApiService.post('/api/v1/signals/subscribe', {
      stock_ids: stockIds,
    });
  }

  /**
   * 取消訂閱即時信號推送
   */
  static async unsubscribeFromSignals(subscriptionId: string): Promise<{
    message: string;
  }> {
    return ApiService.post('/api/v1/signals/unsubscribe', {
      subscription_id: subscriptionId,
    });
  }
}

export default SignalsApiService;