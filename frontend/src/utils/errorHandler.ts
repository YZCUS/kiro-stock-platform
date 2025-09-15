/**
 * 全局錯誤處理器
 */
import { store } from '../store';
import { addToast } from '../store/slices/uiSlice';
import { incrementErrorCount } from '../store/slices/appSlice';

export interface ErrorContext {
  component?: string;
  action?: string;
  userId?: string;
  sessionId?: string;
  url?: string;
  userAgent?: string;
  timestamp?: string;
  additional?: Record<string, any>;
}

export interface ProcessedError {
  id: string;
  type: 'network' | 'api' | 'validation' | 'runtime' | 'unknown';
  message: string;
  originalError: Error;
  context: ErrorContext;
  severity: 'low' | 'medium' | 'high' | 'critical';
  shouldReport: boolean;
  shouldNotify: boolean;
}

class ErrorHandler {
  private errorQueue: ProcessedError[] = [];
  private reportingEnabled: boolean = true;
  private maxQueueSize: number = 100;

  constructor() {
    this.setupGlobalHandlers();
  }

  private setupGlobalHandlers() {
    // 處理未捕獲的 Promise 拒絕
    window.addEventListener('unhandledrejection', (event) => {
      const error = event.reason instanceof Error ? event.reason : new Error(String(event.reason));
      this.handleError(error, {
        component: 'global',
        action: 'unhandled_promise_rejection',
      });
    });

    // 處理未捕獲的 JavaScript 錯誤
    window.addEventListener('error', (event) => {
      const error = event.error || new Error(event.message);
      this.handleError(error, {
        component: 'global',
        action: 'unhandled_error',
        url: event.filename,
      });
    });

    // 處理 Resource 載入錯誤
    window.addEventListener('error', (event) => {
      if (event.target && event.target !== window) {
        const target = event.target as HTMLElement;
        const error = new Error(`Resource failed to load: ${target.tagName}`);
        this.handleError(error, {
          component: 'global',
          action: 'resource_load_error',
          additional: {
            tagName: target.tagName,
            src: (target as any).src || (target as any).href,
          },
        });
      }
    }, true);
  }

  public handleError(error: Error, context: ErrorContext = {}): ProcessedError {
    const processedError = this.processError(error, context);
    
    // 添加到錯誤隊列
    this.addToQueue(processedError);
    
    // 增加錯誤計數
    store.dispatch(incrementErrorCount(context.component || 'unknown'));
    
    // 決定是否顯示用戶通知
    if (processedError.shouldNotify) {
      this.notifyUser(processedError);
    }
    
    // 決定是否上報錯誤
    if (processedError.shouldReport && this.reportingEnabled) {
      this.reportError(processedError);
    }
    
    return processedError;
  }

  private processError(error: Error, context: ErrorContext): ProcessedError {
    const id = this.generateErrorId();
    const type = this.classifyError(error);
    const severity = this.determineSeverity(error, type);
    const message = this.getErrorMessage(error, type);
    
    const fullContext: ErrorContext = {
      ...context,
      url: window.location.href,
      userAgent: navigator.userAgent,
      timestamp: new Date().toISOString(),
    };

    return {
      id,
      type,
      message,
      originalError: error,
      context: fullContext,
      severity,
      shouldReport: severity !== 'low',
      shouldNotify: severity === 'high' || severity === 'critical',
    };
  }

  private classifyError(error: Error): ProcessedError['type'] {
    const message = error.message.toLowerCase();
    const stack = error.stack?.toLowerCase() || '';

    // 網路錯誤
    if (message.includes('network') || 
        message.includes('fetch') || 
        message.includes('connection') ||
        message.includes('timeout')) {
      return 'network';
    }

    // API 錯誤
    if (message.includes('api') || 
        message.includes('http') || 
        message.includes('response') ||
        stack.includes('axios')) {
      return 'api';
    }

    // 驗證錯誤
    if (message.includes('validation') || 
        message.includes('invalid') || 
        message.includes('required')) {
      return 'validation';
    }

    // 運行時錯誤
    if (message.includes('undefined') || 
        message.includes('null') || 
        message.includes('cannot read property') ||
        message.includes('is not a function')) {
      return 'runtime';
    }

    return 'unknown';
  }

