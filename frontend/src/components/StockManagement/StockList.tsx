/**
 * 股票列表組件 - 使用 React Query
 */
'use client';

import React, { useState } from 'react';
import { useStocks, useDeleteStock } from '../../hooks/useStocks';
import { addToast } from '../../store/slices/uiSlice';
import { useAppDispatch } from '../../store';

export interface StockListProps {}

const StockList: React.FC<StockListProps> = () => {
  const dispatch = useAppDispatch();
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 20;

  // 使用 React Query 獲取股票數據
  const {
    data: stocksResponse,
    isLoading,
    error,
    refetch
  } = useStocks({
    page: currentPage,
    pageSize,
    filters: searchTerm ? { search: searchTerm } : {}
  });

  // 刪除股票 mutation
  const deleteStockMutation = useDeleteStock({
    onSuccess: () => {
      dispatch(addToast({
        type: 'success',
        title: '成功',
        message: '股票已成功移除',
      }));
    },
    onError: (error: any) => {
      dispatch(addToast({
        type: 'error',
        title: '錯誤',
        message: error.message || '移除股票失敗，請稍後再試',
      }));
    },
  });

  // 處理刪除股票
  const handleDeleteStock = async (stockId: number, stockName: string) => {
    if (window.confirm(`確定要移除股票 ${stockName} 嗎？`)) {
      deleteStockMutation.mutate(stockId);
    }
  };

  // 處理搜尋
  const handleSearch = (value: string) => {
    setSearchTerm(value);
    setCurrentPage(1); // 重置到第一頁
  };

  const stocks = stocksResponse?.data || [];
  const pagination = stocksResponse?.pagination || {
    page: 1,
    pageSize: 20,
    total: 0,
    totalPages: 0,
  };

  if (error) {
    return (
      <div className="text-center py-8">
        <div className="text-red-500 mb-4">
          載入股票數據時發生錯誤: {error.message}
        </div>
        <button
          onClick={() => refetch()}
          className="btn-primary"
        >
          重新載入
        </button>
      </div>
    );
  }

  return (
    <div className="bg-white shadow rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-medium text-gray-900">股票列表</h2>
        <button className="btn-primary">
          新增股票
        </button>
      </div>

      {/* 搜尋框 */}
      <div className="mb-4">
        <input
          type="text"
          placeholder="搜尋股票名稱或代號..."
          value={searchTerm}
          onChange={(e) => handleSearch(e.target.value)}
          className="input w-full"
        />
      </div>

      {/* 載入狀態 */}
      {isLoading && (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <div className="text-gray-500 mt-4">載入中...</div>
        </div>
      )}

      {/* 股票表格 */}
      {!isLoading && (
        <>
          <div className="overflow-x-auto">
            <table className="min-w-full table-auto table-hover">
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
                    狀態
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    最後更新
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {stocks.map((stock) => (
                  <tr key={stock.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {stock.symbol}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {stock.name}
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
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        stock.is_active
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {stock.is_active ? '啟用' : '停用'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(stock.updated_at).toLocaleDateString('zh-TW')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 space-x-2">
                      <button className="text-blue-600 hover:text-blue-800 font-medium">
                        查看
                      </button>
                      <button className="text-yellow-600 hover:text-yellow-800 font-medium">
                        編輯
                      </button>
                      <button
                        onClick={() => handleDeleteStock(stock.id, stock.name)}
                        disabled={deleteStockMutation.isPending}
                        className="text-red-600 hover:text-red-800 font-medium disabled:opacity-50"
                      >
                        {deleteStockMutation.isPending ? '刪除中...' : '移除'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* 空狀態 */}
          {stocks.length === 0 && (
            <div className="text-center py-8">
              <div className="text-gray-500">
                {searchTerm ? '找不到符合條件的股票' : '尚未新增任何股票'}
              </div>
            </div>
          )}

          {/* 分頁控制 */}
          {pagination.totalPages > 1 && (
            <div className="flex items-center justify-between mt-6">
              <div className="text-sm text-gray-700">
                顯示 {(pagination.page - 1) * pagination.pageSize + 1} - {Math.min(pagination.page * pagination.pageSize, pagination.total)} 筆，
                共 {pagination.total} 筆
              </div>
              <div className="flex space-x-2">
                <button
                  onClick={() => setCurrentPage(pagination.page - 1)}
                  disabled={pagination.page <= 1}
                  className="px-3 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  上一頁
                </button>
                <span className="px-3 py-2 text-sm font-medium text-gray-700">
                  第 {pagination.page} / {pagination.totalPages} 頁
                </span>
                <button
                  onClick={() => setCurrentPage(pagination.page + 1)}
                  disabled={pagination.page >= pagination.totalPages}
                  className="px-3 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  下一頁
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default StockList;