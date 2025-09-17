/**
 * RealtimePriceChart Component Tests
 *
 * 測試 RealtimePriceChart 組件的 props 重構和核心功能
 */
import React from 'react';
import { render, screen, act, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import RealtimePriceChart from '../RealtimePriceChart';
import uiReducer from '../../../store/slices/uiSlice';
import signalsReducer from '../../../store/slices/signalsSlice';

// Mock the lightweight-charts library
jest.mock('lightweight-charts', () => ({
  createChart: jest.fn(() => ({
    addCandlestickSeries: jest.fn(() => ({
      setData: jest.fn(),
      update: jest.fn(),
      data: jest.fn(() => []),
    })),
    addLineSeries: jest.fn(() => ({
      setData: jest.fn(),
      update: jest.fn(),
    })),
    applyOptions: jest.fn(),
    remove: jest.fn(),
  })),
}));

// Mock WebSocket hooks
const mockPriceData = {
  price: 500,
  change: 10,
  change_percent: 2.0,
  volume: 1000000,
  timestamp: '2024-01-01T10:00:00Z',
  ohlc: {
    open: 490,
    high: 505,
    low: 485,
    close: 500,
  }
};

const mockIndicators = {
  SMA: {
    type: 'SMA',
    data: [
      { date: '2024-01-01T10:00:00Z', value: 495 }
    ],
    last_update: '2024-01-01T10:00:00Z'
  }
};

jest.mock('../../../hooks/useWebSocket', () => ({
  usePriceUpdates: jest.fn((stockId) => ({
    priceData: mockPriceData,
    lastUpdate: new Date('2024-01-01T10:00:00Z'),
    isSubscribed: true,
  })),
  useIndicatorUpdates: jest.fn((stockId) => ({
    indicators: mockIndicators,
  })),
}));

// Mock error reporting
jest.mock('../../../lib/errorReporting', () => ({
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
  return ({ children }: { children: React.ReactNode }) => (
    <Provider store={store}>{children}</Provider>
  );
};

// Mock stock data for testing
const mockStock = {
  id: 1,
  symbol: '2330.TW',
  name: '台積電',
};

const mockStockWithoutName = {
  id: 2,
  symbol: '2317.TW',
  name: '', // 測試沒有名稱的情況
};

describe('RealtimePriceChart - Props 重構測試', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Mock DOM API
    global.ResizeObserver = jest.fn().mockImplementation(() => ({
      observe: jest.fn(),
      unobserve: jest.fn(),
      disconnect: jest.fn(),
    }));
  });

  it('應該接受新的 stock props 結構', () => {
    expect(() => {
      render(
        <RealtimePriceChart
          stock={mockStock}
          height={400}
        />,
        { wrapper: createWrapper() }
      );
    }).not.toThrow();

    // 驗證組件正常渲染
    expect(screen.getByText(/即時價格圖表/)).toBeInTheDocument();
  });

  it('應該顯示股票符號和名稱', () => {
    render(
      <RealtimePriceChart
        stock={mockStock}
        height={400}
      />,
      { wrapper: createWrapper() }
    );

    // 驗證股票符號顯示
    expect(screen.getByText(/2330\.TW/)).toBeInTheDocument();
    // 驗證股票名稱顯示
    expect(screen.getByText(/台積電/)).toBeInTheDocument();
  });

  it('應該正確處理沒有名稱的股票', () => {
    render(
      <RealtimePriceChart
        stock={mockStockWithoutName}
        height={400}
      />,
      { wrapper: createWrapper() }
    );

    // 驗證股票符號顯示
    expect(screen.getByText(/2317\.TW/)).toBeInTheDocument();
    // 驗證沒有額外的括號顯示（因為沒有名稱）
    const title = screen.getByText(/2317\.TW.*即時價格圖表/);
    expect(title.textContent).toBe('2317.TW 即時價格圖表');
  });

  it('應該顯示股票ID', () => {
    render(
      <RealtimePriceChart
        stock={mockStock}
        height={400}
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText(/ID: 1/)).toBeInTheDocument();
  });

  it('應該使用正確的高度', () => {
    const customHeight = 600;

    render(
      <RealtimePriceChart
        stock={mockStock}
        height={customHeight}
      />,
      { wrapper: createWrapper() }
    );

    // 查找圖表容器
    const chartContainer = document.querySelector('[style*="height: 600px"]');
    expect(chartContainer).toBeInTheDocument();
  });

  it('應該使用默認高度（400px）', () => {
    render(
      <RealtimePriceChart
        stock={mockStock}
      />,
      { wrapper: createWrapper() }
    );

    // 查找圖表容器，驗證默認高度
    const chartContainer = document.querySelector('[style*="height: 400px"]');
    expect(chartContainer).toBeInTheDocument();
  });
});

