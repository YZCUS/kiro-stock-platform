/**
 * API Service Layer
 */
import axios, { AxiosInstance, AxiosResponse } from 'axios';

// Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_TIMEOUT = 10000;

// API Endpoints
export const API_ENDPOINTS = {
  // Stock endpoints
  STOCKS: {
    LIST: '/api/v1/stocks/',
    CREATE: '/api/v1/stocks/',
    DETAIL: (id: number) => `/api/v1/stocks/${id}/`,
    UPDATE: (id: number) => `/api/v1/stocks/${id}/`,
    DELETE: (id: number) => `/api/v1/stocks/${id}/`,
    BATCH_CREATE: '/api/v1/stocks/batch/',
    REFRESH_DATA: (id: number) => `/api/v1/stocks/${id}/refresh/`,
  },

  // Price endpoints
  PRICES: {
    HISTORY: (stockId: number) => `/api/v1/stocks/${stockId}/price-history/`,
    LATEST: (stockId: number) => `/api/v1/stocks/${stockId}/price/latest/`,
    BACKFILL: (stockId: number) => `/api/v1/stocks/${stockId}/price/backfill/`,
  },

  // Indicator endpoints
  INDICATORS: {
    LIST: (stockId: number) => `/api/v1/stocks/${stockId}/indicators/`,
    SUMMARY: (stockId: number) => `/api/v1/stocks/${stockId}/indicators/summary/`,
    CALCULATE: (stockId: number) => `/api/v1/stocks/${stockId}/indicators/calculate/`,
    SPECIFIC: (stockId: number, indicatorType: string) => `/api/v1/stocks/${stockId}/indicators/${indicatorType}/`,
  },

  // Signal endpoints
  SIGNALS: {
    LIST: '/api/v1/signals/',
    CREATE: '/api/v1/signals/',
    DETAIL: (id: number) => `/api/v1/signals/${id}/`,
    UPDATE: (id: number) => `/api/v1/signals/${id}/`,
    DELETE: (id: number) => `/api/v1/signals/${id}/`,
    BY_STOCK: (stockId: number) => `/api/v1/stocks/${stockId}/signals/`,
  },

  // Analysis endpoints
  ANALYSIS: '/api/v1/analysis/',
  STOCK_ANALYSIS: (stockId: string) => `/api/v1/analysis/${stockId}/`,

  // Auth endpoints
  AUTH: {
    REGISTER: '/api/v1/auth/register',
    LOGIN: '/api/v1/auth/login',
    ME: '/api/v1/auth/me',
    CHANGE_PASSWORD: '/api/v1/auth/change-password',
  },

  // Portfolio endpoints
  PORTFOLIO: {
    LIST: '/api/v1/portfolio/',
    SUMMARY: '/api/v1/portfolio/summary',
    DETAIL: (id: number) => `/api/v1/portfolio/${id}`,
    DELETE: (id: number) => `/api/v1/portfolio/${id}`,
    TRANSACTIONS: '/api/v1/portfolio/transactions',
    TRANSACTION_SUMMARY: '/api/v1/portfolio/transactions/summary',
  },

  // Strategy endpoints
  STRATEGIES: {
    AVAILABLE: '/api/v1/strategies/available',
    SUBSCRIPTIONS: {
      LIST: '/api/v1/strategies/subscriptions',
      CREATE: '/api/v1/strategies/subscriptions',
      DETAIL: (id: number) => `/api/v1/strategies/subscriptions/${id}`,
      UPDATE: (id: number) => `/api/v1/strategies/subscriptions/${id}`,
      DELETE: (id: number) => `/api/v1/strategies/subscriptions/${id}`,
      TOGGLE: (id: number) => `/api/v1/strategies/subscriptions/${id}/toggle`,
    },
    SIGNALS: {
      LIST: '/api/v1/strategies/signals',
      STATISTICS: '/api/v1/strategies/signals/statistics',
      GENERATE: '/api/v1/strategies/signals/generate',
      UPDATE_STATUS: (id: number) => `/api/v1/strategies/signals/${id}/status`,
    },
  },

  // Watchlist endpoints
  WATCHLIST: {
    LIST: '/api/v1/watchlist/',
    DETAILED: '/api/v1/watchlist/detailed',
    ADD: '/api/v1/watchlist/',
    REMOVE: (stockId: number) => `/api/v1/watchlist/${stockId}`,
    CHECK: (stockId: number) => `/api/v1/watchlist/check/${stockId}`,
    POPULAR: '/api/v1/watchlist/popular',
    STATS: '/api/v1/watchlist/stats',
  },

  // System endpoints
  HEALTH: '/health',
  STATUS: '/api/v1/system/status/',
} as const;

