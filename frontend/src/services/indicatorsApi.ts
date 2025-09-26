/**
 * 技術指標 API 服務
 */
import { ApiService, API_ENDPOINTS } from '../lib/api';
import { TechnicalIndicator } from '../types';

export interface IndicatorListParams {
  stock_id: number;
  indicator_types?: string[];
  start_date?: string;
  end_date?: string;
  timeframe?: '1d' | '1h' | '5m';
}

export interface IndicatorCalculateParams {
  stock_id: number;
  indicator_type: 'SMA' | 'EMA' | 'RSI' | 'MACD' | 'BOLLINGER' | 'KD';
  period?: number;
  timeframe?: '1d' | '1h' | '5m';
  parameters?: Record<string, any>;
  start_date?: string;
  end_date?: string;
}

export interface IndicatorBatchCalculateParams {
  stock_id: number;
  indicators: Array<{
    type: string;
    period?: number;
    parameters?: Record<string, any>;
  }>;
  timeframe?: '1d' | '1h' | '5m';
  start_date?: string;
  end_date?: string;
}

export interface IndicatorResponse {
  stock_id: number;
  symbol: string;
  indicator_type: string;
  timeframe: string;
  data: TechnicalIndicator[];
  parameters: Record<string, any>;
  calculated_at: string;
}

export interface IndicatorBatchResponse {
  stock_id: number;
  symbol: string;
  timeframe: string;
  indicators: Record<string, {
    data: TechnicalIndicator[];
    parameters: Record<string, any>;
  }>;
  calculated_at: string;
}

export class IndicatorsApiService {
  /**
   * 獲取技術指標列表
   */
  static async getIndicators(params: IndicatorListParams): Promise<{
    stock_id: number;
    symbol: string;
    timeframe: string;
    indicators: Record<string, IndicatorResponse>;
  }> {
    const queryParams = new URLSearchParams();

    if (params.indicator_types && params.indicator_types.length > 0) {
      params.indicator_types.forEach(type => {
        queryParams.append('indicator_types', type);
      });
    }
    if (params.start_date) {
      queryParams.append('start_date', params.start_date);
    }
    if (params.end_date) {
      queryParams.append('end_date', params.end_date);
    }

    // 確保 timeframe 參數被正確傳遞，如果沒有提供則使用預設值
    const timeframe = params.timeframe || '1d';
    queryParams.append('timeframe', timeframe);

    const url = `${API_ENDPOINTS.INDICATORS.LIST(params.stock_id)}?${queryParams.toString()}`;
    return ApiService.get(url);
  }

  /**
   * 計算特定技術指標
   */
  static async calculateIndicator(params: IndicatorCalculateParams): Promise<IndicatorResponse> {
    const requestData = {
      indicator_type: params.indicator_type,
      period: params.period,
      timeframe: params.timeframe || '1d',
      parameters: params.parameters || {},
      start_date: params.start_date,
      end_date: params.end_date,
    };

    return ApiService.post<IndicatorResponse>(
      API_ENDPOINTS.INDICATORS.CALCULATE(params.stock_id),
      requestData
    );
  }

  /**
   * 批量計算技術指標
   */
  static async batchCalculateIndicators(params: IndicatorBatchCalculateParams): Promise<IndicatorBatchResponse> {
    const requestData = {
      indicators: params.indicators,
      timeframe: params.timeframe || '1d',
      start_date: params.start_date,
      end_date: params.end_date,
    };

    return ApiService.post<IndicatorBatchResponse>(
      `${API_ENDPOINTS.INDICATORS.CALCULATE(params.stock_id)}/batch`,
      requestData
    );
  }

  /**
   * 獲取特定類型的技術指標
   */
  static async getSpecificIndicator(
    stockId: number,
    indicatorType: string,
    params: {
      period?: number;
      timeframe?: '1d' | '1h' | '5m';
      start_date?: string;
      end_date?: string;
    } = {}
  ): Promise<IndicatorResponse> {
    const queryParams = new URLSearchParams();

    if (params.period) {
      queryParams.append('period', params.period.toString());
    }
    if (params.timeframe) {
      queryParams.append('timeframe', params.timeframe);
    }
    if (params.start_date) {
      queryParams.append('start_date', params.start_date);
    }
    if (params.end_date) {
      queryParams.append('end_date', params.end_date);
    }

    const url = `${API_ENDPOINTS.INDICATORS.SPECIFIC(stockId, indicatorType)}?${queryParams.toString()}`;
    return ApiService.get<IndicatorResponse>(url);
  }

  /**
   * 獲取支援的技術指標列表
   */
  static async getSupportedIndicators(): Promise<{
    indicators: Array<{
      type: string;
      name: string;
      description: string;
      default_period?: number;
      parameters: Array<{
        name: string;
        type: 'number' | 'string' | 'boolean';
        default?: any;
        description: string;
      }>;
    }>;
  }> {
    return ApiService.get('/api/v1/indicators/supported');
  }

  /**
   * 刪除指標數據
   */
  static async deleteIndicatorData(
    stockId: number,
    indicatorType: string,
    params: {
      timeframe?: string;
      start_date?: string;
      end_date?: string;
    } = {}
  ): Promise<{ message: string }> {
    const queryParams = new URLSearchParams();

    if (params.timeframe) {
      queryParams.append('timeframe', params.timeframe);
    }
    if (params.start_date) {
      queryParams.append('start_date', params.start_date);
    }
    if (params.end_date) {
      queryParams.append('end_date', params.end_date);
    }

    const url = `${API_ENDPOINTS.INDICATORS.SPECIFIC(stockId, indicatorType)}?${queryParams.toString()}`;
    return ApiService.delete<{ message: string }>(url);
  }

  /**
   * 獲取指標計算狀態
   */
  static async getCalculationStatus(taskId: string): Promise<{
    task_id: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    progress?: number;
    result?: any;
    error?: string;
    created_at: string;
    updated_at: string;
  }> {
    return ApiService.get(`/api/v1/indicators/tasks/${taskId}`);
  }

  /**
   * 觸發指標重新計算
   */
  static async recalculateIndicators(
    stockId: number,
    params: {
      indicator_types?: string[];
      force?: boolean;
      start_date?: string;
      end_date?: string;
    } = {}
  ): Promise<{
    message: string;
    task_id: string;
  }> {
    return ApiService.post(`${API_ENDPOINTS.INDICATORS.CALCULATE(stockId)}/recalculate`, params);
  }
}

export default IndicatorsApiService;