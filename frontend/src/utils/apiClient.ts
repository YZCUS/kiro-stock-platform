/**
 * 增強的 API 客戶端 - 錯誤處理、重試、監控
 */
import axios, { 
  AxiosInstance, 
  AxiosResponse, 
  AxiosError, 
  InternalAxiosRequestConfig,
  CreateAxiosDefaults 
} from 'axios';
import { store } from '../store';
import { 
  setNetworkStatus, 
  incrementRetryCount, 
  resetRetryCount,
  addApiResponseTime,
  incrementErrorCount 
} from '../store/slices/appSlice';

// 錯誤類型定義
export interface ApiError {
  code: string;
  message: string;
  details?: any;
  statusCode?: number;
  timestamp: string;
  path?: string;
}

export interface ApiResponse<T = any> {
  data: T;
  success: boolean;
  message?: string;
  error?: ApiError;
  meta?: {
    page?: number;
    pageSize?: number;
    total?: number;
    totalPages?: number;
  };
}

export interface RetryConfig {
  retries: number;
  retryDelay: number;
  retryCondition?: (error: AxiosError) => boolean;
}

export interface ApiClientConfig extends CreateAxiosDefaults {
  enableRetry?: boolean;
  retryConfig?: RetryConfig;
  enableMonitoring?: boolean;
  enableCache?: boolean;
  cacheTimeout?: number;
}

interface ExtendedAxiosRequestConfig extends InternalAxiosRequestConfig {
  metadata?: { startTime: number };
  retryCount?: number;
}

class ApiClient {
  private instance: AxiosInstance;
  private retryConfig: RetryConfig;
  private enableMonitoring: boolean;
  private enableCache: boolean;
  private cacheTimeout: number;
  private cache: Map<string, { data: any; timestamp: number }> = new Map();

