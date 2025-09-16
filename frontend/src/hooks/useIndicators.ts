/**
 * 技術指標相關的 React Query hooks
 */
import {
  useQuery,
  useMutation,
  useQueryClient,
  UseQueryOptions,
  UseMutationOptions,
} from '@tanstack/react-query';
import IndicatorsApiService, {
  IndicatorListParams,
  IndicatorCalculateParams,
  IndicatorBatchCalculateParams,
  IndicatorResponse,
  IndicatorBatchResponse,
} from '../services/indicatorsApi';

// Query Keys
export const INDICATORS_QUERY_KEYS = {
  all: ['indicators'] as const,
  lists: () => [...INDICATORS_QUERY_KEYS.all, 'list'] as const,
  list: (params: IndicatorListParams) => [...INDICATORS_QUERY_KEYS.lists(), params] as const,
  specific: (stockId: number, type: string, params?: any) => [...INDICATORS_QUERY_KEYS.all, 'specific', stockId, type, params] as const,
  supported: () => [...INDICATORS_QUERY_KEYS.all, 'supported'] as const,
  tasks: () => [...INDICATORS_QUERY_KEYS.all, 'tasks'] as const,
  task: (taskId: string) => [...INDICATORS_QUERY_KEYS.tasks(), taskId] as const,
};

/**
 * 獲取技術指標列表
 */
export function useIndicators(
  params: IndicatorListParams,
  options?: UseQueryOptions<any, Error>
) {
  return useQuery({
    queryKey: INDICATORS_QUERY_KEYS.list(params),
    queryFn: () => IndicatorsApiService.getIndicators(params),
    enabled: !!params.stock_id,
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 5 * 60 * 1000, // 5 minutes
    ...options,
  });
}

/**
 * 獲取特定類型的技術指標
 */
export function useSpecificIndicator(
  stockId: number,
  indicatorType: string,
  params: {
    period?: number;
    timeframe?: '1d' | '1h' | '5m';
    start_date?: string;
    end_date?: string;
  } = {},
  options?: UseQueryOptions<IndicatorResponse, Error>
) {
  return useQuery({
    queryKey: INDICATORS_QUERY_KEYS.specific(stockId, indicatorType, params),
    queryFn: () => IndicatorsApiService.getSpecificIndicator(stockId, indicatorType, params),
    enabled: !!stockId && !!indicatorType,
    staleTime: 1 * 60 * 1000, // 1 minute
    gcTime: 3 * 60 * 1000, // 3 minutes
    ...options,
  });
}

/**
 * 獲取支援的技術指標列表
 */
export function useSupportedIndicators(
  options?: UseQueryOptions<any, Error>
) {
  return useQuery({
    queryKey: INDICATORS_QUERY_KEYS.supported(),
    queryFn: () => IndicatorsApiService.getSupportedIndicators(),
    staleTime: 60 * 60 * 1000, // 1 hour
    gcTime: 2 * 60 * 60 * 1000, // 2 hours
    ...options,
  });
}

/**
 * 獲取計算任務狀態
 */
export function useCalculationStatus(
  taskId: string,
  options?: UseQueryOptions<any, Error>
) {
  return useQuery({
    queryKey: INDICATORS_QUERY_KEYS.task(taskId),
    queryFn: () => IndicatorsApiService.getCalculationStatus(taskId),
    enabled: !!taskId,
    refetchInterval: (data) => {
      // 如果任務完成或失敗，停止輪詢
      if (data && typeof data === 'object' && 'status' in data) {
        const status = (data as any).status;
        if (status === 'completed' || status === 'failed') {
          return false;
        }
      }
      return 2000; // 每2秒輪詢一次
    },
    staleTime: 0, // 立即過期
    gcTime: 1 * 60 * 1000, // 1 minute
    ...options,
  });
}

/**
 * 計算單一技術指標
 */
