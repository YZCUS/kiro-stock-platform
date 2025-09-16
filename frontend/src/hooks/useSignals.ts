/**
 * 交易信號相關的 React Query hooks
 */
import {
  useQuery,
  useMutation,
  useQueryClient,
  UseQueryOptions,
  UseMutationOptions,
} from '@tanstack/react-query';
import SignalsApiService, { SignalListParams, SignalCreateData, SignalUpdateData } from '../services/signalsApi';
import { TradingSignal, PaginatedResponse } from '../types';

// Query Keys
export const SIGNALS_QUERY_KEYS = {
  all: ['signals'] as const,
  lists: () => [...SIGNALS_QUERY_KEYS.all, 'list'] as const,
  list: (params: SignalListParams) => [...SIGNALS_QUERY_KEYS.lists(), params] as const,
  details: () => [...SIGNALS_QUERY_KEYS.all, 'detail'] as const,
  detail: (id: number) => [...SIGNALS_QUERY_KEYS.details(), id] as const,
  byStock: (stockId: number, params?: any) => [...SIGNALS_QUERY_KEYS.all, 'byStock', stockId, params] as const,
  stats: (params?: any) => [...SIGNALS_QUERY_KEYS.all, 'stats', params] as const,
};

/**
 * 獲取交易信號列表
 */
export function useSignals(
  params: SignalListParams = {},
  options?: UseQueryOptions<PaginatedResponse<TradingSignal>, Error>
) {
  return useQuery({
    queryKey: SIGNALS_QUERY_KEYS.list(params),
    queryFn: () => SignalsApiService.getSignals(params),
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 5 * 60 * 1000, // 5 minutes
    ...options,
  });
}

/**
 * 獲取交易信號詳情
 */
export function useSignal(
  id: number,
  options?: UseQueryOptions<TradingSignal, Error>
) {
  return useQuery({
    queryKey: SIGNALS_QUERY_KEYS.detail(id),
    queryFn: () => SignalsApiService.getSignal(id),
    enabled: !!id,
    staleTime: 1 * 60 * 1000, // 1 minute
    gcTime: 3 * 60 * 1000, // 3 minutes
    ...options,
  });
}

/**
 * 獲取特定股票的交易信號
 */
export function useStockSignals(
  stockId: number,
  params: {
    page?: number;
    pageSize?: number;
    signal_type?: string;
    start_date?: string;
    end_date?: string;
  } = {},
  options?: UseQueryOptions<PaginatedResponse<TradingSignal>, Error>
) {
  return useQuery({
    queryKey: SIGNALS_QUERY_KEYS.byStock(stockId, params),
    queryFn: () => SignalsApiService.getStockSignals(stockId, params),
    enabled: !!stockId,
    staleTime: 1 * 60 * 1000, // 1 minute
    gcTime: 3 * 60 * 1000, // 3 minutes
    ...options,
  });
}

/**
 * 獲取信號統計數據
 */
export function useSignalStats(
  params: {
    stock_id?: number;
    market?: string;
    start_date?: string;
    end_date?: string;
  } = {},
  options?: UseQueryOptions<any, Error>
) {
  return useQuery({
    queryKey: SIGNALS_QUERY_KEYS.stats(params),
    queryFn: () => SignalsApiService.getSignalStats(params),
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    ...options,
  });
}

/**
 * 創建交易信號
 */
export function useCreateSignal(
  options?: UseMutationOptions<TradingSignal, Error, SignalCreateData>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: SignalCreateData) => SignalsApiService.createSignal(data),
    onSuccess: (newSignal) => {
      // 使列表緩存失效
      queryClient.invalidateQueries({ queryKey: SIGNALS_QUERY_KEYS.lists() });

      // 使相關股票的信號緩存失效
      queryClient.invalidateQueries({
        queryKey: SIGNALS_QUERY_KEYS.all,
        predicate: (query) => {
          const [, type, stockId] = query.queryKey;
          return type === 'byStock' && stockId === newSignal.stock_id;
        }
      });

      // 設置新創建信號的緩存
      queryClient.setQueryData(SIGNALS_QUERY_KEYS.detail(newSignal.id), newSignal);

      // 使統計數據失效
      queryClient.invalidateQueries({ queryKey: SIGNALS_QUERY_KEYS.stats() });
    },
    ...options,
  });
}

/**
 * 更新交易信號
 */
export function useUpdateSignal(
  options?: UseMutationOptions<TradingSignal, Error, { id: number; data: SignalUpdateData }>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }) => SignalsApiService.updateSignal(id, data),
    onSuccess: (updatedSignal) => {
      // 更新詳情緩存
      queryClient.setQueryData(SIGNALS_QUERY_KEYS.detail(updatedSignal.id), updatedSignal);

      // 使列表緩存失效
      queryClient.invalidateQueries({ queryKey: SIGNALS_QUERY_KEYS.lists() });

      // 使相關股票的信號緩存失效
      queryClient.invalidateQueries({
        queryKey: SIGNALS_QUERY_KEYS.all,
        predicate: (query) => {
          const [, type, stockId] = query.queryKey;
          return type === 'byStock' && stockId === updatedSignal.stock_id;
        }
      });
    },
    ...options,
  });
}

/**
 * 刪除交易信號
 */
export function useDeleteSignal(
  options?: UseMutationOptions<{ message: string }, Error, number>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => SignalsApiService.deleteSignal(id),
    onSuccess: (_, deletedId) => {
      // 移除詳情緩存
      queryClient.removeQueries({ queryKey: SIGNALS_QUERY_KEYS.detail(deletedId) });

      // 使列表緩存失效
      queryClient.invalidateQueries({ queryKey: SIGNALS_QUERY_KEYS.lists() });

      // 使股票相關的信號緩存失效
      queryClient.invalidateQueries({
        queryKey: SIGNALS_QUERY_KEYS.all,
        predicate: (query) => query.queryKey.includes('byStock')
      });

      // 使統計數據失效
      queryClient.invalidateQueries({ queryKey: SIGNALS_QUERY_KEYS.stats() });
    },
    ...options,
  });
}

/**
 * 訂閱信號推送
 */
export function useSubscribeToSignals(
  options?: UseMutationOptions<any, Error, number[]>
) {
  return useMutation({
    mutationFn: (stockIds: number[]) => SignalsApiService.subscribeToSignals(stockIds),
    ...options,
  });
}

/**
 * 取消訂閱信號推送
 */
export function useUnsubscribeFromSignals(
  options?: UseMutationOptions<any, Error, string>
) {
  return useMutation({
    mutationFn: (subscriptionId: string) => SignalsApiService.unsubscribeFromSignals(subscriptionId),
    ...options,
  });
}

/**
 * 獲取即時信號 (使用輪詢)
 */
export function useRealtimeSignals(
  params: SignalListParams = {},
  options?: UseQueryOptions<PaginatedResponse<TradingSignal>, Error>
) {
  return useQuery({
    queryKey: [...SIGNALS_QUERY_KEYS.list(params), 'realtime'],
    queryFn: () => SignalsApiService.getSignals({
      ...params,
      page: 1,
      pageSize: 50, // 最新50個信號
    }),
    refetchInterval: 5 * 1000, // 每5秒刷新
    staleTime: 0, // 立即過期
    gcTime: 30 * 1000, // 30秒緩存
    ...options,
  });
}