/**
 * Portfolio API 服務
 * 處理持倉管理和交易記錄相關的 API 請求
 */
import { ApiService, API_ENDPOINTS } from '@/lib/api';
import type {
  Portfolio,
  PortfolioListResponse,
  PortfolioSummary,
  Transaction,
  TransactionCreateRequest,
  TransactionListResponse,
  TransactionSummary,
  TransactionFilter
} from '@/types';

// =============================================================================
// Portfolio APIs (持倉管理)
// =============================================================================

/**
 * 獲取用戶持倉列表
 */
export const getPortfolioList = async (): Promise<PortfolioListResponse> => {
  return ApiService.get<PortfolioListResponse>(API_ENDPOINTS.PORTFOLIO.LIST);
};

/**
 * 獲取持倉摘要統計
 */
export const getPortfolioSummary = async (): Promise<PortfolioSummary> => {
  return ApiService.get<PortfolioSummary>(API_ENDPOINTS.PORTFOLIO.SUMMARY);
};

/**
 * 獲取單個持倉詳情
 */
export const getPortfolioDetail = async (portfolioId: number): Promise<Portfolio> => {
  return ApiService.get<Portfolio>(API_ENDPOINTS.PORTFOLIO.DETAIL(portfolioId));
};

/**
 * 刪除持倉（清倉）
 */
export const deletePortfolio = async (portfolioId: number): Promise<{ message: string }> => {
  return ApiService.delete<{ message: string }>(API_ENDPOINTS.PORTFOLIO.DELETE(portfolioId));
};

// =============================================================================
// Transaction APIs (交易記錄)
// =============================================================================

/**
 * 創建交易記錄（買入/賣出）
 */
export const createTransaction = async (
  request: TransactionCreateRequest
): Promise<Transaction> => {
  return ApiService.post<Transaction>(API_ENDPOINTS.PORTFOLIO.TRANSACTIONS, request);
};

/**
 * 獲取交易記錄列表
 */
export const getTransactionList = async (
  filter?: TransactionFilter
): Promise<TransactionListResponse> => {
  const params = filter ? new URLSearchParams(filter as any).toString() : '';
  const url = params ? API_ENDPOINTS.PORTFOLIO.TRANSACTIONS + '?' + params : API_ENDPOINTS.PORTFOLIO.TRANSACTIONS;
  return ApiService.get<TransactionListResponse>(url);
};

/**
 * 獲取交易統計摘要
 */
export const getTransactionSummary = async (
  startDate?: string,
  endDate?: string
): Promise<TransactionSummary> => {
  const params = new URLSearchParams();
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);

  const queryString = params.toString();
  const url = queryString
    ? API_ENDPOINTS.PORTFOLIO.TRANSACTION_SUMMARY + '?' + queryString
    : API_ENDPOINTS.PORTFOLIO.TRANSACTION_SUMMARY;

  return ApiService.get<TransactionSummary>(url);
};

// =============================================================================
// 輔助函數
// =============================================================================

/**
 * 計算盈虧百分比
 */
export const calculateProfitLossPercent = (profitLoss: number, totalCost: number): number => {
  if (totalCost === 0) return 0;
  return (profitLoss / totalCost) * 100;
};

/**
 * 格式化金額顯示
 */
export const formatCurrency = (amount: number, decimals: number = 2): string => {
  return new Intl.NumberFormat('zh-TW', {
    style: 'currency',
    currency: 'TWD',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(amount);
};

/**
 * 格式化百分比顯示
 */
export const formatPercent = (percent: number, decimals: number = 2): string => {
  return `${percent >= 0 ? '+' : ''}${percent.toFixed(decimals)}%`;
};

/**
 * 判斷是否盈利
 */
export const isProfitable = (profitLoss: number): boolean => {
  return profitLoss > 0;
};

export default {
  // Portfolio
  getPortfolioList,
  getPortfolioSummary,
  getPortfolioDetail,
  deletePortfolio,
  // Transaction
  createTransaction,
  getTransactionList,
  getTransactionSummary,
  // Helpers
  calculateProfitLossPercent,
  formatCurrency,
  formatPercent,
  isProfitable,
};
