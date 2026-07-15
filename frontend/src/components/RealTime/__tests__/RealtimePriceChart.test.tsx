/**
 * RealtimePriceChart Component Tests
 *
 * 測試 RealtimePriceChart 組件的 props 重構和核心功能
 */
import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { createChart } from "lightweight-charts";
import RealtimePriceChart, { formatDateInput } from "../RealtimePriceChart";
import { useIndicatorUpdates } from "../../../hooks/useWebSocket";
import { useMarketStream } from "../../../hooks/useMarketStream";
import StocksApiService from "../../../services/stocksApi";
import { getStockValuationMetrics } from "../../../services/marketInfoApi";
import uiReducer from "../../../store/slices/uiSlice";
import signalsReducer from "../../../store/slices/signalsSlice";

// Mock the lightweight-charts library
const mockCandlestickSeries = {
  setData: jest.fn(),
  update: jest.fn(),
  data: jest.fn(() => []),
  setMarkers: jest.fn(),
};

const mockSmaSeries = {
  setData: jest.fn(),
  update: jest.fn(),
};

const mockVolumeSeries = {
  setData: jest.fn(),
  update: jest.fn(),
};

const mockPriceScale = {
  applyOptions: jest.fn(),
};

const mockChartApi = {
  addCandlestickSeries: jest.fn(() => mockCandlestickSeries),
  addLineSeries: jest.fn(() => mockSmaSeries),
  addHistogramSeries: jest.fn(() => mockVolumeSeries),
  priceScale: jest.fn(() => mockPriceScale),
  applyOptions: jest.fn(),
  remove: jest.fn(),
};

jest.mock("lightweight-charts", () => ({
  createChart: jest.fn(() => mockChartApi),
}));

// Mock market stream hook
const mockStreamBar = {
  market: "US",
  symbol: "AAPL",
  interval: "5m" as const,
  bucket_start: "2024-01-01T10:00:00Z",
  open: 490,
  high: 505,
  low: 485,
  close: 500,
  volume: 1000000,
  source: "mock_stream",
  is_final: false,
};

const mockPriceData = {
  market: "US",
  symbol: "AAPL",
  price: 500,
  change: 10,
  change_percent: 2.0,
  volume: 1000000,
  timestamp: "2024-01-01T10:00:00Z",
  ohlc: {
    open: 490,
    high: 505,
    low: 485,
    close: 500,
  },
};

const mockIndicators = {
  SMA: {
    type: "SMA",
    data: [{ date: "2024-01-01T10:00:00Z", value: 495 }],
    last_update: "2024-01-01T10:00:00Z",
  },
};

jest.mock("../../../hooks/useWebSocket", () => ({
  useIndicatorUpdates: jest.fn(),
}));

jest.mock("../../../hooks/useMarketStream", () => ({
  useMarketStream: jest.fn(),
}));

jest.mock("../../../services/stocksApi", () => ({
  __esModule: true,
  default: {
    getStockPrices: jest.fn(),
    backfillStockData: jest.fn(),
  },
}));

jest.mock("../../../services/marketInfoApi", () => ({
  getStockValuationMetrics: jest.fn(),
}));

const mockUseMarketStream = useMarketStream as jest.MockedFunction<
  typeof useMarketStream
>;
const mockUseIndicatorUpdates = useIndicatorUpdates as jest.MockedFunction<
  typeof useIndicatorUpdates
>;
const mockCreateChart = createChart as jest.MockedFunction<typeof createChart>;
const mockGetStockPrices =
  StocksApiService.getStockPrices as jest.MockedFunction<
    typeof StocksApiService.getStockPrices
  >;
const mockBackfillStockData =
  StocksApiService.backfillStockData as jest.MockedFunction<
    typeof StocksApiService.backfillStockData
  >;
const mockGetStockValuationMetrics =
  getStockValuationMetrics as jest.MockedFunction<
    typeof getStockValuationMetrics
  >;

const setupWebSocketHookMocks = () => {
  mockUseMarketStream.mockReturnValue({
    quote: mockPriceData,
    bar: mockStreamBar,
    signal: null,
    status: "connected",
    error: null,
  });
  mockUseIndicatorUpdates.mockReturnValue({
    indicators: mockIndicators,
    lastUpdate: new Date("2024-01-01T10:00:00Z"),
    isSubscribed: true,
  });
};

