'use client';

import React, { useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Card, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { 
  Search, 
  Filter, 
  Grid3X3, 
  List, 
  RefreshCw,
  AlertCircle
} from 'lucide-react';
import { AppDispatch, RootState } from '../../store';
import { fetchStocks } from '../../store/slices/stocksSlice';
import StockCard from './StockCard';
import type { Stock } from '../../types';

export interface StockGridViewProps {
  onStockView?: (stock: Stock) => void;
  onStockEdit?: (stock: Stock) => void;
  onStockDelete?: (stock: Stock) => void;
  onStockRefresh?: (stock: Stock) => void;
  viewMode?: 'grid' | 'list';
  onViewModeChange?: (mode: 'grid' | 'list') => void;
}

const StockGridView: React.FC<StockGridViewProps> = ({
  onStockView,
  onStockEdit,
  onStockDelete,
  onStockRefresh,
  viewMode = 'grid',
  onViewModeChange
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
      filters: {
        market: marketFilter === 'ALL' ? '' : marketFilter,
        active_only: true,
        search: searchTerm
      }
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

  const handleStockRefresh = async (stock: Stock) => {
    setRefreshingStocks(prev => new Set(prev).add(stock.id));
    
    try {
      await onStockRefresh?.(stock);
    } finally {
      setRefreshingStocks(prev => {
        const newSet = new Set(prev);
        newSet.delete(stock.id);
        return newSet;
      });
    }
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
    <div className="space-y-6">
      {/* 工具列 */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col lg:flex-row gap-4">
            {/* 搜尋 */}
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="搜尋股票代號或名稱..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-9"
              />
            </div>
            
            {/* 篩選器 */}
            <div className="flex gap-2">
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

            {/* 檢視模式切換 */}
            {onViewModeChange && (
              <div className="flex gap-1 border rounded-lg p-1">
                <Button
                  variant={viewMode === 'grid' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => onViewModeChange('grid')}
                >
                  <Grid3X3 className="w-4 h-4" />
                </Button>
                <Button
                  variant={viewMode === 'list' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => onViewModeChange('list')}
                >
                  <List className="w-4 h-4" />
                </Button>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 錯誤提示 */}
      {error && (
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-red-600 text-sm">
              <AlertCircle className="w-4 h-4" />
              {error}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 股票網格/列表 */}
      {filteredAndSortedStocks.length === 0 ? (
        <Card>
          <CardContent className="p-8">
            <div className="text-center text-gray-500">
              {searchTerm || marketFilter !== 'ALL' 
                ? '沒有符合條件的股票' 
                : '尚未新增任何股票'
              }
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className={
          viewMode === 'grid' 
            ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4'
            : 'space-y-3'
        }>
          {filteredAndSortedStocks.map((stock) => (
            <StockCard
              key={stock.id}
              stock={stock}
              onView={() => onStockView?.(stock)}
              onEdit={() => onStockEdit?.(stock)}
              onDelete={() => onStockDelete?.(stock)}
              onRefresh={() => handleStockRefresh(stock)}
              isRefreshing={refreshingStocks.has(stock.id)}
              showActions={true}
              // TODO: 從 API 獲取價格數據
              priceData={undefined}
            />
          ))}
        </div>
      )}

      {/* 載入更多 */}
      {loading && stocks.length > 0 && (
        <div className="flex justify-center py-4">
          <RefreshCw className="w-5 h-5 animate-spin" />
        </div>
      )}
    </div>
  );
};

export default StockGridView;