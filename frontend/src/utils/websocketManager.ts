/**
 * WebSocket 管理器 - 增強版本，整合 Redux
 */
import { store } from '../store';
import { 
  setWebSocketStatus,
  incrementRetryCount,
  resetRetryCount 
} from '../store/slices/appSlice';
import { addRealTimeSignal } from '../store/slices/signalsSlice';
import { addToast } from '../store/slices/uiSlice';
import { handleError } from './errorHandler';
import type { TradingSignal, WebSocketMessage } from '../types';

export interface WebSocketManagerConfig {
  url?: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
  enableHeartbeat?: boolean;
  enableReconnect?: boolean;
  debug?: boolean;
}

export interface Subscription {
  id: string;
  type: string;
  data?: any;
  callback?: (data: any) => void;
}

class WebSocketManager {
  private ws: WebSocket | null = null;
  private url: string;
  private clientId: string;
  private config: Required<WebSocketManagerConfig>;
  private subscriptions: Map<string, Subscription> = new Map();
  private reconnectAttempts = 0;
  private reconnectTimeoutId: number | null = null;
  private heartbeatIntervalId: number | null = null;
  private isManuallyDisconnected = false;
  private connectionState: 'disconnected' | 'connecting' | 'connected' | 'error' = 'disconnected';
  private messageQueue: any[] = [];
  private lastHeartbeat = 0;

  constructor(config: WebSocketManagerConfig = {}) {
    this.config = {
      url: config.url || this.getDefaultWebSocketUrl(),
      reconnectInterval: config.reconnectInterval || 3000,
      maxReconnectAttempts: config.maxReconnectAttempts || 10,
      heartbeatInterval: config.heartbeatInterval || 30000,
      enableHeartbeat: config.enableHeartbeat ?? true,
      enableReconnect: config.enableReconnect ?? true,
      debug: config.debug ?? process.env.NODE_ENV === 'development',
    };

    this.url = this.config.url;
    this.clientId = this.generateClientId();
    
    this.log('WebSocket Manager initialized', { config: this.config });
  }

