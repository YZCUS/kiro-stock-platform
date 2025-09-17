/**
 * Lazy Component Loader
 * 通用的組件懶載入工具
 */
import React, { Suspense, ComponentType } from 'react';
import dynamic, { DynamicOptions } from 'next/dynamic';

interface LazyLoaderProps {
  fallback?: React.ComponentType;
  errorFallback?: React.ComponentType<{ error: Error; retry: () => void }>;
  minLoadingTime?: number; // 最小載入時間，避免載入過快的閃爍
}

interface LazyComponentConfig extends LazyLoaderProps {
  importFn: () => Promise<{ default: ComponentType<any> } | ComponentType<any>>;
  dynamicOptions?: DynamicOptions<any>;
}

// 預設載入組件
const DefaultLoadingFallback: React.FC = () => (
  <div className="flex items-center justify-center p-8">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
  </div>
);

// 預設錯誤組件
const DefaultErrorFallback: React.FC<{ error: Error; retry: () => void }> = ({
  error,
  retry
}) => (
  <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
    <div className="text-red-800 mb-4">
      <h3 className="font-medium mb-2">組件載入失敗</h3>
      <p className="text-sm">{error.message}</p>
    </div>
    <button
      onClick={retry}
      className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 transition-colors"
    >
      重新載入
    </button>
  </div>
);

// 組件載入狀態管理
const useComponentLoader = (minLoadingTime: number = 0) => {
  const [isLoading, setIsLoading] = React.useState(true);
  const [startTime] = React.useState(Date.now());

  React.useEffect(() => {
    const elapsed = Date.now() - startTime;
    const remainingTime = Math.max(0, minLoadingTime - elapsed);

    const timer = setTimeout(() => {
      setIsLoading(false);
    }, remainingTime);

    return () => clearTimeout(timer);
  }, [startTime, minLoadingTime]);

  return isLoading;
};

// 創建懶載入組件的工廠函數
export const createLazyComponent = <T extends ComponentType<any>>({
  importFn,
  fallback: FallbackComponent = DefaultLoadingFallback,
  errorFallback: ErrorFallback = DefaultErrorFallback,
  minLoadingTime = 0,
  dynamicOptions = {}
}: LazyComponentConfig): ComponentType<React.ComponentProps<T>> => {
  const LazyComponent = dynamic(importFn, {
    ssr: false,
    loading: () => <FallbackComponent />,
    ...dynamicOptions
  });

  const WrappedComponent: ComponentType<React.ComponentProps<T>> = (props) => {
    const [error, setError] = React.useState<Error | null>(null);
    const [retryKey, setRetryKey] = React.useState(0);
    const shouldShowLoading = useComponentLoader(minLoadingTime);

    const handleRetry = React.useCallback(() => {
      setError(null);
      setRetryKey(prev => prev + 1);
    }, []);

    if (error) {
      return <ErrorFallback error={error} retry={handleRetry} />;
    }

    if (shouldShowLoading) {
      return <FallbackComponent />;
    }

    return (
      <Suspense fallback={<FallbackComponent />}>
        <LazyComponent key={retryKey} {...props} />
      </Suspense>
    );
  };

  return WrappedComponent;
};

// 預設的懶載入組件創建器
export const createStandardLazyComponent = <T extends ComponentType<any>>(
  importFn: () => Promise<{ default: T } | T>,
  loadingHeight: number = 200
) => {
  const LoadingFallback = () => (
    <div
      className="bg-white shadow rounded-lg p-6 flex items-center justify-center"
      style={{ minHeight: `${loadingHeight}px` }}
    >
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
    </div>
  );

  return createLazyComponent({
    importFn,
    fallback: LoadingFallback,
    minLoadingTime: 300, // 最小載入時間 300ms
  });
};

// 圖表組件專用的懶載入創建器
export const createLazyChartComponent = <T extends ComponentType<any>>(
  importFn: () => Promise<{ default: T } | T>,
  chartHeight: number = 400
) => {
  const ChartLoadingFallback = () => (
    <div
      className="bg-white shadow rounded-lg p-6 flex flex-col items-center justify-center"
      style={{ height: `${chartHeight}px` }}
    >
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
      <div className="text-gray-500 text-sm">載入圖表組件中...</div>
    </div>
  );

  const ChartErrorFallback: React.FC<{ error: Error; retry: () => void }> = ({
    error,
    retry
  }) => (
    <div
      className="bg-white shadow rounded-lg p-6 flex flex-col items-center justify-center"
      style={{ height: `${chartHeight}px` }}
    >
      <div className="text-red-500 mb-4">
        <svg className="w-12 h-12 mx-auto mb-2" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
        </svg>
        <p className="text-sm">圖表載入失敗</p>
      </div>
      <button
        onClick={retry}
        className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700 transition-colors"
      >
        重新載入
      </button>
    </div>
  );

  return createLazyComponent({
    importFn,
    fallback: ChartLoadingFallback,
    errorFallback: ChartErrorFallback,
    minLoadingTime: 500, // 圖表組件最小載入時間 500ms
  });
};

export default createLazyComponent;