  private determineSeverity(error: Error, type: ProcessedError['type']): ProcessedError['severity'] {
    // 根據錯誤類型確定嚴重程度
    switch (type) {
      case 'network':
        return 'medium';
      case 'api':
        return 'medium';
      case 'validation':
        return 'low';
      case 'runtime':
        return 'high';
      default:
        return 'medium';
    }
  }

  private getErrorMessage(error: Error, type: ProcessedError['type']): string {
    // 用戶友好的錯誤訊息
    const userMessages: Record<ProcessedError['type'], string> = {
      network: '網路連線發生問題，請檢查您的網路連線',
      api: '服務暫時無法使用，請稍後再試',
      validation: '輸入的資料格式不正確，請檢查後重試',
      runtime: '應用程式發生錯誤，請重新載入頁面',
      unknown: '發生未知錯誤，請聯繫技術支援',
    };

    return userMessages[type];
  }

  private generateErrorId(): string {
    return `err_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private addToQueue(error: ProcessedError) {
    this.errorQueue.push(error);
    
    // 限制隊列大小
    if (this.errorQueue.length > this.maxQueueSize) {
      this.errorQueue = this.errorQueue.slice(-this.maxQueueSize);
    }
  }

  private notifyUser(error: ProcessedError) {
    store.dispatch(addToast({
      type: 'error',
      title: '錯誤',
      message: error.message,
      duration: 7000,
    }));
  }

  private reportError(error: ProcessedError) {
    // 在開發環境下只記錄到控制台
    if (process.env.NODE_ENV === 'development') {
      console.group(`🚨 Error Report: ${error.id}`);
      console.error('Processed Error:', error);
      console.error('Original Error:', error.originalError);
      console.error('Context:', error.context);
      console.groupEnd();
      return;
    }

    // 生產環境下可以發送到錯誤追蹤服務
    // 例如 Sentry, LogRocket, Bugsnag 等
    this.sendToErrorService(error);
  }

  private async sendToErrorService(error: ProcessedError) {
    try {
      // 這裡實作發送到錯誤追蹤服務的邏輯
      // 例如:
      // await fetch('/api/errors', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(error),
      // });

      console.log('Error reported to service:', error.id);
    } catch (reportingError) {
      console.error('Failed to report error:', reportingError);
    }
  }

  // 公開方法
  public getErrorQueue(): ProcessedError[] {
    return [...this.errorQueue];
  }

  public clearErrorQueue() {
    this.errorQueue = [];
  }

  public enableReporting() {
    this.reportingEnabled = true;
  }

  public disableReporting() {
    this.reportingEnabled = false;
  }

  public getErrorStats() {
    const stats = {
      total: this.errorQueue.length,
      byType: {} as Record<ProcessedError['type'], number>,
      bySeverity: {} as Record<ProcessedError['severity'], number>,
      recent: this.errorQueue.filter(e => 
        Date.now() - new Date(e.context.timestamp!).getTime() < 3600000 // 1 hour
      ).length,
    };

    this.errorQueue.forEach(error => {
      stats.byType[error.type] = (stats.byType[error.type] || 0) + 1;
      stats.bySeverity[error.severity] = (stats.bySeverity[error.severity] || 0) + 1;
    });

    return stats;
  }
}

// 創建全局錯誤處理器實例
const globalErrorHandler = new ErrorHandler();

// 便捷方法
export const handleError = (error: Error, context?: ErrorContext) => {
  return globalErrorHandler.handleError(error, context);
};

export const getErrorStats = () => {
  return globalErrorHandler.getErrorStats();
};

export const clearErrors = () => {
  globalErrorHandler.clearErrorQueue();
};

export default globalErrorHandler;