const setupResizeObserverMock = () => {
  global.ResizeObserver = jest.fn().mockImplementation(() => ({
    observe: jest.fn(),
    unobserve: jest.fn(),
    disconnect: jest.fn(),
  }));
  global.fetch = jest.fn(() => new Promise(() => {})) as jest.Mock;
  mockGetStockPrices.mockImplementation(() => new Promise(() => {}));
  mockBackfillStockData.mockImplementation(() => new Promise(() => {}));
  mockGetStockValuationMetrics.mockImplementation(() => new Promise(() => {}));
};

const createHistoricalPrices = (length: number) => {
  return Array.from({ length }, (_, index) => {
    const close = 100 + index;

    return {
      date: new Date(Date.UTC(2024, 0, 1 + index)).toISOString(),
      open: close - 1,
      high: close + 1,
      low: close - 2,
      close,
      volume: 1000 + index,
    };
  });
};

// Mock error reporting
jest.mock("../../../lib/errorReporting", () => ({
  reportError: jest.fn(),
}));

// Test store setup
const createTestStore = () => {
  return configureStore({
    reducer: {
      ui: uiReducer,
      signals: signalsReducer,
    },
  });
};

const createWrapper = (store = createTestStore()) => {
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <Provider store={store}>{children}</Provider>
  );
  Wrapper.displayName = "TestWrapper";
  return Wrapper;
};

// Mock stock data for testing
const mockStock = {
  id: 1,
  symbol: "2330.TW",
  name: "台積電",
};

const mockStockWithoutName = {
  id: 2,
  symbol: "2317.TW",
  name: "", // 測試沒有名稱的情況
};

describe("價格查詢日期", () => {
  it("應該使用本地日曆日期而不是 UTC 日期", () => {
    const date = new Date(2024, 0, 31, 23, 30);
    const toISOStringSpy = jest
      .spyOn(date, "toISOString")
      .mockImplementation(() => {
        throw new Error("不應使用 UTC 日期");
      });

    expect(formatDateInput(date)).toBe("2024-01-31");
    expect(toISOStringSpy).not.toHaveBeenCalled();
  });
});

