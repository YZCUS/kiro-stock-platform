/**
 * 股號驗證 API 服務
 * 可重用的股票代號驗證模組
 */
import { ApiService } from '../lib/api';

export interface StockValidationResult {
  valid: boolean;
  symbol: string;
  name: string;
  market: string;
  currency?: string;
  exchange?: string;
  quote_type?: string;
}

export interface StockEnsureResult {
  exists: boolean;
  created: boolean;
  stock: {
    id: number;
    symbol: string;
    name: string;
    market: string;
    latest_price?: {
      close: number;
      change: number;
      change_percent: number;
      date: string;
      volume: number;
    };
  };
}

export interface StockValidationError {
  detail: string;
}

/**
 * 驗證股票代號是否有效
 * @param symbol 股票代號
 * @param market 市場代碼 (TW/US)
 * @returns 股票基本信息
 */
export async function validateStockSymbol(
  symbol: string,
  market: 'TW' | 'US'
): Promise<StockValidationResult> {
  try {
    const response = await ApiService.post<StockValidationResult>(
      `/api/v1/stocks/validate?symbol=${encodeURIComponent(symbol)}&market=${market}`,
      {}
    );
    return response;
  } catch (error: any) {
    throw new Error(
      error.response?.data?.detail || '驗證股票代號失敗'
    );
  }
}

/**
 * 自動偵測市場並驗證股票代號
 * @param symbol 股票代號
 * @returns 股票基本信息
 */
export async function validateStockSymbolAuto(
  symbol: string
): Promise<StockValidationResult> {
  const trimmedSymbol = symbol.trim().toUpperCase();

  // 自動判斷市場：數字為台股，英文為美股
  const market: 'TW' | 'US' = /^\d+$/.test(trimmedSymbol) ? 'TW' : 'US';

  return validateStockSymbol(trimmedSymbol, market);
}

/**
 * 格式化股票代號
 * @param symbol 股票代號
 * @param market 市場代碼
 * @returns 格式化後的股票代號
 */
export function formatStockSymbol(symbol: string, market: 'TW' | 'US'): string {
  const trimmedSymbol = symbol.trim().toUpperCase();

  if (market === 'TW' && !trimmedSymbol.endsWith('.TW')) {
    return `${trimmedSymbol}.TW`;
  }

  return trimmedSymbol;
}

/**
 * 自動偵測市場類型
 * @param symbol 股票代號
 * @returns 市場代碼
 */
export function detectMarket(symbol: string): 'TW' | 'US' {
  const trimmedSymbol = symbol.trim().toUpperCase();
  return /^\d+$/.test(trimmedSymbol) ? 'TW' : 'US';
}

/**
 * 確保股票存在於資料庫中，如果不存在則創建並抓取價格
 * @param symbol 股票代號
 * @param market 市場代碼 (TW/US)
 * @returns 股票完整信息
 */
export async function ensureStockExists(
  symbol: string,
  market: 'TW' | 'US'
): Promise<StockEnsureResult> {
  try {
    const response = await ApiService.post<StockEnsureResult>(
      `/api/v1/stocks/ensure?symbol=${encodeURIComponent(symbol)}&market=${market}`,
      {}
    );
    return response;
  } catch (error: any) {
    // 從後端錯誤響應中提取友善的錯誤訊息
    const detail = error.response?.data?.detail;

    if (detail && typeof detail === 'string') {
      // 後端已經提供了友善的錯誤訊息，直接使用
      throw new Error(detail);
    } else {
      // 後備錯誤訊息
      throw new Error(`查詢股票「${symbol}」失敗，請稍後再試`);
    }
  }
}

/**
 * 自動偵測市場並確保股票存在
 * @param symbol 股票代號
 * @returns 股票完整信息
 */
export async function ensureStockExistsAuto(
  symbol: string
): Promise<StockEnsureResult> {
  const trimmedSymbol = symbol.trim().toUpperCase();
  const market = detectMarket(trimmedSymbol);
  return ensureStockExists(trimmedSymbol, market);
}

export default {
  validateStockSymbol,
  validateStockSymbolAuto,
  formatStockSymbol,
  detectMarket,
  ensureStockExists,
  ensureStockExistsAuto,
};
