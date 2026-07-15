/**
 * StockManagementPage Component Tests
 *
 * 測試狀態管理優化後的 StockManagementPage 組件
 */
import React from "react";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  within,
} from "@testing-library/react";
import { Provider } from "react-redux";
import { combineReducers, configureStore } from "@reduxjs/toolkit";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import StockManagementPage from "../StockManagementPage";
import uiReducer from "../../../store/slices/uiSlice";
import signalsReducer from "../../../store/slices/signalsSlice";
import authReducer from "../../../store/slices/authSlice";
import stockListReducer from "../../../store/slices/stockListSlice";
import * as stockListApi from "../../../services/stockListApi";
import * as portfolioApi from "../../../services/portfolioApi";
import StocksApiService from "../../../services/stocksApi";

const mockRouterPush = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockRouterPush,
    refresh: jest.fn(),
  }),
}));

jest.mock("../../Portfolio/TransactionModal", () => {
  return function MockTransactionModal() {
    return null;
  };
});

jest.mock("../../../services/stockListApi", () => ({
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

jest.mock("../../../services/stocksApi", () => ({
  __esModule: true,
  default: {
    getStocks: jest.fn(),
    backfillStockData: jest.fn(),
    prefetchStockPrices: jest.fn(),
  },
}));

jest.mock("../../../services/portfolioApi", () => ({
  getPortfolioList: jest.fn(),
}));

// Mock the useStocks and useDeleteStock hooks
const mockStocksData = {
  items: [
    {
      id: 1,
      symbol: "2330.TW",
      name: "台積電",
      market: "TW",
      is_active: true,
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z",
    },
    {
      id: 2,
      symbol: "2317.TW",
      name: "鴻海",
      market: "TW",
      is_active: true,
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z",
    },
    {
      id: 3,
      symbol: "AAPL",
      name: "Apple Inc.",
      market: "US",
      is_active: true,
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z",
    },
  ],
  page: 1,
  per_page: 20,
  total: 3,
  total_pages: 1,
};

const mockPortfolioData = {
  items: [
    {
      id: 101,
      user_id: "user-1",
      stock_id: 1,
      stock_symbol: "2330.TW",
      stock_name: "台積電",
      quantity: 10,
      avg_cost: 600,
      total_cost: 6000,
      current_price: 650,
      current_value: 6500,
      profit_loss: 500,
      profit_loss_percent: 8.33,
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-02T00:00:00Z",
    },
    {
      id: 102,
      user_id: "user-1",
      stock_id: 3,
      stock_symbol: "AAPL",
      stock_name: "Apple Inc.",
      quantity: 5,
      avg_cost: 180,
      total_cost: 900,
      current_price: 190,
      current_value: 950,
      profit_loss: 50,
      profit_loss_percent: 5.56,
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-02T00:00:00Z",
    },
  ],
  total: 2,
  total_cost: 6900,
  total_current_value: 7450,
  total_profit_loss: 550,
  total_profit_loss_percent: 7.97,
};

const mockUseDeleteStock = jest.fn();
const mockUseCreateStock = jest.fn();

jest.mock("../../../hooks/useStocks", () => ({
  useDeleteStock: (...args: any[]) => mockUseDeleteStock(...args),
  useCreateStock: (...args: any[]) => mockUseCreateStock(...args),
}));

jest.mock("../../../hooks/useStockValidation", () => ({
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
  name: "Default Watchlist",
  description: "",
  list_type: "WATCHLIST",
  is_default: true,
  item_count: mockStocksData.items.length,
  stocks_count: mockStocksData.items.length,
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
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
              id: "user-1",
              email: "test@example.com",
              username: "tester",
              created_at: "2024-01-01T00:00:00Z",
              updated_at: "2024-01-01T00:00:00Z",
            }
          : null,
        token: isAuthenticated ? "test-token" : null,
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

const createWrapper = (
  store = createTestStore(),
  queryClient = createQueryClient(),
) => {
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <Provider store={store}>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </Provider>
  );
  Wrapper.displayName = "TestWrapper";
  return Wrapper;
};

const openPortfolioView = async () => {
  const selector = await screen.findByRole("button", {
    name: /Default Watchlist/,
  });
  await waitFor(() => expect(selector).toBeEnabled());
  fireEvent.click(selector);
  fireEvent.click(screen.getByRole("button", { name: "我的持倉" }));
};

// Mock window.confirm
global.confirm = jest.fn();

describe("StockManagementPage - 狀態管理優化測試", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockRouterPush.mockClear();

    // Default mock implementations
    (portfolioApi.getPortfolioList as jest.Mock).mockResolvedValue(
      mockPortfolioData,
    );

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
    (stockListApi.getStockLists as jest.Mock).mockResolvedValue({
      items: [mockDefaultList],
    });
    (stockListApi.getListStocks as jest.Mock).mockImplementation(
      () => new Promise(() => {}),
    );
    (stockListApi.removeStockFromList as jest.Mock).mockResolvedValue({
      message: "removed",
      list_id: mockDefaultList.id,
      stock_id: mockStocksData.items[0].id,
    });
    (stockListApi.addStockToList as jest.Mock).mockResolvedValue({});
    (stockListApi.reorderListStocks as jest.Mock).mockResolvedValue({
      message: "ok",
      updated_count: 0,
    });
    (stockListApi.reorderStockLists as jest.Mock).mockResolvedValue({
      message: "ok",
      updated_count: 0,
    });
    (StocksApiService.getStocks as jest.Mock).mockResolvedValue({
      items: [],
      page: 1,
      per_page: 20,
      total: 0,
      total_pages: 0,
    });
    (StocksApiService.backfillStockData as jest.Mock).mockResolvedValue({
      success: true,
      message: "success",
      data_points: 700,
    });
    (StocksApiService.prefetchStockPrices as jest.Mock).mockResolvedValue({
      success: true,
      message: "success",
      total_stocks: 0,
      updated: 0,
      skipped: 0,
      failed: 0,
      total_records: 0,
      errors: [],
      results: [],
    });
  });

  it("清單模式應使用 Redux 清單資料且不呼叫持倉 API", () => {
    render(<StockManagementPage />, { wrapper: createWrapper() });

    expect(portfolioApi.getPortfolioList).not.toHaveBeenCalled();
    expect(screen.getByText("台積電")).toBeInTheDocument();
    expect(screen.getByText("鴻海")).toBeInTheDocument();
    expect(screen.getByText("Apple Inc.")).toBeInTheDocument();
  });

  it("清單模式應該顯示所有清單股票並隱藏分頁控制", () => {
    render(<StockManagementPage />, { wrapper: createWrapper() });

    expect(screen.getByText("台積電")).toBeInTheDocument();
    expect(screen.getByText("鴻海")).toBeInTheDocument();
    expect(screen.getByText("Apple Inc.")).toBeInTheDocument();
    expect(screen.queryByText(/顯示第/)).not.toBeInTheDocument();
  });

  it("應該在目前清單內搜尋，不發出額外 API 請求", () => {
    render(<StockManagementPage />, { wrapper: createWrapper() });

    const searchInput = screen.getByPlaceholderText("搜尋股票名稱或代號...");
    fireEvent.change(searchInput, { target: { value: "台積電" } });

    expect(screen.getByText("台積電")).toBeInTheDocument();
    expect(screen.queryByText("鴻海")).not.toBeInTheDocument();
    expect(screen.queryByText("Apple Inc.")).not.toBeInTheDocument();
    expect(portfolioApi.getPortfolioList).not.toHaveBeenCalled();
  });

  it("應該透過確認對話框從目前清單移除股票", async () => {
    render(<StockManagementPage />, { wrapper: createWrapper() });

    const deleteButtons = screen.getAllByText("移除");
    fireEvent.click(deleteButtons[0]);

    expect(screen.getByText("確認從清單移除")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "確定" }));

    await waitFor(() => {
      expect(stockListApi.removeStockFromList).toHaveBeenCalledWith(1, 1);
    });
  });

  it("切換持倉時應該顯示載入狀態", async () => {
    (portfolioApi.getPortfolioList as jest.Mock).mockImplementationOnce(
      () => new Promise(() => {}),
    );

    render(<StockManagementPage />, { wrapper: createWrapper() });
    await openPortfolioView();

    expect(screen.getAllByText("載入中...").length).toBeGreaterThan(0);
  });

  it("持倉 API 失敗時應顯示可重試的錯誤狀態", async () => {
    (portfolioApi.getPortfolioList as jest.Mock).mockRejectedValueOnce(
      new Error("持倉服務暫時無法使用"),
    );

    render(<StockManagementPage />, { wrapper: createWrapper() });
    await openPortfolioView();

    expect(await screen.findByText("持倉服務暫時無法使用")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "重新載入" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("目前沒有持倉")).not.toBeInTheDocument();
  });

  it("清單模式不應執行持倉查詢", () => {
    render(<StockManagementPage />, { wrapper: createWrapper() });

    expect(portfolioApi.getPortfolioList).not.toHaveBeenCalled();
  });

  it("應該顯示空狀態", async () => {
    (stockListApi.getListStocks as jest.Mock).mockResolvedValueOnce({
      list_id: mockDefaultList.id,
      items: [],
      total: 0,
    });

    const store = createTestStore({ currentListStocks: [] });
    render(<StockManagementPage />, { wrapper: createWrapper(store) });

    expect(await screen.findByText("此清單還沒有股票")).toBeInTheDocument();
  });

  it("尚無清單時應該提供可執行的指引，不顯示無效按鈕", () => {
    (stockListApi.getStockLists as jest.Mock).mockImplementationOnce(
      () => new Promise(() => {}),
    );
    const store = createTestStore({
      lists: [],
      currentList: null,
      currentListStocks: [],
    });

    render(<StockManagementPage />, { wrapper: createWrapper(store) });

    expect(screen.getByText("尚未建立觀察清單")).toBeInTheDocument();
    expect(
      screen.getByText(/使用上方清單選擇器的「新建清單」/),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "建立第一個清單" }),
    ).not.toBeInTheDocument();
  });

  it("清單載入失敗時只顯示錯誤狀態，不同時顯示空狀態", async () => {
    (stockListApi.getListStocks as jest.Mock).mockRejectedValueOnce({
      response: { data: { detail: "清單服務暫時無法使用" } },
    });
    const store = createTestStore({ currentListStocks: [] });

    render(<StockManagementPage />, { wrapper: createWrapper(store) });

    expect(await screen.findByText("清單服務暫時無法使用")).toBeInTheDocument();
    expect(screen.getByText("無法載入股票資料")).toBeInTheDocument();
    expect(screen.queryByText("此清單還沒有股票")).not.toBeInTheDocument();
  });

  it("價格不存在時應該顯示更新中狀態", () => {
    const store = createTestStore({
      currentListStocks: [
        {
          ...mockStocksData.items[0],
          latest_price: null,
        } as any,
      ],
    });

    render(<StockManagementPage />, { wrapper: createWrapper(store) });

    expect(screen.getByText("價格更新中")).toBeInTheDocument();
    expect(screen.getByText("待更新")).toBeInTheDocument();
  });

  it("新增既有股票到清單後應該背景回填價格", async () => {
    (StocksApiService.getStocks as jest.Mock).mockResolvedValueOnce({
      items: [
        {
          id: 9,
          symbol: "TSLA",
          name: "Tesla, Inc.",
          market: "US",
          is_active: true,
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-01T00:00:00Z",
        },
      ],
      page: 1,
      per_page: 20,
      total: 1,
      total_pages: 1,
    });

    render(<StockManagementPage />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByRole("button", { name: "新增股票" }));
    fireEvent.change(
      screen.getByPlaceholderText(
        "台股輸入數字（如 2330）或美股英文（如 AAPL）",
      ),
      {
        target: { value: "TSLA" },
      },
    );
    fireEvent.click(screen.getByRole("button", { name: "確認新增" }));

    await waitFor(() => {
      expect(stockListApi.addStockToList).toHaveBeenCalledWith(1, {
        stock_id: 9,
      });
    });

    expect(StocksApiService.backfillStockData).toHaveBeenCalledWith(
      9,
      expect.objectContaining({
        start_date: expect.any(String),
        end_date: expect.any(String),
      }),
    );
  });

  it("新增股票對話框應該支援 Escape 並把焦點還給觸發按鈕", async () => {
    render(<StockManagementPage />, { wrapper: createWrapper() });

    const trigger = screen.getByRole("button", { name: "新增股票" });
    trigger.focus();
    fireEvent.click(trigger);

    const dialog = screen.getByRole("dialog", { name: "新增股票" });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    await waitFor(() => {
      expect(screen.getByLabelText(/股票代號/)).toHaveFocus();
    });

    fireEvent.keyDown(document, { key: "Escape" });

    expect(
      screen.queryByRole("dialog", { name: "新增股票" }),
    ).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it("持倉模式應直接使用 portfolio API 的 stock_id 與 current_price", async () => {
    render(<StockManagementPage />, { wrapper: createWrapper() });
    await openPortfolioView();

    expect(portfolioApi.getPortfolioList).toHaveBeenCalledTimes(1);
    expect(await screen.findByText("NT$650.00")).toBeInTheDocument();
    expect(screen.getByText("$190.00")).toBeInTheDocument();
    expect(screen.getAllByText("待更新")).toHaveLength(2);
    expect(
      screen.getByRole("link", { name: "查看 2330.TW 圖表" }),
    ).toHaveAttribute("href", "/dashboard?stock=1");
    expect(
      screen.queryByRole("navigation", { name: "股票分頁" }),
    ).not.toBeInTheDocument();

    const totalCard = screen.getByText("持倉股票數").parentElement;
    expect(totalCard).not.toBeNull();
    expect(within(totalCard as HTMLElement).getByText("2")).toBeInTheDocument();
  });

  it("持倉搜尋應在已載入的完整清單內完成", async () => {
    render(<StockManagementPage />, { wrapper: createWrapper() });
    await openPortfolioView();
    await screen.findByText("NT$650.00");

    fireEvent.change(screen.getByPlaceholderText("搜尋股票名稱或代號..."), {
      target: { value: "AAPL" },
    });

    expect(screen.getByText("Apple Inc.")).toBeInTheDocument();
    expect(screen.queryByText("台積電")).not.toBeInTheDocument();
    expect(portfolioApi.getPortfolioList).toHaveBeenCalledTimes(1);
  });

  it("應該顯示搜尋無結果狀態", () => {
    render(<StockManagementPage />, { wrapper: createWrapper() });

    const searchInput = screen.getByPlaceholderText("搜尋股票名稱或代號...");
    fireEvent.change(searchInput, { target: { value: "不存在的股票" } });

    expect(screen.getByText("找不到符合條件的股票")).toBeInTheDocument();
  });

  it("應該正確顯示統計信息", () => {
    render(<StockManagementPage />, { wrapper: createWrapper() });

    const totalCard = screen.getByText("當前清單股票數").parentElement;
    const twCard = screen.getByText("台股數量").parentElement;
    const usCard = screen.getByText("美股數量").parentElement;

    expect(totalCard).not.toBeNull();
    expect(twCard).not.toBeNull();
    expect(usCard).not.toBeNull();
    expect(within(totalCard as HTMLElement).getByText("3")).toBeInTheDocument();
    expect(within(twCard as HTMLElement).getByText("2")).toBeInTheDocument();
    expect(within(usCard as HTMLElement).getByText("1")).toBeInTheDocument();
  });

  it("應該處理刪除操作的載入狀態", () => {
    mockUseDeleteStock.mockReturnValue({
      mutate: jest.fn(),
      isPending: true,
      isError: false,
      error: null,
    });

    render(<StockManagementPage />, { wrapper: createWrapper() });

    // 驗證載入狀態顯示
    expect(screen.getAllByText("載入中...").length).toBeGreaterThan(0);
  });
});