describe("RealtimePriceChart - Props 重構測試", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupWebSocketHookMocks();
    setupResizeObserverMock();
  });

  it("應該接受新的 stock props 結構", async () => {
    render(<RealtimePriceChart stock={mockStock} height={400} />, {
      wrapper: createWrapper(),
    });

    expect(
      screen.queryByText("2330.TW (台積電) 即時價格圖表"),
    ).not.toBeInTheDocument();
    expect(mockUseMarketStream).toHaveBeenCalledWith("TW", "2330.TW", true);
    expect(mockUseIndicatorUpdates).toHaveBeenCalledWith(1);
    await waitFor(() => {
      expect(mockGetStockPrices).toHaveBeenCalledWith(
        1,
        expect.objectContaining({
          start_date: expect.any(String),
          end_date: expect.any(String),
          timeframe: "1d",
          limit: 756,
        }),
      );
    });
  });

  it("匿名研究時不應觸發需要登入的歷史價格回填", async () => {
    mockGetStockPrices.mockResolvedValueOnce(createHistoricalPrices(10));

    render(<RealtimePriceChart stock={mockStock} />, {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(mockGetStockPrices).toHaveBeenCalled();
    });
    expect(mockBackfillStockData).not.toHaveBeenCalled();
  });

  it("登入狀態允許需要時回填歷史價格", async () => {
    mockGetStockPrices.mockResolvedValueOnce(createHistoricalPrices(10));
    mockBackfillStockData.mockResolvedValueOnce({
      message: "ok",
      completed: true,
      success: true,
      symbol: "2330.TW",
      records_processed: 0,
      records_saved: 0,
      date_range: null,
      timestamp: "2026-07-15T00:00:00Z",
    });

    render(<RealtimePriceChart stock={mockStock} allowBackfill />, {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(mockBackfillStockData).toHaveBeenCalledWith(
        1,
        expect.objectContaining({
          start_date: expect.any(String),
          end_date: expect.any(String),
        }),
      );
    });
  });

  it("5m 沒有資料時應該回退載入日線資料", async () => {
    mockGetStockPrices
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce(createHistoricalPrices(130));

    render(<RealtimePriceChart stock={mockStock} timeframe="5m" />, {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(mockGetStockPrices).toHaveBeenCalledWith(
        1,
        expect.objectContaining({
          timeframe: "5m",
          limit: 390,
        }),
      );
      expect(mockGetStockPrices).toHaveBeenCalledWith(
        1,
        expect.objectContaining({
          timeframe: "1d",
          limit: 756,
        }),
      );
    });

    expect(screen.getByText("5分K暫無資料，已顯示日線")).toBeInTheDocument();
  });

  it("應該提供日線與 5分K 切換", async () => {
    render(<RealtimePriceChart stock={mockStock} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByRole("button", { name: "日線" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );

    fireEvent.click(screen.getByRole("button", { name: "5分K" }));

    expect(screen.getByRole("button", { name: "5分K" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );

    await waitFor(() => {
      expect(mockGetStockPrices).toHaveBeenCalledWith(
        1,
        expect.objectContaining({
          timeframe: "5m",
          limit: 390,
        }),
      );
    });
  });

  it("不應該在圖表內重複顯示股票標題", () => {
    render(<RealtimePriceChart stock={mockStock} height={400} />, {
      wrapper: createWrapper(),
    });

    expect(screen.queryByText(/2330\.TW/)).not.toBeInTheDocument();
    expect(screen.queryByText(/台積電/)).not.toBeInTheDocument();
  });

  it("沒有名稱的股票也不應該顯示內部圖表標題", () => {
    render(<RealtimePriceChart stock={mockStockWithoutName} height={400} />, {
      wrapper: createWrapper(),
    });

    expect(
      screen.queryByText(/2317\.TW.*即時價格圖表/),
    ).not.toBeInTheDocument();
  });

  it("不應該顯示內部股票 ID", () => {
    render(<RealtimePriceChart stock={mockStock} height={400} />, {
      wrapper: createWrapper(),
    });

    expect(screen.queryByText(/ID: 1/)).not.toBeInTheDocument();
  });

  it("應該使用正確的高度", () => {
    const customHeight = 600;

    render(<RealtimePriceChart stock={mockStock} height={customHeight} />, {
      wrapper: createWrapper(),
    });

    // 查找圖表容器
    const chartContainer = document.querySelector('[style*="height: 600px"]');
    expect(chartContainer).toBeInTheDocument();
  });

  it("應該使用默認高度（400px）", () => {
    render(<RealtimePriceChart stock={mockStock} timeframe="5m" />, {
      wrapper: createWrapper(),
    });

    // 查找圖表容器，驗證默認高度
    const chartContainer = document.querySelector('[style*="height: 400px"]');
    expect(chartContainer).toBeInTheDocument();
  });
});

describe("RealtimePriceChart - 功能測試", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupWebSocketHookMocks();
    setupResizeObserverMock();
  });

  it("不應該顯示冗餘的訂閱狀態", () => {
    render(<RealtimePriceChart stock={mockStock} timeframe="5m" />, {
      wrapper: createWrapper(),
    });

    expect(screen.queryByText("已訂閱")).not.toBeInTheDocument();
    expect(screen.queryByText("未訂閱")).not.toBeInTheDocument();
  });

  it("不應該在圖表內重複顯示價格資訊卡", () => {
    render(<RealtimePriceChart stock={mockStock} />, {
      wrapper: createWrapper(),
    });

    expect(screen.queryByText("當前價格")).not.toBeInTheDocument();
    expect(screen.queryByText("$500.00")).not.toBeInTheDocument();
    expect(screen.queryByText("+10.00")).not.toBeInTheDocument();
    expect(screen.queryByText("+2.00%")).not.toBeInTheDocument();
  });

  it("不應該在圖表內重複顯示最後更新時間", () => {
    render(<RealtimePriceChart stock={mockStock} />, {
      wrapper: createWrapper(),
    });

    expect(screen.queryByText(/最後更新:/)).not.toBeInTheDocument();
  });

  it("應該顯示即時指標信息", () => {
    render(<RealtimePriceChart stock={mockStock} />, {
      wrapper: createWrapper(),
    });

    // 驗證即時指標區域
    expect(screen.getByText("即時指標")).toBeInTheDocument();
    expect(screen.getByText("SMA")).toBeInTheDocument();
    expect(screen.getByText("495.00")).toBeInTheDocument();
  });

  it("應該顯示圖例", () => {
    render(<RealtimePriceChart stock={mockStock} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("上漲")).toBeInTheDocument();
    expect(screen.getByText("下跌")).toBeInTheDocument();
    expect(screen.getByText("成交量")).toBeInTheDocument();
    expect(screen.getByText("5K均線")).toBeInTheDocument();
    expect(screen.getByText("20K均線")).toBeInTheDocument();
    expect(screen.getByText("60K均線")).toBeInTheDocument();
    expect(screen.getByText("120K均線")).toBeInTheDocument();
    expect(screen.getByText("扣抵價標記")).toBeInTheDocument();
  });

  it("應該為圖表提供可存取的 OHLC 與資料期間摘要", async () => {
    mockGetStockPrices.mockResolvedValueOnce(createHistoricalPrices(10));

    render(<RealtimePriceChart stock={mockStock} />, {
      wrapper: createWrapper(),
    });

    const chart = screen.getByRole("img", {
      name: "2330.TW 日線價格圖",
    });
    const descriptionId = chart.getAttribute("aria-describedby");

    expect(descriptionId).toBeTruthy();
    await waitFor(() => {
      const description = document.getElementById(descriptionId as string);
      expect(description).toHaveTextContent("日線共 10 筆資料");
      expect(description).toHaveTextContent("最新開盤 108.00");
      expect(description).toHaveTextContent("最高 110.00");
      expect(description).toHaveTextContent("最低 107.00");
      expect(description).toHaveTextContent("收盤 109.00");
    });
  });

  it("應忽略 API 回傳的非有限 OHLC 資料", async () => {
    mockGetStockPrices.mockResolvedValueOnce([
      {
        date: "2026-07-15",
        open: null,
        high: null,
        low: null,
        close: null,
        volume: 0,
      } as unknown as ReturnType<typeof createHistoricalPrices>[number],
      ...createHistoricalPrices(1),
    ]);

    render(<RealtimePriceChart stock={mockStock} />, {
      wrapper: createWrapper(),
    });

    const chart = screen.getByRole("img", {
      name: "2330.TW 日線價格圖",
    });
    const descriptionId = chart.getAttribute("aria-describedby");

    await waitFor(() => {
      expect(
        document.getElementById(descriptionId as string),
      ).toHaveTextContent("日線共 1 筆資料");
    });
  });

  it("日線日期不應因本機時區退回前一天", async () => {
    mockGetStockPrices.mockResolvedValueOnce([
      {
        date: "2024-01-01",
        open: 100,
        high: 102,
        low: 99,
        close: 101,
        volume: 1000,
      },
    ]);

    render(<RealtimePriceChart stock={mockStock} />, {
      wrapper: createWrapper(),
    });

    const chart = screen.getByRole("img", { name: "2330.TW 日線價格圖" });
    const descriptionId = chart.getAttribute("aria-describedby");

    await waitFor(() => {
      expect(
        document.getElementById(descriptionId as string),
      ).toHaveTextContent("2024/01/01");
    });
    expect(
      document.getElementById(descriptionId as string),
    ).not.toHaveTextContent("2023/12/31");
  });

  it("應該顯示均線摘要但不暴露載入 K 棒數", async () => {
    mockGetStockPrices.mockResolvedValueOnce(createHistoricalPrices(130));

    render(<RealtimePriceChart stock={mockStock} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("均線與扣抵價")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("227.00")).toBeInTheDocument();
    });

    expect(screen.queryByText(/已載入 .* 根 K 棒/)).not.toBeInTheDocument();
    expect(screen.getByText("20K")).toBeInTheDocument();
    expect(screen.getByText("60K")).toBeInTheDocument();
    expect(screen.getByText("120K")).toBeInTheDocument();
    expect(screen.getByText(/225\.00/)).toBeInTheDocument();
  });

  it("應該在均線摘要下方顯示估值指標", async () => {
    mockGetStockValuationMetrics.mockResolvedValueOnce({
      symbol: "2330.TW",
      market: "TW",
      provider: "finnhub",
      market_cap: 100000,
      market_cap_unit: "million",
      pe_ttm: 20,
      pb: 5,
      ps_ttm: 8,
      ev_to_ebitda: 14,
      dividend_yield: 1.5,
      beta: 1.1,
      eps_ttm: 10,
      week_52_high: 700,
      week_52_low: 500,
    });

    render(<RealtimePriceChart stock={mockStock} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("估值指標")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("來源 finnhub")).toBeInTheDocument();
    });

    expect(screen.getByText("P/E")).toBeInTheDocument();
    expect(screen.getByText("20.00")).toBeInTheDocument();
    expect(screen.getByText("殖利率")).toBeInTheDocument();
    expect(screen.getByText("1.50%")).toBeInTheDocument();
    expect(screen.getByText("52 週區間")).toBeInTheDocument();
  });

  it("資料不足時不應顯示所需 K 棒數", async () => {
    mockGetStockPrices.mockResolvedValueOnce(createHistoricalPrices(30));

    render(<RealtimePriceChart stock={mockStock} />, {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(screen.getByText("5K")).toBeInTheDocument();
    });

    expect(screen.queryByText(/需要 \d+ 根/)).not.toBeInTheDocument();
    expect(screen.getAllByText("--").length).toBeGreaterThan(0);
  });
});

