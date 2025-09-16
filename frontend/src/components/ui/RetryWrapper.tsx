/**
 * Retry Wrapper Component for Error Recovery
 */
'use client';

import React, { useState, useCallback } from 'react';
import { ButtonLoader } from './LoadingStates';

interface RetryWrapperProps {
  children: React.ReactNode;
  onRetry: () => Promise<void> | void;
  error?: Error | string | null;
  isLoading?: boolean;
  maxRetries?: number;
  retryText?: string;
  errorMessage?: string;
  showErrorDetails?: boolean;
  className?: string;
}

export const RetryWrapper: React.FC<RetryWrapperProps> = ({
  children,
  onRetry,
  error,
  isLoading = false,
  maxRetries = 3,
  retryText = '重試',
  errorMessage,
  showErrorDetails = process.env.NODE_ENV === 'development',
  className = '',
}) => {
  const [retryCount, setRetryCount] = useState(0);
  const [isRetrying, setIsRetrying] = useState(false);

  const handleRetry = useCallback(async () => {
    if (retryCount >= maxRetries) return;

    setIsRetrying(true);
    try {
      await onRetry();
      setRetryCount(0); // 成功後重置重試計數
    } catch (error) {
      setRetryCount(prev => prev + 1);
      console.error('Retry failed:', error);
    } finally {
      setIsRetrying(false);
    }
  }, [onRetry, retryCount, maxRetries]);

  if (error && !isLoading && !isRetrying) {
    const errorText = typeof error === 'string' ? error : error.message;
    const canRetry = retryCount < maxRetries;

    return (
      <div className={`bg-white border border-red-200 rounded-lg p-6 ${className}`}>
        <div className="flex items-center justify-center mb-4">
          <div className="flex items-center justify-center w-12 h-12 bg-red-100 rounded-full">
            <svg
              className="w-6 h-6 text-red-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 18.5c-.77.833.192 2.5 1.732 2.5z"
              />
            </svg>
          </div>
        </div>

        <h3 className="text-lg font-medium text-gray-900 text-center mb-2">
          載入失敗
        </h3>

        <p className="text-gray-600 text-center mb-4">
          {errorMessage || '載入數據時發生錯誤，請稍後再試。'}
        </p>

        {showErrorDetails && (
          <details className="mb-4 p-3 bg-gray-50 rounded text-sm">
            <summary className="cursor-pointer font-medium text-gray-700 mb-2">
              錯誤詳情
            </summary>
            <pre className="whitespace-pre-wrap text-red-600 text-xs overflow-auto">
              {errorText}
            </pre>
          </details>
        )}

        {retryCount > 0 && (
          <p className="text-sm text-gray-500 text-center mb-4">
            重試次數: {retryCount}/{maxRetries}
          </p>
        )}

        <div className="text-center">
          {canRetry ? (
            <button
              onClick={handleRetry}
              disabled={isRetrying}
              className="inline-flex items-center px-4 py-2 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isRetrying ? (
                <>
                  <ButtonLoader size="sm" />
                  <span className="ml-2">重試中...</span>
                </>
              ) : (
                retryText
              )}
            </button>
          ) : (
            <div className="text-center">
              <p className="text-red-600 mb-3">已達到最大重試次數</p>
              <button
                onClick={() => window.location.reload()}
                className="inline-flex items-center px-4 py-2 bg-gray-600 text-white font-medium rounded-md hover:bg-gray-700 transition-colors"
              >
                重新載入頁面
              </button>
            </div>
          )}
        </div>
      </div>
    );
  }

  if (isLoading || isRetrying) {
    return (
      <div className={`bg-white rounded-lg p-6 text-center ${className}`}>
        <div className="flex items-center justify-center mb-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
        <p className="text-gray-600">
          {isRetrying ? '重試中...' : '載入中...'}
        </p>
      </div>
    );
  }

  return <>{children}</>;
};

// Hook for retry logic
export function useRetry<T>(
  asyncFunction: () => Promise<T>,
  dependencies: any[] = [],
  maxRetries: number = 3
) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  const execute = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await asyncFunction();
      setData(result);
      setRetryCount(0); // 成功後重置
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setIsLoading(false);
    }
  }, [asyncFunction, ...dependencies]);

  const retry = useCallback(async () => {
    if (retryCount >= maxRetries) return;

    setRetryCount(prev => prev + 1);
    await execute();
  }, [execute, retryCount, maxRetries]);

  React.useEffect(() => {
    execute();
  }, [execute]);

  return {
    data,
    error,
    isLoading,
    retry,
    retryCount,
    canRetry: retryCount < maxRetries,
  };
}

export default RetryWrapper;