// Types
export interface ApiResponse<T = any> {
  data: T;
  message?: string;
  status: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface ApiError {
  message: string;
  detail?: string;
  code?: string;
  status_code?: number;
}

// Create axios instance
const createApiClient = (): AxiosInstance => {
  const client = axios.create({
    baseURL: API_BASE_URL,
    timeout: API_TIMEOUT,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // Request interceptor
  client.interceptors.request.use(
    (config) => {
      // Add auth token if available
      const token = localStorage.getItem('token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    },
    (error) => Promise.reject(error)
  );

  // Response interceptor
  client.interceptors.response.use(
    (response: AxiosResponse) => response,
    (error) => {
      if (error.response?.status === 401) {
        // Handle unauthorized access
        localStorage.removeItem('token');
        window.location.href = '/login';
      }
      return Promise.reject(error);
    }
  );

  return client;
};

// Create singleton instance
const apiClientInstance = createApiClient();

// Helper function to unwrap API response data
function unwrapApiResponse<T>(responseData: any): T {
  // 檢查回應是否有 data 屬性且不為空
  if (responseData && typeof responseData === 'object' && 'data' in responseData && responseData.data !== undefined) {
    console.debug('API response unwrapped: found data field', { original: responseData, unwrapped: responseData.data });
    return responseData.data;
  } else {
    // 如果沒有 data 屬性，直接返回原始數據
    console.debug('API response used as-is: no data field found', { response: responseData });
    return responseData;
  }
}

// Generic HTTP methods as direct exports
export async function get<T>(url: string, params?: any): Promise<T> {
  const response = await apiClientInstance.get<ApiResponse<T>>(url, { params });
  return unwrapApiResponse<T>(response.data);
}

export async function post<T>(url: string, data?: any): Promise<T> {
  const response = await apiClientInstance.post<ApiResponse<T>>(url, data);
  return unwrapApiResponse<T>(response.data);
}

export async function put<T>(url: string, data?: any): Promise<T> {
  const response = await apiClientInstance.put<ApiResponse<T>>(url, data);
  return unwrapApiResponse<T>(response.data);
}

export async function del<T>(url: string): Promise<T> {
  const response = await apiClientInstance.delete<ApiResponse<T>>(url);
  return unwrapApiResponse<T>(response.data);
}

export async function patch<T>(url: string, data?: any): Promise<T> {
  const response = await apiClientInstance.patch<ApiResponse<T>>(url, data);
  return unwrapApiResponse<T>(response.data);
}

// API Service Class with static methods (compatible wrapper)
export class ApiService {
  static get = get;
  static post = post;
  static put = put;
  static delete = del;
  static patch = patch;

  // Stock API methods (static)
  static async getStocks(params?: {
    market?: string;
    symbol?: string;
    page?: number;
    per_page?: number;
  }): Promise<PaginatedResponse<any>> {
    return get(API_ENDPOINTS.STOCKS.LIST, params);
  }

  static async getStock(id: number): Promise<any> {
    return get(API_ENDPOINTS.STOCKS.DETAIL(id));
  }

  static async createStock(data: any): Promise<any> {
    return post(API_ENDPOINTS.STOCKS.CREATE, data);
  }

  static async updateStock(id: number, data: any): Promise<any> {
    return put(API_ENDPOINTS.STOCKS.UPDATE(id), data);
  }

  static async deleteStock(id: number): Promise<void> {
    return del(API_ENDPOINTS.STOCKS.DELETE(id));
  }

  static async getStockPriceHistory(id: number, params?: {
    start_date?: string;
    end_date?: string;
    interval?: string;
  }): Promise<any[]> {
    return get(API_ENDPOINTS.PRICES.HISTORY(id), params);
  }

  // Indicator API methods (static)
  static async getIndicators(stockId: number, params?: {
    symbol?: string;
    indicator_type?: string;
    page?: number;
    per_page?: number;
  }): Promise<PaginatedResponse<any>> {
    return get(API_ENDPOINTS.INDICATORS.LIST(stockId), params);
  }

  static async getStockIndicators(stockId: number, params?: {
    indicator_type?: string;
    start_date?: string;
    end_date?: string;
  }): Promise<any[]> {
    return get(API_ENDPOINTS.INDICATORS.LIST(stockId), params);
  }

  // Signal API methods (static)
  static async getSignals(params?: {
    symbol?: string;
    signal_type?: string;
    start_date?: string;
    end_date?: string;
    page?: number;
    per_page?: number;
  }): Promise<PaginatedResponse<any>> {
    return get(API_ENDPOINTS.SIGNALS.LIST, params);
  }

  static async getStockSignals(stockId: number, params?: {
    signal_type?: string;
    start_date?: string;
    end_date?: string;
  }): Promise<any[]> {
    return get(API_ENDPOINTS.SIGNALS.BY_STOCK(stockId), params);
  }

  // Analysis API methods (static)
  static async getAnalysis(params?: {
    symbol?: string;
    analysis_type?: string;
    start_date?: string;
    end_date?: string;
  }): Promise<any> {
    return get(API_ENDPOINTS.ANALYSIS, params);
  }

  static async getStockAnalysis(stockId: string, params?: {
    analysis_type?: string;
    timeframe?: string;
  }): Promise<any> {
    return get(API_ENDPOINTS.STOCK_ANALYSIS(stockId), params);
  }

  // System API methods (static)
  static async getHealth(): Promise<any> {
    return get(API_ENDPOINTS.HEALTH);
  }

  static async getSystemStatus(): Promise<any> {
    return get(API_ENDPOINTS.STATUS);
  }

  // Utility methods (static)
  static isHealthy(): Promise<boolean> {
    return get<any>(API_ENDPOINTS.HEALTH)
      .then(health => (health as any).status === 'healthy')
      .catch(() => false);
  }

  // File upload method (static)
  static async uploadFile(url: string, file: File, onProgress?: (progress: number) => void): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);

    const config = {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: onProgress ? (progressEvent: any) => {
        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(progress);
      } : undefined,
    };

    const response = await apiClientInstance.post(url, formData, config);
    return unwrapApiResponse<any>(response.data);
  }
}

// Export the axios instance for direct use if needed
export { apiClientInstance as apiClient };

// Export default class
export default ApiService;