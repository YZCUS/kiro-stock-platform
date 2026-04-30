/**
 * StockManagementPage Component Tests
 *
 * 測試狀態管理優化後的 StockManagementPage 組件
 */
import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { Provider } from 'react-redux';
import { combineReducers, configureStore } from '@reduxjs/toolkit';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import StockManagementPage from '../StockManagementPage';
import uiReducer from '../../../store/slices/uiSlice';
import signalsReducer from '../../../store/slices/signalsSlice';
import authReducer from '../../../store/slices/authSlice';
import stockListReducer from '../../../store/slices/stockListSlice';
import * as stockListApi from '../../../services/stockListApi';

const mockRouterPush = jest.fn();

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockRouterPush,
    refresh: jest.fn(),
  }),
}));

jest.mock('../../Portfolio/TransactionModal', () => {
  return function MockTransactionModal() {
    return null;
  };
});

jest.mock('../../../services/stockListApi', () => ({
  getStockLists: jest.fn(),
  getStockList: jest.fn(),
  createStockList: jest.fn(),
  updateStockList: jest.fn(),
  deleteStockList: jest.fn(),
  getListStocks: jest.fn(),
  addStockToList: jest.fn(),
  batchAddStocksToList: jest.fn(),
  removeStockFromList: jest.fn(),
  reorderStockLists: jest.fn(),
  reorderListStocks: jest.fn(),
}));

