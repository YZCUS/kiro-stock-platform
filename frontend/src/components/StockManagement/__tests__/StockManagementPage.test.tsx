/**
 * StockManagementPage Component Tests
 *
 * 測試狀態管理優化後的 StockManagementPage 組件
 */
import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import StockManagementPage from '../StockManagementPage';
import uiReducer from '../../../store/slices/uiSlice';
import signalsReducer from '../../../store/slices/signalsSlice';

// Mock the useStocks and useDeleteStock hooks
const mockStocksData = {
  data: [
    {
      id: 1,
      symbol: '2330.TW',
      name: '台積電',
      market: 'TW',
      is_active: true,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
    {
      id: 2,
      symbol: '2317.TW',
      name: '鴻海',
      market: 'TW',
      is_active: true,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
    {
      id: 3,
      symbol: 'AAPL',
      name: 'Apple Inc.',
      market: 'US',
      is_active: true,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
  ],
  pagination: {
    page: 1,
    pageSize: 20,
    total: 3,
    totalPages: 1,
  },
};

const mockUseStocks = jest.fn();
const mockUseDeleteStock = jest.fn();

jest.mock('../../../hooks/useStocks', () => ({
  useStocks: (...args: any[]) => mockUseStocks(...args),
  useDeleteStock: (...args: any[]) => mockUseDeleteStock(...args),
}));

// Test setup
const createTestStore = () => {
  return configureStore({
    reducer: {
      ui: uiReducer,
      signals: signalsReducer,
    },
  });
};

const createQueryClient = () => {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  });
};

const createWrapper = (store = createTestStore(), queryClient = createQueryClient()) => {
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <Provider store={store}>
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    </Provider>
  );
  Wrapper.displayName = 'TestWrapper';
  return Wrapper;
};

// Mock window.confirm
global.confirm = jest.fn();

describe('StockManagementPage - 狀態管理優化測試', () => {
  beforeEach(() => {
    jest.clearAllMocks();

    // Default mock implementations
    mockUseStocks.mockReturnValue({
      data: mockStocksData,
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    });

    mockUseDeleteStock.mockReturnValue({
      mutate: jest.fn(),
      isPending: false,
      isError: false,
      error: null,
    });

    (global.confirm as jest.Mock).mockReturnValue(true);
  });

  it('應該使用 React Query 獲取股票數據而不是 Redux', () => {
    render(<StockManagementPage />, { wrapper: createWrapper() });

    // 驗證 useStocks hook 被調用
    expect(mockUseStocks).toHaveBeenCalledWith({
      page: 1,
      pageSize: 20,
    });

    // 驗證股票列表被渲染
    expect(screen.getByText('台積電')).toBeInTheDocument();
    expect(screen.getByText('鴻海')).toBeInTheDocument();
    expect(screen.getByText('Apple Inc.')).toBeInTheDocument();
  });

  it('應該正確顯示分頁信息', () => {
    const mockDataWithPagination = {
      ...mockStocksData,
      pagination: {
        page: 1,
        pageSize: 2,
        total: 10,
        totalPages: 5,
      },
    };

    mockUseStocks.mockReturnValue({
      data: mockDataWithPagination,
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    });

    render(<StockManagementPage />, { wrapper: createWrapper() });

    // 驗證分頁控制顯示
    expect(screen.getByText(/顯示第 1 到 2 頁，共 10 頁/)).toBeInTheDocument();
  });

  it('應該處理搜尋功能並重新查詢', () => {
    render(<StockManagementPage />, { wrapper: createWrapper() });

    const searchInput = screen.getByPlaceholderText('搜尋股票名稱或代號...');

    // 模擬搜尋輸入
    fireEvent.change(searchInput, { target: { value: '台積電' } });

    // 驗證搜尋參數被正確傳遞
    expect(mockUseStocks).toHaveBeenLastCalledWith({
      page: 1,
      pageSize: 20,
      search: '台積電',
    });
  });

  it('應該處理分頁變更', () => {
    // Mock 有多頁的數據
    const mockDataWithMultiplePages = {
      ...mockStocksData,
      pagination: {
        page: 1,
        pageSize: 1,
        total: 3,
        totalPages: 3,
      },
    };

    mockUseStocks.mockReturnValue({
      data: mockDataWithMultiplePages,
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    });

    render(<StockManagementPage />, { wrapper: createWrapper() });

    // 點擊頁碼2
    const page2Button = screen.getByText('2');
    fireEvent.click(page2Button);

    // 驗證分頁參數被更新
    expect(mockUseStocks).toHaveBeenLastCalledWith({
      page: 2,
      pageSize: 20,
    });
  });

  it('應該使用 React Query mutation 處理股票刪除', async () => {
    const mockMutate = jest.fn();
    mockUseDeleteStock.mockReturnValue({
      mutate: mockMutate,
      isPending: false,
      isError: false,
      error: null,
    });

    render(<StockManagementPage />, { wrapper: createWrapper() });

    // 點擊刪除按鈕
    const deleteButtons = screen.getAllByText('移除');
    fireEvent.click(deleteButtons[0]);

    // 驗證 mutation 被調用
    expect(mockMutate).toHaveBeenCalledWith(1);
  });

  it('應該顯示載入狀態', () => {
    mockUseStocks.mockReturnValue({
      data: null,
      isLoading: true,
      error: null,
      refetch: jest.fn(),
    });

    render(<StockManagementPage />, { wrapper: createWrapper() });

    expect(screen.getByText('載入中...')).toBeInTheDocument();
  });

  it('應該顯示錯誤狀態和重試功能', () => {
    const mockRefetch = jest.fn();
    mockUseStocks.mockReturnValue({
      data: null,
      isLoading: false,
      error: { message: '網路連接失敗' },
      refetch: mockRefetch,
    });

    render(<StockManagementPage />, { wrapper: createWrapper() });

    expect(screen.getByText('網路連接失敗')).toBeInTheDocument();

    // 點擊重新載入
    const retryButton = screen.getByText('重新載入');
    fireEvent.click(retryButton);

    expect(mockRefetch).toHaveBeenCalled();
  });

  it('應該顯示空狀態', () => {
    mockUseStocks.mockReturnValue({
      data: { data: [], pagination: { page: 1, pageSize: 20, total: 0, totalPages: 0 } },
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    });

    render(<StockManagementPage />, { wrapper: createWrapper() });

    expect(screen.getByText('尚未新增任何股票')).toBeInTheDocument();
  });

  it('應該顯示搜尋無結果狀態', () => {
    mockUseStocks.mockReturnValue({
      data: { data: [], pagination: { page: 1, pageSize: 20, total: 0, totalPages: 0 } },
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    });

    render(<StockManagementPage />, { wrapper: createWrapper() });

    const searchInput = screen.getByPlaceholderText('搜尋股票名稱或代號...');
    fireEvent.change(searchInput, { target: { value: '不存在的股票' } });

    expect(screen.getByText('找不到符合條件的股票')).toBeInTheDocument();
  });

  it('應該正確顯示統計信息', () => {
    render(<StockManagementPage />, { wrapper: createWrapper() });

    // 驗證總數
    expect(screen.getByText('3')).toBeInTheDocument(); // 總數

    // 驗證台股數量
    expect(screen.getByText('2')).toBeInTheDocument(); // 台股有2支

    // 驗證美股數量
    expect(screen.getByText('1')).toBeInTheDocument(); // 美股有1支
  });

  it('應該處理刪除操作的載入狀態', () => {
    mockUseDeleteStock.mockReturnValue({
      mutate: jest.fn(),
      isPending: true,
      isError: false,
      error: null,
    });

    render(<StockManagementPage />, { wrapper: createWrapper() });

    // 驗證載入狀態顯示
    expect(screen.getByText('載入中...')).toBeInTheDocument();
  });
});

