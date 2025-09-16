/**
 * 圖表頁面組件
 */
'use client';

import React, { useState } from 'react';

export interface ChartPageProps {
  stockId?: number;
}

const ChartPage: React.FC<ChartPageProps> = ({ stockId = 1 }) => {
  const [timeframe, setTimeframe] = useState('1D');
  const [indicators, setIndicators] = useState<string[]>(['SMA', 'RSI']);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">
          股票圖表分析
        </h1>
        <p className="text-gray-600">
          提供K線圖表和技術指標分析功能
        </p>
      </div>

      {/* 控制區域 */}
      <div className="bg-white shadow rounded-lg p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-medium text-gray-900">圖表設定</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* 股票選擇 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              股票代號
            </label>
            <select className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option>台積電 (2330.TW)</option>
              <option>鴻海 (2317.TW)</option>
              <option>聯發科 (2454.TW)</option>
              <option>Apple (AAPL)</option>
              <option>Google (GOOGL)</option>
            </select>
          </div>

          {/* 時間框架 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              時間框架
            </label>
            <div className="flex space-x-2">
              {['1D', '5D', '1M', '3M', '1Y'].map((tf) => (
                <button
                  key={tf}
                  onClick={() => setTimeframe(tf)}
                  className={`px-3 py-1 text-sm rounded-md ${
                    timeframe === tf
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  {tf}
                </button>
              ))}
            </div>
          </div>

          {/* 技術指標 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              技術指標
            </label>
            <div className="space-y-2">
              {['SMA', 'EMA', 'RSI', 'MACD', 'BB'].map((indicator) => (
                <label key={indicator} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={indicators.includes(indicator)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setIndicators([...indicators, indicator]);
                      } else {
                        setIndicators(indicators.filter(i => i !== indicator));
                      }
                    }}
                    className="mr-2 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-700">{indicator}</span>
                </label>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 主圖表區域 */}
      <div className="bg-white shadow rounded-lg p-6 mb-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">價格圖表</h2>
        <div className="h-96 bg-gray-50 rounded-lg flex items-center justify-center border-2 border-dashed border-gray-300">
          <div className="text-center">
            <div className="text-gray-500 text-lg font-medium mb-2">
              TradingView K線圖表
            </div>
            <div className="text-gray-400">
              包含價格數據和所選技術指標
            </div>
          </div>
        </div>
      </div>

      {/* 技術指標圖表區域 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">RSI 指標</h3>
          <div className="h-48 bg-gray-50 rounded-lg flex items-center justify-center border-2 border-dashed border-gray-300">
            <div className="text-center">
              <div className="text-gray-500 text-sm font-medium mb-1">
                RSI 震盪指標
              </div>
              <div className="text-gray-400 text-xs">
                相對強弱指標 (14期)
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">MACD 指標</h3>
          <div className="h-48 bg-gray-50 rounded-lg flex items-center justify-center border-2 border-dashed border-gray-300">
            <div className="text-center">
              <div className="text-gray-500 text-sm font-medium mb-1">
                MACD 指標
              </div>
              <div className="text-gray-400 text-xs">
                指數平滑移動平均匯聚背馳
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 統計資訊 */}
      <div className="mt-6 grid grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white shadow rounded-lg p-4">
          <div className="text-sm text-gray-600">目前價格</div>
          <div className="text-2xl font-bold text-gray-900">NT$ 575.00</div>
          <div className="text-sm text-green-600">+2.50 (+0.44%)</div>
        </div>

        <div className="bg-white shadow rounded-lg p-4">
          <div className="text-sm text-gray-600">日高</div>
          <div className="text-lg font-semibold text-gray-900">NT$ 578.00</div>
        </div>

        <div className="bg-white shadow rounded-lg p-4">
          <div className="text-sm text-gray-600">日低</div>
          <div className="text-lg font-semibold text-gray-900">NT$ 572.50</div>
        </div>

        <div className="bg-white shadow rounded-lg p-4">
          <div className="text-sm text-gray-600">成交量</div>
          <div className="text-lg font-semibold text-gray-900">12.5M</div>
        </div>
      </div>
    </div>
  );
};

export default ChartPage;