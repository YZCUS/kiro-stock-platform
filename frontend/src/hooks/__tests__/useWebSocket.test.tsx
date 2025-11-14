/**
 * WebSocket Hooks Tests
 *
 * 這些測試驗證了 WebSocket hooks 在依賴修復後的正確行為
 */
import React from 'react';
import { renderHook, act, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import {
  useWebSocket,
  useWebSocketEvent,
  useStockSubscription,
  useMultipleStockSubscriptions,
  usePriceUpdates
} from '../useWebSocket';
import uiReducer from '../../store/slices/uiSlice';
import signalsReducer from '../../store/slices/signalsSlice';

// Mock WebSocket Manager
const mockWebSocketManager = {
  connect: jest.fn(),
  disconnect: jest.fn(),
  on: jest.fn(),
  off: jest.fn(),
  isConnected: jest.fn(),
  subscribeToStock: jest.fn(),
  unsubscribeFromStock: jest.fn(),
};

// Mock the WebSocket manager module
jest.mock('../../lib/websocket', () => ({
  getWebSocketManager: () => mockWebSocketManager,
  WebSocketEventType: {
    WELCOME: 'welcome',
    ERROR: 'error',
    PRICE_UPDATE: 'price_update',
    SIGNAL_UPDATE: 'signal_update',
  },
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
  Wrapper.displayName = 'ReduxWrapper';
  return Wrapper;
};

describe('useWebSocket', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockWebSocketManager.connect.mockResolvedValue(undefined);
    mockWebSocketManager.isConnected.mockReturnValue(false);
  });

  it('應該正確註冊和清理事件監聽器', async () => {
    const { unmount } = renderHook(() => useWebSocket(), {
      wrapper: createWrapper(),
    });

    // 驗證事件監聽器被註冊
    expect(mockWebSocketManager.on).toHaveBeenCalledWith('welcome', expect.any(Function));
    expect(mockWebSocketManager.on).toHaveBeenCalledWith('error', expect.any(Function));

    // 驗證連接被建立
    expect(mockWebSocketManager.connect).toHaveBeenCalled();

    // 卸載組件
    unmount();

    // 驗證事件監聽器被清理
    expect(mockWebSocketManager.off).toHaveBeenCalledWith('welcome', expect.any(Function));
    expect(mockWebSocketManager.off).toHaveBeenCalledWith('error', expect.any(Function));
  });

  it('應該正確處理連接成功', async () => {
    const { result } = renderHook(() => useWebSocket(), {
      wrapper: createWrapper(),
    });

    // 初始狀態
    expect(result.current.isConnected).toBe(false);
    expect(result.current.error).toBe(null);

    // 模擬 welcome 事件
    const welcomeHandler = mockWebSocketManager.on.mock.calls.find(
      call => call[0] === 'welcome'
    )?.[1];

    if (welcomeHandler) {
      act(() => {
        welcomeHandler();
      });
    }

    // 驗證狀態更新
    expect(result.current.isConnected).toBe(true);
    expect(result.current.isReconnecting).toBe(false);
    expect(result.current.error).toBe(null);
  });

  it('應該正確處理連接錯誤', async () => {
    const { result } = renderHook(() => useWebSocket(), {
      wrapper: createWrapper(),
    });

    const errorMessage = 'Connection failed';

    // 模擬 error 事件
    const errorHandler = mockWebSocketManager.on.mock.calls.find(
      call => call[0] === 'error'
    )?.[1];

    if (errorHandler) {
      act(() => {
        errorHandler({ message: errorMessage });
      });
    }

    // 驗證錯誤狀態
    expect(result.current.isConnected).toBe(false);
    expect(result.current.error).toBe(errorMessage);
  });

  it('應該支援手動重連', async () => {
    const { result } = renderHook(() => useWebSocket(), {
      wrapper: createWrapper(),
    });

    // 執行重連
    await act(async () => {
      await result.current.reconnect();
    });

    // 驗證重連邏輯
    expect(mockWebSocketManager.connect).toHaveBeenCalledTimes(2); // 初始連接 + 重連
    expect(result.current.isReconnecting).toBe(false);
  });

  it('應該支援手動斷開連接', () => {
    const { result } = renderHook(() => useWebSocket(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.disconnect();
    });

    expect(mockWebSocketManager.disconnect).toHaveBeenCalled();
    expect(result.current.isConnected).toBe(false);
    expect(result.current.isReconnecting).toBe(false);
  });
});

