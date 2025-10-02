/**
 * WebSocket React Hooks
 */
import { useEffect, useRef, useCallback } from 'react';
import { useAppDispatch, useAppSelector } from '../store';
import { setWebSocketConnected, setWebSocketReconnecting, setWebSocketError } from '../store/slices/uiSlice';
import { addRealtimeSignal } from '../store/slices/signalsSlice';
import { getWebSocketManager, WebSocketEventType, WebSocketCallback } from '../lib/websocket';
import { WebSocketMessage, TradingSignal } from '../types';

/**
 * 基礎 WebSocket Hook
 */
export function useWebSocket() {
  const dispatch = useAppDispatch();
  const wsManager = useRef(getWebSocketManager());

  // 從 Redux 讀取全局狀態，而不是使用本地 state
  const isConnected = useAppSelector((state) => state.ui.websocket.connected);
  const isReconnecting = useAppSelector((state) => state.ui.websocket.reconnecting);
  const error = useAppSelector((state) => state.ui.websocket.connectionError);

  // 穩定化事件處理器，避免不必要的重新訂閱
  const handleWelcome = useCallback(() => {
    dispatch(setWebSocketConnected(true));
    dispatch(setWebSocketReconnecting(false));
    dispatch(setWebSocketError(null));
  }, [dispatch]);

  const handleError = useCallback((message: WebSocketMessage) => {
    const errorMsg = message.message || 'WebSocket connection error';
    dispatch(setWebSocketConnected(false));
    dispatch(setWebSocketError(errorMsg));
  }, [dispatch]);

  const handleDisconnected = useCallback(() => {
    dispatch(setWebSocketConnected(false));
  }, [dispatch]);

  useEffect(() => {
    const manager = wsManager.current;

    // 同步初始狀態 - 如果已經連接，更新 Redux
    if (manager.isConnected()) {
      dispatch(setWebSocketConnected(true));
      dispatch(setWebSocketError(null));
    }

    // 註冊事件監聽器
    manager.on(WebSocketEventType.WELCOME, handleWelcome);
    manager.on(WebSocketEventType.ERROR, handleError);
    manager.on(WebSocketEventType.DISCONNECTED, handleDisconnected);

    // 嘗試連接（如果尚未連接）
    if (!manager.isConnected()) {
      manager.connect().catch(error => {
        const errorMsg = error.message || 'Failed to connect to WebSocket';
        dispatch(setWebSocketError(errorMsg));
      });
    }

    // 清理函數
    return () => {
      manager.off(WebSocketEventType.WELCOME, handleWelcome);
      manager.off(WebSocketEventType.ERROR, handleError);
      manager.off(WebSocketEventType.DISCONNECTED, handleDisconnected);
    };
  }, [dispatch, handleWelcome, handleError, handleDisconnected]);

  // 手動重連
  const reconnect = useCallback(() => {
    dispatch(setWebSocketReconnecting(true));
    dispatch(setWebSocketError(null));

    wsManager.current.connect().catch(error => {
      const errorMsg = error.message || 'Failed to reconnect to WebSocket';
      dispatch(setWebSocketReconnecting(false));
      dispatch(setWebSocketError(errorMsg));
    });
  }, [dispatch]);

  // 斷開連接
  const disconnect = useCallback(() => {
    wsManager.current.disconnect();
    dispatch(setWebSocketConnected(false));
    dispatch(setWebSocketReconnecting(false));
    dispatch(setWebSocketError(null));
  }, [dispatch]);

  return {
    isConnected,
    isReconnecting,
    error,
    reconnect,
    disconnect,
    wsManager: wsManager.current,
  };
}

/**
 * WebSocket 事件監聽 Hook
 */
export function useWebSocketEvent(
  eventType: WebSocketEventType,
  callback: WebSocketCallback,
  deps: React.DependencyList = []
) {
  const wsManager = useRef(getWebSocketManager());

  useEffect(() => {
    const manager = wsManager.current;
    manager.on(eventType, callback);

    return () => {
      manager.off(eventType, callback);
    };
  }, [eventType, ...deps]);
}

/**
 * 股票訂閱 Hook
 */
export function useStockSubscription(stockId: number | null, symbol?: string) {
  const wsManager = useRef(getWebSocketManager());
  const [isSubscribed, setIsSubscribed] = useState(false);

  // 穩定化事件處理器
  const handleWelcome = useCallback(() => {
    if (stockId) {
      const manager = wsManager.current;
      const success = manager.subscribeToStock(stockId, symbol);
      setIsSubscribed(success);
    }
  }, [stockId, symbol]);

  useEffect(() => {
    if (!stockId) {
      setIsSubscribed(false);
      return;
    }

    const manager = wsManager.current;

    // 如果已連接，立即訂閱
    if (manager.isConnected()) {
      const success = manager.subscribeToStock(stockId, symbol);
      setIsSubscribed(success);
    }

    // 監聽連接建立事件，連接後自動訂閱
    manager.on(WebSocketEventType.WELCOME, handleWelcome);

    // 清理函數
    return () => {
      if (stockId) {
        manager.unsubscribeFromStock(stockId);
        setIsSubscribed(false);
      }
      manager.off(WebSocketEventType.WELCOME, handleWelcome);
    };
  }, [stockId, symbol, handleWelcome]);

  return { isSubscribed };
}

