/**
 * WebSocket Hook
 */
import { useEffect, useRef, useCallback } from 'react';
import { useAppSelector } from '../store';
import websocketManager from '../utils/websocketManager';

export interface UseWebSocketOptions {
  autoConnect?: boolean;
  subscriptions?: Array<{
    type: string;
    data?: any;
    callback?: (data: any) => void;
  }>;
}

export const useWebSocket = (options: UseWebSocketOptions = {}) => {
  const { autoConnect = true, subscriptions = [] } = options;
  const subscriptionIds = useRef<string[]>([]);
  
  // 從 Redux 獲取 WebSocket 狀態
  const connectionStatus = useAppSelector(state => state.app.systemStatus.websocket);
  const isOnline = useAppSelector(state => state.app.network.isOnline);
  
  // 連接 WebSocket
  const connect = useCallback(async () => {
    try {
      await websocketManager.connect();
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
    }
  }, []);

  // 斷開 WebSocket
  const disconnect = useCallback(() => {
    websocketManager.disconnect();
  }, []);

  // 發送消息
  const send = useCallback((message: any) => {
    return websocketManager.send(message);
  }, []);

  // 訂閱
  const subscribe = useCallback((type: string, data?: any, callback?: (data: any) => void) => {
    const id = websocketManager.subscribe(type, data, callback);
    subscriptionIds.current.push(id);
    return id;
  }, []);

  // 取消訂閱
  const unsubscribe = useCallback((id: string) => {
    const success = websocketManager.unsubscribe(id);
    if (success) {
      subscriptionIds.current = subscriptionIds.current.filter(subId => subId !== id);
    }
    return success;
  }, []);

  // 便捷訂閱方法
  const subscribeToStock = useCallback((stockId: number, callback?: (data: any) => void) => {
    return subscribe('stock', { stock_id: stockId }, callback);
  }, [subscribe]);

  const subscribeToSignals = useCallback((callback?: (data: any) => void) => {
    return subscribe('signals', undefined, callback);
  }, [subscribe]);

  const subscribeToGlobal = useCallback((callback?: (data: any) => void) => {
    return subscribe('global', undefined, callback);
  }, [subscribe]);

  // 自動連接
  useEffect(() => {
    if (autoConnect && isOnline) {
      connect();
    }

    return () => {
      // 清理所有訂閱
      subscriptionIds.current.forEach(id => {
        websocketManager.unsubscribe(id);
      });
      subscriptionIds.current = [];
    };
  }, [autoConnect, isOnline, connect]);

  // 處理初始訂閱
  useEffect(() => {
    if (connectionStatus === 'connected' && subscriptions.length > 0) {
      subscriptions.forEach(({ type, data, callback }) => {
        subscribe(type, data, callback);
      });
    }
  }, [connectionStatus, subscriptions, subscribe]);

  // 監聽網路狀態變化
  useEffect(() => {
    if (!isOnline && connectionStatus === 'connected') {
      disconnect();
    } else if (isOnline && connectionStatus === 'disconnected' && autoConnect) {
      connect();
    }
  }, [isOnline, connectionStatus, autoConnect, connect, disconnect]);

  return {
    connectionStatus,
    isConnected: connectionStatus === 'connected',
    isConnecting: connectionStatus === 'reconnecting',
    connect,
    disconnect,
    send,
    subscribe,
    unsubscribe,
    subscribeToStock,
    subscribeToSignals,
    subscribeToGlobal,
    stats: websocketManager.getStats(),
  };
};