describe('useWebSocketEvent', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('應該正確註冊和清理自定義事件監聽器', () => {
    const mockCallback = jest.fn();
    const eventType = 'custom_event';

    const { unmount } = renderHook(
      () => useWebSocketEvent(eventType, mockCallback, []),
      { wrapper: createWrapper() }
    );

    // 驗證事件監聽器被註冊
    expect(mockWebSocketManager.on).toHaveBeenCalledWith(eventType, mockCallback);

    // 卸載組件
    unmount();

    // 驗證事件監聽器被清理
    expect(mockWebSocketManager.off).toHaveBeenCalledWith(eventType, mockCallback);
  });

  it('應該在依賴變化時重新註冊監聽器', () => {
    const mockCallback = jest.fn();
    let eventType = 'event1';

    const { rerender } = renderHook(
      ({ type }) => useWebSocketEvent(type, mockCallback, [type]),
      {
        wrapper: createWrapper(),
        initialProps: { type: eventType }
      }
    );

    // 第一次註冊
    expect(mockWebSocketManager.on).toHaveBeenCalledWith('event1', mockCallback);

    // 重置 mock
    jest.clearAllMocks();

    // 改變 eventType
    eventType = 'event2';
    rerender({ type: eventType });

    // 驗證舊監聽器被移除，新監聽器被註冊
    expect(mockWebSocketManager.off).toHaveBeenCalledWith('event1', mockCallback);
    expect(mockWebSocketManager.on).toHaveBeenCalledWith('event2', mockCallback);
  });
});

describe('useStockSubscription', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockWebSocketManager.isConnected.mockReturnValue(true);
    mockWebSocketManager.subscribeToStock.mockReturnValue(true);
  });

  it('應該在股票ID變化時正確訂閱和取消訂閱', () => {
    let stockId: number | null = 1;
    const symbol = '2330.TW';

    const { result, rerender } = renderHook(
      ({ id, sym }) => useStockSubscription(id, sym),
      {
        wrapper: createWrapper(),
        initialProps: { id: stockId, sym: symbol }
      }
    );

    // 驗證初始訂閱
    expect(mockWebSocketManager.subscribeToStock).toHaveBeenCalledWith(1, symbol);
    expect(result.current.isSubscribed).toBe(true);

    // 改變股票ID
    stockId = 2;
    rerender({ id: stockId, sym: symbol });

    // 驗證取消舊訂閱並訂閱新股票
    expect(mockWebSocketManager.unsubscribeFromStock).toHaveBeenCalledWith(1);
    expect(mockWebSocketManager.subscribeToStock).toHaveBeenCalledWith(2, symbol);
  });

  it('應該在stockId為null時取消訂閱', () => {
    const { result, rerender } = renderHook(
      ({ id }) => useStockSubscription(id, '2330.TW'),
      {
        wrapper: createWrapper(),
        initialProps: { id: 1 }
      }
    );

    expect(result.current.isSubscribed).toBe(true);

    // 設置為null
    rerender({ id: null });

    expect(result.current.isSubscribed).toBe(false);
  });

  it('應該在WebSocket重新連接時自動重新訂閱', () => {
    renderHook(() => useStockSubscription(1, '2330.TW'), {
      wrapper: createWrapper(),
    });

    // 清除初始調用
    jest.clearAllMocks();

    // 模擬 welcome 事件（重新連接）
    const welcomeHandler = mockWebSocketManager.on.mock.calls.find(
      call => call[0] === 'welcome'
    )?.[1];

    if (welcomeHandler) {
      act(() => {
        welcomeHandler();
      });
    }

    // 驗證重新訂閱
    expect(mockWebSocketManager.subscribeToStock).toHaveBeenCalledWith(1, '2330.TW');
  });
});

