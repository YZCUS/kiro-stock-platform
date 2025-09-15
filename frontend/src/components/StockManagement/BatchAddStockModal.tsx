'use client';

import React, { useState } from 'react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { AlertCircle, Upload, Loader2, X, Plus } from 'lucide-react';
import { useDispatch } from 'react-redux';
import { AppDispatch } from '../../store';
import { batchCreateStocks } from '../../store/slices/stocksSlice';

export interface BatchAddStockModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (results: any) => void;
}

interface StockInput {
  id: string;
  symbol: string;
  market: 'TW' | 'US';
  name: string;
  error?: string;
}

const BatchAddStockModal: React.FC<BatchAddStockModalProps> = ({
  isOpen,
  onClose,
  onSuccess
}) => {
  const dispatch = useDispatch<AppDispatch>();
  const [stocks, setStocks] = useState<StockInput[]>([
    { id: '1', symbol: '', market: 'TW', name: '' }
  ]);
  const [textInput, setTextInput] = useState('');
  const [inputMode, setInputMode] = useState<'form' | 'text'>('form');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const resetForm = () => {
    setStocks([{ id: '1', symbol: '', market: 'TW', name: '' }]);
    setTextInput('');
    setInputMode('form');
    setError(null);
    setIsSubmitting(false);
  };

  React.useEffect(() => {
    if (!isOpen) {
      resetForm();
    }
  }, [isOpen]);

  const addStockRow = () => {
    const newId = Date.now().toString();
    setStocks(prev => [...prev, { id: newId, symbol: '', market: 'TW', name: '' }]);
  };

  const removeStockRow = (id: string) => {
    if (stocks.length > 1) {
      setStocks(prev => prev.filter(stock => stock.id !== id));
    }
  };

  const updateStock = (id: string, field: keyof StockInput, value: string) => {
    setStocks(prev => prev.map(stock => 
      stock.id === id 
        ? { ...stock, [field]: value, error: undefined }
        : stock
    ));
  };

  const validateStock = (stock: StockInput): string | null => {
    if (!stock.symbol.trim()) {
      return '請輸入股票代號';
    }

    const symbol = stock.symbol.trim().toUpperCase();

    if (stock.market === 'TW' && !/^\d{4}$/.test(symbol)) {
      return '台股代號格式錯誤';
    }

    if (stock.market === 'US' && !/^[A-Z]{1,5}$/.test(symbol)) {
      return '美股代號格式錯誤';
    }

    return null;
  };

  const parseTextInput = () => {
    const lines = textInput.split('\n').filter(line => line.trim());
    const parsedStocks: StockInput[] = [];

    lines.forEach((line, index) => {
      const parts = line.split(/[\t,]/).map(part => part.trim());
      if (parts.length >= 2) {
        const symbol = parts[0].toUpperCase();
        const market = parts[1].toUpperCase() === 'US' ? 'US' : 'TW';
        const name = parts[2] || '';
        
        parsedStocks.push({
          id: `parsed_${index}`,
          symbol,
          market,
          name
        });
      }
    });

    if (parsedStocks.length > 0) {
      setStocks(parsedStocks);
      setInputMode('form');
    }
  };

  const validateAllStocks = (): boolean => {
    let hasError = false;
    const updatedStocks = stocks.map(stock => {
      const error = validateStock(stock);
      if (error) hasError = true;
      return { ...stock, error };
    });

    setStocks(updatedStocks);

    // 檢查重複代號
    const symbols = stocks.map(s => s.symbol.trim().toUpperCase()).filter(Boolean);
    const duplicates = symbols.filter((symbol, index) => symbols.indexOf(symbol) !== index);
    
    if (duplicates.length > 0) {
      setError(`發現重複的股票代號: ${duplicates.join(', ')}`);
      return false;
    }

    if (hasError) {
      setError('請修正表單中的錯誤');
      return false;
    }

    return true;
  };

  const handleSubmit = async () => {
    setError(null);

    if (!validateAllStocks()) {
      return;
    }

    const validStocks = stocks.filter(stock => stock.symbol.trim());
    
    if (validStocks.length === 0) {
      setError('請至少輸入一支股票');
      return;
    }

    setIsSubmitting(true);

    try {
      const stocksData = validStocks.map(stock => ({
        symbol: stock.symbol.trim().toUpperCase(),
        market: stock.market,
        name: stock.name.trim() || undefined
      }));

      const result = await dispatch(batchCreateStocks({ stocks: stocksData })).unwrap();
      
      onSuccess?.(result);
      onClose();
    } catch (err: any) {
      setError(err.message || '批次新增失敗');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!isSubmitting) {
      onClose();
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="批次新增股票"
      description="一次新增多支股票到追蹤清單"
      size="lg"
    >
      <div className="space-y-4">
        {/* 輸入模式切換 */}
        <div className="flex gap-2">
          <Button
            type="button"
            variant={inputMode === 'form' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setInputMode('form')}
            disabled={isSubmitting}
          >
            表單輸入
          </Button>
          <Button
            type="button"
            variant={inputMode === 'text' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setInputMode('text')}
            disabled={isSubmitting}
          >
            文字輸入
          </Button>
        </div>

        {/* 文字輸入模式 */}
        {inputMode === 'text' && (
          <div className="space-y-3">
            <div className="text-sm text-gray-600">
              每行一支股票，格式：代號,市場,名稱（名稱可選）
            </div>
            <textarea
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              placeholder="2330,TW,台積電&#10;AAPL,US,Apple Inc.&#10;0050,TW"
              className="w-full h-32 p-3 border rounded-lg resize-none"
              disabled={isSubmitting}
            />
            <Button
              type="button"
              onClick={parseTextInput}
              disabled={!textInput.trim() || isSubmitting}
              className="w-full"
            >
              解析並轉換為表單
            </Button>
          </div>
        )}

        {/* 表單輸入模式 */}
        {inputMode === 'form' && (
          <div className="space-y-3">
            <div className="max-h-60 overflow-y-auto space-y-3">
              {stocks.map((stock, index) => (
                <div key={stock.id} className="flex gap-2 items-start">
                  <div className="flex-none w-8 h-9 flex items-center justify-center text-sm text-gray-500">
                    {index + 1}
                  </div>
                  
                  {/* 股票代號 */}
                  <div className="flex-1">
                    <input
                      type="text"
                      placeholder="代號"
                      value={stock.symbol}
                      onChange={(e) => updateStock(stock.id, 'symbol', e.target.value)}
                      className={`w-full px-3 py-2 border rounded text-sm uppercase ${
                        stock.error ? 'border-red-500' : 'border-gray-300'
                      }`}
                      disabled={isSubmitting}
                    />
                    {stock.error && (
                      <div className="text-xs text-red-600 mt-1">{stock.error}</div>
                    )}
                  </div>

                  {/* 市場 */}
                  <select
                    value={stock.market}
                    onChange={(e) => updateStock(stock.id, 'market', e.target.value)}
                    className="px-3 py-2 border border-gray-300 rounded text-sm"
                    disabled={isSubmitting}
                  >
                    <option value="TW">台股</option>
                    <option value="US">美股</option>
                  </select>

                  {/* 名稱 */}
                  <div className="flex-1">
                    <input
                      type="text"
                      placeholder="名稱（選填）"
                      value={stock.name}
                      onChange={(e) => updateStock(stock.id, 'name', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                      disabled={isSubmitting}
                    />
                  </div>

                  {/* 刪除按鈕 */}
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => removeStockRow(stock.id)}
                    disabled={stocks.length === 1 || isSubmitting}
                    className="flex-none"
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              ))}
            </div>

            {/* 新增行按鈕 */}
            <Button
              type="button"
              variant="outline"
              onClick={addStockRow}
              disabled={isSubmitting}
              className="w-full flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              新增股票行
            </Button>
          </div>
        )}

        {/* 錯誤訊息 */}
        {error && (
          <div className="flex items-center gap-2 text-red-600 text-sm p-3 bg-red-50 rounded-lg">
            <AlertCircle className="w-4 h-4" />
            {error}
          </div>
        )}

        {/* 格式說明 */}
        <div className="text-xs text-gray-500 p-3 bg-gray-50 rounded-lg space-y-1">
          <div className="font-medium">格式要求：</div>
          <div>• 台股：4位數字代號 (例: 2330, 0050)</div>
          <div>• 美股：1-5位英文字母代號 (例: AAPL, GOOGL)</div>
          <div>• 不能有重複的股票代號</div>
        </div>

        {/* 按鈕 */}
        <div className="flex gap-3 pt-4">
          <Button
            type="button"
            variant="outline"
            onClick={handleClose}
            disabled={isSubmitting}
            className="flex-1"
          >
            取消
          </Button>
          <Button
            type="button"
            onClick={handleSubmit}
            disabled={isSubmitting || stocks.every(s => !s.symbol.trim())}
            className="flex-1 flex items-center gap-2"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                新增中...
              </>
            ) : (
              <>
                <Upload className="w-4 h-4" />
                批次新增 ({stocks.filter(s => s.symbol.trim()).length})
              </>
            )}
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export default BatchAddStockModal;