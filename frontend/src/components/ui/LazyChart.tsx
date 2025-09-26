/**
 * Lazy Chart Wrapper Component
 * 提供通用的圖表懶載入包裝器
 */
import React, { Suspense } from 'react';
import dynamic from 'next/dynamic';

interface LazyChartProps {
  type: 'realtime' | 'basic' | 'advanced';
  stockId?: number;
  symbol?: string;
  height?: number;
  stock?: {
    id: number;
    symbol: string;
    name?: string;
  };
  fallbackHeight?: number;
}

// 動態載入不同類型的圖表
const RealtimePriceChart = dynamic(
  () => import('../RealTime/RealtimePriceChart'),
  {
    ssr: false,
  }
);

const ChartPage = dynamic(
  () => import('../Charts/ChartPage'),
  {
    ssr: false,
  }
);

// 載入狀態組件
const ChartSkeleton: React.FC<{ height?: number }> = ({ height = 400 }) => (
  <div
    className="bg-white shadow rounded-lg p-6 flex items-center justify-center animate-pulse"
    style={{ height: `${height}px` }}
  >
    <div className="text-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
      <div className="h-4 bg-gray-200 rounded w-32 mx-auto mb-2"></div>
      <div className="h-3 bg-gray-200 rounded w-24 mx-auto"></div>
    </div>
  </div>
);

// 錯誤邊界組件
const ChartErrorBoundary: React.FC<{
  children: React.ReactNode;
  onRetry?: () => void;
}> = ({ children, onRetry }) => {
  return (
    <div className="bg-white shadow rounded-lg p-6">
      <Suspense
        fallback={<ChartSkeleton />}
      >
        {children}
      </Suspense>
    </div>
  );
};

export const LazyChart: React.FC<LazyChartProps> = ({
  type,
  stockId,
  symbol,
  height = 400,
  stock,
  fallbackHeight
}) => {
  const renderChart = () => {
    switch (type) {
      case 'realtime':
        if (stock) {
          return <RealtimePriceChart stock={stock} height={height} />;
        } else if (stockId && symbol) {
          // 向後兼容舊的 props 結構
          return (
            <RealtimePriceChart
              stock={{ id: stockId, symbol, name: symbol }}
              height={height}
            />
          );
        }
        return <div className="text-red-500">股票信息不完整</div>;

      case 'basic':
      case 'advanced':
        return <ChartPage stockId={stockId} />;

      default:
        return <div className="text-red-500">未知的圖表類型</div>;
    }
  };

  return (
    <ChartErrorBoundary>
      {renderChart()}
    </ChartErrorBoundary>
  );
};

// 預設導出組件與額外的便利組件
export default LazyChart;

// 便利組件
export const LazyRealtimeChart: React.FC<{
  stock: { id: number; symbol: string; name?: string };
  height?: number;
}> = ({ stock, height }) => (
  <LazyChart type="realtime" stock={stock} height={height} />
);

export const LazyBasicChart: React.FC<{
  stockId?: number;
}> = ({ stockId }) => (
  <LazyChart type="basic" stockId={stockId} />
);

export const LazyAdvancedChart: React.FC<{
  stockId?: number;
}> = ({ stockId }) => (
  <LazyChart type="advanced" stockId={stockId} />
);