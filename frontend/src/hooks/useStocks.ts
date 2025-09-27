/**
 * 股票相關的 React Query hooks
 */
import {
  useQuery,
  useMutation,
  useQueryClient,
  UseQueryOptions,
  UseMutationOptions,
} from '@tanstack/react-query';
import StocksApiService, { StockListParams, StockCreateData, StockUpdateData } from '../services/stocksApi';
import { Stock, PaginatedResponse } from '../types';

// Query Keys
export const STOCKS_QUERY_KEYS = {
  all: ['stocks'] as const,
  lists: () => [...STOCKS_QUERY_KEYS.all, 'list'] as const,
  list: (params: StockListParams) => [...STOCKS_QUERY_KEYS.lists(), params] as const,
  details: () => [...STOCKS_QUERY_KEYS.all, 'detail'] as const,
  detail: (id: number) => [...STOCKS_QUERY_KEYS.details(), id] as const,
  prices: () => [...STOCKS_QUERY_KEYS.all, 'prices'] as const,
  priceHistory: (stockId: number, params: any) => [...STOCKS_QUERY_KEYS.prices(), stockId, params] as const,
  latestPrice: (stockId: number) => [...STOCKS_QUERY_KEYS.prices(), stockId, 'latest'] as const,
};

/**
 * 獲取股票列表
 */
export function useStocks(
  params: StockListParams = {},
  options?: UseQueryOptions<PaginatedResponse<Stock>, Error>
) {
  return useQuery({
    queryKey: STOCKS_QUERY_KEYS.list(params),
    queryFn: () => StocksApiService.getStocks(params),
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    ...options,
  });
}

/**
 * 獲取股票詳情
 */
export function useStock(
  id: number,
  options?: UseQueryOptions<Stock, Error>
) {
  return useQuery({
    queryKey: STOCKS_QUERY_KEYS.detail(id),
    queryFn: () => StocksApiService.getStock(id),
    enabled: !!id,
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 5 * 60 * 1000, // 5 minutes
    ...options,
  });
}

/**
 * 獲取股票價格歷史
 */
export function useStockPriceHistory(
  stockId: number,
  params: {
    start_date?: string;
    end_date?: string;
    interval?: '1d' | '1h' | '5m';
  } = {},
  options?: UseQueryOptions<any, Error>
) {
  return useQuery({
    queryKey: STOCKS_QUERY_KEYS.priceHistory(stockId, params),
    queryFn: () => StocksApiService.getStockPriceHistory(stockId, params),
    enabled: !!stockId,
    staleTime: 1 * 60 * 1000, // 1 minute
    gcTime: 5 * 60 * 1000, // 5 minutes
    ...options,
  });
}

/**
 * 獲取股票最新價格
 */
export function useStockLatestPrice(
  stockId: number,
  options?: UseQueryOptions<any, Error>
) {
  return useQuery({
    queryKey: STOCKS_QUERY_KEYS.latestPrice(stockId),
    queryFn: () => StocksApiService.getStockLatestPrice(stockId),
    enabled: !!stockId,
    refetchInterval: 10 * 1000, // 每10秒刷新
    staleTime: 5 * 1000, // 5 seconds
    gcTime: 1 * 60 * 1000, // 1 minute
    ...options,
  });
}

/**
 * 創建股票
 */
export function useCreateStock(
  options?: UseMutationOptions<Stock, Error, StockCreateData>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: StockCreateData) => StocksApiService.createStock(data),
    onSuccess: (data) => {
      // 使列表緩存失效
      queryClient.invalidateQueries({ queryKey: STOCKS_QUERY_KEYS.lists() });

      // 設置新創建股票的緩存
      queryClient.setQueryData(STOCKS_QUERY_KEYS.detail(data.id), data);
    },
    ...options,
  });
}

/**
 * 更新股票
 */
