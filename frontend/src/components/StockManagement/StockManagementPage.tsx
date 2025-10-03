/**
 * 股票管理頁面組件
 */
'use client';

import React, { useState, useMemo } from 'react';
import Link from 'next/link';
import { useAppDispatch } from '../../store';
import { addToast } from '../../store/slices/uiSlice';
import { useStocks, useDeleteStock, useCreateStock } from '../../hooks/useStocks';
import { StockFilter } from '../../types';

export interface StockManagementPageProps {}

const StockManagementPage: React.FC<StockManagementPageProps> = () => {
  const dispatch = useAppDispatch();
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newStock, setNewStock] = useState({
    symbol: '',
    market: 'TW' as 'TW' | 'US',
  });

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
    onSuccess: () => {
      dispatch(addToast({
        type: 'success',
        title: '成功',
        message: '已成功新增股票',
      }));
      setShowAddModal(false);
      setNewStock({ symbol: '', market: 'TW' });
      refetch();
    },
    onError: (error: any) => {
      dispatch(addToast({
        type: 'error',
        title: '錯誤',
        message: error.response?.data?.detail || '新增股票失敗，請稍後再試',
      }));
    },
  });

  // 從響應中提取數據
  const stocks = stocksResponse?.items || [];
  const pagination = {
    page: stocksResponse?.page || 1,
    pageSize: stocksResponse?.per_page || 20,
    total: stocksResponse?.total || 0,
    totalPages: stocksResponse?.total_pages || 0,
  };
  const loading = isLoading || deleteStockMutation.isPending;
  const error = queryError?.message || null;

  // 處理刪除股票
  const handleDeleteStock = async (stockId: number, stockName: string) => {
    if (window.confirm(`確定要移除股票 ${stockName} 嗎？`)) {
      deleteStockMutation.mutate(stockId);
    }
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

  // 處理新增股票
  const handleAddStock = async () => {
    if (!newStock.symbol.trim()) {
      dispatch(addToast({
        type: 'error',
        title: '錯誤',
        message: '請填寫股票代號',
      }));
      return;
    }

    createStockMutation.mutate(newStock);
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
          <h2 className="text-lg font-medium text-gray-900">股票列表</h2>
          <button
            onClick={() => setShowAddModal(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium"
          >
            新增股票
          </button>
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
                      <span>{stock.market === 'TW' ? 'NT$' : '$'}{stock.latest_price.close.toFixed(2)}</span>
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
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 space-x-2">
                    <Link
                      href={`/charts?stock=${stock.id}`}
                      className="text-blue-600 hover:text-blue-800 font-medium"
                    >
                      查看
                    </Link>
                    <button
                      onClick={() => handleDeleteStock(stock.id, stock.name)}
                      className="text-red-600 hover:text-red-800 font-medium"
                    >
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
              <p className="text-sm font-medium text-gray-600">追蹤股票總數</p>
              <p className="text-2xl font-bold text-gray-900">{pagination.total}</p>
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
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-medium text-gray-900 mb-4">新增股票</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  市場 <span className="text-red-500">*</span>
                </label>
                <div className="flex gap-4">
                  <label className="flex items-center cursor-pointer">
                    <input
                      type="radio"
                      name="market"
                      value="TW"
                      checked={newStock.market === 'TW'}
                      onChange={(e) => setNewStock({...newStock, market: 'TW'})}
                      className="mr-2"
                      disabled={createStockMutation.isPending}
                    />
                    <span className="text-sm text-gray-700">台股</span>
                  </label>
                  <label className="flex items-center cursor-pointer">
                    <input
                      type="radio"
                      name="market"
                      value="US"
                      checked={newStock.market === 'US'}
                      onChange={(e) => setNewStock({...newStock, market: 'US'})}
                      className="mr-2"
                      disabled={createStockMutation.isPending}
                    />
                    <span className="text-sm text-gray-700">美股</span>
                  </label>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  股票代號 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={newStock.symbol}
                  onChange={(e) => setNewStock({...newStock, symbol: e.target.value.toUpperCase()})}
                  placeholder="台股: 2330.TW | 美股: AAPL"
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  disabled={createStockMutation.isPending}
                />
                <p className="mt-1 text-xs text-gray-500">
                  系統將自動抓取股票名稱
                </p>
              </div>

              <div className="flex justify-end gap-3 mt-6">
                <button
                  onClick={() => {
                    setShowAddModal(false);
                    setNewStock({ symbol: '', market: 'TW' });
                  }}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                  disabled={createStockMutation.isPending}
                >
                  取消
                </button>
                <button
                  onClick={handleAddStock}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  disabled={createStockMutation.isPending}
                >
                  {createStockMutation.isPending ? '新增中...' : '確認新增'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default StockManagementPage;