/**
 * 股票 API 服務
 */
import { ApiService, API_ENDPOINTS } from '../lib/api';
import { Stock, StockFilter, StockCreateForm, PaginatedResponse } from '../types';

export interface StockListParams {
  page?: number;
  pageSize?: number;
  filters?: StockFilter;
}

export interface StockCreateData extends StockCreateForm {}

export interface StockUpdateData {
  name?: string;
  is_active?: boolean;
}

export interface StockBatchCreateData {
  stocks: StockCreateForm[];
}

export class StocksApiService {
  /**
   * 獲取股票列表
   */
  static async getStocks(params: StockListParams & { search?: string } = {}): Promise<PaginatedResponse<Stock>> {
    const queryParams = new URLSearchParams();

    if (params.page) {
      queryParams.append('page', params.page.toString());
    }
    if (params.pageSize) {
      queryParams.append('per_page', params.pageSize.toString());
    }
    if (params.filters?.market) {
      queryParams.append('market', params.filters.market);
    }
    if (params.filters?.active_only !== undefined) {
      queryParams.append('is_active', params.filters.active_only.toString());
    }
    // Support both params.search and params.filters.search
    const searchTerm = (params as any).search || params.filters?.search;
    if (searchTerm) {
      queryParams.append('search', searchTerm);
    }

    const url = `${API_ENDPOINTS.STOCKS.LIST}?${queryParams.toString()}`;
    return ApiService.get<PaginatedResponse<Stock>>(url);
  }

  /**
   * 獲取單一股票詳情
   */
  static async getStock(id: number): Promise<Stock> {
    return ApiService.get<Stock>(API_ENDPOINTS.STOCKS.DETAIL(id));
  }

  /**
   * 創建新股票
   */
  static async createStock(data: StockCreateData): Promise<Stock> {
    return ApiService.post<Stock>(API_ENDPOINTS.STOCKS.CREATE, data);
  }

  /**
   * 更新股票信息
   */
  static async updateStock(id: number, data: StockUpdateData): Promise<Stock> {
    return ApiService.patch<Stock>(API_ENDPOINTS.STOCKS.UPDATE(id), data);
  }

  /**
   * 刪除股票
   */
  static async deleteStock(id: number): Promise<{ message: string }> {
    return ApiService.delete<{ message: string }>(API_ENDPOINTS.STOCKS.DELETE(id));
  }

  /**
   * 批量創建股票
   */
  static async batchCreateStocks(data: StockBatchCreateData): Promise<{
    created: Stock[];
    errors: { symbol: string; error: string }[];
  }> {
    return ApiService.post<{
      created: Stock[];
      errors: { symbol: string; error: string }[];
    }>(API_ENDPOINTS.STOCKS.BATCH_CREATE, data);
  }

  /**
   * 刷新股票數據
   */
  static async refreshStockData(id: number): Promise<{
    message: string;
    task_id?: string;
  }> {
    return ApiService.post<{
      message: string;
      task_id?: string;
    }>(API_ENDPOINTS.STOCKS.REFRESH_DATA(id));
  }

  /**
   * 獲取股票價格歷史
   */
  static async getStockPriceHistory(
    stockId: number,
    params: {
      start_date?: string;
      end_date?: string;
      interval?: '1d' | '1h' | '5m';
    } = {}
  ): Promise<{
    symbol: string;
    data: Array<{
      date: string;
      open: number;
      high: number;
      low: number;
      close: number;
      volume: number;
      adjusted_close?: number;
    }>;
  }> {
    const queryParams = new URLSearchParams();
    if (params.start_date) {
      queryParams.append('start_date', params.start_date);
    }
    if (params.end_date) {
      queryParams.append('end_date', params.end_date);
    }
    if (params.interval) {
      queryParams.append('interval', params.interval);
    }

    const url = `${API_ENDPOINTS.PRICES.HISTORY(stockId)}?${queryParams.toString()}`;
    return ApiService.get(url);
  }

  /**
   * 獲取股票最新價格
   */
  static async getStockLatestPrice(stockId: number): Promise<{
    symbol: string;
    price: number;
    change: number;
    change_percent: number;
    volume: number;
    timestamp: string;
  }> {
    return ApiService.get(API_ENDPOINTS.PRICES.LATEST(stockId));
  }

  /**
   * 觸發股票數據回填
   */
  static async backfillStockData(
    stockId: number,
    params: {
      start_date?: string;
      end_date?: string;
      force?: boolean;
    } = {}
  ): Promise<{
    message: string;
    completed: boolean;
    success: boolean;
    symbol: string;
    records_processed: number;
    records_saved: number;
    date_range: any;
    timestamp: string;
  }> {
    return ApiService.post(API_ENDPOINTS.PRICES.BACKFILL(stockId), params);
  }

  /**
   * 刷新所有活躍股票的最新價格數據
   */
  static async refreshAllStockPrices(): Promise<{
    success: boolean;
    message: string;
    total_stocks: number;
    successful: number;
    failed: number;
    results: Array<{
      stock_id: number;
      symbol: string;
      name: string;
      success: boolean;
      data_points: number;
      message: string;
      errors?: string[];
    }>;
  }> {
    return ApiService.post('/api/v1/stocks/refresh-all', {});
  }

  /**
   * 批量回填所有缺失價格的股票數據（僅針對完全沒有數據的股票）
   */
  static async backfillMissingPrices(): Promise<{
    success: boolean;
    message: string;
    total_stocks: number;
    successful: number;
    failed: number;
    results: Array<{
      stock_id: number;
      symbol: string;
      name: string;
      success: boolean;
      data_points: number;
      message: string;
      errors?: string[];
    }>;
  }> {
    return ApiService.post('/api/v1/stocks/backfill-missing', {});
  }
}

export default StocksApiService;