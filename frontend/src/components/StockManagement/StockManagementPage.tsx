/**
 * 股票管理頁面組件
 */
'use client';

import React, { useState, useMemo, useEffect } from 'react';
import Link from 'next/link';
import { useAppDispatch, useAppSelector } from '../../store';
import { addToast } from '../../store/slices/uiSlice';
import { fetchListStocks, addStockToList, removeStockFromList } from '../../store/slices/stockListSlice';
import { useStocks, useDeleteStock, useCreateStock } from '../../hooks/useStocks';
import { StockFilter } from '../../types';
import StocksApiService from '../../services/stocksApi';
import ConfirmDialog from '../ui/ConfirmDialog';
import TransactionModal from '../Portfolio/TransactionModal';
import { ShoppingCart, TrendingDown, BarChart3, Trash2 } from 'lucide-react';
import UnifiedStockSelector from './UnifiedStockSelector';

export interface StockManagementPageProps {}

const StockManagementPage: React.FC<StockManagementPageProps> = () => {
  const dispatch = useAppDispatch();
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [showAddModal, setShowAddModal] = useState(false);
  const [isBackfilling, setIsBackfilling] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<{
    isOpen: boolean;
    stockId: number | null;
    stockName: string;
  }>({
    isOpen: false,
    stockId: null,
    stockName: '',
  });
  const [stockSymbol, setStockSymbol] = useState('');
  const [viewMode, setViewMode] = useState<'all' | 'portfolio'>('all');
  const [currentListId, setCurrentListId] = useState<number | null>(null);
  const [transactionModal, setTransactionModal] = useState<{
    isOpen: boolean;
    stock: any | null;
    type: 'BUY' | 'SELL';
  }>({
    isOpen: false,
    stock: null,
    type: 'BUY'
  });

  // 從 Redux 獲取清單股票
  const { currentListStocks } = useAppSelector((state) => state.stockList);

  // 當清單改變時，載入清單中的股票
  useEffect(() => {
    if (currentListId && viewMode === 'all') {
      dispatch(fetchListStocks(currentListId));
    }
  }, [currentListId, viewMode, dispatch]);

  // 構建查詢參數
  const queryParams = useMemo(() => {
    const params: { page: number; pageSize: number; search?: string } = { page, pageSize };
    if (searchTerm.trim()) {
      params.search = searchTerm.trim();
    }
    return params;
  }, [page, pageSize, searchTerm]);

  // 使用 React Query 獲取股票數據
  const {
    data: stocksResponse,
    isLoading,
    error: queryError,
    refetch
  } = useStocks(queryParams);

  // 使用 React Query 刪除 mutation
  const deleteStockMutation = useDeleteStock({
    onSuccess: () => {
      dispatch(addToast({
        type: 'success',
        title: '成功',
        message: '已成功移除股票',
      }));
      // 立即重新獲取列表
      refetch();
    },
    onError: () => {
      dispatch(addToast({
        type: 'error',
        title: '錯誤',
        message: '移除股票失敗，請稍後再試',
      }));
    },
  });

  // 使用 React Query 新增 mutation
  const createStockMutation = useCreateStock({
    onSuccess: async (newStock) => {
      dispatch(addToast({
        type: 'success',
        title: '成功',
        message: '已成功新增股票',
      }));

      // 如果有選中的清單，自動添加到清單
      if (currentListId && newStock?.id) {
        try {
          await dispatch(addStockToList({
            listId: currentListId,
            data: { stock_id: newStock.id }
          })).unwrap();
        } catch (error) {
          console.error('添加股票到清單失敗:', error);
        }
      }

      // 延遲一下讓後端有時間處理
      setTimeout(async () => {
        try {
          // 自動回填新增股票的價格數據
          const backfillResult = await StocksApiService.backfillMissingPrices();

          if (backfillResult.total_stocks > 0) {
            dispatch(addToast({
              type: 'success',
              title: '已自動回填',
              message: `成功回填 ${backfillResult.successful} 個股票的價格數據`,
            }));
          }
        } catch (error) {
          console.error('Auto-backfill failed:', error);
        } finally {
          // 無論回填是否成功，都刷新列表
          await refetch();
        }
      }, 500);
    },
    onError: (error: any) => {
      dispatch(addToast({
        type: 'error',
        title: '錯誤',
        message: error.response?.data?.detail || '新增股票失敗，請稍後再試',
      }));
    },
  });

  // 從響應中提取數據並根據 viewMode 和清單過濾
  const allStocks = stocksResponse?.items || [];
  const stocks = useMemo(() => {
    if (viewMode === 'portfolio') {
      return allStocks.filter(stock => stock.is_portfolio);
    } else if (viewMode === 'all' && currentListId) {
      // 根據清單中的股票 ID 過濾
      const listStockIds = currentListStocks.map(item => item.stock_id);
      return allStocks.filter(stock => listStockIds.includes(stock.id));
    }
    return allStocks;
  }, [allStocks, viewMode, currentListId, currentListStocks]);

  const pagination = {
    page: stocksResponse?.page || 1,
    pageSize: stocksResponse?.per_page || 20,
    total: stocksResponse?.total || 0,
    totalPages: stocksResponse?.total_pages || 0,
  };
  const loading = isLoading || deleteStockMutation.isPending;
  const error = queryError?.message || null;

  // 打開刪除確認對話框
  const handleDeleteStock = (stockId: number, stockName: string) => {
    setDeleteConfirm({
      isOpen: true,
      stockId,
      stockName,
    });
  };

  // 確認刪除/移除
  const confirmDelete = async () => {
    if (!deleteConfirm.stockId) {
      return;
    }

    // 如果在清單模式，從清單移除；否則刪除股票
    if (viewMode === 'all' && currentListId) {
      try {
        await dispatch(removeStockFromList({
          listId: currentListId,
          stockId: deleteConfirm.stockId
        })).unwrap();

        dispatch(addToast({
          type: 'success',
          title: '成功',
          message: '已從清單中移除股票'
        }));

        // 重新載入清單股票
        if (currentListId) {
          dispatch(fetchListStocks(currentListId));
        }
      } catch (error: any) {
        dispatch(addToast({
          type: 'error',
          title: '錯誤',
          message: error?.message || error?.toString() || '移除失敗'
        }));
      }
    } else {
      // 從系統中刪除股票
      deleteStockMutation.mutate(deleteConfirm.stockId);
    }

    setDeleteConfirm({ isOpen: false, stockId: null, stockName: '' });
  };

  // 取消刪除
  const cancelDelete = () => {
    setDeleteConfirm({ isOpen: false, stockId: null, stockName: '' });
  };

  // 處理搜尋（防抖處理在實際應用中可以使用 useDebounce）
  const handleSearchChange = (value: string) => {
    setSearchTerm(value);
    setPage(1); // 重置到第一頁
  };

  // 處理分頁
  const handlePageChange = (newPage: number) => {
    setPage(newPage);
  };

  // 處理重新載入並自動回填缺失價格
  const handleRefreshWithBackfill = async () => {
    setIsBackfilling(true);

    try {
      // 先檢查是否有缺失價格的股票並回填
      const backfillResult = await StocksApiService.backfillMissingPrices();

      if (!backfillResult || !backfillResult.success) {
        throw new Error('回填結果無效');
      }

      // 如果所有股票都有價格，只刷新列表並顯示成功訊息
      if (backfillResult.total_stocks === 0) {
        await refetch();
        dispatch(addToast({
          type: 'success',
          title: '已更新',
          message: '股票列表已刷新',
        }));
        return;
      }

      // 如果有回填成功的股票
      dispatch(addToast({
        type: 'success',
        title: '回填完成',
        message: `成功回填 ${backfillResult.successful} 個股票的價格數據`,
      }));

      // 顯示失敗的股票（如果有）
      if (backfillResult.failed > 0) {
        const failedSymbols = backfillResult.results
          .filter(r => !r.success)
          .map(r => r.symbol)
          .join(', ');

        dispatch(addToast({
          type: 'warning',
          title: '部分失敗',
          message: `${backfillResult.failed} 個股票回填失敗: ${failedSymbols}`,
        }));
      }

      // 回填後重新載入列表
      await refetch();

    } catch (error: any) {
      console.error('❌ 操作失敗:', error);

      const errorMessage = error.response?.data?.detail
        || error.message
        || '操作失敗，請稍後再試';

      dispatch(addToast({
        type: 'error',
        title: '錯誤',
        message: errorMessage,
      }));
    } finally {
      setIsBackfilling(false);
    }
  };

  // 自動識別市場：數字為台股，英文為美股
  const detectMarket = (symbol: string): 'TW' | 'US' => {
    const trimmedSymbol = symbol.trim().toUpperCase();
    // 如果全部是數字，判定為台股
    if (/^\d+$/.test(trimmedSymbol)) {
      return 'TW';
    }
    // 如果包含英文字母，判定為美股
    return 'US';
  };

  // 格式化股票代號
  const formatSymbol = (symbol: string, market: 'TW' | 'US'): string => {
    const trimmedSymbol = symbol.trim().toUpperCase();
    // 台股需要加上 .TW 後綴（如果沒有的話）
    if (market === 'TW' && !trimmedSymbol.endsWith('.TW')) {
      return `${trimmedSymbol}.TW`;
    }
    return trimmedSymbol;
  };

  // 處理新增股票
  const handleAddStock = () => {
    const trimmedSymbol = stockSymbol.trim();

    if (!trimmedSymbol) {
      dispatch(addToast({
        type: 'error',
        title: '錯誤',
        message: '請填寫股票代號',
      }));
      return;
    }

    // 驗證格式
    if (!/^[A-Za-z0-9.]+$/.test(trimmedSymbol)) {
      dispatch(addToast({
        type: 'error',
        title: '錯誤',
        message: '股票代號只能包含英文字母和數字',
      }));
      return;
    }

    // 自動識別市場
    const market = detectMarket(trimmedSymbol);
    const formattedSymbol = formatSymbol(trimmedSymbol, market);

    // 提交到後端（後端會自動查詢公司名稱）
    createStockMutation.mutate({
      symbol: formattedSymbol,
      market: market,
    });

    // 成功後清空輸入（在 mutation onSuccess 中處理）
    setStockSymbol('');
    setShowAddModal(false);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">
          股票管理
        </h1>
        <p className="text-gray-600">
          管理監控的股票列表，新增或移除股票追蹤
        </p>
      </div>

      {/* 搜尋和新增區域 */}
      <div className="bg-white shadow rounded-lg p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-4">
            <h2 className="text-lg font-medium text-gray-900">股票列表</h2>
            {/* 統一選擇器 - 整合清單和視圖模式 */}
            <UnifiedStockSelector
              onListChange={setCurrentListId}
              viewMode={viewMode}
              onViewModeChange={setViewMode}
            />
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleRefreshWithBackfill}
              disabled={isBackfilling}
              className="bg-green-600 hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white px-4 py-2 rounded-md text-sm font-medium flex items-center gap-2"
            >
              {isBackfilling ? (
                <>
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  抓取中...
                </>
              ) : (
                <>🔄 重新載入</>
              )}
            </button>
            <button
              onClick={() => setShowAddModal(true)}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium"
            >
              新增股票
            </button>
          </div>
        </div>

        <div className="mb-4">
          <input
            type="text"
            placeholder="搜尋股票名稱或代號..."
            value={searchTerm}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* 股票表格 */}
        <div className="overflow-x-auto">
          <table className="min-w-full table-auto">
            <thead>
              <tr className="bg-gray-50">
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  股票代號
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  名稱
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  市場
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  最新價格
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  漲跌幅
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  操作
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {stocks.map((stock) => (
                <tr key={stock.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {stock.symbol}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {stock.name || stock.symbol}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      stock.market === 'TW'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-blue-100 text-blue-800'
                    }`}>
                      {stock.market === 'TW' ? '台股' : '美股'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {stock.latest_price?.close ? (
                      <span className="font-semibold">{stock.market === 'TW' ? 'NT$' : '$'}{stock.latest_price.close.toFixed(2)}</span>
                    ) : (
                      <span className="text-gray-400">---</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    {stock.latest_price?.change_percent !== null && stock.latest_price?.change_percent !== undefined ? (
                      <span className={stock.latest_price.change_percent >= 0 ? 'text-green-600 font-medium' : 'text-red-600 font-medium'}>
                        {stock.latest_price.change_percent >= 0 ? '+' : ''}{stock.latest_price.change_percent.toFixed(2)}%
                      </span>
                    ) : (
                      <span className="text-gray-400">---</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm space-x-2">
                    <button
                      onClick={() => setTransactionModal({ isOpen: true, stock, type: 'BUY' })}
                      className="text-green-600 hover:text-green-800 font-medium inline-flex items-center gap-1"
                      title="買入"
                    >
                      <ShoppingCart className="w-3.5 h-3.5" />
                      買入
                    </button>
                    <button
                      onClick={() => setTransactionModal({ isOpen: true, stock, type: 'SELL' })}
                      className="text-orange-600 hover:text-orange-800 font-medium inline-flex items-center gap-1"
                      title="賣出"
                    >
                      <TrendingDown className="w-3.5 h-3.5" />
                      賣出
                    </button>
                    <Link
                      href={`/charts?stock=${stock.id}`}
                      className="text-blue-600 hover:text-blue-800 font-medium inline-flex items-center gap-1"
                      title="查看圖表"
                    >
                      <BarChart3 className="w-3.5 h-3.5" />
                      圖表
                    </Link>
                    <button
                      onClick={() => handleDeleteStock(stock.id, stock.name)}
                      className="text-red-600 hover:text-red-800 font-medium inline-flex items-center gap-1"
                      title="移除股票"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      移除
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {loading && (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <div className="text-gray-500 mt-4">載入中...</div>
          </div>
        )}

        {!loading && stocks.length === 0 && (
          <div className="text-center py-8">
            <div className="text-gray-500">
              {searchTerm ? '找不到符合條件的股票' : '尚未新增任何股票'}
            </div>
          </div>
        )}

        {error && (
          <div className="text-center py-8">
            <div className="text-red-500">
              {error}
            </div>
            <button
              onClick={() => refetch()}
              className="mt-2 text-blue-600 hover:text-blue-800 font-medium"
            >
              重新載入
            </button>
          </div>
        )}

        {/* 分頁控制 */}
        {pagination.totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 bg-white border-t border-gray-200 sm:px-6">
            <div className="flex justify-between flex-1 sm:hidden">
              <button
                onClick={() => handlePageChange(page - 1)}
                disabled={page <= 1}
                className="relative inline-flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                上一頁
              </button>
              <button
                onClick={() => handlePageChange(page + 1)}
                disabled={page >= pagination.totalPages}
                className="relative ml-3 inline-flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                下一頁
              </button>
            </div>
            <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
              <div>
                <p className="text-sm text-gray-700">
                  顯示第 <span className="font-medium">{(page - 1) * pageSize + 1}</span> 到{' '}
                  <span className="font-medium">
                    {Math.min(page * pageSize, pagination.total)}
                  </span>{' '}
                  頁，共 <span className="font-medium">{pagination.total}</span> 頁
                </p>
              </div>
              <div>
                <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
                  <button
                    onClick={() => handlePageChange(page - 1)}
                    disabled={page <= 1}
                    className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    上一頁
                  </button>

                  {/* 頁碼 */}
                  {Array.from({ length: Math.min(5, pagination.totalPages) }, (_, i) => {
                    let pageNumber;
                    if (pagination.totalPages <= 5) {
                      pageNumber = i + 1;
                    } else if (page <= 3) {
                      pageNumber = i + 1;
                    } else if (page >= pagination.totalPages - 2) {
                      pageNumber = pagination.totalPages - 4 + i;
                    } else {
                      pageNumber = page - 2 + i;
                    }

                    return (
                      <button
                        key={pageNumber}
                        onClick={() => handlePageChange(pageNumber)}
                        className={`relative inline-flex items-center px-4 py-2 border text-sm font-medium ${
                          page === pageNumber
                            ? 'z-10 bg-blue-50 border-blue-500 text-blue-600'
                            : 'bg-white border-gray-300 text-gray-500 hover:bg-gray-50'
                        }`}
                      >
                        {pageNumber}
                      </button>
                    );
                  })}

                  <button
                    onClick={() => handlePageChange(page + 1)}
                    disabled={page >= pagination.totalPages}
                    className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    下一頁
                  </button>
                </nav>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 統計區域 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center">
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-600">
                {viewMode === 'all' && currentListId ? '當前清單股票數' :
                 viewMode === 'portfolio' ? '持倉股票數' : '追蹤股票總數'}
              </p>
              <p className="text-2xl font-bold text-gray-900">{stocks.length}</p>
            </div>
          </div>
        </div>

        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center">
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-600">台股數量</p>
              <p className="text-2xl font-bold text-green-600">
                {stocks.filter(s => s.market === 'TW').length}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center">
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-600">美股數量</p>
              <p className="text-2xl font-bold text-blue-600">
                {stocks.filter(s => s.market === 'US').length}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* 新增股票 Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md animate-scale-in">
            <h3 className="text-lg font-medium text-gray-900 mb-4">新增股票</h3>

            {/* 提示訊息 */}
            <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
              <div className="flex">
                <svg className="h-5 w-5 text-blue-400 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div className="text-sm text-blue-700">
                  <p className="font-medium mb-1">支援台股與美股</p>
                  <ul className="list-disc list-inside space-y-1 text-xs">
                    <li><strong>台股</strong>：輸入數字代號（如：2330）</li>
                    <li><strong>美股</strong>：輸入英文代碼（如：AAPL）</li>
                    <li>系統將自動查詢公司名稱</li>
                  </ul>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  股票代號 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={stockSymbol}
                  onChange={(e) => setStockSymbol(e.target.value.toUpperCase())}
                  placeholder="台股輸入數字（如 2330）或美股英文（如 AAPL）"
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  disabled={createStockMutation.isPending}
                  autoFocus
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      handleAddStock();
                    }
                  }}
                />
                {stockSymbol && (
                  <p className="mt-2 text-xs text-gray-600">
                    {detectMarket(stockSymbol) === 'TW' ? (
                      <span className="text-green-600">
                        ✓ <strong>台股</strong>
                      </span>
                    ) : (
                      <span className="text-blue-600">
                        ✓ <strong>美股</strong>
                      </span>
                    )}
                  </p>
                )}
              </div>

              <div className="flex justify-end gap-3 mt-6">
                <button
                  onClick={() => {
                    setShowAddModal(false);
                    setStockSymbol('');
                  }}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                  disabled={createStockMutation.isPending}
                >
                  取消
                </button>
                <button
                  onClick={handleAddStock}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  disabled={createStockMutation.isPending || !stockSymbol.trim()}
                >
                  {createStockMutation.isPending ? (
                    <>
                      <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      新增中...
                    </>
                  ) : '確認新增'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 刪除確認對話框 */}
      <ConfirmDialog
        isOpen={deleteConfirm.isOpen}
        title={viewMode === 'all' && currentListId ? '確認從清單移除' : '確認刪除股票'}
        message={
          viewMode === 'all' && currentListId
            ? `確定要從清單中移除股票「${deleteConfirm.stockName}」嗎？股票本身不會被刪除。`
            : `確定要刪除股票「${deleteConfirm.stockName}」嗎？此操作無法復原。`
        }
        confirmText="確定"
        cancelText="取消"
        type="danger"
        onConfirm={confirmDelete}
        onCancel={cancelDelete}
      />

      {/* 交易 Modal */}
      <TransactionModal
        isOpen={transactionModal.isOpen}
        onClose={() => setTransactionModal({ isOpen: false, stock: null, type: 'BUY' })}
        stock={transactionModal.stock}
        transactionType={transactionModal.type}
        onSuccess={() => {
          // 交易成功後重新載入列表
          refetch();
        }}
      />
    </div>
  );
};

export default StockManagementPage;