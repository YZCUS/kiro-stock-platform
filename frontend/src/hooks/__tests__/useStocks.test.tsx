/**
 * useStocks Hook Tests
 */
import React from 'react';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useStocks, useCreateStock, useDeleteStock, useBackfillStockData, STOCKS_QUERY_KEYS } from '../useStocks';
import StocksApiService from '../../services/stocksApi';
import { Stock, PaginatedResponse } from '../../types';

// Mock the API service
jest.mock('../../services/stocksApi');
const mockedStocksApiService = StocksApiService as jest.Mocked<typeof StocksApiService>;

// Mock data
const mockStock: Stock = {
  id: 1,
  symbol: '2330.TW',
  name: '台積電',
  market: 'TW',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

const mockPaginatedResponse: PaginatedResponse<Stock> = {
  items: [mockStock],
  total: 1,
  page: 1,
  per_page: 10,
  total_pages: 1,
};

// Test wrapper with QueryClient
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  });

  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  Wrapper.displayName = 'QueryWrapper';
  return Wrapper;
};

describe('useStocks', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('fetches stocks successfully', async () => {
    mockedStocksApiService.getStocks.mockResolvedValueOnce(mockPaginatedResponse);

    const { result } = renderHook(() => useStocks(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockPaginatedResponse);
    expect(mockedStocksApiService.getStocks).toHaveBeenCalledWith({});
  });

  it('handles error when fetching stocks fails', async () => {
    const error = new Error('Failed to fetch stocks');
    mockedStocksApiService.getStocks.mockRejectedValueOnce(error);

    const { result } = renderHook(() => useStocks(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toEqual(error);
  });

  it('passes parameters to API call', async () => {
    const params = { page: 2, pageSize: 20 };
    mockedStocksApiService.getStocks.mockResolvedValueOnce(mockPaginatedResponse);

    renderHook(() => useStocks(params), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(mockedStocksApiService.getStocks).toHaveBeenCalledWith(params);
    });
  });

  it('shows loading state initially', () => {
    mockedStocksApiService.getStocks.mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    const { result } = renderHook(() => useStocks(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();
  });
});

describe('useCreateStock', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('creates stock successfully', async () => {
    const newStockData = {
      symbol: '2317.TW',
      name: '鴻海',
      market: 'TW' as const,
    };

    mockedStocksApiService.createStock.mockResolvedValueOnce({
      ...mockStock,
      id: 2,
      ...newStockData,
    });

    const { result } = renderHook(() => useCreateStock(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(newStockData);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockedStocksApiService.createStock).toHaveBeenCalledWith(newStockData);
    expect(result.current.data).toEqual({
      ...mockStock,
      id: 2,
      ...newStockData,
    });
  });

  it('handles error when creating stock fails', async () => {
    const error = new Error('Failed to create stock');
    mockedStocksApiService.createStock.mockRejectedValueOnce(error);

    const { result } = renderHook(() => useCreateStock(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      symbol: '2317.TW',
      name: '鴻海',
      market: 'TW',
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toEqual(error);
  });
});

describe('useDeleteStock', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('deletes stock successfully', async () => {
    const mockResponse = { message: 'Stock deleted successfully' };
    mockedStocksApiService.deleteStock.mockResolvedValueOnce(mockResponse);

    const { result } = renderHook(() => useDeleteStock(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(1);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockedStocksApiService.deleteStock).toHaveBeenCalledWith(1);
    expect(result.current.data).toEqual(mockResponse);
  });

  it('handles error when deleting stock fails', async () => {
    const error = new Error('Failed to delete stock');
    mockedStocksApiService.deleteStock.mockRejectedValueOnce(error);

    const { result } = renderHook(() => useDeleteStock(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(1);

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toEqual(error);
  });
});

describe('useBackfillStockData - 優化後的緩存失效測試', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    jest.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    // 模拟 queryClient.invalidateQueries
    jest.spyOn(queryClient, 'invalidateQueries');
  });

  const createWrapperWithClient = () => {
    const Wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
    Wrapper.displayName = 'QueryWrapperWithClient';
    return Wrapper;
  };

  const expectBackfillInvalidations = (stockId: number, params: unknown) => {
    expect(queryClient.invalidateQueries).toHaveBeenCalledTimes(5);

    const invalidateCallsArgs = (queryClient.invalidateQueries as jest.Mock).mock.calls;

    expect(invalidateCallsArgs[0][0]).toEqual({
      queryKey: ['stocks', 'prices']
    });

    expect(invalidateCallsArgs[1][0]).toEqual({
      queryKey: ['stocks', 'prices', stockId, params]
    });

    expect(invalidateCallsArgs[2][0]).toEqual({
      predicate: expect.any(Function)
    });

    expect(invalidateCallsArgs[3][0]).toEqual({
      queryKey: ['stocks', 'prices', stockId, 'latest']
    });

    expect(invalidateCallsArgs[4][0]).toEqual({
      queryKey: ['stocks', 'detail', stockId]
    });
  };

  it('應該用分層策略失效回填相關快取', async () => {
    const mockBackfillResponse = {
      message: "數據回填已完成",
      completed: true,
      success: true,
      symbol: "2330.TW",
      records_processed: 100,
      records_saved: 100,
      date_range: { start: "2024-01-01", end: "2024-01-31" },
      timestamp: "2024-01-01T00:00:00Z"
    };
    mockedStocksApiService.backfillStockData.mockResolvedValueOnce(mockBackfillResponse);

    const { result } = renderHook(() => useBackfillStockData(), {
      wrapper: createWrapperWithClient(),
    });

    const stockId = 1;
    const params = { start_date: '2024-01-01', end_date: '2024-01-31' };

    // 執行回填操作
    await act(async () => {
      result.current.mutate({ stockId, params });
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // 驗證 API 被正確調用
    expect(mockedStocksApiService.backfillStockData).toHaveBeenCalledWith(stockId, params);

    expectBackfillInvalidations(stockId, params);
  });

  it('應該在回填失敗時不執行緩存失效', async () => {
    const error = new Error('Backfill failed');
    mockedStocksApiService.backfillStockData.mockRejectedValueOnce(error);

    const { result } = renderHook(() => useBackfillStockData(), {
      wrapper: createWrapperWithClient(),
    });

    await act(async () => {
      result.current.mutate({ stockId: 1, params: {} });
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    // 失敗時不應該執行緩存失效
    expect(queryClient.invalidateQueries).not.toHaveBeenCalled();
  });

  it('應該正確處理不同股票和參數的緩存失效', async () => {
    const mockResponse = {
      message: "數據回填已完成",
      completed: true,
      success: true,
      symbol: "AAPL",
      records_processed: 50,
      records_saved: 50,
      date_range: { start: "2024-01-01", end: "2024-01-31" },
      timestamp: "2024-01-01T00:00:00Z"
    };
    mockedStocksApiService.backfillStockData.mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useBackfillStockData(), {
      wrapper: createWrapperWithClient(),
    });

    // 測試股票1
    const stockId1 = 1;
    const params1 = { start_date: '2024-01-01' };

    await act(async () => {
      result.current.mutate({ stockId: stockId1, params: params1 });
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // 重置 mock
    (queryClient.invalidateQueries as jest.Mock).mockClear();

    // 測試股票2
    const stockId2 = 2;
    const params2 = { start_date: '2024-02-01', interval: '1h' };

    await act(async () => {
      result.current.mutate({ stockId: stockId2, params: params2 });
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expectBackfillInvalidations(stockId2, params2);
  });

  it('應該在合理時間內完成快取失效', async () => {
    const mockResponse = {
      message: "數據回填已完成",
      completed: true,
      success: true,
      symbol: "TSLA",
      records_processed: 0,
      records_saved: 0,
      date_range: {},
      timestamp: "2024-01-01T00:00:00Z"
    };
    mockedStocksApiService.backfillStockData.mockResolvedValueOnce(mockResponse);

    const { result } = renderHook(() => useBackfillStockData(), {
      wrapper: createWrapperWithClient(),
    });

    const startTime = performance.now();

    await act(async () => {
      result.current.mutate({ stockId: 1, params: {} });
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const endTime = performance.now();
    const executionTime = endTime - startTime;

    expect(queryClient.invalidateQueries).toHaveBeenCalledTimes(5);
    expect(executionTime).toBeLessThan(1000); // 基本的性能檢查
  });
});

describe('useStocks - 緩存鍵一致性測試', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('應該為相同參數生成相同的緩存鍵', () => {
    const params1 = { market: 'TW', page: 1, pageSize: 10 };
    const params2 = { market: 'TW', page: 1, pageSize: 10 };

    expect(STOCKS_QUERY_KEYS.list(params1)).toEqual(STOCKS_QUERY_KEYS.list(params2));
  });

  it('應該為不同參數生成不同的緩存鍵', () => {
    const params1 = { market: 'TW', page: 1 };
    const params2 = { market: 'US', page: 1 };

    mockedStocksApiService.getStocks.mockResolvedValue(mockPaginatedResponse);

    // 不同參數的兩次調用
    renderHook(() => useStocks(params1), { wrapper: createWrapper() });
    renderHook(() => useStocks(params2), { wrapper: createWrapper() });

    // API 應該被調用兩次（不同的緩存鍵）
    expect(mockedStocksApiService.getStocks).toHaveBeenCalledTimes(2);
    expect(mockedStocksApiService.getStocks).toHaveBeenCalledWith(params1);
    expect(mockedStocksApiService.getStocks).toHaveBeenCalledWith(params2);
  });
});
