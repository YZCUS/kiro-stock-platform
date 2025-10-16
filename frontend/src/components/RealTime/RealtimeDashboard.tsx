/**
 * 即時圖表分析 - 單一股票顯示模式
 */
'use client';

import React, { useState, useEffect, useMemo, useRef } from 'react';
import dynamic from 'next/dynamic';
import { useSearchParams } from 'next/navigation';
import { useAppDispatch, useAppSelector } from '@/store';
import { fetchStockLists, fetchListStocks } from '@/store/slices/stockListSlice';
import { useWebSocket, useMarketStatus } from '../../hooks/useWebSocket';
import { ensureStockExistsAuto, StockEnsureResult } from '../../services/stockValidationApi';
import { ChevronDown, TrendingUp, Activity, BarChart3, Search, X } from 'lucide-react';

// 動態載入圖表組件
const RealtimePriceChart = dynamic(() => import('./RealtimePriceChart'), {
  ssr: false,
  loading: () => (
    <div className="bg-white shadow rounded-lg p-6 h-[600px] flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-500">載入圖表中...</p>
      </div>
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
  const dispatch = useAppDispatch();
  const searchParams = useSearchParams();
  const { isAuthenticated } = useAppSelector((state) => state.auth);
  const { lists, currentListStocks, loading } = useAppSelector((state) => state.stockList);

  const [selectedListId, setSelectedListId] = useState<number | null>(null);
  const [selectedStockId, setSelectedStockId] = useState<number | null>(null);
  const [showListDropdown, setShowListDropdown] = useState(false);
  const [showStockDropdown, setShowStockDropdown] = useState(false);

  // 直接輸入股票代號的狀態
  const [symbolInput, setSymbolInput] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [directStock, setDirectStock] = useState<any | null>(null);

  // WebSocket 狀態
  const { isConnected, error: wsError } = useWebSocket();
  const { marketStatus } = useMarketStatus();

  // Refs for dropdown containers
  const listDropdownRef = useRef<HTMLDivElement>(null);
  const stockDropdownRef = useRef<HTMLDivElement>(null);

  // 從 URL 參數讀取股票 ID
  const stockIdFromUrl = searchParams.get('stock');

  // 載入清單
  useEffect(() => {
    if (isAuthenticated && lists.length === 0) {
      dispatch(fetchStockLists());
    }
  }, [isAuthenticated, dispatch, lists.length]);

  // 當選擇清單時載入該清單的股票
  useEffect(() => {
    if (selectedListId) {
      dispatch(fetchListStocks(selectedListId));
    }
  }, [selectedListId, dispatch]);

  // 當清單載入後，自動選擇第一個清單
  useEffect(() => {
    if (lists.length > 0 && !selectedListId) {
      setSelectedListId(lists[0].id);
    }
  }, [lists, selectedListId]);

  // 當有 URL 股票參數時，載入所有清單的股票來查找該股票
  useEffect(() => {
    if (stockIdFromUrl && lists.length > 0 && !selectedStockId) {
      // 載入所有清單的股票來查找目標股票
      lists.forEach(list => {
        dispatch(fetchListStocks(list.id));
      });
    }
  }, [stockIdFromUrl, lists, selectedStockId, dispatch]);

  // 當股票列表載入後，自動選擇第一個股票或 URL 參數指定的股票
  useEffect(() => {
    if (currentListStocks.length > 0) {
      // 如果已經選擇了股票，檢查該股票是否在當前清單中
      if (selectedStockId) {
        const stockExists = currentListStocks.find(s => s.id === selectedStockId);
        // 如果選中的股票不在當前清單中，重新選擇第一支股票
        if (!stockExists) {
          setSelectedStockId(currentListStocks[0].id);
        }
      } else {
        // 如果沒有選擇股票
        // 如果 URL 有指定股票 ID，優先選擇該股票
        if (stockIdFromUrl) {
          const stockId = parseInt(stockIdFromUrl, 10);
          const stockExists = currentListStocks.find(s => s.id === stockId);
          if (stockExists) {
            setSelectedStockId(stockId);
            return;
          }
        }
        // 否則選擇第一個股票
        setSelectedStockId(currentListStocks[0].id);
      }
    }
  }, [currentListStocks, selectedStockId, stockIdFromUrl]);

  // 點擊外部關閉下拉選單
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        listDropdownRef.current &&
        !listDropdownRef.current.contains(event.target as Node)
      ) {
        setShowListDropdown(false);
      }
      if (
        stockDropdownRef.current &&
        !stockDropdownRef.current.contains(event.target as Node)
      ) {
        setShowStockDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const selectedList = useMemo(() => {
    return lists.find(list => list.id === selectedListId);
  }, [lists, selectedListId]);

  const selectedStock = useMemo(() => {
    // 如果有直接查詢的股票，優先使用
    if (directStock) {
      return directStock;
    }
    // 否則從清單中選擇
    return currentListStocks.find(stock => stock.id === selectedStockId);
  }, [currentListStocks, selectedStockId, directStock]);

  // 計算價格變動百分比
  const priceChangePercent = selectedStock?.latest_price?.change_percent;
  const priceChange = selectedStock?.latest_price?.change;
  const currentPrice = selectedStock?.latest_price?.close;

  // 處理股票查詢
  const handleSearch = async () => {
    if (!symbolInput.trim()) return;

    // 先清除舊狀態，避免訂閱時序問題
    setDirectStock(null);
    setSelectedListId(null);
    setSelectedStockId(null);
    setIsSearching(true);
    setSearchError(null);

    try {
      const result = await ensureStockExistsAuto(symbolInput.trim());

      // 確保 API 返回後才設置新股票
      // 使用 setTimeout 確保狀態清除後才設置新值，避免 WebSocket 訂閱時序問題
      setTimeout(() => {
        setDirectStock(result.stock);
      }, 100);

    } catch (error: any) {
      setSearchError(error.message || '查詢股票失敗');
      setDirectStock(null);
    } finally {
      setIsSearching(false);
    }
  };

  // 處理 Enter 鍵搜尋
  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  // 清除直接查詢
  const handleClearSearch = () => {
    setSymbolInput('');
    setDirectStock(null);
    setSearchError(null);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              即時圖表分析
            </h1>
            <p className="text-gray-600">
              選擇清單和股票，查看即時價格走勢和技術指標
            </p>
          </div>
        </div>
      </div>

      {/* 搜尋和選擇器區域 */}
      <div className="bg-white shadow rounded-lg p-6 mb-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 直接輸入股票代號 */}
          <div className="lg:col-span-1">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              快速查詢股票
            </label>
            <div className="flex gap-2">
              <div className="flex-1">
                <input
                  type="text"
                  value={symbolInput}
                  onChange={(e) => setSymbolInput(e.target.value.toUpperCase())}
                  onKeyPress={handleKeyPress}
                  onFocus={() => {
                    setShowListDropdown(false);
                    setShowStockDropdown(false);
                  }}
                  placeholder="輸入股號 (如: AAPL, 2330)"
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  disabled={isSearching}
                />
                {searchError && (
                  <p className="mt-1 text-xs text-red-600">{searchError}</p>
                )}
              </div>
              <button
                onClick={handleSearch}
                disabled={isSearching || !symbolInput.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {isSearching ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                ) : (
                  <Search className="w-4 h-4" />
                )}
              </button>
              {directStock && (
                <button
                  onClick={handleClearSearch}
                  className="px-3 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>

          {/* 清單選擇器 */}
          <div ref={listDropdownRef}>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              選擇清單
            </label>
            <div className="relative">
              <button
                onClick={() => {
                  setShowListDropdown(!showListDropdown);
                  setShowStockDropdown(false);
                }}
                className={`w-full bg-white border border-gray-300 rounded-md px-4 py-2 text-left flex items-center justify-between hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 ${directStock && !showListDropdown ? 'opacity-50' : ''}`}
              >
                <span className={selectedList ? 'text-gray-900' : 'text-gray-400'}>
                  {selectedList ? selectedList.name : '請選擇清單'}
                </span>
                <ChevronDown className="w-5 h-5 text-gray-400" />
              </button>

              {showListDropdown && (
                <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-auto">
                  {loading ? (
                    <div className="px-4 py-3 text-sm text-gray-500">載入中...</div>
                  ) : lists.length === 0 ? (
                    <div className="px-4 py-3 text-sm text-gray-500">尚無清單</div>
                  ) : (
                    lists.map((list) => (
                      <button
                        key={list.id}
                        onClick={() => {
                          setSelectedListId(list.id);
                          setSelectedStockId(null);
                          setShowListDropdown(false);
                          // 不自動清除查詢結果
                        }}
                        className={`w-full px-4 py-2 text-left hover:bg-gray-100 ${
                          selectedListId === list.id ? 'bg-blue-50 text-blue-700' : 'text-gray-900'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span>{list.name}</span>
                          <span className="text-xs text-gray-500">
                            {list.stocks_count} 檔股票
                          </span>
                        </div>
                      </button>
                    ))
                  )}
                </div>
              )}
            </div>
          </div>

          {/* 股票選擇器 */}
          <div ref={stockDropdownRef}>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              選擇股票
            </label>
            <div className="relative">
              <button
                onClick={() => {
                  setShowStockDropdown(!showStockDropdown);
                  setShowListDropdown(false);
                }}
                disabled={!selectedListId}
                className={`w-full bg-white border border-gray-300 rounded-md px-4 py-2 text-left flex items-center justify-between hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed ${directStock && !showStockDropdown ? 'opacity-50' : ''}`}
              >
                {(() => {
                  const listStock = selectedStockId && currentListStocks.find(s => s.id === selectedStockId);
                  if (listStock) {
                    return (
                      <span className="text-gray-900">
                        {listStock.symbol} - {listStock.name}
                      </span>
                    );
                  }
                  return <span className="text-gray-400">請先選擇清單</span>;
                })()}
                <ChevronDown className="w-5 h-5 text-gray-400" />
              </button>

              {showStockDropdown && selectedListId && (
                <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-auto">
                  {loading ? (
                    <div className="px-4 py-3 text-sm text-gray-500">載入中...</div>
                  ) : currentListStocks.length === 0 ? (
                    <div className="px-4 py-3 text-sm text-gray-500">此清單沒有股票</div>
                  ) : (
                    currentListStocks.map((stock) => (
                      <button
                        key={stock.id}
                        onClick={() => {
                          setSelectedStockId(stock.id);
                          setShowStockDropdown(false);
                          // 切換到清單模式，清除查詢結果
                          setDirectStock(null);
                          setSymbolInput('');
                          setSearchError(null);
                        }}
                        className={`w-full px-4 py-2 text-left hover:bg-gray-100 ${
                          selectedStockId === stock.id ? 'bg-blue-50 text-blue-700' : 'text-gray-900'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <div className="font-medium">{stock.symbol}</div>
                            <div className="text-xs text-gray-500">{stock.name}</div>
                          </div>
                          {stock.latest_price?.close && (
                            <div className="text-right">
                              <div className="font-medium">
                                {stock.market === 'TW' ? 'NT$' : '$'}{stock.latest_price.close.toFixed(2)}
                              </div>
                              {stock.latest_price.change_percent !== null && (
                                <div className={`text-xs ${
                                  stock.latest_price.change_percent >= 0 ? 'text-green-600' : 'text-red-600'
                                }`}>
                                  {stock.latest_price.change_percent >= 0 ? '+' : ''}
                                  {stock.latest_price.change_percent.toFixed(2)}%
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </button>
                    ))
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 股票資訊卡片 */}
      {selectedStock && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-blue-100 text-blue-600">
                <TrendingUp className="w-6 h-6" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">當前價格</p>
                <p className="text-2xl font-bold text-gray-900">
                  {selectedStock.market === 'TW' ? 'NT$' : '$'}
                  {currentPrice?.toFixed(2) || '--'}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex items-center">
              <div className={`p-3 rounded-full ${
                priceChange && priceChange >= 0 ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'
              }`}>
                <Activity className="w-6 h-6" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">漲跌</p>
                <p className={`text-2xl font-bold ${
                  priceChange && priceChange >= 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {priceChange !== null && priceChange !== undefined
                    ? `${priceChange >= 0 ? '+' : ''}${priceChange.toFixed(2)}`
                    : '--'
                  }
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex items-center">
              <div className={`p-3 rounded-full ${
                priceChangePercent && priceChangePercent >= 0 ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'
              }`}>
                <BarChart3 className="w-6 h-6" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">漲跌幅</p>
                <p className={`text-2xl font-bold ${
                  priceChangePercent && priceChangePercent >= 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {priceChangePercent !== null && priceChangePercent !== undefined
                    ? `${priceChangePercent >= 0 ? '+' : ''}${priceChangePercent.toFixed(2)}%`
                    : '--'
                  }
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex items-center">
              <div className={`p-3 rounded-full ${
                marketStatus.is_open ? 'bg-green-100 text-green-600' : 'bg-orange-100 text-orange-600'
              }`}>
                <Activity className="w-6 h-6" />
              </div>
              <div className="ml-4">
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
      )}

      {/* 主要內容區域 */}
      <div className="space-y-8">
        {/* 主圖表 - 全寬顯示 */}
        <div className="w-full">
          {selectedStock ? (
            <div className="bg-white shadow rounded-lg overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-2xl font-bold text-gray-900">
                      {selectedStock.symbol} - {selectedStock.name}
                    </h2>
                  </div>
                  {selectedStock.latest_price?.date && (
                    <div className="text-sm text-gray-500">
                      更新時間: {selectedStock.latest_price.date}
                    </div>
                  )}
                </div>
              </div>
              <div className="p-6">
                <RealtimePriceChart
                  key={selectedStock.id}
                  stock={{
                    id: selectedStock.id,
                    symbol: selectedStock.symbol,
                    name: selectedStock.name
                  }}
                  height={500}
                />
              </div>
            </div>
          ) : (
            <div className="bg-white shadow rounded-lg p-6 h-[500px] flex items-center justify-center">
              <div className="text-center text-gray-500">
                <div className="text-6xl mb-4">📊</div>
                <div className="text-xl font-medium mb-2">請選擇清單和股票</div>
                <div className="text-sm">從上方下拉選單選擇要分析的股票，或直接輸入股號查詢</div>
              </div>
            </div>
          )}
        </div>

        {/* 下方區域 - 分成兩欄 */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
          {/* 股票列表 */}
          {currentListStocks.length > 0 && (
            <div className="bg-white shadow rounded-lg p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                {selectedList?.name || '股票列表'}
              </h3>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {currentListStocks.map((stock) => (
                  <button
                    key={stock.id}
                    onClick={() => {
                      setSelectedStockId(stock.id);
                      // 切換到清單模式，清除查詢結果
                      setDirectStock(null);
                      setSymbolInput('');
                      setSearchError(null);
                    }}
                    className={`w-full p-3 rounded-lg text-left transition-colors ${
                      selectedStockId === stock.id
                        ? 'bg-blue-50 border border-blue-200'
                        : 'bg-gray-50 hover:bg-gray-100 border border-transparent'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-gray-900 truncate">
                          {stock.symbol}
                        </div>
                        <div className="text-sm text-gray-600 truncate">
                          {stock.name}
                        </div>
                      </div>
                      {stock.latest_price?.close && (
                        <div className="ml-3 text-right">
                          <div className="text-sm font-medium text-gray-900">
                            {stock.market === 'TW' ? 'NT$' : '$'}
                            {stock.latest_price.close.toFixed(2)}
                          </div>
                          {stock.latest_price.change_percent !== null && (
                            <div className={`text-xs ${
                              stock.latest_price.change_percent >= 0
                                ? 'text-green-600'
                                : 'text-red-600'
                            }`}>
                              {stock.latest_price.change_percent >= 0 ? '+' : ''}
                              {stock.latest_price.change_percent.toFixed(2)}%
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* 即時信號 */}
          <div>
            <RealtimeSignals />
          </div>
        </div>
      </div>
    </div>
  );
};

export default RealtimeDashboard;
