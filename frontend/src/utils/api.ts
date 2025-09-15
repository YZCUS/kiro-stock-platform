/**
 * API 客戶端 - 使用增強的 API 客戶端
 */
import apiClient from './apiClient';
import type {
  Stock,
  PriceData,
  TradingSignal,
  StockDataResponse,
  SignalHistoryResponse,
  ApiResponse,
} from '../types';

// 股票相關 API
export const stocksApi = {
  // 取得股票清單
  async getStocks(params?: {
    market?: string;
    active_only?: boolean;
    limit?: number;
  }): Promise<Stock[]> {
    const response = await apiClient.get('/stocks', { params });
    return response.data;
  },

  // 取得單支股票資訊
  async getStock(stockId: number): Promise<Stock> {
    const response = await apiClient.get(`/stocks/${stockId}`);
    return response.data;
  },

  // 新增股票
  async createStock(data: {
    symbol: string;
    market: string;
    name?: string;
  }): Promise<Stock> {
    const response = await apiClient.post('/stocks', data);
    return response.data;
  },

  // 更新股票
  async updateStock(
    stockId: number,
    data: { name?: string; is_active?: boolean }
  ): Promise<Stock> {
    const response = await apiClient.put(`/stocks/${stockId}`, data);
    return response.data;
  },

  // 刪除股票
  async deleteStock(stockId: number): Promise<void> {
    await apiClient.delete(`/stocks/${stockId}`);
  },

  // 批次新增股票
  async batchCreateStocks(data: {
    stocks: Array<{ symbol: string; market: string; name?: string }>;
  }): Promise<any> {
    const response = await apiClient.post('/stocks/batch', data);
    return response.data;
  },

  // 搜尋股票
  async searchStocks(symbol: string, market?: string): Promise<Stock[]> {
    const params = market ? { market } : {};
    const response = await apiClient.get(`/stocks/search/${symbol}`, { params });
    return response.data;
  },

  // 取得股票完整數據
  async getStockData(
    stockId: number,
    params?: {
      start_date?: string;
      end_date?: string;
      page?: number;
      page_size?: number;
      include_indicators?: boolean;
    }
  ): Promise<StockDataResponse> {
    const response = await apiClient.get(`/stocks/${stockId}/data`, { params });
    return response.data;
  },

  // 取得股票價格數據
  async getStockPrices(
    stockId: number,
    params?: {
      start_date?: string;
      end_date?: string;
      limit?: number;
    }
  ): Promise<PriceData[]> {
    const response = await apiClient.get(`/stocks/${stockId}/prices`, { params });
    return response.data;
  },

  // 取得股票技術指標
  async getStockIndicators(
    stockId: number,
    params?: {
      indicator_type?: string;
      start_date?: string;
      end_date?: string;
      page?: number;
      page_size?: number;
    }
  ): Promise<any> {
    const response = await apiClient.get(`/stocks/${stockId}/indicators`, { params });
    return response.data;
  },

  // 手動更新股票數據
  async refreshStockData(
    stockId: number,
    params?: { days?: number }
  ): Promise<any> {
    const response = await apiClient.post(`/stocks/${stockId}/refresh`, null, { params });
    return response.data;
  },

  // 收集股票數據
  async collectStockData(data: {
    symbol: string;
    market: string;
    start_date?: string;
    end_date?: string;
  }): Promise<any> {
    const response = await apiClient.post('/stocks/collect', data);
    return response.data;
  },

  // 收集所有股票數據
  async collectAllStocksData(): Promise<any> {
    const response = await apiClient.post('/stocks/collect-all');
    return response.data;
  },

  // 驗證股票數據
  async validateStockData(
    stockId: number,
    params?: { days?: number }
  ): Promise<any> {
    const response = await apiClient.get(`/stocks/${stockId}/validate`, { params });
    return response.data;
  },
};

// 技術分析相關 API
export const analysisApi = {
  // 計算技術指標
  async calculateTechnicalIndicator(data: {
    stock_id: number;
    indicator: string;
    days?: number;
  }): Promise<any> {
    const response = await apiClient.post('/analysis/technical-analysis', data);
    return response.data;
  },

  // 取得所有技術指標
  async getAllTechnicalIndicators(
    stockId: number,
    params?: { days?: number }
  ): Promise<any[]> {
    const response = await apiClient.get(`/analysis/technical-analysis/${stockId}`, { params });
    return response.data;
  },

  // 偵測交易信號
  async detectTradingSignals(data: {
    stock_id: number;
    signal_types?: string[];
  }): Promise<any[]> {
    const response = await apiClient.post('/analysis/signals', data);
    return response.data;
  },

  // 取得股票交易信號
  async getStockSignals(
    stockId: number,
    params?: {
      signal_type?: string;
      limit?: number;
    }
  ): Promise<any[]> {
    const response = await apiClient.get(`/analysis/signals/${stockId}`, { params });
    return response.data;
  },

  // 批次技術分析
  async batchTechnicalAnalysis(params?: {
    market?: string;
    indicator?: string;
    days?: number;
    limit?: number;
  }): Promise<any> {
    const response = await apiClient.get('/analysis/batch-analysis', { params });
    return response.data;
  },

  // 取得市場概覽
  async getMarketOverview(params?: { market?: string }): Promise<any> {
    const response = await apiClient.get('/analysis/market-overview', { params });
    return response.data;
  },
};

// 交易信號相關 API
export const signalsApi = {
  // 取得所有交易信號
  async getAllSignals(params?: {
    signal_type?: string;
    market?: string;
    min_confidence?: number;
    start_date?: string;
    end_date?: string;
    page?: number;
    page_size?: number;
  }): Promise<SignalHistoryResponse> {
    const response = await apiClient.get('/signals', { params });
    return response.data;
  },

  // 取得信號歷史
  async getSignalHistory(params?: {
    days?: number;
    signal_type?: string;
    market?: string;
    limit?: number;
  }): Promise<TradingSignal[]> {
    const response = await apiClient.get('/signals/history', { params });
    return response.data;
  },

  // 取得信號統計
  async getSignalStats(params?: {
    days?: number;
    market?: string;
  }): Promise<any> {
    const response = await apiClient.get('/signals/stats', { params });
    return response.data;
  },

  // 取得股票信號
  async getStockSignals(
    stockId: number,
    params?: {
      signal_type?: string;
      days?: number;
      limit?: number;
    }
  ): Promise<TradingSignal[]> {
    const response = await apiClient.get(`/signals/${stockId}`, { params });
    return response.data;
  },

  // 即時偵測股票信號
  async detectStockSignals(
    stockId: number,
    params?: {
      signal_types?: string[];
      save_results?: boolean;
    }
  ): Promise<TradingSignal[]> {
    const response = await apiClient.post(`/signals/${stockId}/detect`, null, { params });
    return response.data;
  },

  // 刪除交易信號
  async deleteSignal(signalId: number): Promise<void> {
    await apiClient.delete(`/signals/${signalId}`);
  },
};

// 系統相關 API
export const systemApi = {
  // 健康檢查
  async healthCheck(): Promise<any> {
    const response = await apiClient.get('/test');
    return response.data;
  },

  // 取得 API 文檔
  async getApiDocs(): Promise<any> {
    const response = await apiClient.get('/docs');
    return response.data;
  },
};

// 導出預設 API 客戶端
export default apiClient;