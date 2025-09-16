/**
 * 股票管理頁面組件
 */
'use client';

import React, { useState, useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '../../store';
import { fetchStocks, deleteStock, setFilters, clearError } from '../../store/slices/stocksSlice';
import { addToast } from '../../store/slices/uiSlice';

export interface StockManagementPageProps {}

const StockManagementPage: React.FC<StockManagementPageProps> = () => {
  const dispatch = useAppDispatch();
  const { stocks, loading, error, pagination, filters } = useAppSelector(state => state.stocks);
  const [searchTerm, setSearchTerm] = useState('');

  // 載入股票數據
  useEffect(() => {
    dispatch(fetchStocks({}));
  }, [dispatch]);

  // 處理搜尋
  useEffect(() => {
    dispatch(setFilters({ ...filters, search: searchTerm }));
  }, [searchTerm, dispatch, filters]);

  // 處理刪除股票
  const handleDeleteStock = async (stockId: number, stockName: string) => {
    if (window.confirm(`確定要移除股票 ${stockName} 嗎？`)) {
      try {
        await dispatch(deleteStock(stockId)).unwrap();
        dispatch(addToast({
          type: 'success',
          title: '成功',
          message: `已成功移除股票 ${stockName}`,
        }));
      } catch (error) {
        dispatch(addToast({
          type: 'error',
          title: '錯誤',
          message: '移除股票失敗，請稍後再試',
        }));
      }
    }
  };

  // 過濾股票
  const filteredStocks = stocks.filter(stock =>
    stock.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    stock.symbol.toLowerCase().includes(searchTerm.toLowerCase())
  );

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
          <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium">
            新增股票
          </button>
        </div>

        <div className="mb-4">
          <input
            type="text"
            placeholder="搜尋股票名稱或代號..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
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
                  價格
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  漲跌
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  操作
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredStocks.map((stock) => (
                <tr key={stock.id} className="hover:bg-gray-50">
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
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {stock.market === 'TW' ? 'NT$' : '$'} ---
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span className="text-gray-500">
                      未獲取
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 space-x-2">
                    <button className="text-blue-600 hover:text-blue-800 font-medium">
                      查看
                    </button>
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

        {!loading && filteredStocks.length === 0 && (
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
              onClick={() => {
                dispatch(clearError());
                dispatch(fetchStocks({}));
              }}
              className="mt-2 text-blue-600 hover:text-blue-800 font-medium"
            >
              重新載入
            </button>
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
    </div>
  );
};

export default StockManagementPage;