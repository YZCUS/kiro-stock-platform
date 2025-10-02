/**
 * 即時儀表板組件 - 整合所有即時功能
 */
'use client';

import React, { useState, useMemo } from 'react';
import dynamic from 'next/dynamic';
import { useStocks } from '../../hooks/useStocks';
import { useSignals } from '../../hooks/useSignals';
import { useWebSocket, useMarketStatus, useMultipleStockSubscriptions } from '../../hooks/useWebSocket';

// 動態載入重型圖表組件
const RealtimePriceChart = dynamic(() => import('./RealtimePriceChart'), {
  ssr: false,
  loading: () => (
    <div className="bg-white shadow rounded-lg p-6 h-96 flex items-center justify-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
    </div>
  ),
});

const RealtimeSignals = dynamic(() => import('./RealtimeSignals'), {
  ssr: false,
  loading: () => (
    <div className="bg-white shadow rounded-lg p-6 h-64 flex items-center justify-center">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
    </div>
  ),
});

export interface RealtimeDashboardProps {}

const RealtimeDashboard: React.FC<RealtimeDashboardProps> = () => {
  const [selectedStockIds, setSelectedStockIds] = useState<number[]>([1, 2, 4]);
  const [activeStockId, setActiveStockId] = useState<number>(1);

  // WebSocket 狀態
  const { isConnected, error: wsError } = useWebSocket();

  // 市場狀態
  const { marketStatus } = useMarketStatus();

  // 多股票訂閱
  const { subscribedStocks, subscriptionCount } = useMultipleStockSubscriptions(selectedStockIds);

  // 獲取股票列表數據
  const { data: stocksData, isLoading: stocksLoading } = useStocks({ pageSize: 10 });

  // 使用 useMemo 優化股票列表，減少不必要的重新渲染
  const stocks = useMemo(() => {
    return stocksData?.items || [];
  }, [stocksData?.items]);

  // 獲取最新信號數據
  const { data: signalsData } = useSignals({ pageSize: 5 });
  const latestSignals = useMemo(() => {
    return signalsData?.items || [];
  }, [signalsData?.items]);

  // 使用 useMemo 優化股票查找，避免重複查找操作
  const activeStock = useMemo(() => {
    return stocks.find(stock => stock.id === activeStockId);
  }, [stocks, activeStockId]);

  // 使用 useMemo 優化顯示的股票列表（前5個）
  const displayStocks = useMemo(() => {
    return stocks.slice(0, 5);
  }, [stocks]);

  // 使用 useMemo 優化已訂閱股票的詳細信息
  const subscribedStocksDetails = useMemo(() => {
    return selectedStockIds.map(stockId => stocks.find(s => s.id === stockId)).filter(Boolean);
  }, [selectedStockIds, stocks]);

  // 切換股票訂閱
  const toggleStockSubscription = (stockId: number) => {
    if (selectedStockIds.includes(stockId)) {
      setSelectedStockIds(prev => prev.filter(id => id !== stockId));
    } else {
      setSelectedStockIds(prev => [...prev, stockId]);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              即時交易儀表板
            </h1>
            <p className="text-gray-600">
              股票價格、技術指標和交易信號的即時監控
            </p>
          </div>

          {/* 連接狀態 */}
          <div className="text-right">
            <div className={`inline-flex items-center px-3 py-2 rounded-full text-sm font-medium ${
              isConnected
                ? 'bg-green-100 text-green-800'
                : 'bg-red-100 text-red-800'
            }`}>
              <div className={`w-2 h-2 rounded-full mr-2 ${
                isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
              }`}></div>
              {isConnected ? '即時連線' : '連線中斷'}
            </div>
            {wsError && (
              <p className="text-xs text-red-600 mt-1">{wsError}</p>
            )}
          </div>
        </div>
      </div>

      {/* 統計卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center">
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-600">連線狀態</p>
              <p className={`text-2xl font-bold ${
                isConnected ? 'text-green-600' : 'text-red-600'
              }`}>
                {isConnected ? '正常' : '斷線'}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center">
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-600">訂閱股票</p>
              <p className="text-2xl font-bold text-blue-600">
                {subscriptionCount}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center">
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-600">最新信號</p>
              <p className="text-2xl font-bold text-purple-600">
                {latestSignals.length}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center">
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-600">市場狀態</p>
              <p className={`text-2xl font-bold ${
                marketStatus.is_open ? 'text-green-600' : 'text-orange-600'
              }`}>
                {marketStatus.is_open ? '開盤' : '休市'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* 股票選擇器 */}
      <div className="bg-white shadow rounded-lg p-6 mb-8">
        <h3 className="text-lg font-medium text-gray-900 mb-4">股票訂閱管理</h3>

        {stocksLoading ? (
          <div className="animate-pulse flex space-x-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-20 bg-gray-200 rounded flex-1"></div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {displayStocks.map((stock) => {
              const isSubscribed = selectedStockIds.includes(stock.id);
              const isActive = activeStockId === stock.id;

              return (
                <div
                  key={stock.id}
                  className={`p-4 border-2 rounded-lg cursor-pointer transition-all ${
                    isActive
                      ? 'border-blue-500 bg-blue-50'
                      : isSubscribed
                      ? 'border-green-300 bg-green-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => setActiveStockId(stock.id)}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="font-medium text-gray-900">
                      {stock.symbol}
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleStockSubscription(stock.id);
                      }}
                      className={`w-6 h-6 rounded border-2 flex items-center justify-center text-xs ${
                        isSubscribed
                          ? 'bg-green-500 border-green-500 text-white'
                          : 'border-gray-300 hover:border-green-300'
                      }`}
                    >
                      {isSubscribed ? '✓' : '+'}
                    </button>
                  </div>
                  <div className="text-sm text-gray-600">{stock.name}</div>
                  <div className={`text-xs mt-1 ${
                    subscribedStocks.includes(stock.id) ? 'text-green-600' : 'text-gray-400'
                  }`}>
                    {subscribedStocks.includes(stock.id) ? '已訂閱' : '未訂閱'}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 主要內容區域 */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        {/* 主圖表 */}
        <div className="xl:col-span-2">
          {activeStock ? (
            <RealtimePriceChart
              key={activeStock.id}
              stock={{
                id: activeStock.id,
                symbol: activeStock.symbol,
                name: activeStock.name
              }}
              height={600}
            />
          ) : (
            <div className="bg-white shadow rounded-lg p-6 h-96 flex items-center justify-center">
              <div className="text-center text-gray-500">
                <div className="text-xl mb-2">📊</div>
                <div>請選擇一個股票來查看即時圖表</div>
              </div>
            </div>
          )}
        </div>

        {/* 側邊欄 */}
        <div className="xl:col-span-1 space-y-6">
          {/* 即時信號 */}
          <RealtimeSignals />

          {/* 訂閱股票列表 */}
          {selectedStockIds.length > 0 && (
            <div className="bg-white shadow rounded-lg p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">已訂閱股票</h3>
              <div className="space-y-3">
                {subscribedStocksDetails.map((stock) => {
                  return (
                    <div
                      key={stock.id}
                      className={`flex items-center justify-between p-3 rounded-lg cursor-pointer ${
                        activeStockId === stock.id
                          ? 'bg-blue-50 border border-blue-200'
                          : 'bg-gray-50 hover:bg-gray-100'
                      }`}
                      onClick={() => setActiveStockId(stock.id)}
                    >
                      <div>
                        <div className="font-medium text-gray-900">
                          {stock.symbol}
                        </div>
                        <div className="text-sm text-gray-600">
                          {stock.name}
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <div className={`w-2 h-2 rounded-full ${
                          subscribedStocks.includes(stock.id) ? 'bg-green-500' : 'bg-gray-400'
                        }`}></div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleStockSubscription(stock.id);
                          }}
                          className="text-red-600 hover:text-red-800 text-sm"
                        >
                          取消
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 多股票小圖表 */}
      {selectedStockIds.length > 1 && (
        <div className="mt-8">
          <h3 className="text-lg font-medium text-gray-900 mb-4">多股票監控</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {selectedStockIds.slice(0, 6).map((stockId) => {
              const stock = stocks.find(s => s.id === stockId);
              if (!stock || stockId === activeStockId) return null;

              return (
                <div key={stockId} className="bg-white shadow rounded-lg overflow-hidden">
                  <div className="p-3 border-b border-gray-200">
                    <h4 className="font-medium text-gray-900">{stock.symbol}</h4>
                    <p className="text-sm text-gray-600">{stock.name}</p>
                  </div>
                  <RealtimePriceChart
                    stock={{
                      id: stockId,
                      symbol: stock.symbol,
                      name: stock.name
                    }}
                    height={200}
                  />
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default RealtimeDashboard;