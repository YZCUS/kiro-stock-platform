/**
 * 股票管理頁面組件
 */
'use client';

import React, { useState, useMemo, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAppDispatch, useAppSelector } from '../../store';
import { addToast } from '../../store/slices/uiSlice';
import { fetchStockLists, fetchListStocks, addStockToList, removeStockFromList } from '../../store/slices/stockListSlice';
import { useStocks, useDeleteStock, useCreateStock } from '../../hooks/useStocks';
import { useStockValidation } from '../../hooks/useStockValidation';
import StocksApiService from '../../services/stocksApi';
import ConfirmDialog from '../ui/ConfirmDialog';
import TransactionModal from '../Portfolio/TransactionModal';
import StockReorderModal from './StockReorderModal';
import { ShoppingCart, TrendingDown, BarChart3, Trash2, ArrowUpDown, Plus } from 'lucide-react';
import UnifiedStockSelector from './UnifiedStockSelector';
import * as stockListApi from '../../services/stockListApi';

const StockManagementPage: React.FC = () => {
  const router = useRouter();
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
  const [transactionModal, setTransactionModal] = useState<{
    isOpen: boolean;
    stock: any | null;
    type: 'BUY' | 'SELL';
  }>({
    isOpen: false,
    stock: null,
    type: 'BUY'
  });
  const [isReorderModalOpen, setIsReorderModalOpen] = useState(false);

  // 從 Redux 獲取清單股票和清單列表
  const { currentListStocks, lists, currentList } = useAppSelector((state) => state.stockList);

  // 使用 Redux 的 currentList.id 作為當前清單 ID
  const currentListId = currentList?.id || null;
  const { isAuthenticated } = useAppSelector((state) => state.auth);

  // 股號驗證 Hook
  const { validationError, validate, reset: resetValidation } = useStockValidation();

  // 檢查登入狀態，未登入則重定向到登入頁面
  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login?redirect=/stocks');
    }
  }, [isAuthenticated, router]);

  // 載入清單列表（如果尚未載入）
  useEffect(() => {
    if (isAuthenticated && lists.length === 0) {
      dispatch(fetchStockLists());
    }
  }, [isAuthenticated, lists.length, dispatch]);

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

      // 如果有選中的清單，自動添加到清單並重新獲取清單股票（包含最新價格）
      if (currentListId && newStock?.id) {
        try {
          await dispatch(addStockToList({
            listId: currentListId,
            data: { stock_id: newStock.id }
          })).unwrap();

          // 重新獲取清單股票（包含最新價格）
          await dispatch(fetchListStocks(currentListId));

          dispatch(addToast({
            type: 'success',
            title: '成功',
            message: '已添加到清單',
          }));
        } catch (error) {
          console.error('添加股票到清單失敗:', error);
        }
      } else {
        // 如果不在清單視圖，刷新所有股票列表
        await refetch();
      }
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
  const allStocks = useMemo(() => stocksResponse?.items || [], [stocksResponse?.items]);
  const stocks = useMemo(() => {
    if (viewMode === 'portfolio') {
      // 持倉視圖：從所有股票中過濾
      return allStocks.filter(stock => stock.is_portfolio);
    } else if (viewMode === 'all' && currentListId) {
      // 清單視圖：直接使用 Redux 中的 currentListStocks（已包含完整 Stock 對象和 latest_price）
      const trimmedSearchTerm = searchTerm.trim().toLowerCase();
      if (!trimmedSearchTerm) {
        return currentListStocks;
      }

      return currentListStocks.filter((stock) => {
        const symbol = stock.symbol?.toLowerCase() || '';
        const name = stock.name?.toLowerCase() || '';
        return symbol.includes(trimmedSearchTerm) || name.includes(trimmedSearchTerm);
      });
    }
    // 如果沒有選擇清單，不顯示任何股票
    return [];
  }, [allStocks, viewMode, currentListId, currentListStocks, searchTerm]);

  // 根據當前視圖模式計算分頁資訊
  const pagination = useMemo(() => {
    if (viewMode === 'all' && currentListId) {
      // 列表視圖：使用列表中的股票數量
      const total = stocks.length;
      return {
        page: 1, // 列表視圖不分頁，顯示所有股票
        pageSize: total,
        total,
        totalPages: 1,
      };
    }
    // 持倉視圖或其他視圖：使用 API 回應的分頁資訊
    return {
      page: stocksResponse?.page || 1,
      pageSize: stocksResponse?.per_page || 20,
      total: stocksResponse?.total || 0,
      totalPages: stocksResponse?.total_pages || 0,
    };
  }, [viewMode, currentListId, stocks.length, stocksResponse]);
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

    // 只在清單模式允許移除股票
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
    } else if (viewMode === 'portfolio') {
      // 持倉不允許直接刪除，應該通過賣出交易
      dispatch(addToast({
        type: 'warning',
        title: '提示',
        message: '持倉股票請使用「賣出」功能來清倉，不能直接移除'
      }));
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

  // 處理重新載入並刷新當前視圖的股票價格
  const handleRefreshWithBackfill = async () => {
    setIsBackfilling(true);

    try {
      // 獲取當前視圖的股票列表
      const currentStocks = stocks;

      if (currentStocks.length === 0) {
        dispatch(addToast({
          type: 'info',
          title: '提示',
          message: '目前沒有股票需要刷新',
        }));
        return;
      }

      // 提取股票代號列表
      const stockSymbols = currentStocks.map(s => s.symbol);

      // 刷新當前視圖中的股票價格數據
      const refreshResult = await StocksApiService.refreshAllStockPrices();

      if (!refreshResult || !refreshResult.success) {
        throw new Error('刷新結果無效');
      }

      // 過濾出當前視圖中的股票刷新結果
      const relevantResults = refreshResult.results.filter(r =>
        stockSymbols.includes(r.symbol)
      );
      const successCount = relevantResults.filter(r => r.success).length;
      const failedResults = relevantResults.filter(r => !r.success);

      // 顯示刷新成功訊息
      if (successCount > 0) {
        const viewName = viewMode === 'portfolio' ? '持倉' : '清單';
        dispatch(addToast({
          type: 'success',
          title: '刷新完成',
          message: `成功刷新 ${viewName} 中 ${successCount} 支股票的價格數據`,
        }));
      } else {
        dispatch(addToast({
          type: 'info',
          title: '已更新',
          message: '股票列表已刷新',
        }));
      }

      // 顯示失敗的股票（如果有）
      if (failedResults.length > 0) {
        const failedSymbols = failedResults
          .map(r => r.symbol)
          .join(', ');

        dispatch(addToast({
          type: 'warning',
          title: '部分失敗',
          message: `${failedResults.length} 支股票刷新失敗: ${failedSymbols}`,
        }));
      }

      // 刷新後重新載入列表
      if (viewMode === 'all' && currentListId) {
        // 如果在清單視圖，重新獲取清單股票（包含最新價格）
        await dispatch(fetchListStocks(currentListId));
      } else {
        // 否則刷新全局股票列表
        await refetch();
      }

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

  // 處理新增股票
  const handleAddStock = async () => {
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

    try {
      // 使用驗證 API 驗證股票代號
      const validationResult = await validate(trimmedSymbol);

      if (!validationResult) {
        // 驗證失敗
        dispatch(addToast({
          type: 'error',
          title: '驗證失敗',
          message: validationError || '無效的股票代號',
        }));
        return;
      }

      // 驗證成功，使用驗證結果
      const { symbol: formattedSymbol, market, name } = validationResult;

      // 先檢查股票是否已經存在於資料庫中
      const existingStocksResponse = await StocksApiService.getStocks({
        search: formattedSymbol,
        page: 1,
        pageSize: 20
      });

      let stockToAdd = null;

      // 檢查搜尋結果中是否有完全匹配的股票
      if (existingStocksResponse?.items?.length > 0) {
        stockToAdd = existingStocksResponse.items.find(
          (s: any) => s.symbol === formattedSymbol && s.market === market
        );
      }

      if (stockToAdd) {
        // 股票已存在，直接添加到清單
        if (currentListId) {
          try {
            await dispatch(addStockToList({
              listId: currentListId,
              data: { stock_id: stockToAdd.id }
            })).unwrap();

            dispatch(addToast({
              type: 'success',
              title: '成功',
              message: `已將 ${name} (${formattedSymbol}) 添加到清單`,
            }));

            // 刷新清單
            dispatch(fetchListStocks(currentListId));
          } catch (error: any) {
            // 檢查是否是重複添加的錯誤
            const errorMsg = error?.message || error?.toString() || '';
            if (errorMsg.includes('已存在') || errorMsg.includes('已在清單中')) {
              dispatch(addToast({
                type: 'warning',
                title: '提示',
                message: '該股票已在此清單中',
              }));
            } else {
              dispatch(addToast({
                type: 'error',
                title: '錯誤',
                message: errorMsg || '添加股票到清單失敗',
              }));
            }
          }
        } else {
          dispatch(addToast({
            type: 'info',
            title: '提示',
            message: '股票已存在於資料庫中，請選擇清單後再添加',
          }));
        }
      } else {
        // 股票不存在，創建新股票
        createStockMutation.mutate({
          symbol: formattedSymbol,
          market: market as 'TW' | 'US',
        });
      }

      // 清空輸入並關閉 modal
      setStockSymbol('');
      resetValidation();
      setShowAddModal(false);
    } catch (error) {
      console.error('添加股票失敗:', error);
      dispatch(addToast({
        type: 'error',
        title: '錯誤',
        message: '添加股票失敗，請稍後再試',
      }));
    }
  };

  // 處理股票排序
  const handleSaveStockReorder = async (reorderedStocks: any[]) => {
    if (!currentListId) return;

    try {
      // 準備排序數據
      const stock_orders = reorderedStocks.map((stock, index) => ({
        stock_id: stock.id,
        sort_order: index
      }));

      // 調用 API
      await stockListApi.reorderListStocks(currentListId, { stock_orders });

      // 重新載入清單股票
      await dispatch(fetchListStocks(currentListId));

      dispatch(addToast({
        type: 'success',
        title: '成功',
        message: '股票順序已更新'
      }));

      setIsReorderModalOpen(false);
    } catch (error: any) {
      dispatch(addToast({
        type: 'error',
        title: '錯誤',
        message: error?.message || error?.toString() || '更新順序失敗'
      }));
    }
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
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  抓取中...
                </>
              ) : (
                <>🔄 重新載入</>
              )}
            </button>
            {/* 只在清單視圖顯示新增股票和排序按鈕，持倉視圖不允許直接新增 */}
            {viewMode === 'all' && currentListId && stocks.length > 1 && (
              <button
                onClick={() => setIsReorderModalOpen(true)}
                className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-md text-sm font-medium flex items-center gap-2"
                title="調整股票順序"
              >
                <ArrowUpDown className="w-4 h-4" />
                排序
              </button>
            )}
            {viewMode === 'all' && (
              <button
                onClick={() => setShowAddModal(true)}
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium"
              >
                新增股票
              </button>
            )}
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
                      href={`/dashboard?stock=${stock.id}`}
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
          <div className="text-center py-12">
            <div className="text-gray-500">
              {viewMode === 'all' && lists.length === 0 ? (
                <div className="max-w-md mx-auto">
                  <svg className="w-16 h-16 mx-auto mb-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                  <p className="text-lg font-medium text-gray-700 mb-2">尚未建立任何清單</p>
                  <p className="text-sm text-gray-500 mb-6">建立您的第一個股票清單，開始追蹤您感興趣的股票</p>
                  <button
                    onClick={() => {
                      // 這裡需要觸發新建清單的 modal
                      // 暫時使用 alert 提示
                      alert('請使用上方的下拉選單中的「新建清單」功能來建立清單');
                    }}
                    className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded-md text-sm font-medium"
                  >
                    <Plus className="w-4 h-4" />
                    建立第一個清單
                  </button>
                </div>
              ) : viewMode === 'all' && !currentListId ? (
                <div>
                  <p className="text-lg mb-2">請先選擇一個清單</p>
                  <p className="text-sm">使用上方的下拉選單選擇要管理的股票清單</p>
                </div>
              ) : searchTerm ? (
                '找不到符合條件的股票'
              ) : (
                <div className="max-w-md mx-auto">
                  <svg className="w-16 h-16 mx-auto mb-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                  </svg>
                  <p className="text-lg font-medium text-gray-700 mb-2">此清單還沒有股票</p>
                  <p className="text-sm text-gray-500">點擊上方「新增股票」按鈕來添加股票</p>
                </div>
              )}
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

      {/* 股票排序 Modal */}
      <StockReorderModal
        isOpen={isReorderModalOpen}
        onClose={() => setIsReorderModalOpen(false)}
        stocks={stocks}
        onSave={handleSaveStockReorder}
      />
    </div>
  );
};

export default StockManagementPage;
