'use client';

import React, { useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { 
  Search, 
  Filter, 
  MoreVertical, 
  TrendingUp, 
  TrendingDown, 
  Minus,
  RefreshCw,
  Trash2,
  Edit,
  Eye,
  AlertCircle
} from 'lucide-react';
import { AppDispatch, RootState } from '../../store';
import { fetchStocks, refreshStockData } from '../../store/slices/stocksSlice';
import type { Stock } from '../../types';

export interface StockListProps {
  onStockSelect?: (stock: Stock) => void;
  onStockEdit?: (stock: Stock) => void;
  onStockDelete?: (stock: Stock) => void;
  selectedStockIds?: number[];
  onSelectionChange?: (selectedIds: number[]) => void;
  showActions?: boolean;
}

const StockList: React.FC<StockListProps> = ({
  onStockSelect,
  onStockEdit,
  onStockDelete,
  selectedStockIds = [],
  onSelectionChange,
  showActions = true
}) => {
  const dispatch = useDispatch<AppDispatch>();
  const { stocks, loading, error } = useSelector((state: RootState) => state.stocks);
  
  const [searchTerm, setSearchTerm] = useState('');
  const [marketFilter, setMarketFilter] = useState<'ALL' | 'TW' | 'US'>('ALL');
  const [sortBy, setSortBy] = useState<'symbol' | 'name' | 'created_at'>('symbol');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [refreshingStocks, setRefreshingStocks] = useState<Set<number>>(new Set());

  useEffect(() => {
    dispatch(fetchStocks({
      market: marketFilter === 'ALL' ? undefined : marketFilter,
      active_only: true
    }));
  }, [dispatch, marketFilter]);

  // 過濾和排序股票
  const filteredAndSortedStocks = React.useMemo(() => {
    let filtered = stocks.filter(stock => {
      const matchesSearch = !searchTerm || 
        stock.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
        stock.name?.toLowerCase().includes(searchTerm.toLowerCase());
      
      const matchesMarket = marketFilter === 'ALL' || stock.market === marketFilter;
      
      return matchesSearch && matchesMarket && stock.is_active;
    });

    filtered.sort((a, b) => {
      let aValue: string | number;
      let bValue: string | number;

      switch (sortBy) {
        case 'symbol':
          aValue = a.symbol;
          bValue = b.symbol;
          break;
        case 'name':
          aValue = a.name || a.symbol;
          bValue = b.name || b.symbol;
          break;
        case 'created_at':
          aValue = new Date(a.created_at).getTime();
          bValue = new Date(b.created_at).getTime();
          break;
        default:
          aValue = a.symbol;
          bValue = b.symbol;
      }

      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortOrder === 'asc' 
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }

      return sortOrder === 'asc' 
        ? (aValue as number) - (bValue as number)
        : (bValue as number) - (aValue as number);
    });

    return filtered;
  }, [stocks, searchTerm, marketFilter, sortBy, sortOrder]);

  const handleSelectAll = () => {
    if (selectedStockIds.length === filteredAndSortedStocks.length) {
      onSelectionChange?.([]);
    } else {
      onSelectionChange?.(filteredAndSortedStocks.map(stock => stock.id));
    }
  };

  const handleStockSelect = (stockId: number) => {
    const newSelection = selectedStockIds.includes(stockId)
      ? selectedStockIds.filter(id => id !== stockId)
      : [...selectedStockIds, stockId];
    
    onSelectionChange?.(newSelection);
  };

  const handleRefreshStock = async (stock: Stock) => {
    setRefreshingStocks(prev => new Set(prev).add(stock.id));
    
    try {
      await dispatch(refreshStockData({ 
        stockId: stock.id, 
        days: 30 
      })).unwrap();
    } catch (error) {
      console.error('刷新股票數據失敗:', error);
    } finally {
      setRefreshingStocks(prev => {
        const newSet = new Set(prev);
        newSet.delete(stock.id);
        return newSet;
      });
    }
  };

  const getStockStatusIcon = (stock: Stock) => {
    // 這裡可以根據股票的最新價格變化來顯示趨勢圖標
    // 暫時返回默認圖標
    return <Minus className="w-4 h-4 text-gray-400" />;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('zh-TW');
  };

  if (loading && stocks.length === 0) {
    return (
      <Card>
        <CardContent className="p-8">
          <div className="flex items-center justify-center">
            <RefreshCw className="w-6 h-6 animate-spin mr-2" />
            載入股票清單中...
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5" />
            股票清單 ({filteredAndSortedStocks.length})
          </CardTitle>
          
          {showActions && selectedStockIds.length > 0 && (
            <div className="text-sm text-gray-600">
              已選擇 {selectedStockIds.length} 支股票
            </div>
          )}
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* 搜尋和篩選 */}
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <Input
              placeholder="搜尋股票代號或名稱..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9"
            />
          </div>
          
          <select
            value={marketFilter}
            onChange={(e) => setMarketFilter(e.target.value as 'ALL' | 'TW' | 'US')}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
          >
            <option value="ALL">全部市場</option>
            <option value="TW">台股</option>
            <option value="US">美股</option>
          </select>
          
          <select
            value={`${sortBy}_${sortOrder}`}
            onChange={(e) => {
              const [sort, order] = e.target.value.split('_');
              setSortBy(sort as 'symbol' | 'name' | 'created_at');
              setSortOrder(order as 'asc' | 'desc');
            }}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
          >
            <option value="symbol_asc">代號 ↑</option>
            <option value="symbol_desc">代號 ↓</option>
            <option value="name_asc">名稱 ↑</option>
            <option value="name_desc">名稱 ↓</option>
            <option value="created_at_desc">建立時間 ↓</option>
            <option value="created_at_asc">建立時間 ↑</option>
          </select>
        </div>

        {/* 錯誤提示 */}
        {error && (
          <div className="flex items-center gap-2 text-red-600 text-sm p-3 bg-red-50 rounded-lg">
            <AlertCircle className="w-4 h-4" />
            {error}
          </div>
        )}

        {/* 股票清單 */}
        {filteredAndSortedStocks.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            {searchTerm || marketFilter !== 'ALL' ? '沒有符合條件的股票' : '尚未新增任何股票'}
          </div>
        ) : (
          <div className="space-y-2">
            {/* 全選選項 */}
            {showActions && onSelectionChange && (
              <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                <input
                  type="checkbox"
                  checked={selectedStockIds.length === filteredAndSortedStocks.length}
                  onChange={handleSelectAll}
                  className="rounded"
                />
                <span className="text-sm text-gray-600">全選</span>
              </div>
            )}

            {/* 股票項目 */}
            {filteredAndSortedStocks.map((stock) => (
              <div
                key={stock.id}
                className={`flex items-center gap-3 p-4 border rounded-lg hover:bg-gray-50 transition-colors ${
                  selectedStockIds.includes(stock.id) ? 'bg-blue-50 border-blue-200' : ''
                }`}
              >
                {/* 選擇框 */}
                {showActions && onSelectionChange && (
                  <input
                    type="checkbox"
                    checked={selectedStockIds.includes(stock.id)}
                    onChange={() => handleStockSelect(stock.id)}
                    className="rounded"
                  />
                )}

                {/* 股票資訊 */}
                <div 
                  className="flex-1 cursor-pointer"
                  onClick={() => onStockSelect?.(stock)}
                >
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2">
                      {getStockStatusIcon(stock)}
                      <div>
                        <div className="font-medium text-gray-900">
                          {stock.symbol}
                          <span className="ml-2 text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                            {stock.market}
                          </span>
                        </div>
                        <div className="text-sm text-gray-600">
                          {stock.name || '無名稱'}
                        </div>
                      </div>
                    </div>
                    
                    <div className="ml-auto text-right">
                      <div className="text-xs text-gray-500">
                        建立：{formatDate(stock.created_at)}
                      </div>
                      {stock.updated_at !== stock.created_at && (
                        <div className="text-xs text-gray-500">
                          更新：{formatDate(stock.updated_at)}
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* 操作按鈕 */}
                {showActions && (
                  <div className="flex items-center gap-1">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleRefreshStock(stock)}
                      disabled={refreshingStocks.has(stock.id)}
                      title="刷新數據"
                    >
                      <RefreshCw className={`w-4 h-4 ${refreshingStocks.has(stock.id) ? 'animate-spin' : ''}`} />
                    </Button>
                    
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onStockEdit?.(stock)}
                      title="編輯"
                    >
                      <Edit className="w-4 h-4" />
                    </Button>
                    
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onStockDelete?.(stock)}
                      title="刪除"
                      className="text-red-600 hover:text-red-700"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* 載入更多 */}
        {loading && stocks.length > 0 && (
          <div className="flex justify-center py-4">
            <RefreshCw className="w-5 h-5 animate-spin" />
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default StockList;