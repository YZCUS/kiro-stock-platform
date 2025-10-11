/**
 * 股票清單 API 服務
 */
import { ApiService } from '@/lib/api';
import type {
  StockList,
  StockListCreateRequest,
  StockListUpdateRequest,
  StockListListResponse,
  StockListItem,
  StockListItemAddRequest,
  StockListItemBatchAddRequest,
  StockListItemListResponse
} from '@/types';

const BASE_URL = '/api/v1/stock-lists';

// =============================================================================
// 股票清單管理
// =============================================================================

/**
 * 獲取用戶的所有股票清單
 */
export const getStockLists = async (): Promise<StockListListResponse> => {
  return ApiService.get<StockListListResponse>(BASE_URL + '/');
};

/**
 * 獲取單個股票清單
 */
export const getStockList = async (listId: number): Promise<StockList> => {
  return ApiService.get<StockList>(`${BASE_URL}/${listId}`);
};

/**
 * 創建新的股票清單
 */
export const createStockList = async (data: StockListCreateRequest): Promise<StockList> => {
  return ApiService.post<StockList>(BASE_URL + '/', data);
};

/**
 * 更新股票清單
 */
export const updateStockList = async (listId: number, data: StockListUpdateRequest): Promise<StockList> => {
  return ApiService.put<StockList>(`${BASE_URL}/${listId}`, data);
};

/**
 * 刪除股票清單
 */
export const deleteStockList = async (listId: number): Promise<{ message: string; list_id: number }> => {
  return ApiService.delete<{ message: string; list_id: number }>(`${BASE_URL}/${listId}`);
};

// =============================================================================
// 清單項目管理
// =============================================================================

/**
 * 獲取清單中的所有股票
 */
export const getListStocks = async (listId: number): Promise<StockListItemListResponse> => {
  return ApiService.get<StockListItemListResponse>(`${BASE_URL}/${listId}/stocks`);
};

/**
 * 添加股票到清單
 */
export const addStockToList = async (listId: number, data: StockListItemAddRequest): Promise<StockListItem> => {
  return ApiService.post<StockListItem>(`${BASE_URL}/${listId}/stocks`, data);
};

/**
 * 批量添加股票到清單
 */
export const batchAddStocksToList = async (
  listId: number,
  data: StockListItemBatchAddRequest
): Promise<{ message: string; success_count: number; failed_count: number; errors: string[] }> => {
  return ApiService.post(`${BASE_URL}/${listId}/stocks/batch`, data);
};

/**
 * 從清單中移除股票
 */
export const removeStockFromList = async (
  listId: number,
  stockId: number
): Promise<{ message: string; list_id: number; stock_id: number }> => {
  return ApiService.delete(`${BASE_URL}/${listId}/stocks/${stockId}`);
};

export default {
  getStockLists,
  getStockList,
  createStockList,
  updateStockList,
  deleteStockList,
  getListStocks,
  addStockToList,
  batchAddStocksToList,
  removeStockFromList,
};