  private getDefaultWebSocketUrl(): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = process.env.NEXT_PUBLIC_WS_URL || 
                 process.env.NEXT_PUBLIC_API_URL?.replace(/^https?:/, protocol) ||
                 `${protocol}//${window.location.host}`;
    return `${host}/ws`;
  }

  private generateClientId(): string {
    return `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private log(message: string, data?: any) {
    if (this.config.debug) {
      console.log(`[WebSocket Manager] ${message}`, data);
    }
  }

  private updateConnectionState(state: typeof this.connectionState) {
    const prevState = this.connectionState;
    this.connectionState = state;
    
    // 更新 Redux store
    const wsStatus = state === 'connected' ? 'connected' : 
                    state === 'connecting' ? 'reconnecting' : 'disconnected';
    store.dispatch(setWebSocketStatus(wsStatus));

    this.log(`Connection state changed: ${prevState} -> ${state}`);
  }

  public connect(): Promise<void> {
    if (this.connectionState === 'connected' || this.connectionState === 'connecting') {
      this.log('Already connected or connecting');
      return Promise.resolve();
    }

    this.isManuallyDisconnected = false;
    this.updateConnectionState('connecting');

    return new Promise((resolve, reject) => {
      try {
        const wsUrl = `${this.url}?client_id=${this.clientId}`;
        this.log('Attempting to connect to:', wsUrl);
        
        this.ws = new WebSocket(wsUrl);

        const connectTimeout = setTimeout(() => {
          if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
            this.ws.close();
            reject(new Error('WebSocket connection timeout'));
          }
        }, 10000); // 10 seconds timeout

        this.ws.onopen = () => {
          clearTimeout(connectTimeout);
          this.log('WebSocket connected successfully');
          
          this.updateConnectionState('connected');
          this.reconnectAttempts = 0;
          store.dispatch(resetRetryCount());
          
          // 開始心跳
          if (this.config.enableHeartbeat) {
            this.startHeartbeat();
          }

          // 重新訂閱
          this.resubscribeAll();
          
          // 發送隊列中的消息
          this.flushMessageQueue();

          // 顯示連接成功通知
          store.dispatch(addToast({
            type: 'success',
            title: 'WebSocket 已連接',
            message: '即時數據更新已啟用',
            duration: 3000,
          }));

          resolve();
        };

        this.ws.onmessage = (event) => {
          this.handleMessage(event);
        };

        this.ws.onclose = (event) => {
          clearTimeout(connectTimeout);
          this.log('WebSocket closed', { code: event.code, reason: event.reason });
          
          this.updateConnectionState('disconnected');
          this.stopHeartbeat();

          if (!this.isManuallyDisconnected && this.config.enableReconnect) {
            this.scheduleReconnect();
          }
        };

        this.ws.onerror = (error) => {
          clearTimeout(connectTimeout);
          this.log('WebSocket error:', error);
          
          this.updateConnectionState('error');
          
          const wsError = new Error('WebSocket connection error');
          handleError(wsError, { 
            component: 'websocket',
            action: 'connection_error' 
          });

          reject(wsError);
        };

      } catch (error) {
        this.updateConnectionState('error');
        reject(error);
      }
    });
  }

  public disconnect(): void {
    this.log('Manually disconnecting WebSocket');
    
    this.isManuallyDisconnected = true;
    this.stopHeartbeat();
    this.clearReconnectTimeout();
    
    if (this.ws) {
      this.ws.close(1000, 'Manual disconnect');
      this.ws = null;
    }
    
    this.updateConnectionState('disconnected');
    this.subscriptions.clear();
    this.messageQueue = [];
  }

  private handleMessage(event: MessageEvent) {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);
      this.log('Received message:', message);

      // 更新最後心跳時間
      this.lastHeartbeat = Date.now();

      // 處理不同類型的消息
      switch (message.type) {
        case 'welcome':
          this.log('Received welcome message:', message.message);
          break;

        case 'pong':
          this.log('Received pong');
          break;

        case 'error':
          this.log('Received error message:', message.message);
          store.dispatch(addToast({
            type: 'error',
            title: 'WebSocket 錯誤',
            message: message.message || '未知錯誤',
            duration: 5000,
          }));
          break;

        case 'stock_update':
          this.handleStockUpdate(message.data);
          break;

        case 'signal_update':
          this.handleSignalUpdate(message.data);
          break;

        case 'market_update':
          this.handleMarketUpdate(message.data);
          break;

        case 'system_notification':
          this.handleSystemNotification(message.data);
          break;

        default:
          this.log('Unknown message type:', message.type);
      }

      // 觸發訂閱回調
      this.triggerSubscriptionCallbacks(message);

    } catch (error) {
      this.log('Failed to parse message:', error);
      handleError(error as Error, { 
        component: 'websocket',
        action: 'message_parse_error' 
      });
    }
  }

  private handleStockUpdate(data: any) {
    this.log('Stock update received:', data);
    // 可以觸發股票數據更新
    // 例如: store.dispatch(updateStockData(data));
  }

  private handleSignalUpdate(data: TradingSignal) {
    this.log('Signal update received:', data);
    store.dispatch(addRealTimeSignal(data));
    
    // 顯示新信號通知
    store.dispatch(addToast({
      type: 'info',
      title: '新交易信號',
      message: `${data.symbol}: ${data.signal_type}`,
      duration: 5000,
    }));
  }

  private handleMarketUpdate(data: any) {
    this.log('Market update received:', data);
    // 處理市場更新
  }

  private handleSystemNotification(data: any) {
    this.log('System notification received:', data);
    
    store.dispatch(addToast({
      type: data.type || 'info',
      title: data.title || '系統通知',
      message: data.message,
      duration: data.duration || 5000,
    }));
  }

  private triggerSubscriptionCallbacks(message: WebSocketMessage) {
    this.subscriptions.forEach((subscription) => {
      if (subscription.type === message.type && subscription.callback) {
        try {
          subscription.callback(message.data);
        } catch (error) {
          this.log('Subscription callback error:', error);
        }
      }
    });
  }

  private startHeartbeat() {
    this.stopHeartbeat();
    this.lastHeartbeat = Date.now();
    
    this.heartbeatIntervalId = window.setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.send({ type: 'ping' });
        
        // 檢查心跳超時
        const timeSinceLastHeartbeat = Date.now() - this.lastHeartbeat;
        if (timeSinceLastHeartbeat > this.config.heartbeatInterval * 2) {
          this.log('Heartbeat timeout, reconnecting...');
          this.ws.close();
        }
      }
    }, this.config.heartbeatInterval);
  }

  private stopHeartbeat() {
    if (this.heartbeatIntervalId) {
      clearInterval(this.heartbeatIntervalId);
      this.heartbeatIntervalId = null;
    }
  }

  private scheduleReconnect() {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      this.log('Max reconnect attempts reached');
      this.updateConnectionState('error');
      
      store.dispatch(addToast({
        type: 'error',
        title: 'WebSocket 連接失敗',
        message: '無法連接到服務器，請檢查網路連接',
        duration: 10000,
      }));
      
      return;
    }

    this.reconnectAttempts++;
    store.dispatch(incrementRetryCount());
    
    const delay = Math.min(
      this.config.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1),
      30000 // 最大 30 秒
    );

    this.log(`Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`);

    this.reconnectTimeoutId = window.setTimeout(() => {
      if (!this.isManuallyDisconnected) {
        this.connect().catch((error) => {
          this.log('Reconnect failed:', error);
        });
      }
    }, delay);
  }

  private clearReconnectTimeout() {
    if (this.reconnectTimeoutId) {
      clearTimeout(this.reconnectTimeoutId);
      this.reconnectTimeoutId = null;
    }
  }

  private resubscribeAll() {
    this.log('Resubscribing to all subscriptions');
    this.subscriptions.forEach((subscription) => {
      this.send({
        type: subscription.type,
        data: subscription.data,
      });
    });
  }

  private flushMessageQueue() {
    this.log(`Flushing ${this.messageQueue.length} queued messages`);
    
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift();
      this.send(message, false); // 不要再次加入隊列
    }
  }

  public send(message: any, queueIfDisconnected = true): boolean {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(JSON.stringify(message));
        this.log('Message sent:', message);
        return true;
      } catch (error) {
        this.log('Failed to send message:', error);
        return false;
      }
    } else {
      this.log('WebSocket not connected, message queued:', message);
      
      if (queueIfDisconnected) {
        this.messageQueue.push(message);
      }
      
      return false;
    }
  }

  // 訂閱管理
  public subscribe(type: string, data?: any, callback?: (data: any) => void): string {
    const id = `sub_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const subscription: Subscription = { id, type, data, callback };
    this.subscriptions.set(id, subscription);
    
    // 發送訂閱請求
    this.send({
      type: `subscribe_${type}`,
      data,
    });

    this.log('Added subscription:', subscription);
    return id;
  }

  public unsubscribe(id: string): boolean {
    const subscription = this.subscriptions.get(id);
    if (!subscription) {
      return false;
    }

    // 發送取消訂閱請求
    this.send({
      type: `unsubscribe_${subscription.type}`,
      data: subscription.data,
    });

    this.subscriptions.delete(id);
    this.log('Removed subscription:', id);
    return true;
  }

  public unsubscribeAll(): void {
    this.subscriptions.forEach((_, id) => {
      this.unsubscribe(id);
    });
  }

  // 便捷訂閱方法
  public subscribeToStock(stockId: number, callback?: (data: any) => void): string {
    return this.subscribe('stock', { stock_id: stockId }, callback);
  }

  public subscribeToSignals(callback?: (data: any) => void): string {
    return this.subscribe('signals', undefined, callback);
  }

  public subscribeToGlobal(callback?: (data: any) => void): string {
    return this.subscribe('global', undefined, callback);
  }

  // 狀態查詢
  public getConnectionState(): string {
    return this.connectionState;
  }

  public isConnected(): boolean {
    return this.connectionState === 'connected';
  }

  public getSubscriptions(): Subscription[] {
    return Array.from(this.subscriptions.values());
  }

  public getStats() {
    return {
      connectionState: this.connectionState,
      reconnectAttempts: this.reconnectAttempts,
      subscriptions: this.subscriptions.size,
      queuedMessages: this.messageQueue.length,
      lastHeartbeat: this.lastHeartbeat,
      clientId: this.clientId,
    };
  }
}

// 創建全局 WebSocket 管理器實例
const globalWebSocketManager = new WebSocketManager();

export default globalWebSocketManager;
export { WebSocketManager };