/**
 * 即時價格更新 Hook
 */
export function usePriceUpdates(stockId: number | null) {
  const [priceData, setPriceData] = useState<any>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  // 訂閱股票
  const { isSubscribed } = useStockSubscription(stockId);

  // 監聽價格更新
  useWebSocketEvent(
    WebSocketEventType.PRICE_UPDATE,
    useCallback((message: WebSocketMessage) => {
      if (message.data && message.data.stock_id === stockId) {
        setPriceData(message.data);
        setLastUpdate(new Date());
      }
    }, [stockId]),
    [stockId]
  );

  return {
    priceData,
    lastUpdate,
    isSubscribed,
  };
}

/**
 * 即時信號更新 Hook
 */
export function useSignalUpdates() {
  const dispatch = useAppDispatch();
  const [signals, setSignals] = useState<TradingSignal[]>([]);

  // 監聽信號更新
  useWebSocketEvent(
    WebSocketEventType.SIGNAL_UPDATE,
    useCallback((message: WebSocketMessage) => {
      if (message.data) {
        const signal = message.data as TradingSignal;

        // 更新 Redux store
        dispatch(addRealtimeSignal(signal));

        // 更新本地狀態
        setSignals(prev => [signal, ...prev.slice(0, 49)]); // 保持最多50個信號
      }
    }, [dispatch]),
    []
  );

  return { signals };
}

/**
 * 即時技術指標更新 Hook
 */
export function useIndicatorUpdates(stockId: number | null) {
  const [indicators, setIndicators] = useState<Record<string, any>>({});
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  // 訂閱股票
  const { isSubscribed } = useStockSubscription(stockId);

  // 監聽指標更新
  useWebSocketEvent(
    WebSocketEventType.INDICATOR_UPDATE,
    useCallback((message: WebSocketMessage) => {
      if (message.data && message.data.stock_id === stockId) {
        setIndicators(prev => ({
          ...prev,
          [message.data.indicator_type]: message.data
        }));
        setLastUpdate(new Date());
      }
    }, [stockId]),
    [stockId]
  );

  return {
    indicators,
    lastUpdate,
    isSubscribed,
  };
}

/**
 * 市場狀態更新 Hook
 */
export function useMarketStatus() {
  const [marketStatus, setMarketStatus] = useState<Record<string, any>>({});

  // 監聽市場狀態更新
  useWebSocketEvent(
    WebSocketEventType.MARKET_STATUS,
    useCallback((message: WebSocketMessage) => {
      if (message.data) {
        setMarketStatus(message.data);
      }
    }, []),
    []
  );

  return { marketStatus };
}

/**
 * 系統通知 Hook
 */
export function useSystemNotifications() {
  const [notifications, setNotifications] = useState<any[]>([]);

  // 監聽系統通知
  useWebSocketEvent(
    WebSocketEventType.SYSTEM_NOTIFICATION,
    useCallback((message: WebSocketMessage) => {
      if (message.data) {
        setNotifications(prev => [
          {
            ...message.data,
            id: Date.now(),
            timestamp: new Date(),
          },
          ...prev.slice(0, 9) // 保持最多10個通知
        ]);
      }
    }, []),
    []
  );

  // 清除通知
  const clearNotification = useCallback((id: number) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  }, []);

  // 清除所有通知
  const clearAllNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  return {
    notifications,
    clearNotification,
    clearAllNotifications,
  };
}

/**
 * 多股票訂閱 Hook
 */
export function useMultipleStockSubscriptions(stockIds: number[]) {
  const wsManager = useRef(getWebSocketManager());
  const [subscribedStocks, setSubscribedStocks] = useState<Set<number>>(new Set());

  // 穩定化事件處理器
  const handleWelcome = useCallback(() => {
    const manager = wsManager.current;
    const newSubscribed = new Set<number>();

    stockIds.forEach(stockId => {
      const success = manager.subscribeToStock(stockId);
      if (success) {
        newSubscribed.add(stockId);
      }
    });
    setSubscribedStocks(newSubscribed);
  }, [stockIds]);

  useEffect(() => {
    const manager = wsManager.current;
    const newSubscribed = new Set<number>();

    // 訂閱新股票
    stockIds.forEach(stockId => {
      if (manager.isConnected()) {
        const success = manager.subscribeToStock(stockId);
        if (success) {
          newSubscribed.add(stockId);
        }
      }
    });

    // 處理連接建立事件
    manager.on(WebSocketEventType.WELCOME, handleWelcome);
    setSubscribedStocks(newSubscribed);

    // 清理函數
    return () => {
      stockIds.forEach(stockId => {
        manager.unsubscribeFromStock(stockId);
      });
      manager.off(WebSocketEventType.WELCOME, handleWelcome);
    };
  }, [stockIds, handleWelcome]);

  return {
    subscribedStocks: Array.from(subscribedStocks),
    subscriptionCount: subscribedStocks.size,
  };
}