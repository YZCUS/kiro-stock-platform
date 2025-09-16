/**
 * useStocks Hook Tests
 */
import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useStocks, useCreateStock, useDeleteStock } from '../useStocks';
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
  data: [mockStock],
  pagination: {
    page: 1,
    pageSize: 10,
    total: 1,
    totalPages: 1,
  },
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

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
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