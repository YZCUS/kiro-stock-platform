'use client';

import React, { useState } from 'react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Search, Plus, AlertCircle } from 'lucide-react';
import { useDispatch } from 'react-redux';
import { AppDispatch } from '../../store';
import { searchStocks } from '../../store/slices/stocksSlice';

export interface StockSearchFormProps {
  onStockSelect?: (stock: any) => void;
  onAddNewStock?: (symbol: string, market: string) => void;
}

const StockSearchForm: React.FC<StockSearchFormProps> = ({
  onStockSelect,
  onAddNewStock
}) => {
  const dispatch = useDispatch<AppDispatch>();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedMarket, setSelectedMarket] = useState<'TW' | 'US'>('TW');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!searchTerm.trim()) {
      setError('請輸入股票代號');
      return;
    }

    setIsSearching(true);
    setError(null);

    try {
      const result = await dispatch(searchStocks({
        symbol: searchTerm.trim(),
        market: selectedMarket
      })).unwrap();
      
      setSearchResults(result);
      
      if (result.length === 0) {
        setError('未找到相關股票');
      }
    } catch (err: any) {
      setError(err.message || '搜尋失敗');
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const handleAddNew = () => {
    if (!searchTerm.trim()) {
      setError('請輸入股票代號');
      return;
    }

    const symbol = searchTerm.trim().toUpperCase();
    
    // 驗證台股代號格式 (4位數字)
    if (selectedMarket === 'TW' && !/^\d{4}$/.test(symbol)) {
      setError('台股代號格式錯誤，請輸入4位數字');
      return;
    }
    
    // 驗證美股代號格式 (1-5位英文字母)
    if (selectedMarket === 'US' && !/^[A-Z]{1,5}$/.test(symbol)) {
      setError('美股代號格式錯誤，請輸入1-5位英文字母');
      return;
    }

    onAddNewStock?.(symbol, selectedMarket);
    setSearchTerm('');
    setError(null);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Search className="w-5 h-5" />
          股票搜尋與新增
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 搜尋表單 */}
        <div className="space-y-4">
          {/* 市場選擇 */}
          <div className="flex gap-2">
            <Button
              variant={selectedMarket === 'TW' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedMarket('TW')}
              className="flex-1"
            >
              台股
            </Button>
            <Button
              variant={selectedMarket === 'US' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedMarket('US')}
              className="flex-1"
            >
              美股
            </Button>
          </div>

          {/* 搜尋輸入 */}
          <div className="flex gap-2">
            <Input
              placeholder={selectedMarket === 'TW' ? '輸入台股代號 (例: 2330)' : '輸入美股代號 (例: AAPL)'}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyPress={handleKeyPress}
              className="flex-1"
            />
            <Button
              onClick={handleSearch}
              disabled={isSearching || !searchTerm.trim()}
            >
              {isSearching ? '搜尋中...' : '搜尋'}
            </Button>
          </div>

          {/* 錯誤訊息 */}
          {error && (
            <div className="flex items-center gap-2 text-red-600 text-sm">
              <AlertCircle className="w-4 h-4" />
              {error}
            </div>
          )}
        </div>

        {/* 搜尋結果 */}
        {searchResults.length > 0 && (
          <div className="space-y-2">
            <h4 className="font-medium text-gray-700">搜尋結果</h4>
            <div className="space-y-2 max-h-60 overflow-y-auto">
              {searchResults.map((stock) => (
                <div
                  key={stock.id}
                  className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50 cursor-pointer"
                  onClick={() => onStockSelect?.(stock)}
                >
                  <div>
                    <div className="font-medium">{stock.symbol}</div>
                    <div className="text-sm text-gray-600">{stock.name}</div>
                  </div>
                  <div className="text-sm text-gray-500">
                    {stock.market}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 新增股票按鈕 */}
        {searchTerm.trim() && searchResults.length === 0 && !isSearching && (
          <div className="border-t pt-4">
            <div className="text-sm text-gray-600 mb-2">
              未找到 "{searchTerm}" 在資料庫中，您可以新增此股票：
            </div>
            <Button
              onClick={handleAddNew}
              variant="outline"
              className="w-full flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              新增 {searchTerm.toUpperCase()} ({selectedMarket})
            </Button>
          </div>
        )}

        {/* 使用說明 */}
        <div className="text-xs text-gray-500 space-y-1">
          <div>• 台股：輸入4位數字代號 (例: 2330)</div>
          <div>• 美股：輸入1-5位英文字母代號 (例: AAPL)</div>
          <div>• 點擊搜尋結果可選擇股票，或新增不存在的股票</div>
        </div>
      </CardContent>
    </Card>
  );
};

export default StockSearchForm;