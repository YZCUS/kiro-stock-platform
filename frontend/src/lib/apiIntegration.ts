/**
 * API Integration Layer with Fallback Support
 */
import axios from 'axios';
import { TradingSignal, TradingSignalType } from '../types';

// Environment configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_TIMEOUT = 10000; // 10 seconds

// Create axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Local interface for mock data (simplified for fallback)
interface MockTradingSignal {
  id: string;
  symbol: string;
  signal_type: TradingSignalType;
  price: number;
  timestamp: string;
  confidence: number;
  description: string;
}

interface StockData {
  symbol: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number;
  timestamp: string;
}

interface FetchParams {
  symbol?: string;
  market?: string;
  start_date?: string;
  end_date?: string;
  page?: number;
  limit?: number;
}

// Mock data for fallback
const mockTradingSignals: MockTradingSignal[] = [
  {
    id: '1',
    symbol: '2330.TW',
    signal_type: 'rsi_oversold',
    price: 580.0,
    timestamp: new Date().toISOString(),
    confidence: 0.85,
    description: 'RSI oversold condition with bullish momentum'
  },
  {
    id: '2',
    symbol: 'AAPL',
    signal_type: 'resistance_break',
    price: 185.0,
    timestamp: new Date().toISOString(),
    confidence: 0.78,
    description: 'Resistance level reached with high volume'
  }
];

const mockStockData: StockData[] = [
  {
    symbol: '2330.TW',
    price: 580.0,
    change: 5.0,
    change_percent: 0.87,
    volume: 12500000,
    timestamp: new Date().toISOString()
  },
  {
    symbol: 'AAPL',
    price: 185.0,
    change: -2.5,
    change_percent: -1.33,
    volume: 85000000,
    timestamp: new Date().toISOString()
  }
];

// Fallback tracking
let fallbackModeActive = false;

export function isFallbackModeActive(): boolean {
  return fallbackModeActive;
}

// API integration functions with fallback
export async function fetchSignalsWithFallback(params: FetchParams = {}): Promise<{
  items: MockTradingSignal[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}> {
  try {
    const response = await apiClient.get('/api/v1/signals/', { params });
    // 修正：實際API返回的是 PaginatedResponse 結構
    fallbackModeActive = false;
    return response.data; // 直接返回完整的分頁結構
  } catch (error) {
    console.warn('API call failed, using mock data:', error);
    fallbackModeActive = true;

    // Filter mock data based on params if needed
    let filtered = mockTradingSignals;
    if (params.symbol) {
      filtered = filtered.filter(signal => signal.symbol.includes(params.symbol!));
    }

    // Return complete paginated structure matching backend format
    const page = params.page || 1;
    const per_page = params.limit || 20;
    const total = filtered.length;
    const total_pages = Math.ceil(total / per_page);

    // Apply pagination to mock data
    const startIndex = (page - 1) * per_page;
    const paginatedItems = filtered.slice(startIndex, startIndex + per_page);

    return {
      items: paginatedItems,
      total,
      page,
      per_page,
      total_pages
    };
  }
}

export async function fetchStocksWithFallback(params: FetchParams = {}): Promise<{
  items: StockData[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}> {
  try {
    const response = await apiClient.get('/api/v1/stocks/', { params });
    // 修正：實際API返回的是 StockListResponse 結構，與 PaginatedResponse 兼容
    fallbackModeActive = false;
    return response.data; // 直接返回完整的分頁結構
  } catch (error) {
    console.warn('API call failed, using mock data:', error);
    fallbackModeActive = true;

    // Filter mock data based on params if needed
    let filtered = mockStockData;
    if (params.symbol) {
      filtered = filtered.filter(stock => stock.symbol.includes(params.symbol!));
    }

    // Return complete paginated structure matching backend format
    const page = params.page || 1;
    const per_page = params.limit || 20;
    const total = filtered.length;
    const total_pages = Math.ceil(total / per_page);

    // Apply pagination to mock data
    const startIndex = (page - 1) * per_page;
    const paginatedItems = filtered.slice(startIndex, startIndex + per_page);

    return {
      items: paginatedItems,
      total,
      page,
      per_page,
      total_pages
    };
  }
}

export async function fetchIndicatorsWithFallback(params: FetchParams = {}) {
  try {
    const response = await apiClient.get('/api/v1/indicators/', { params });
    // 修正：指標API可能返回不同的結構，優先使用 indicators 字段
    fallbackModeActive = false;
    return response.data.indicators || response.data;
  } catch (error) {
    console.warn('API call failed, using mock data:', error);
    fallbackModeActive = true;

    // Mock indicator data
    return {
      symbol: params.symbol || '2330.TW',
      indicators: {
        rsi: 65.5,
        sma_20: 575.0,
        sma_50: 570.0,
        ema_12: 578.0,
        ema_26: 572.0,
        macd: 2.5,
        macd_signal: 1.8,
        macd_histogram: 0.7,
        bollinger_upper: 590.0,
        bollinger_middle: 575.0,
        bollinger_lower: 560.0
      },
      timestamp: new Date().toISOString()
    };
  }
}

export async function createStockWithFallback(stockData: { symbol: string; market: 'TW' | 'US'; name?: string }): Promise<StockData> {
  try {
    const response = await apiClient.post('/api/v1/stocks/', stockData);
    fallbackModeActive = false;
    return response.data;
  } catch (error) {
    console.warn('API call failed, using mock data:', error);
    fallbackModeActive = true;

    // Return mock created stock
    return {
      symbol: stockData.symbol,
      price: 100.0,
      change: 0,
      change_percent: 0,
      volume: 0,
      timestamp: new Date().toISOString()
    };
  }
}

export async function deleteStockWithFallback(stockId: number): Promise<void> {
  try {
    await apiClient.delete(`/api/v1/stocks/${stockId}`);
    fallbackModeActive = false;
  } catch (error) {
    console.warn('API call failed, using mock behavior:', error);
    fallbackModeActive = true;
    // For mock, just return successfully
  }
}

// Health check function
export async function checkApiHealth(): Promise<boolean> {
  try {
    const response = await apiClient.get('/health');
    const isHealthy = response.status === 200 && response.data.status === 'healthy';
    if (isHealthy) fallbackModeActive = false;
    return isHealthy;
  } catch (error) {
    console.warn('API health check failed:', error);
    fallbackModeActive = true;
    return false;
  }
}

// Export the axios instance for direct use if needed
export { apiClient };
export default apiClient;