describe("RealtimePriceChart - 錯誤處理測試", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupWebSocketHookMocks();
    setupResizeObserverMock();

    // Mock console.error
    jest.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    (console.error as jest.Mock).mockRestore();
  });

  it("應該處理無效的價格數據", async () => {
    // Mock 返回無效數據的 hook
    mockUseMarketStream.mockReturnValue({
      quote: null,
      bar: null,
      signal: null,
      status: "idle",
      error: null,
    });

    render(<RealtimePriceChart stock={mockStock} />, {
      wrapper: createWrapper(),
    });

    expect(screen.queryByText("未訂閱")).not.toBeInTheDocument();

    // 驗證沒有價格信息顯示
    expect(screen.queryByText("當前價格")).not.toBeInTheDocument();
  });

  it("應該處理缺少股票信息的情況", () => {
    const incompleteStock = {
      id: 1,
      symbol: "2330.TW",
    };

    render(<RealtimePriceChart stock={incompleteStock} />, {
      wrapper: createWrapper(),
    });

    expect(screen.queryByText("2330.TW 即時價格圖表")).not.toBeInTheDocument();
    expect(mockUseMarketStream).toHaveBeenCalledWith("TW", "2330.TW", true);
  });

  it("價格 API 失敗時應該顯示錯誤並允許重試", async () => {
    mockGetStockPrices
      .mockRejectedValueOnce(new Error("network error"))
      .mockResolvedValueOnce(createHistoricalPrices(10));

    render(<RealtimePriceChart stock={mockStock} />, {
      wrapper: createWrapper(),
    });

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "無法載入價格圖表",
    );
    expect(
      screen.queryByText("目前沒有可顯示的價格資料"),
    ).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "重新載入" }));

    await waitFor(() => {
      expect(mockGetStockPrices).toHaveBeenCalledTimes(2);
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });
  });
});

