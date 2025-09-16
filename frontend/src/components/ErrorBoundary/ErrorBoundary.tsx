/**
 * React 錯誤邊界組件
 */
'use client';

import React, { Component, ReactNode } from 'react';
import { AlertCircle, RefreshCw, Bug, Home } from 'lucide-react';
import Button from '../ui/Button';
import Card, { CardHeader, CardTitle, CardContent } from '../ui/Card';

interface ErrorInfo {
  componentStack: string;
  errorBoundary?: string;
  errorBoundaryStack?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
  eventId?: string;
}

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: (error: Error, errorInfo: ErrorInfo, retry: () => void) => ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  level?: 'page' | 'component' | 'critical';
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  private retryTimeoutId: number | null = null;

  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    // 更新 state，下一次渲染將顯示錯誤 UI
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    const { onError } = this.props;
    
    // 記錄錯誤詳情
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    
    // 更新狀態
    this.setState({
      error,
      errorInfo,
      eventId: this.generateEventId(),
    });

    // 調用自定義錯誤處理器
    if (onError) {
      onError(error, errorInfo);
    }

    // 發送錯誤報告 (可選)
    this.reportError(error, errorInfo);
  }

  componentWillUnmount() {
    if (this.retryTimeoutId) {
      window.clearTimeout(this.retryTimeoutId);
    }
  }

  private generateEventId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  private reportError = (error: Error, errorInfo: ErrorInfo) => {
    // 這裡可以集成錯誤報告服務，如 Sentry
    const errorReport = {
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      userAgent: navigator.userAgent,
      url: window.location.href,
      timestamp: new Date().toISOString(),
      eventId: this.state.eventId,
    };

    // 在開發環境下只打印到控制台
    if (process.env.NODE_ENV === 'development') {
      console.group('🐛 Error Report');
      console.error('Error:', error);
      console.error('Error Info:', errorInfo);
      console.error('Full Report:', errorReport);
      console.groupEnd();
    } else {
      // 生產環境下可以發送到錯誤追蹤服務
      // 例如: Sentry.captureException(error, { extra: errorReport });
    }
  };

  private handleRetry = () => {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined });
  };

  private handleReload = () => {
    window.location.reload();
  };

  private handleGoHome = () => {
    window.location.href = '/';
  };

  private renderDefaultFallback() {
    const { error, errorInfo, eventId } = this.state;
    const { level = 'component' } = this.props;

    if (level === 'critical') {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-100">
          <Card className="max-w-lg">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-red-600">
                <AlertCircle className="w-6 h-6" />
                系統發生嚴重錯誤
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-gray-600">
                很抱歉，應用程式遇到了無法恢復的錯誤。請重新載入頁面或聯繫技術支援。
              </p>
              
              {process.env.NODE_ENV === 'development' && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                  <div className="text-sm font-medium text-red-800 mb-2">
                    錯誤詳情 (開發模式):
                  </div>
                  <pre className="text-xs text-red-700 overflow-x-auto">
                    {error?.message}
                  </pre>
                </div>
              )}
              
              <div className="flex gap-2">
                <Button onClick={this.handleReload} className="flex-1">
                  <RefreshCw className="w-4 h-4 mr-2" />
                  重新載入
                </Button>
                <Button onClick={this.handleGoHome} variant="outline" className="flex-1">
                  <Home className="w-4 h-4 mr-2" />
                  返回首頁
                </Button>
              </div>
              
              {eventId && (
                <p className="text-xs text-gray-400 text-center">
                  錯誤 ID: {eventId}
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      );
    }

    if (level === 'page') {
      return (
        <div className="flex items-center justify-center py-16">
          <Card className="max-w-md">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-orange-600">
                <Bug className="w-5 h-5" />
                頁面載入錯誤
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-gray-600">
                此頁面發生錯誤，請嘗試重新載入或返回上一頁。
              </p>
              
              <div className="flex gap-2">
                <Button onClick={this.handleRetry} variant="outline" className="flex-1">
                  <RefreshCw className="w-4 h-4 mr-2" />
                  重試
                </Button>
                <Button onClick={this.handleReload} className="flex-1">
                  重新載入
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      );
    }

    // 組件級別錯誤
    return (
      <div className="border border-red-200 bg-red-50 rounded-lg p-4">
        <div className="flex items-center gap-2 text-red-600 mb-2">
          <AlertCircle className="w-4 h-4" />
          <span className="font-medium">組件錯誤</span>
        </div>
        <p className="text-sm text-red-700 mb-3">
          此組件發生錯誤，請嘗試重新載入。
        </p>
        <Button 
          onClick={this.handleRetry} 
          size="sm" 
          variant="outline"
          className="text-red-600 border-red-300 hover:bg-red-100"
        >
          <RefreshCw className="w-3 h-3 mr-1" />
          重試
        </Button>
      </div>
    );
  }

  render() {
    const { hasError, error, errorInfo } = this.state;
    const { children, fallback } = this.props;

    if (hasError && error && errorInfo) {
      // 如果提供了自定義 fallback，使用它
      if (fallback) {
        return fallback(error, errorInfo, this.handleRetry);
      }

      // 否則使用默認的錯誤 UI
      return this.renderDefaultFallback();
    }

    return children;
  }
}

// 高階組件包裝器
export const withErrorBoundary = <P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Omit<ErrorBoundaryProps, 'children'>
) => {
  const WrappedComponent = (props: P) => (
    <ErrorBoundary {...errorBoundaryProps}>
      <Component {...props} />
    </ErrorBoundary>
  );

  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`;

  return WrappedComponent;
};

export default ErrorBoundary;