// Mock the useStocks and useDeleteStock hooks
const mockStocksData = {
  items: [
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
  page: 1,
  per_page: 20,
  total: 3,
  total_pages: 1,
};

const mockUseStocks = jest.fn();
const mockUseDeleteStock = jest.fn();
const mockUseCreateStock = jest.fn();

jest.mock('../../../hooks/useStocks', () => ({
  useStocks: (...args: any[]) => mockUseStocks(...args),
  useDeleteStock: (...args: any[]) => mockUseDeleteStock(...args),
  useCreateStock: (...args: any[]) => mockUseCreateStock(...args),
}));

jest.mock('../../../hooks/useStockValidation', () => ({
  useStockValidation: () => ({
    isValidating: false,
    validationError: null,
    validatedStock: null,
    validate: jest.fn(),
    reset: jest.fn(),
  }),
}));

const mockDefaultList = {
  id: 1,
  name: 'Default Watchlist',
  description: '',
  list_type: 'WATCHLIST',
  is_default: true,
  item_count: mockStocksData.items.length,
  stocks_count: mockStocksData.items.length,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

const rootReducer = combineReducers({
  ui: uiReducer,
  signals: signalsReducer,
  auth: authReducer,
  stockList: stockListReducer,
});

// Test setup
const createTestStore = ({
  lists = [mockDefaultList],
  currentList = mockDefaultList,
  currentListStocks = mockStocksData.items,
  stockListLoading = false,
  stockListError = null,
  isAuthenticated = true,
} = {}) => {
  return configureStore({
    reducer: rootReducer,
    preloadedState: {
      auth: {
        isAuthenticated,
        user: isAuthenticated
          ? {
              id: 'user-1',
              email: 'test@example.com',
              username: 'tester',
              created_at: '2024-01-01T00:00:00Z',
              updated_at: '2024-01-01T00:00:00Z',
            }
          : null,
        token: isAuthenticated ? 'test-token' : null,
        loading: false,
        error: null,
      },
      stockList: {
        lists,
        currentList,
        currentListStocks,
        loading: stockListLoading,
        error: stockListError,
      },
    } as any,
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
    mockRouterPush.mockClear();

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

    mockUseCreateStock.mockReturnValue({
      mutate: jest.fn(),
      isPending: false,
      isError: false,
      error: null,
    });

    (global.confirm as jest.Mock).mockReturnValue(true);
    (stockListApi.getStockLists as jest.Mock).mockResolvedValue({ items: [mockDefaultList] });
    (stockListApi.getListStocks as jest.Mock).mockImplementation(() => new Promise(() => {}));
    (stockListApi.removeStockFromList as jest.Mock).mockResolvedValue({
      message: 'removed',
      list_id: mockDefaultList.id,
      stock_id: mockStocksData.items[0].id,
    });
    (stockListApi.addStockToList as jest.Mock).mockResolvedValue({});
    (stockListApi.reorderListStocks as jest.Mock).mockResolvedValue({ message: 'ok', updated_count: 0 });
    (stockListApi.reorderStockLists as jest.Mock).mockResolvedValue({ message: 'ok', updated_count: 0 });
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

  it('清單模式應該顯示所有清單股票並隱藏 API 分頁控制', () => {
    const mockDataWithPagination = {
      ...mockStocksData,
      page: 1,
      per_page: 2,
      total: 10,
      total_pages: 5,
    };

    mockUseStocks.mockReturnValue({
      data: mockDataWithPagination,
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    });

    render(<StockManagementPage />, { wrapper: createWrapper() });

    expect(screen.getByText('台積電')).toBeInTheDocument();
    expect(screen.getByText('鴻海')).toBeInTheDocument();
    expect(screen.getByText('Apple Inc.')).toBeInTheDocument();
    expect(screen.queryByText(/顯示第/)).not.toBeInTheDocument();
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

  it('應該透過確認對話框從目前清單移除股票', async () => {
    render(<StockManagementPage />, { wrapper: createWrapper() });

    const deleteButtons = screen.getAllByText('移除');
    fireEvent.click(deleteButtons[0]);

    expect(screen.getByText('確認從清單移除')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '確定' }));

    await waitFor(() => {
      expect(stockListApi.removeStockFromList).toHaveBeenCalledWith(1, 1);
    });
  });

  it('應該顯示載入狀態', () => {
    mockUseStocks.mockReturnValue({
      data: null,
      isLoading: true,
      error: null,
      refetch: jest.fn(),
    });

    render(<StockManagementPage />, { wrapper: createWrapper() });

    expect(screen.getAllByText('載入中...').length).toBeGreaterThan(0);
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
      data: { items: [], page: 1, per_page: 20, total: 0, total_pages: 0 },
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    });

    const store = createTestStore({ currentListStocks: [] });
    render(<StockManagementPage />, { wrapper: createWrapper(store) });

    expect(screen.getByText('此清單還沒有股票')).toBeInTheDocument();
  });

  it('應該顯示搜尋無結果狀態', () => {
    render(<StockManagementPage />, { wrapper: createWrapper() });

    const searchInput = screen.getByPlaceholderText('搜尋股票名稱或代號...');
    fireEvent.change(searchInput, { target: { value: '不存在的股票' } });

    expect(screen.getByText('找不到符合條件的股票')).toBeInTheDocument();
  });

  it('應該正確顯示統計信息', () => {
    render(<StockManagementPage />, { wrapper: createWrapper() });

    const totalCard = screen.getByText('當前清單股票數').parentElement;
    const twCard = screen.getByText('台股數量').parentElement;
    const usCard = screen.getByText('美股數量').parentElement;

    expect(totalCard).not.toBeNull();
    expect(twCard).not.toBeNull();
    expect(usCard).not.toBeNull();
    expect(within(totalCard as HTMLElement).getByText('3')).toBeInTheDocument();
    expect(within(twCard as HTMLElement).getByText('2')).toBeInTheDocument();
    expect(within(usCard as HTMLElement).getByText('1')).toBeInTheDocument();
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
    expect(screen.getAllByText('載入中...').length).toBeGreaterThan(0);
  });
});

describe('StockManagementPage - 客戶端狀態管理', () => {
  beforeEach(() => {
    jest.clearAllMocks();
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
    mockUseCreateStock.mockReturnValue({
      mutate: jest.fn(),
      isPending: false,
      isError: false,
      error: null,
    });
    (stockListApi.getListStocks as jest.Mock).mockImplementation(() => new Promise(() => {}));
    (stockListApi.removeStockFromList as jest.Mock).mockResolvedValue({
      message: 'removed',
      list_id: mockDefaultList.id,
      stock_id: mockStocksData.items[0].id,
    });
  });

  it('應該使用 Redux 管理清單移除成功的 Toast 通知', async () => {
    const store = createTestStore();

    render(<StockManagementPage />, {
      wrapper: createWrapper(store)
    });

    const deleteButtons = screen.getAllByText('移除');
    fireEvent.click(deleteButtons[0]);
    fireEvent.click(screen.getByRole('button', { name: '確定' }));

    await waitFor(() => {
      const state = store.getState();
      expect(state.ui.toasts).toHaveLength(1);
      expect(state.ui.toasts[0].type).toBe('success');
      expect(state.ui.toasts[0].title).toBe('成功');
    });
  });

  it('應該處理清單移除失敗的錯誤 Toast', async () => {
    const store = createTestStore();
    (stockListApi.removeStockFromList as jest.Mock).mockRejectedValueOnce({
      response: { data: { detail: '移除失敗' } },
    });

    render(<StockManagementPage />, {
      wrapper: createWrapper(store)
    });

    const deleteButtons = screen.getAllByText('移除');
    fireEvent.click(deleteButtons[0]);
    fireEvent.click(screen.getByRole('button', { name: '確定' }));

    await waitFor(() => {
      const state = store.getState();
      expect(state.ui.toasts).toHaveLength(1);
      expect(state.ui.toasts[0].type).toBe('error');
      expect(state.ui.toasts[0].title).toBe('錯誤');
      expect(state.ui.toasts[0].message).toBe('移除失敗');
    });
  });
});

describe('StockManagementPage - 性能優化', () => {
  beforeEach(() => {
    jest.clearAllMocks();
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
    mockUseCreateStock.mockReturnValue({
      mutate: jest.fn(),
      isPending: false,
      isError: false,
      error: null,
    });
  });

  it('重新渲染時應該維持相同查詢參數', () => {
    const { rerender } = render(<StockManagementPage />, { wrapper: createWrapper() });

    const initialParams = mockUseStocks.mock.calls[mockUseStocks.mock.calls.length - 1][0];

    // 重新渲染但不改變 props
    rerender(<StockManagementPage />);

    expect(mockUseStocks.mock.calls[mockUseStocks.mock.calls.length - 1][0]).toEqual(initialParams);
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