export function useUpdateStock(
  options?: UseMutationOptions<Stock, Error, { id: number; data: StockUpdateData }>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }) => StocksApiService.updateStock(id, data),
    onSuccess: (updatedStock) => {
      // 更新詳情緩存
      queryClient.setQueryData(STOCKS_QUERY_KEYS.detail(updatedStock.id), updatedStock);

      // 使列表緩存失效
      queryClient.invalidateQueries({ queryKey: STOCKS_QUERY_KEYS.lists() });
    },
    ...options,
  });
}

/**
 * 刪除股票
 */
export function useDeleteStock(
  options?: UseMutationOptions<{ message: string }, Error, number>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => StocksApiService.deleteStock(id),
    onSuccess: (_, deletedId) => {
      // 移除詳情緩存
      queryClient.removeQueries({ queryKey: STOCKS_QUERY_KEYS.detail(deletedId) });

      // 使列表緩存失效
      queryClient.invalidateQueries({ queryKey: STOCKS_QUERY_KEYS.lists() });

      // 移除相關的價格數據緩存
      queryClient.removeQueries({ queryKey: STOCKS_QUERY_KEYS.prices() });
    },
    ...options,
  });
}

/**
 * 批量創建股票
 */
export function useBatchCreateStocks(
  options?: UseMutationOptions<any, Error, { stocks: StockCreateData[] }>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data) => StocksApiService.batchCreateStocks(data),
    onSuccess: () => {
      // 使列表緩存失效
      queryClient.invalidateQueries({ queryKey: STOCKS_QUERY_KEYS.lists() });
    },
    ...options,
  });
}

/**
 * 刷新股票數據
 */
export function useRefreshStockData(
  options?: UseMutationOptions<any, Error, number>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => StocksApiService.refreshStockData(id),
    onSuccess: (_, stockId) => {
      // 使相關緩存失效
      queryClient.invalidateQueries({ queryKey: STOCKS_QUERY_KEYS.detail(stockId) });
      queryClient.invalidateQueries({ queryKey: STOCKS_QUERY_KEYS.latestPrice(stockId) });
    },
    ...options,
  });
}

/**
 * 股票數據回填
 */
export function useBackfillStockData(
  options?: UseMutationOptions<{
    message: string;
    completed: boolean;
    success: boolean;
    symbol: string;
    records_processed: number;
    records_saved: number;
    date_range: any;
    timestamp: string;
  }, Error, { stockId: number; params: any }>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ stockId, params }) => StocksApiService.backfillStockData(stockId, params),
    onSuccess: (_, { stockId, params }) => {
      // 修正：使用多層級策略確保所有相關快取都被正確無效化
      // 解決了之前 includes() 方法無法正確匹配 React Query 鍵結構的問題

      // 1. 無效化所有價格相關查詢（使用查詢鍵前綴匹配）
      // 這會無效化所有以 ['stocks', 'prices'] 開頭的查詢
      queryClient.invalidateQueries({
        queryKey: STOCKS_QUERY_KEYS.prices()
      });

      // 2. 無效化特定股票的價格歷史查詢（精確匹配）
      queryClient.invalidateQueries({
        queryKey: STOCKS_QUERY_KEYS.priceHistory(stockId, params)
      });

      // 3. 無效化該股票的所有價格歷史查詢（不限參數）
      // 使用精確的陣列位置檢查，而非不可靠的 includes()
      queryClient.invalidateQueries({
        predicate: (query) => {
          const queryKey = query.queryKey;
          // 檢查查詢鍵結構：['stocks', 'prices', stockId, params]
          return Array.isArray(queryKey) &&
                 queryKey.length >= 3 &&
                 queryKey[0] === 'stocks' &&
                 queryKey[1] === 'prices' &&
                 queryKey[2] === stockId;
        }
      });

      // 4. 無效化最新價格查詢
      queryClient.invalidateQueries({
        queryKey: STOCKS_QUERY_KEYS.latestPrice(stockId)
      });

      // 5. 無效化股票詳情以確保相關數據同步
      queryClient.invalidateQueries({
        queryKey: STOCKS_QUERY_KEYS.detail(stockId)
      });
    },
    ...options,
  });
}