describe("StockManagementPage - 客戶端狀態管理", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (portfolioApi.getPortfolioList as jest.Mock).mockResolvedValue(
      mockPortfolioData,
    );
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
    (stockListApi.getListStocks as jest.Mock).mockImplementation(
      () => new Promise(() => {}),
    );
    (stockListApi.removeStockFromList as jest.Mock).mockResolvedValue({
      message: "removed",
      list_id: mockDefaultList.id,
      stock_id: mockStocksData.items[0].id,
    });
  });

  it("應該使用 Redux 管理清單移除成功的 Toast 通知", async () => {
    const store = createTestStore();

    render(<StockManagementPage />, {
      wrapper: createWrapper(store),
    });

    const deleteButtons = screen.getAllByText("移除");
    fireEvent.click(deleteButtons[0]);
    fireEvent.click(screen.getByRole("button", { name: "確定" }));

    await waitFor(() => {
      const state = store.getState();
      expect(state.ui.toasts).toHaveLength(1);
      expect(state.ui.toasts[0].type).toBe("success");
      expect(state.ui.toasts[0].title).toBe("成功");
    });
  });

  it("應該處理清單移除失敗的錯誤 Toast", async () => {
    const store = createTestStore();
    (stockListApi.removeStockFromList as jest.Mock).mockRejectedValueOnce({
      response: { data: { detail: "移除失敗" } },
    });

    render(<StockManagementPage />, {
      wrapper: createWrapper(store),
    });

    const deleteButtons = screen.getAllByText("移除");
    fireEvent.click(deleteButtons[0]);
    fireEvent.click(screen.getByRole("button", { name: "確定" }));

    await waitFor(() => {
      const state = store.getState();
      expect(state.ui.toasts).toHaveLength(1);
      expect(state.ui.toasts[0].type).toBe("error");
      expect(state.ui.toasts[0].title).toBe("錯誤");
      expect(state.ui.toasts[0].message).toBe("移除失敗");
    });
  });
});
