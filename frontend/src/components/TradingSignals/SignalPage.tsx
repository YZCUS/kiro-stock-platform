/**
 * 交易信號頁面組件
 */
'use client';

import React, { useState } from 'react';

export interface SignalPageProps {}

const SignalPage: React.FC<SignalPageProps> = () => {
  const [selectedStock, setSelectedStock] = useState<string>('');

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">
          交易信號分析
        </h1>
        <p className="text-gray-600">
          即時監控股票交易信號，包括黃金交叉、死亡交叉等技術指標信號
        </p>
      </div>

      {/* 股票選擇器 */}
      <div className="bg-white shadow rounded-lg p-6 mb-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">選擇股票</h2>
        <div className="flex items-center space-x-4">
          <select
            value={selectedStock}
            onChange={(e) => setSelectedStock(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">請選擇股票</option>
            <option value="2330.TW">台積電 (2330)</option>
            <option value="2317.TW">鴻海 (2317)</option>
            <option value="2454.TW">聯發科 (2454)</option>
            <option value="AAPL">Apple (AAPL)</option>
            <option value="GOOGL">Google (GOOGL)</option>
            <option value="TSLA">Tesla (TSLA)</option>
          </select>
        </div>
      </div>

      {/* 信號圖表區域 */}
      {selectedStock && (
        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">
            {selectedStock} - 交易信號圖表
          </h2>
          <div className="h-96 bg-gray-50 rounded-lg flex items-center justify-center border-2 border-dashed border-gray-300">
            <div className="text-center">
              <div className="text-gray-500 text-lg font-medium mb-2">
                信號圖表將在此顯示
              </div>
              <div className="text-gray-400">
                包含K線圖、技術指標和買賣信號標示
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 信號列表 */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">最新信號</h2>
        <div className="space-y-4">
          {/* 示例信號項目 */}
          <div className="border-l-4 border-green-500 bg-green-50 p-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-green-800">
                  黃金交叉信號 - 買入建議
                </h3>
                <p className="text-sm text-green-700 mt-1">
                  台積電 (2330.TW) - MA5 向上突破 MA20
                </p>
              </div>
              <div className="text-right">
                <div className="text-sm font-medium text-green-800">NT$ 575.00</div>
                <div className="text-xs text-green-600">2024-01-15 14:30</div>
              </div>
            </div>
          </div>

          <div className="border-l-4 border-red-500 bg-red-50 p-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-red-800">
                  死亡交叉信號 - 賣出建議
                </h3>
                <p className="text-sm text-red-700 mt-1">
                  鴻海 (2317.TW) - MA5 向下跌破 MA20
                </p>
              </div>
              <div className="text-right">
                <div className="text-sm font-medium text-red-800">NT$ 105.50</div>
                <div className="text-xs text-red-600">2024-01-15 13:45</div>
              </div>
            </div>
          </div>

          <div className="border-l-4 border-blue-500 bg-blue-50 p-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-blue-800">
                  RSI超賣信號 - 關注建議
                </h3>
                <p className="text-sm text-blue-700 mt-1">
                  聯發科 (2454.TW) - RSI指標低於30，可能反彈
                </p>
              </div>
              <div className="text-right">
                <div className="text-sm font-medium text-blue-800">NT$ 890.00</div>
                <div className="text-xs text-blue-600">2024-01-15 12:20</div>
              </div>
            </div>
          </div>
        </div>

        {!selectedStock && (
          <div className="text-center py-8">
            <div className="text-gray-500">
              請先選擇股票以查看相關交易信號
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SignalPage;