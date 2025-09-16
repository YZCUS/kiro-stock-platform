'use client';

import React, { useState } from 'react';
import Modal from '../ui/Modal';
import Button from '../ui/Button';
import Input from '../ui/Input';
import { AlertCircle, Plus, Loader2 } from 'lucide-react';
import { useDispatch } from 'react-redux';
import { AppDispatch } from '../../store';
import { createStock } from '../../store/slices/stocksSlice';

export interface AddStockModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultSymbol?: string;
  defaultMarket?: 'TW' | 'US';
  onSuccess?: (stock: any) => void;
}

const AddStockModal: React.FC<AddStockModalProps> = ({
  isOpen,
  onClose,
  defaultSymbol = '',
  defaultMarket = 'TW',
  onSuccess
}) => {
  const dispatch = useDispatch<AppDispatch>();
  const [formData, setFormData] = useState({
    symbol: defaultSymbol,
    market: defaultMarket,
    name: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 重置表單
  const resetForm = () => {
    setFormData({
      symbol: defaultSymbol,
      market: defaultMarket,
      name: ''
    });
    setError(null);
    setIsSubmitting(false);
  };

  // 當 modal 關閉時重置表單
  React.useEffect(() => {
    if (!isOpen) {
      resetForm();
    }
  }, [isOpen]);

  // 當預設值改變時更新表單
  React.useEffect(() => {
    if (isOpen) {
      setFormData(prev => ({
        ...prev,
        symbol: defaultSymbol,
        market: defaultMarket
      }));
    }
  }, [defaultSymbol, defaultMarket, isOpen]);

  const validateForm = () => {
    if (!formData.symbol.trim()) {
      setError('請輸入股票代號');
      return false;
    }

    const symbol = formData.symbol.trim().toUpperCase();

    // 驗證台股代號格式
    if (formData.market === 'TW' && !/^\d{4}$/.test(symbol)) {
      setError('台股代號格式錯誤，請輸入4位數字');
      return false;
    }

    // 驗證美股代號格式
    if (formData.market === 'US' && !/^[A-Z]{1,5}$/.test(symbol)) {
      setError('美股代號格式錯誤，請輸入1-5位英文字母');
      return false;
    }

    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const stockData = {
        symbol: formData.symbol.trim().toUpperCase(),
        market: formData.market,
        name: formData.name.trim() || undefined
      };

      const result = await dispatch(createStock(stockData)).unwrap();
      
      onSuccess?.(result);
      onClose();
    } catch (err: any) {
      setError(err.message || '新增股票失敗');
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
      title="新增股票"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* 市場選擇 */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700">
            市場
          </label>
          <div className="flex gap-2">
            <Button
              type="button"
              variant={formData.market === 'TW' ? 'primary' : 'outline'}
              size="sm"
              onClick={() => setFormData(prev => ({ ...prev, market: 'TW' }))}
              disabled={isSubmitting}
              className="flex-1"
            >
              台股
            </Button>
            <Button
              type="button"
              variant={formData.market === 'US' ? 'primary' : 'outline'}
              size="sm"
              onClick={() => setFormData(prev => ({ ...prev, market: 'US' }))}
              disabled={isSubmitting}
              className="flex-1"
            >
              美股
            </Button>
          </div>
        </div>

        {/* 股票代號 */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700">
            股票代號 *
          </label>
          <Input
            placeholder={formData.market === 'TW' ? '例: 2330' : '例: AAPL'}
            value={formData.symbol}
            onChange={(e) => setFormData(prev => ({ ...prev, symbol: e.target.value }))}
            disabled={isSubmitting}
            className="uppercase"
          />
        </div>

        {/* 股票名稱 */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700">
            股票名稱 (選填)
          </label>
          <Input
            placeholder={formData.market === 'TW' ? '例: 台積電' : '例: Apple Inc.'}
            value={formData.name}
            onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
            disabled={isSubmitting}
          />
          <div className="text-xs text-gray-500">
            如果不填寫，系統會嘗試自動獲取股票名稱
          </div>
        </div>

        {/* 錯誤訊息 */}
        {error && (
          <div className="flex items-center gap-2 text-red-600 text-sm p-3 bg-red-50 rounded-lg">
            <AlertCircle className="w-4 h-4" />
            {error}
          </div>
        )}

        {/* 格式說明 */}
        <div className="text-xs text-gray-500 p-3 bg-gray-50 rounded-lg space-y-1">
          <div className="font-medium">代號格式要求：</div>
          <div>• 台股：4位數字 (例: 2330, 0050)</div>
          <div>• 美股：1-5位英文字母 (例: AAPL, GOOGL)</div>
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
            type="submit"
            disabled={isSubmitting || !formData.symbol.trim()}
            className="flex-1 flex items-center gap-2"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                新增中...
              </>
            ) : (
              <>
                <Plus className="w-4 h-4" />
                新增股票
              </>
            )}
          </Button>
        </div>
      </form>
    </Modal>
  );
};

export default AddStockModal;