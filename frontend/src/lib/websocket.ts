/**
 * WebSocket Manager for Real-time Stock Data
 */
import { getWebSocketUrl } from './runtimeConfig';

export enum WebSocketEventType {
  CONNECTED = 'connected',
  DISCONNECTED = 'disconnected',
  ERROR = 'error',
  RECONNECTING = 'reconnecting',
  MESSAGE = 'message',
  STOCK_UPDATE = 'stock_update',
  TRADING_SIGNAL = 'trading_signal',
  PRICE_UPDATE = 'price_update',
  SIGNAL_UPDATE = 'signal_update',
  INDICATOR_UPDATE = 'indicator_update',
  MARKET_STATUS = 'market_status',
  SYSTEM_NOTIFICATION = 'system_notification',
  WELCOME = 'welcome'
}

export type WebSocketCallback<T = unknown> = (data?: T) => void;

interface WebSocketSubscription {
  eventType: WebSocketEventType;
  callback: WebSocketCallback<unknown>;
}

class WebSocketManager {
  private ws: WebSocket | null = null;
  private url: string;
  private subscriptions: Map<string, WebSocketSubscription[]> = new Map();
  private reconnectInterval: number = 5000;
  private maxReconnectAttempts: number = 5;
  private reconnectAttempts: number = 0;
  private isConnecting: boolean = false;
  private stockSubscriptions: Set<number> = new Set();

  constructor(url: string) {
    this.url = url;
  }

  // Event listener compatibility methods for hooks
  on<T = unknown>(eventType: string, callback: WebSocketCallback<T>): void {
    this.subscribe(eventType as WebSocketEventType, callback);
  }

  off<T = unknown>(eventType: string, callback: WebSocketCallback<T>): void {
    const key = eventType.toString();
    const subscriptions = this.subscriptions.get(key);

    if (subscriptions) {
      const index = subscriptions.findIndex(sub => sub.callback === callback as WebSocketCallback<unknown>);
      if (index > -1) {
        subscriptions.splice(index, 1);
      }
    }
  }

  // Stock subscription methods
  subscribeToStock(stockId: number, symbol?: string): boolean {
    console.log('[WebSocket] subscribeToStock 被調用', {
      stockId,
      symbol,
      stockIdType: typeof stockId,
      isNumber: typeof stockId === 'number',
      isPositive: stockId > 0,
      stackTrace: new Error().stack?.split('\n').slice(2, 5).join('\n')
    });

    // 嚴格驗證 stockId 有效性
    if (!stockId || typeof stockId !== 'number' || stockId <= 0) {
      console.warn('[WebSocket] 訂閱失敗：無效的 stock_id', { stockId, type: typeof stockId });
      return false;
    }

    if (!this.isConnected()) {
      console.warn('[WebSocket] 訂閱失敗：WebSocket 未連接', { stockId });
      return false;
    }

    const message = {
      type: 'subscribe_stock',
      data: {
        stock_id: stockId,
        symbol: symbol
      }
    };

    console.log('[WebSocket] 準備發送訂閱消息', message);
    console.log('[WebSocket] message.data.stock_id =', message.data.stock_id, 'typeof =', typeof message.data.stock_id);

    this.stockSubscriptions.add(stockId);
    this.send(message);
    return true;
  }

  unsubscribeFromStock(stockId: number): void {
    this.stockSubscriptions.delete(stockId);
    if (this.isConnected()) {
      this.send({
        type: 'unsubscribe_stock',
        data: {
          stock_id: stockId
        }
      });
    }
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        console.log('[WebSocket] Already connected');
        resolve();
        return;
      }

      if (this.isConnecting) {
        console.log('[WebSocket] Connection already in progress');
        reject(new Error('Connection already in progress'));
        return;
      }

      this.isConnecting = true;
      console.log('[WebSocket] Attempting connection...');
      console.log('[WebSocket] URL:', this.url);
      console.log('[WebSocket] Current location:', typeof window !== 'undefined' ? window.location.href : 'N/A');

