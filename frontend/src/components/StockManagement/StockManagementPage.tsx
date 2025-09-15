'use client';

import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import { Plus, Upload, Download, Trash2, RefreshCw } from 'lucide-react';
import { Layout } from '../Layout';
import StockSearchForm from './StockSearchForm';
import AddStockModal from './AddStockModal';
import BatchAddStockModal from './BatchAddStockModal';
import StockList from './StockList';
import { useDispatch } from 'react-redux';
import { AppDispatch } from '../../store';
import { deleteStock, batchDeleteStocks } from '../../store/slices/stocksSlice';
import type { Stock } from '../../types';

const StockManagementPage: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  
  // Modal 狀態
  const [showAddModal, setShowAddModal] = useState(false);
  const [showBatchAddModal, setShowBatchAddModal] = useState(false);
  const [addModalDefaults, setAddModalDefaults] = useState<{
    symbol?: string;
    market?: 'TW' | 'US';
  }>({});
  
  // 選擇狀態
  const [selectedStockIds, setSelectedStockIds] = useState<number[]>([]);
  const [isDeleting, setIsDeleting] = useState(false);

  // 處理股票選擇
  const handleStockSelect = (stock: Stock) => {
    // 可以導航到股票詳細頁面
    console.log('選擇股票:', stock);
  };

  // 處理新增股票成功
  const handleAddStockSuccess = (stock: Stock) => {
    console.log('成功新增股票:', stock);
    // 可以顯示成功訊息或導航到股票頁面
  };

  // 處理批次新增成功
  const handleBatchAddSuccess = (results: any) => {
    console.log('批次新增結果:', results);
    // 可以顯示成功訊息和統計
  };

  // 處理從搜尋表單新增股票
  const handleAddFromSearch = (symbol: string, market: string) => {
    setAddModalDefaults({ symbol, market: market as 'TW' | 'US' });
    setShowAddModal(true);
  };

  // 處理股票編輯
  const handleStockEdit = (stock: Stock) => {
    setAddModalDefaults({ 
      symbol: stock.symbol, 
      market: stock.market as 'TW' | 'US' 
    });
    setShowAddModal(true);
  };

  // 處理單個股票刪除
  const handleStockDelete = async (stock: Stock) => {
    if (!confirm(`確定要刪除股票 ${stock.symbol} (${stock.name || '無名稱'}) 嗎？`)) {
      return;
    }

    try {
      await dispatch(deleteStock(stock.id)).unwrap();
      console.log('成功刪除股票:', stock.symbol);
    } catch (error: any) {
      console.error('刪除股票失敗:', error.message);
      alert('刪除失敗：' + error.message);
    }
  };

  // 處理批次刪除
  const handleBatchDelete = async () => {
    if (selectedStockIds.length === 0) {
      return;
    }

    if (!confirm(`確定要刪除選中的 ${selectedStockIds.length} 支股票嗎？此操作無法撤銷。`)) {
      return;
    }

    setIsDeleting(true);
    
    try {
      await dispatch(batchDeleteStocks(selectedStockIds)).unwrap();
      setSelectedStockIds([]);
      console.log('成功批次刪除股票');
    } catch (error: any) {
      console.error('批次刪除失敗:', error.message);
      alert('批次刪除失敗：' + error.message);
    } finally {
      setIsDeleting(false);
    }
  };

  // 處理匯出
  const handleExport = () => {
    // TODO: 實作匯出功能
    console.log('匯出選中的股票:', selectedStockIds);
  };

  return (
    <Layout>
      <div className="space-y-6">
        {/* 頁面標題 */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">股票管理</h1>
            <p className="text-gray-600 mt-1">管理您的股票追蹤清單</p>
          </div>
          
          <div className="flex gap-3">
            <Button
              variant="outline"
              onClick={() => setShowBatchAddModal(true)}
              className="flex items-center gap-2"
            >
              <Upload className="w-4 h-4" />
              批次新增
            </Button>
            
            <Button
              onClick={() => setShowAddModal(true)}
              className="flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              新增股票
            </Button>
          </div>
        </div>

        {/* 股票搜尋 */}
        <StockSearchForm
          onStockSelect={handleStockSelect}
          onAddNewStock={handleAddFromSearch}
        />

        {/* 批次操作工具列 */}
        {selectedStockIds.length > 0 && (
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-600">
                  已選擇 {selectedStockIds.length} 支股票
                </div>
                
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleExport}
                    className="flex items-center gap-2"
                  >
                    <Download className="w-4 h-4" />
                    匯出
                  </Button>
                  
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleBatchDelete}
                    disabled={isDeleting}
                    className="flex items-center gap-2 text-red-600 hover:text-red-700"
                  >
                    {isDeleting ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <Trash2 className="w-4 h-4" />
                    )}
                    刪除選中
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* 股票清單 */}
        <StockList
          onStockSelect={handleStockSelect}
          onStockEdit={handleStockEdit}
          onStockDelete={handleStockDelete}
          selectedStockIds={selectedStockIds}
          onSelectionChange={setSelectedStockIds}
          showActions={true}
        />

        {/* Modals */}
        <AddStockModal
          isOpen={showAddModal}
          onClose={() => {
            setShowAddModal(false);
            setAddModalDefaults({});
          }}
          defaultSymbol={addModalDefaults.symbol}
          defaultMarket={addModalDefaults.market}
          onSuccess={handleAddStockSuccess}
        />

        <BatchAddStockModal
          isOpen={showBatchAddModal}
          onClose={() => setShowBatchAddModal(false)}
          onSuccess={handleBatchAddSuccess}
        />
      </div>
    </Layout>
  );
};

export default StockManagementPage;