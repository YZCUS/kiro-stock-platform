'use client';

import dynamic from 'next/dynamic';

const RealtimePriceChart = dynamic(
  () => import('../../components/RealTime/RealtimePriceChart'),
  {
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    ),
  }
);

const RealtimeSignals = dynamic(
  () => import('../../components/RealTime/RealtimeSignals'),
  {
    ssr: false,
    loading: () => (
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
    ),
  }
);

export default function ChartsPage() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">
          即時圖表分析
        </h1>
        <p className="text-gray-600">
          即時價格圖表和交易信號監控
        </p>
      </div>

      {/* 即時價格圖表 */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        <div className="xl:col-span-2">
          <RealtimePriceChart
            stock={{
              id: 1,
              symbol: "2330.TW",
              name: "台積電"
            }}
            height={500}
          />
        </div>

        {/* 即時信號面板 */}
        <div className="xl:col-span-1">
          <RealtimeSignals />
        </div>
      </div>

      {/* 多股票監控面板 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <RealtimePriceChart
          stock={{
            id: 2,
            symbol: "2317.TW",
            name: "鴻海"
          }}
          height={300}
        />
        <RealtimePriceChart
          stock={{
            id: 4,
            symbol: "AAPL",
            name: "Apple Inc."
          }}
          height={300}
        />
      </div>
    </div>
  );
}