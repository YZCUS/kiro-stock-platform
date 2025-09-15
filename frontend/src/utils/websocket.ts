/**
 * WebSocket 客戶端
 */
import type { WebSocketMessage, WebSocketSubscription } from '../types';

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private clientId: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectInterval = 3000;
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private isConnecting = false;
  private isManuallyDisconnected = false;

  // 事件監聽器
  private listeners: Map<string, Set<(data: any) => void>> = new Map();

  constructor(url?: string, clientId?: string) {
    this.url = url || this.getWebSocketUrl();
    this.clientId = clientId || this.generateClientId();
  }

  /**
   * 取得 WebSocket URL
   */
  private getWebSocketUrl(): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = process.env.NEXT_PUBLIC_WS_URL || 
                 process.env.NEXT_PUBLIC_API_URL?.replace(/^https?:/, protocol) ||
                 `${protocol}//${window.location.host}`;
    return `${host}/ws`;
  }

  /**
   * 生成客戶端 ID
   */
  private generateClientId(): string {
    return `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * 連接 WebSocket
   */
  public connect(): Promise<void> {
    if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
      return Promise.resolve();
    }

    this.isConnecting = true;
    this.isManuallyDisconnected = false;

    return new Promise((resolve, reject) => {
      try {
        const wsUrl = `${this.url}?client_id=${this.clientId}`;
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          console.log('WebSocket 連接成功');
          this.isConnecting = false;
          this.reconnectAttempts = 0;
          this.startHeartbeat();
          this.emit('connected', { clientId: this.clientId });
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);
            this.handleMessage(message);
          } catch (error) {
            console.error('解析 WebSocket 消息失敗:', error);
          }
        };

        this.ws.onclose = (event) => {
          console.log('WebSocket 連接關閉:', event.code, event.reason);
          this.isConnecting = false;
          this.stopHeartbeat();
          this.emit('disconnected', { code: event.code, reason: event.reason });

          // 自動重連（如果不是手動斷開）
          if (!this.isManuallyDisconnected && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect();
          }
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket 錯誤:', error);
          this.isConnecting = false;
          this.emit('error', error);
          reject(error);
        };

      } catch (error) {
        this.isConnecting = false;
        reject(error);
      }
    });
  }

  /**
   * 斷開連接
   */
  public disconnect(): void {
    this.isManuallyDisconnected = true;
    this.stopHeartbeat();
    
    if (this.ws) {
      this.ws.close(1000, 'Manual disconnect');
      this.ws = null;
    }
  }

  /**
   * 發送消息
   */
  public send(message: WebSocketSubscription): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket 未連接，無法發送消息');
    }
  }

  /**
   * 訂閱股票更新
   */
  public subscribeToStock(stockId: number): void {
    this.send({
      type: 'subscribe_stock',
      data: { stock_id: stockId }
    });
  }

  /**
   * 取消訂閱股票
   */
  public unsubscribeFromStock(stockId: number): void {
    this.send({
      type: 'unsubscribe_stock',
      data: { stock_id: stockId }
    });
  }

  /**
   * 訂閱全局更新
   */
  public subscribeToGlobal(): void {
    this.send({
      type: 'subscribe_global'
    });
  }

  /**
   * 取消全局訂閱
   */
  public unsubscribeFromGlobal(): void {
    this.send({
      type: 'unsubscribe_global'
    });
  }

  /**
   * 處理接收到的消息
   */
  private handleMessage(message: WebSocketMessage): void {
    const { type, data } = message;

    // 觸發對應類型的監聽器
    this.emit(type, data);

    // 處理特殊消息類型
    switch (type) {
      case 'welcome':
        console.log('收到歡迎消息:', message.message);
        break;
      case 'error':
        console.error('WebSocket 錯誤消息:', message.message);
        break;
      case 'pong':
        // 心跳響應，無需特殊處理
        break;
      default:
        // 其他消息類型已通過 emit 處理
        break;
    }
  }

  /**
   * 開始心跳
   */
  private startHeartbeat(): void {
    this.heartbeatInterval = setInterval(() => {
      this.send({ type: 'ping' });
    }, 30000); // 每30秒發送一次心跳
  }

  /**
   * 停止心跳
   */
  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  /**
   * 安排重連
   */
  private scheduleReconnect(): void {
    this.reconnectAttempts++;
    const delay = this.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(`將在 ${delay}ms 後嘗試重連 (第 ${this.reconnectAttempts} 次)`);
    
    setTimeout(() => {
      if (!this.isManuallyDisconnected) {
        this.connect().catch((error) => {
          console.error('重連失敗:', error);
        });
      }
    }, delay);
  }

  /**
   * 添加事件監聽器
   */
  public on(event: string, callback: (data: any) => void): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback);
  }

  /**
   * 移除事件監聽器
   */
  public off(event: string, callback: (data: any) => void): void {
    const eventListeners = this.listeners.get(event);
    if (eventListeners) {
      eventListeners.delete(callback);
      if (eventListeners.size === 0) {
        this.listeners.delete(event);
      }
    }
  }

  /**
   * 觸發事件
   */
  private emit(event: string, data: any): void {
    const eventListeners = this.listeners.get(event);
    if (eventListeners) {
      eventListeners.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`事件處理器錯誤 (${event}):`, error);
        }
      });
    }
  }

  /**
   * 取得連接狀態
   */
  public getConnectionState(): string {
    if (!this.ws) return 'DISCONNECTED';
    
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'CONNECTING';
      case WebSocket.OPEN:
        return 'CONNECTED';
      case WebSocket.CLOSING:
        return 'CLOSING';
      case WebSocket.CLOSED:
        return 'DISCONNECTED';
      default:
        return 'UNKNOWN';
    }
  }

  /**
   * 檢查是否已連接
   */
  public isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

// 創建全局 WebSocket 客戶端實例
export const globalWebSocketClient = new WebSocketClient();

// 導出 WebSocket hook
export const useWebSocket = () => {
  return globalWebSocketClient;
};