describe('StockManagementPage - 客戶端狀態管理', () => {
  it('應該只使用 Redux 管理 UI 狀態（Toast 通知）', async () => {
    const store = createTestStore();
    const mockMutate = jest.fn();

    // Mock 成功的刪除操作
    mockUseDeleteStock.mockImplementation((options) => {
      return {
        mutate: (id: number) => {
          mockMutate(id);
          // 模擬成功回調
          if (options?.onSuccess) {
            options.onSuccess();
          }
        },
        isPending: false,
        isError: false,
        error: null,
      };
    });

    render(<StockManagementPage />, {
      wrapper: createWrapper(store)
    });

    // 點擊刪除按鈕
    const deleteButtons = screen.getAllByText('移除');
    fireEvent.click(deleteButtons[0]);

    // 驗證 Toast 狀態被添加到 Redux store
    const state = store.getState();
    expect(state.ui.toasts).toHaveLength(1);
    expect(state.ui.toasts[0].type).toBe('success');
    expect(state.ui.toasts[0].title).toBe('成功');
  });

  it('應該處理刪除失敗的錯誤 Toast', () => {
    const store = createTestStore();
    const mockMutate = jest.fn();

    // Mock 失敗的刪除操作
    mockUseDeleteStock.mockImplementation((options) => {
      return {
        mutate: (id: number) => {
          mockMutate(id);
          // 模擬失敗回調
          if (options?.onError) {
            options.onError(new Error('刪除失敗'));
          }
        },
        isPending: false,
        isError: false,
        error: null,
      };
    });

    render(<StockManagementPage />, {
      wrapper: createWrapper(store)
    });

    // 點擊刪除按鈕
    const deleteButtons = screen.getAllByText('移除');
    fireEvent.click(deleteButtons[0]);

    // 驗證錯誤 Toast 被添加
    const state = store.getState();
    expect(state.ui.toasts).toHaveLength(1);
    expect(state.ui.toasts[0].type).toBe('error');
    expect(state.ui.toasts[0].title).toBe('錯誤');
  });
});

describe('StockManagementPage - 性能優化', () => {
  it('應該使用 useMemo 優化查詢參數', () => {
    const { rerender } = render(<StockManagementPage />, { wrapper: createWrapper() });

    const initialCallCount = mockUseStocks.mock.calls.length;

    // 重新渲染但不改變 props
    rerender(<StockManagementPage />);

    // useStocks 不應該因為重新渲染而被額外調用
    expect(mockUseStocks.mock.calls.length).toBe(initialCallCount);
  });

  it('應該正確處理防抖搜尋（概念驗證）', () => {
    render(<StockManagementPage />, { wrapper: createWrapper() });

    const searchInput = screen.getByPlaceholderText('搜尋股票名稱或代號...');

    // 快速連續輸入
    fireEvent.change(searchInput, { target: { value: '台' } });
    fireEvent.change(searchInput, { target: { value: '台積' } });
    fireEvent.change(searchInput, { target: { value: '台積電' } });

    // 驗證最終查詢參數
    expect(mockUseStocks).toHaveBeenLastCalledWith({
      page: 1,
      pageSize: 20,
      search: '台積電',
    });
  });
});