export function useCalculateIndicator(
  options?: UseMutationOptions<IndicatorResponse, Error, IndicatorCalculateParams>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params: IndicatorCalculateParams) => IndicatorsApiService.calculateIndicator(params),
    onSuccess: (data, variables) => {
      // 更新指標緩存
      queryClient.setQueryData(
        INDICATORS_QUERY_KEYS.specific(variables.stock_id, variables.indicator_type, {
          period: variables.period,
          timeframe: variables.timeframe,
        }),
        data
      );

      // 使相關的指標列表緩存失效
      queryClient.invalidateQueries({
        queryKey: INDICATORS_QUERY_KEYS.lists(),
        predicate: (query) => {
          const params = query.queryKey[2] as IndicatorListParams;
          return params?.stock_id === variables.stock_id;
        }
      });
    },
    ...options,
  });
}

/**
 * 批量計算技術指標
 */
export function useBatchCalculateIndicators(
  options?: UseMutationOptions<IndicatorBatchResponse, Error, IndicatorBatchCalculateParams>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params: IndicatorBatchCalculateParams) => IndicatorsApiService.batchCalculateIndicators(params),
    onSuccess: (data, variables) => {
      // 使相關的指標緩存失效
      queryClient.invalidateQueries({
        queryKey: INDICATORS_QUERY_KEYS.all,
        predicate: (query) => {
          if (query.queryKey[1] === 'list') {
            const params = query.queryKey[2] as IndicatorListParams;
            return params?.stock_id === variables.stock_id;
          }
          if (query.queryKey[1] === 'specific') {
            return query.queryKey[2] === variables.stock_id;
          }
          return false;
        }
      });
    },
    ...options,
  });
}

/**
 * 刪除指標數據
 */
export function useDeleteIndicatorData(
  options?: UseMutationOptions<{ message: string }, Error, {
    stockId: number;
    indicatorType: string;
    params?: any;
  }>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ stockId, indicatorType, params }) =>
      IndicatorsApiService.deleteIndicatorData(stockId, indicatorType, params),
    onSuccess: (_, variables) => {
      // 移除特定指標緩存
      queryClient.removeQueries({
        queryKey: INDICATORS_QUERY_KEYS.specific(variables.stockId, variables.indicatorType)
      });

      // 使相關的指標列表緩存失效
      queryClient.invalidateQueries({
        queryKey: INDICATORS_QUERY_KEYS.lists(),
        predicate: (query) => {
          const params = query.queryKey[2] as IndicatorListParams;
          return params?.stock_id === variables.stockId;
        }
      });
    },
    ...options,
  });
}

/**
 * 觸發指標重新計算
 */
export function useRecalculateIndicators(
  options?: UseMutationOptions<any, Error, {
    stockId: number;
    params?: any;
  }>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ stockId, params }) => IndicatorsApiService.recalculateIndicators(stockId, params),
    onSuccess: (_, variables) => {
      // 使相關的指標緩存失效
      queryClient.invalidateQueries({
        queryKey: INDICATORS_QUERY_KEYS.all,
        predicate: (query) => {
          if (query.queryKey[1] === 'list') {
            const params = query.queryKey[2] as IndicatorListParams;
            return params?.stock_id === variables.stockId;
          }
          if (query.queryKey[1] === 'specific') {
            return query.queryKey[2] === variables.stockId;
          }
          return false;
        }
      });
    },
    ...options,
  });
}

/**
 * 組合 hook：同時獲取多個常用指標
 */
export function useCommonIndicators(
  stockId: number,
  timeframe: '1d' | '1h' | '5m' = '1d',
  options?: UseQueryOptions<any, Error>
) {
  const indicators = ['SMA', 'EMA', 'RSI', 'MACD'];

  return useQuery({
    queryKey: ['indicators', 'common', stockId, timeframe],
    queryFn: async () => {
      const results = await Promise.allSettled(
        indicators.map(type =>
          IndicatorsApiService.getSpecificIndicator(stockId, type, { timeframe })
        )
      );

      const data: Record<string, any> = {};
      results.forEach((result, index) => {
        if (result.status === 'fulfilled') {
          data[indicators[index]] = result.value;
        } else {
          data[indicators[index]] = { error: result.reason };
        }
      });

      return data;
    },
    enabled: !!stockId,
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 5 * 60 * 1000, // 5 minutes
    ...options,
  });
}