describe("RealtimePriceChart - Chart integration tests", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupWebSocketHookMocks();
    setupResizeObserverMock();
  });

  it("應該使用 height prop 初始化圖表", () => {
    render(<RealtimePriceChart stock={mockStock} height={500} />, {
      wrapper: createWrapper(),
    });

    expect(mockCreateChart).toHaveBeenCalledWith(
      expect.any(HTMLDivElement),
      expect.objectContaining({ height: 500 }),
    );
  });

  it("應該建立 5K、20K、60K、120K 均線序列", () => {
    render(<RealtimePriceChart stock={mockStock} />, {
      wrapper: createWrapper(),
    });

    expect(mockChartApi.addLineSeries).toHaveBeenCalledTimes(4);
    expect(mockChartApi.addLineSeries).toHaveBeenCalledWith(
      expect.objectContaining({ title: "5K" }),
    );
    expect(mockChartApi.addLineSeries).toHaveBeenCalledWith(
      expect.objectContaining({ title: "20K" }),
    );
    expect(mockChartApi.addLineSeries).toHaveBeenCalledWith(
      expect.objectContaining({ title: "60K" }),
    );
    expect(mockChartApi.addLineSeries).toHaveBeenCalledWith(
      expect.objectContaining({ title: "120K" }),
    );
  });

  it("應該建立成交量柱狀圖序列", () => {
    render(<RealtimePriceChart stock={mockStock} />, {
      wrapper: createWrapper(),
    });

    expect(mockChartApi.addHistogramSeries).toHaveBeenCalledWith(
      expect.objectContaining({
        priceFormat: { type: "volume" },
        priceScaleId: "",
      }),
    );
    expect(mockChartApi.priceScale).toHaveBeenCalledWith("");
    expect(mockPriceScale.applyOptions).toHaveBeenCalledWith(
      expect.objectContaining({
        scaleMargins: expect.objectContaining({
          top: 0.78,
          bottom: 0,
        }),
      }),
    );
  });

  it("應該在各期均線扣抵 K 棒上設定扣抵價標記", async () => {
    mockGetStockPrices.mockResolvedValueOnce(createHistoricalPrices(130));

    render(<RealtimePriceChart stock={mockStock} />, {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(mockCandlestickSeries.setMarkers).toHaveBeenCalledWith(
        expect.arrayContaining([
          expect.objectContaining({ text: "5K扣 225.00" }),
          expect.objectContaining({ text: "20K扣 210.00" }),
          expect.objectContaining({ text: "60K扣 170.00" }),
          expect.objectContaining({ text: "120K扣 110.00" }),
        ]),
      );
    });

    const markers = mockCandlestickSeries.setMarkers.mock.calls.at(-1)?.[0];
    expect(markers.map((marker: { text: string }) => marker.text)).toEqual([
      "120K扣 110.00",
      "60K扣 170.00",
      "20K扣 210.00",
      "5K扣 225.00",
    ]);
  });

  it("應該把即時 OHLC 價格更新寫入 K 線序列", async () => {
    render(<RealtimePriceChart stock={mockStock} timeframe="5m" />, {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(mockCandlestickSeries.update).toHaveBeenCalledWith(
        expect.objectContaining({
          open: 490,
          high: 505,
          low: 485,
          close: 500,
        }),
      );
      expect(mockVolumeSeries.update).toHaveBeenCalledWith(
        expect.objectContaining({
          value: 1000000,
        }),
      );
    });
  });
});