describe('RealtimePriceChart - 功能測試', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    global.ResizeObserver = jest.fn().mockImplementation(() => ({
      observe: jest.fn(),
      unobserve: jest.fn(),
      disconnect: jest.fn(),
    }));
  });

  it('應該顯示訂閱狀態', () => {
    render(
      <RealtimePriceChart
        stock={mockStock}
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText('已訂閱')).toBeInTheDocument();

    // 驗證綠色狀態指示器
    const statusIndicator = document.querySelector('.bg-green-500.animate-pulse');
    expect(statusIndicator).toBeInTheDocument();
  });

  it('應該顯示當前價格信息', () => {
    render(
      <RealtimePriceChart
        stock={mockStock}
      />,
      { wrapper: createWrapper() }
    );

    // 驗證當前價格
    expect(screen.getByText('$500.00')).toBeInTheDocument();

    // 驗證漲跌
    expect(screen.getByText('+10.00')).toBeInTheDocument();

    // 驗證漲跌幅
    expect(screen.getByText('+2.00%')).toBeInTheDocument();

    // 驗證成交量
    expect(screen.getByText('1,000,000')).toBeInTheDocument();
  });

  it('應該顯示最後更新時間', () => {
    render(
      <RealtimePriceChart
        stock={mockStock}
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText(/最後更新:/)).toBeInTheDocument();
  });

  it('應該顯示技術指標信息', () => {
    render(
      <RealtimePriceChart
        stock={mockStock}
      />,
      { wrapper: createWrapper() }
    );

    // 驗證技術指標區域
    expect(screen.getByText('技術指標')).toBeInTheDocument();
    expect(screen.getByText('SMA')).toBeInTheDocument();
    expect(screen.getByText('495.00')).toBeInTheDocument();
  });

  it('應該顯示圖例', () => {
    render(
      <RealtimePriceChart
        stock={mockStock}
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText('上漲')).toBeInTheDocument();
    expect(screen.getByText('下跌')).toBeInTheDocument();
    expect(screen.getByText('SMA(20)')).toBeInTheDocument();
  });
});

describe('RealtimePriceChart - 錯誤處理測試', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    global.ResizeObserver = jest.fn().mockImplementation(() => ({
      observe: jest.fn(),
      unobserve: jest.fn(),
      disconnect: jest.fn(),
    }));

    // Mock console.error
    jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    (console.error as jest.Mock).mockRestore();
  });

  it('應該處理無效的價格數據', async () => {
    // Mock 返回無效數據的 hook
    const { usePriceUpdates } = require('../../../hooks/useWebSocket');
    usePriceUpdates.mockReturnValue({
      priceData: null,
      lastUpdate: null,
      isSubscribed: false,
    });

    render(
      <RealtimePriceChart
        stock={mockStock}
      />,
      { wrapper: createWrapper() }
    );

    // 驗證未訂閱狀態
    expect(screen.getByText('未訂閱')).toBeInTheDocument();

    // 驗證沒有價格信息顯示
    expect(screen.queryByText('當前價格')).not.toBeInTheDocument();
  });

  it('應該處理缺少股票信息的情況', () => {
    const incompleteStock = {
      id: 1,
      symbol: '2330.TW',
      // 缺少 name 屬性
    } as any;

    expect(() => {
      render(
        <RealtimePriceChart
          stock={incompleteStock}
        />,
        { wrapper: createWrapper() }
      );
    }).not.toThrow();

    expect(screen.getByText(/2330\.TW.*即時價格圖表/)).toBeInTheDocument();
  });
});

describe('RealtimePriceChart - Props 類型安全測試', () => {
  it('應該接受符合 Pick<Stock, "id" | "symbol" | "name"> 類型的 stock prop', () => {
    // 這個測試確保類型定義正確
    const validStockProp = {
      id: 1,
      symbol: '2330.TW',
      name: '台積電',
    };

    expect(() => {
      render(
        <RealtimePriceChart
          stock={validStockProp}
        />,
        { wrapper: createWrapper() }
      );
    }).not.toThrow();
  });

  it('應該接受可選的 height prop', () => {
    expect(() => {
      render(
        <RealtimePriceChart
          stock={mockStock}
          height={500}
        />,
        { wrapper: createWrapper() }
      );
    }).not.toThrow();
  });
});

describe('RealtimePriceChart - WebSocket 集成測試', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    global.ResizeObserver = jest.fn().mockImplementation(() => ({
      observe: jest.fn(),
      unobserve: jest.fn(),
      disconnect: jest.fn(),
    }));
  });

  it('應該使用正確的 stockId 調用 WebSocket hooks', () => {
    const { usePriceUpdates, useIndicatorUpdates } = require('../../../hooks/useWebSocket');

    render(
      <RealtimePriceChart
        stock={mockStock}
      />,
      { wrapper: createWrapper() }
    );

    // 驗證 hooks 被正確的 stockId 調用
    expect(usePriceUpdates).toHaveBeenCalledWith(1);
    expect(useIndicatorUpdates).toHaveBeenCalledWith(1);
  });

  it('應該在 stockId 變化時重新調用 WebSocket hooks', () => {
    const { usePriceUpdates, useIndicatorUpdates } = require('../../../hooks/useWebSocket');

    const { rerender } = render(
      <RealtimePriceChart
        stock={mockStock}
      />,
      { wrapper: createWrapper() }
    );

    // 清除初始調用
    usePriceUpdates.mockClear();
    useIndicatorUpdates.mockClear();

    // 重新渲染使用不同的股票
    const newStock = { id: 2, symbol: '2317.TW', name: '鴻海' };
    rerender(
      <RealtimePriceChart
        stock={newStock}
      />
    );

    // 驗證使用新的 stockId
    expect(usePriceUpdates).toHaveBeenCalledWith(2);
    expect(useIndicatorUpdates).toHaveBeenCalledWith(2);
  });
});