describe('useMultipleStockSubscriptions', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockWebSocketManager.isConnected.mockReturnValue(true);
    mockWebSocketManager.subscribeToStock.mockReturnValue(true);
  });

  it('應該正確處理多股票訂閱', () => {
    const stockIds = [1, 2, 3];

    const { result } = renderHook(
      () => useMultipleStockSubscriptions(stockIds),
      { wrapper: createWrapper() }
    );

    // 驗證所有股票都被訂閱
    expect(mockWebSocketManager.subscribeToStock).toHaveBeenCalledTimes(3);
    expect(mockWebSocketManager.subscribeToStock).toHaveBeenCalledWith(1);
    expect(mockWebSocketManager.subscribeToStock).toHaveBeenCalledWith(2);
    expect(mockWebSocketManager.subscribeToStock).toHaveBeenCalledWith(3);

    expect(result.current.subscribedStocks).toEqual([1, 2, 3]);
    expect(result.current.subscriptionCount).toBe(3);
  });

  it('應該在股票列表變化時正確更新訂閱', () => {
    let stockIds = [1, 2];

    const { rerender } = renderHook(
      ({ ids }) => useMultipleStockSubscriptions(ids),
      {
        wrapper: createWrapper(),
        initialProps: { ids: stockIds }
      }
    );

    // 清除初始調用
    jest.clearAllMocks();

    // 更新股票列表
    stockIds = [2, 3, 4];
    rerender({ ids: stockIds });

    // 驗證舊訂閱被取消
    expect(mockWebSocketManager.unsubscribeFromStock).toHaveBeenCalledWith(1);
    expect(mockWebSocketManager.unsubscribeFromStock).toHaveBeenCalledWith(2);

    // 驗證新訂閱被建立
    expect(mockWebSocketManager.subscribeToStock).toHaveBeenCalledWith(2);
    expect(mockWebSocketManager.subscribeToStock).toHaveBeenCalledWith(3);
    expect(mockWebSocketManager.subscribeToStock).toHaveBeenCalledWith(4);
  });
});

describe('usePriceUpdates', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockWebSocketManager.isConnected.mockReturnValue(true);
    mockWebSocketManager.subscribeToStock.mockReturnValue(true);
  });

  it('應該正確處理價格更新事件', () => {
    const stockId = 1;
    const { result } = renderHook(
      () => usePriceUpdates(stockId),
      { wrapper: createWrapper() }
    );

    // 模擬價格更新事件
    const priceUpdateHandler = mockWebSocketManager.on.mock.calls.find(
      call => call[0] === 'price_update'
    )?.[1];

    const mockPriceData = {
      stock_id: stockId,
      price: 500,
      change: 10,
      change_percent: 2.0,
    };

    if (priceUpdateHandler) {
      act(() => {
        priceUpdateHandler({ data: mockPriceData });
      });
    }

    // 驗證價格數據被更新
    expect(result.current.priceData).toEqual(mockPriceData);
    expect(result.current.lastUpdate).toBeInstanceOf(Date);
    expect(result.current.isSubscribed).toBe(true);
  });

  it('應該只處理匹配的股票價格更新', () => {
    const stockId = 1;
    const { result } = renderHook(
      () => usePriceUpdates(stockId),
      { wrapper: createWrapper() }
    );

    // 模擬不匹配的價格更新
    const priceUpdateHandler = mockWebSocketManager.on.mock.calls.find(
      call => call[0] === 'price_update'
    )?.[1];

    const mockPriceData = {
      stock_id: 2, // 不同的股票ID
      price: 500,
    };

    if (priceUpdateHandler) {
      act(() => {
        priceUpdateHandler({ data: mockPriceData });
      });
    }

    // 驗證價格數據沒有被更新
    expect(result.current.priceData).toBe(null);
    expect(result.current.lastUpdate).toBe(null);
  });
});

describe('WebSocket Hooks - 依賴管理測試', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('useWebSocket - 事件處理器應該在dispatch變化時重新創建', () => {
    const store1 = createTestStore();
    const store2 = createTestStore();

    const { rerender } = renderHook(
      ({ store }) => useWebSocket(),
      {
        wrapper: ({ children }) => (
          <Provider store={store}>{children}</Provider>
        ),
        initialProps: { store: store1 }
      }
    );

    const initialOnCalls = mockWebSocketManager.on.mock.calls.length;

    // 重新渲染使用不同的 store (不同的 dispatch)
    rerender({ store: store2 });

    // 應該有新的事件監聽器註冊（因為依賴變化）
    expect(mockWebSocketManager.on.mock.calls.length).toBeGreaterThan(initialOnCalls);
  });

  it('useStockSubscription - handleWelcome應該在stockId或symbol變化時重新創建', () => {
    mockWebSocketManager.isConnected.mockReturnValue(true);

    const { rerender } = renderHook(
      ({ id, sym }) => useStockSubscription(id, sym),
      {
        wrapper: createWrapper(),
        initialProps: { id: 1, sym: '2330.TW' }
      }
    );

    // 清除初始調用
    jest.clearAllMocks();

    // 改變 symbol
    rerender({ id: 1, sym: '2317.TW' });

    // 驗證事件監聽器被重新註冊（因為依賴變化）
    expect(mockWebSocketManager.off).toHaveBeenCalledWith('welcome', expect.any(Function));
    expect(mockWebSocketManager.on).toHaveBeenCalledWith('welcome', expect.any(Function));
  });
});