describe("RealtimePriceChart - WebSocket 集成測試", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupWebSocketHookMocks();
    setupResizeObserverMock();
  });

  it("應該使用正確的 stockId 調用 WebSocket hooks", () => {
    // Mock is already defined at the top via jest.mock()

    render(<RealtimePriceChart stock={mockStock} />, {
      wrapper: createWrapper(),
    });

    // 驗證 hooks 被正確的 stockId 調用
    expect(mockUseMarketStream).toHaveBeenCalledWith("TW", "2330.TW", true);
    expect(mockUseIndicatorUpdates).toHaveBeenCalledWith(1);
  });

  it("應該在 stockId 變化時重新調用 WebSocket hooks", () => {
    // Mock is already defined at the top via jest.mock()

    const { rerender } = render(<RealtimePriceChart stock={mockStock} />, {
      wrapper: createWrapper(),
    });

    // 清除初始調用
    mockUseMarketStream.mockClear();
    mockUseIndicatorUpdates.mockClear();

    // 重新渲染使用不同的股票
    const newStock = { id: 2, symbol: "2317.TW", name: "鴻海" };
    rerender(<RealtimePriceChart stock={newStock} />);

    // 驗證使用新的 stockId
    expect(mockUseMarketStream).toHaveBeenCalledWith("TW", "2317.TW", true);
    expect(mockUseIndicatorUpdates).toHaveBeenCalledWith(2);
  });
});