      try {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
          console.log('[WebSocket] Connection opened, waiting for welcome message...');
          this.isConnecting = false;
          this.reconnectAttempts = 0;
          this.emit(WebSocketEventType.CONNECTED);
          // Don't emit WELCOME here - wait for server's welcome message
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        this.ws.onclose = (event) => {
          console.log('[WebSocket] Disconnected');
          console.log('[WebSocket] Close code:', event.code);
          console.log('[WebSocket] Close reason:', event.reason || 'No reason provided');
          console.log('[WebSocket] Was clean:', event.wasClean);
          this.isConnecting = false;
          this.emit(WebSocketEventType.DISCONNECTED);
          this.attemptReconnect();
        };

        this.ws.onerror = (error) => {
          console.error('[WebSocket] Error occurred');
          console.error('[WebSocket] Error event:', error);
          console.error('[WebSocket] URL:', this.url);
          console.error('[WebSocket] ReadyState:', this.ws?.readyState, '(0=CONNECTING, 1=OPEN, 2=CLOSING, 3=CLOSED)');
          this.isConnecting = false;
          const errorMsg = `Failed to connect to ${this.url}`;
          this.emit(WebSocketEventType.ERROR, error);
          this.emit('error', { message: errorMsg }); // Hook compatibility
          reject(new Error(errorMsg));
        };

      } catch (error) {
        console.error('Failed to create WebSocket connection:', error);
        this.isConnecting = false;
        this.emit(WebSocketEventType.ERROR, error);
        this.emit('error', { message: error.message }); // Hook compatibility
        reject(error);
      }
    });
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.isConnecting = false;
    this.reconnectAttempts = 0;
  }

  send(data: unknown): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const jsonString = JSON.stringify(data);
      console.log('[WebSocket] 發送原始 JSON:', jsonString);
      console.log('[WebSocket] 解析後驗證:', JSON.parse(jsonString));
      this.ws.send(jsonString);
    } else {
      console.warn('WebSocket is not connected. Message not sent:', data);
    }
  }

  subscribe<T = unknown>(eventType: WebSocketEventType, callback: WebSocketCallback<T>): () => void {
    const key = eventType.toString();

    if (!this.subscriptions.has(key)) {
      this.subscriptions.set(key, []);
    }

    const subscription: WebSocketSubscription = {
      eventType,
      callback: callback as WebSocketCallback<unknown>,
    };
    this.subscriptions.get(key)!.push(subscription);

    // Return unsubscribe function
    return () => {
      const subscriptions = this.subscriptions.get(key);
      if (subscriptions) {
        const index = subscriptions.indexOf(subscription);
        if (index > -1) {
          subscriptions.splice(index, 1);
        }
      }
    };
  }

  private emit(eventType: WebSocketEventType | string, data?: unknown): void {
    const key = eventType.toString();
    const subscriptions = this.subscriptions.get(key);

    if (subscriptions) {
      subscriptions.forEach(subscription => {
        try {
          subscription.callback(data);
        } catch (error) {
          console.error(`Error in WebSocket callback for ${eventType}:`, error);
        }
      });
    }
  }

  private handleMessage(data: unknown): void {
    this.emit(WebSocketEventType.MESSAGE, data);
    const message = data && typeof data === 'object'
      ? data as {
        type?: string;
        message?: string;
        payload?: unknown;
        data?: { stock?: { symbol?: string } };
      }
      : {};

    // Handle specific message types
    if (message.type) {
      switch (message.type) {
        case 'welcome':
          console.log('[WebSocket] Received welcome message from server');
          this.emit(WebSocketEventType.WELCOME, data);
          this.emit('welcome', data); // Backwards compatibility
          break;
        case 'initial_data':
          // 接收到初始股票數據（訂閱後的首次數據推送）
          console.log('[WebSocket] Received initial data for stock:', message.data?.stock?.symbol);
          this.emit('initial_data', data);
          break;
        case 'stock_update':
          this.emit(WebSocketEventType.STOCK_UPDATE, message.payload);
          break;
        case 'trading_signal':
          this.emit(WebSocketEventType.TRADING_SIGNAL, message.payload);
          break;
        case 'price_update':
          this.emit('price_update', data);
          break;
        case 'signal_update':
          this.emit('signal_update', data);
          break;
        case 'indicator_update':
          this.emit('indicator_update', data);
          break;
        case 'market_status':
          this.emit('market_status', data);
          break;
        case 'system_notification':
          this.emit('system_notification', data);
          break;
        case 'error':
          console.warn('[WebSocket] Server error:', message.message || message.payload);
          this.emit('error', data);
          break;
        default:
          console.log('[WebSocket] Unknown message type:', message.type);
      }
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('[WebSocket] Max reconnect attempts reached');
      const errorMsg = `Failed to reconnect after ${this.maxReconnectAttempts} attempts`;
      this.emit(WebSocketEventType.ERROR, { message: errorMsg });
      this.emit('error', { message: errorMsg });
      return;
    }

    this.reconnectAttempts++;
    console.log(`[WebSocket] Reconnect attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}...`);
    console.log(`[WebSocket] Will retry in ${this.reconnectInterval}ms`);

    this.emit(WebSocketEventType.RECONNECTING);

    setTimeout(() => {
      this.connect().catch(err => {
        console.error('[WebSocket] Reconnect failed:', err.message);
      });
    }, this.reconnectInterval);
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  getReadyState(): number | null {
    return this.ws ? this.ws.readyState : null;
  }
}

// Singleton instance
let webSocketManager: WebSocketManager | null = null;

export function getWebSocketManager(url?: string): WebSocketManager {
  if (!webSocketManager) {
    // Import dynamically to avoid SSR issues
    let wsUrl: string;
    if (url) {
      wsUrl = url;
    } else {
      wsUrl = getWebSocketUrl();
      console.log('[WebSocket] Resolved URL:', wsUrl);
    }
    webSocketManager = new WebSocketManager(wsUrl);
  }
  return webSocketManager;
}

export default WebSocketManager;