  constructor(config: ApiClientConfig = {}) {
    const {
      enableRetry = true,
      retryConfig = {
        retries: 3,
        retryDelay: 1000,
        retryCondition: (error) => {
          return !error.response || error.response.status >= 500;
        }
      },
      enableMonitoring = true,
      enableCache = false,
      cacheTimeout = 300000, // 5 minutes
      ...axiosConfig
    } = config;

    this.retryConfig = retryConfig;
    this.enableMonitoring = enableMonitoring;
    this.enableCache = enableCache;
    this.cacheTimeout = cacheTimeout;

    // 創建 axios 實例
    this.instance = axios.create({
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
      ...axiosConfig,
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // 請求攔截器
    this.instance.interceptors.request.use(
      (config: ExtendedAxiosRequestConfig) => {
        // 添加請求開始時間用於監控
        config.metadata = { startTime: Date.now() };

        // 添加認證 token
        const state = store.getState();
        const token = state.app.session?.user ? 'mock-token' : null;
        
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }

        // 檢查快取
        if (this.enableCache && config.method === 'get') {
          const cacheKey = this.getCacheKey(config);
          const cached = this.cache.get(cacheKey);
          
          if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
            // 返回快取的數據 (這裡需要特殊處理，因為攔截器不能直接返回數據)
            config.headers['X-Cache-Hit'] = 'true';
          }
        }

        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // 響應攔截器
    this.instance.interceptors.response.use(
      (response: AxiosResponse) => {
        const config = response.config as ExtendedAxiosRequestConfig;
        
        // 監控響應時間
        if (this.enableMonitoring && config.metadata?.startTime) {
          const responseTime = Date.now() - config.metadata.startTime;
          const endpoint = this.getEndpointFromUrl(config.url || '');
          
          store.dispatch(addApiResponseTime({ endpoint, time: responseTime }));
        }

        // 重置重試計數
        store.dispatch(resetRetryCount());

        // 更新網路狀態
        store.dispatch(setNetworkStatus(true));

        // 快取響應
        if (this.enableCache && config.method === 'get') {
          const cacheKey = this.getCacheKey(config);
          this.cache.set(cacheKey, {
            data: response.data,
            timestamp: Date.now()
          });
        }

        // For interceptor, we need to modify response.data, not return a different structure
        if (response.data && typeof response.data === 'object' && !('success' in response.data)) {
          response.data = {
            data: response.data,
            success: true,
            message: 'Request successful',
          };
        }
        return response;
      },
      async (error: AxiosError) => {
        const config = error.config as ExtendedAxiosRequestConfig;

        // 監控錯誤
        if (this.enableMonitoring) {
          const endpoint = this.getEndpointFromUrl(config?.url || '');
          store.dispatch(incrementErrorCount(endpoint));

          if (config?.metadata?.startTime) {
            const responseTime = Date.now() - config.metadata.startTime;
            store.dispatch(addApiResponseTime({ endpoint, time: responseTime }));
          }
        }

        // 處理網路錯誤
        if (!error.response) {
          store.dispatch(setNetworkStatus(false));
        }

        // 重試邏輯
        if (this.shouldRetry(error, config)) {
          return this.retryRequest(error);
        }

        return Promise.reject(this.normalizeError(error));
      }
    );
  }

  private shouldRetry(error: AxiosError, config?: ExtendedAxiosRequestConfig): boolean {
    if (!config) return false;
    
    const retryCount = config.retryCount || 0;
    const shouldRetryByCondition = this.retryConfig.retryCondition?.(error) ?? true;
    
    return (
      retryCount < this.retryConfig.retries &&
      shouldRetryByCondition &&
      config.method !== 'post' // 避免重複 POST 請求
    );
  }

  private async retryRequest(error: AxiosError): Promise<AxiosResponse> {
    const config = error.config as ExtendedAxiosRequestConfig;
    
    config.retryCount = (config.retryCount || 0) + 1;
    
    // 增加重試計數
    store.dispatch(incrementRetryCount());

    // 計算延遲時間 (指數退避)
    const delay = this.retryConfig.retryDelay * Math.pow(2, config.retryCount - 1);
    
    await new Promise(resolve => setTimeout(resolve, delay));
    
    return this.instance(config);
  }

  private normalizeResponse<T>(response: AxiosResponse): ApiResponse<T> {
    // 統一響應格式
    if (response.data && typeof response.data === 'object' && 'success' in response.data) {
      return response.data;
    }

    return {
      data: response.data,
      success: true,
      message: 'Request successful',
    };
  }

  private normalizeError(error: AxiosError): ApiError {
    const timestamp = new Date().toISOString();
    
    if (!error.response) {
      // 網路錯誤
      return {
        code: 'NETWORK_ERROR',
        message: '網路連線錯誤',
        timestamp,
      };
    }

    const { status, data, config } = error.response;
    
    // 服務器錯誤
    if (data && typeof data === 'object' && 'error' in data) {
      return {
        ...(data.error as any),
        statusCode: status,
        timestamp,
        path: config?.url,
      };
    }

    // 默認錯誤格式
    return {
      code: `HTTP_${status}`,
      message: this.getErrorMessage(status),
      statusCode: status,
      timestamp,
      path: config?.url,
      details: data,
    };
  }

  private getErrorMessage(status: number): string {
    const messages: Record<number, string> = {
      400: '請求參數錯誤',
      401: '未授權，請重新登入',
      403: '沒有權限執行此操作',
      404: '請求的資源不存在',
      409: '資源衝突',
      422: '請求資料驗證失敗',
      429: '請求過於頻繁，請稍後再試',
      500: '服務器內部錯誤',
      502: '服務器網關錯誤',
      503: '服務暫時不可用',
      504: '服務器響應超時',
    };

    return messages[status] || '未知錯誤';
  }

  private getCacheKey(config: ExtendedAxiosRequestConfig): string {
    const { url, params } = config;
    return `${url}:${JSON.stringify(params || {})}`;
  }

  private getEndpointFromUrl(url: string): string {
    try {
      const pathname = new URL(url).pathname;
      return pathname.split('/').slice(0, 3).join('/'); // /api/v1
    } catch {
      return url;
    }
  }

  // 公開方法
  public async get<T = any>(url: string, config?: any): Promise<ApiResponse<T>> {
    const response = await this.instance.get(url, config);
    return response.data;
  }

  public async post<T = any>(url: string, data?: any, config?: any): Promise<ApiResponse<T>> {
    const response = await this.instance.post(url, data, config);
    return response.data;
  }

  public async put<T = any>(url: string, data?: any, config?: any): Promise<ApiResponse<T>> {
    const response = await this.instance.put(url, data, config);
    return response.data;
  }

  public async patch<T = any>(url: string, data?: any, config?: any): Promise<ApiResponse<T>> {
    const response = await this.instance.patch(url, data, config);
    return response.data;
  }

  public async delete<T = any>(url: string, config?: any): Promise<ApiResponse<T>> {
    const response = await this.instance.delete(url, config);
    return response.data;
  }

  // 快取管理
  public clearCache(): void {
    this.cache.clear();
  }

  public removeCacheEntry(key: string): void {
    this.cache.delete(key);
  }

  // 獲取實例 (用於特殊情況)
  public getInstance(): AxiosInstance {
    return this.instance;
  }
}

// 創建默認客戶端
const defaultApiClient = new ApiClient({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
  enableRetry: true,
  enableMonitoring: true,
  enableCache: true,
});

export default defaultApiClient;
export { ApiClient };