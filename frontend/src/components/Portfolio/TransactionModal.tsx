/**
 * 交易 Modal - 買入/賣出股票
 */
'use client';

import React, { useState, useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '@/store';
import { addTransaction } from '@/store/slices/portfolioSlice';
import { addToast } from '@/store/slices/uiSlice';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Stock, TransactionType } from '@/types';
import { X, AlertCircle } from 'lucide-react';

interface TransactionModalProps {
  isOpen: boolean;
  onClose: () => void;
  stock: Stock | null;
  transactionType: TransactionType;
  onSuccess?: () => void;
}

export default function TransactionModal({
  isOpen,
  onClose,
  stock,
  transactionType,
  onSuccess
}: TransactionModalProps) {
  const dispatch = useAppDispatch();
  const { portfolios } = useAppSelector((state) => state.portfolio);
  const [formData, setFormData] = useState({
    quantity: '',
    price: '',
    fee: '',
    tax: '',
    transaction_date: new Date().toISOString().split('T')[0],
    note: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  // 獲取當前股票的持倉數量
  const currentHolding = stock ? portfolios.find(p => p.stock_id === stock.id) : null;
  const availableQuantity = currentHolding?.quantity || 0;

  // 重置表單當 modal 開啟或股票變更時
  useEffect(() => {
    if (isOpen && stock) {
      setFormData({
        quantity: '',
        price: stock.latest_price?.close?.toString() || '',
        fee: '',
        tax: '',
        transaction_date: new Date().toISOString().split('T')[0],
        note: ''
      });
    }
  }, [isOpen, stock]);

  if (!isOpen || !stock) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // 驗證
    if (!formData.quantity || !formData.price) {
      dispatch(addToast({
        type: 'error',
        title: '錯誤',
        message: '請填寫數量和價格'
      }));
      return;
    }

    const quantity = parseInt(formData.quantity);
    const price = parseFloat(formData.price);
    const fee = formData.fee ? parseFloat(formData.fee) : 0;
    const tax = formData.tax ? parseFloat(formData.tax) : 0;

    if (quantity <= 0 || price <= 0) {
      dispatch(addToast({
        type: 'error',
        title: '錯誤',
        message: '數量和價格必須大於 0'
      }));
      return;
    }

    // 賣出時檢查庫存
    if (transactionType === 'SELL') {
      if (availableQuantity === 0) {
        dispatch(addToast({
          type: 'error',
          title: '無法賣出',
          message: `您尚未持有 ${stock.symbol}，無法進行賣出操作`
        }));
        return;
      }

      if (quantity > availableQuantity) {
        dispatch(addToast({
          type: 'error',
          title: '庫存不足',
          message: `可賣出數量: ${availableQuantity} 股，您輸入了 ${quantity} 股`
        }));
        return;
      }
    }

    setIsSubmitting(true);

    try {
      await dispatch(addTransaction({
        stock_id: stock.id,
        transaction_type: transactionType,
        quantity,
        price,
        fee,
        tax,
        transaction_date: formData.transaction_date,
        note: formData.note || undefined
      })).unwrap();

      dispatch(addToast({
        type: 'success',
        title: '成功',
        message: `${transactionType === 'BUY' ? '買入' : '賣出'}交易已記錄`
      }));

      // 重置表單
      setFormData({
        quantity: '',
        price: '',
        fee: '',
        tax: '',
        transaction_date: new Date().toISOString().split('T')[0],
        note: ''
      });

      onSuccess?.();
      onClose();
    } catch (err: any) {
      dispatch(addToast({
        type: 'error',
        title: '錯誤',
        message: err.message || '交易記錄失敗'
      }));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const calculateTotal = () => {
    const quantity = parseInt(formData.quantity) || 0;
    const price = parseFloat(formData.price) || 0;
    const fee = parseFloat(formData.fee) || 0;
    const tax = parseFloat(formData.tax) || 0;

    const subtotal = quantity * price;
    return transactionType === 'BUY'
      ? subtotal + fee
      : subtotal - fee - tax;
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        {/* Header */}
        <div className={`px-6 py-4 border-b ${transactionType === 'BUY' ? 'bg-green-50' : 'bg-red-50'}`}>
          <div className="flex justify-between items-center">
            <div>
              <h2 className={`text-xl font-bold ${transactionType === 'BUY' ? 'text-green-700' : 'text-red-700'}`}>
                {transactionType === 'BUY' ? '買入股票' : '賣出股票'}
              </h2>
              <p className="text-sm text-gray-600 mt-1">
                {stock.symbol} - {stock.name}
              </p>
            </div>
            <Button variant="ghost" size="sm" onClick={onClose}>
              <X className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* 賣出時的庫存警告 */}
          {transactionType === 'SELL' && availableQuantity === 0 && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-red-800">
                <p className="font-semibold">無法賣出</p>
                <p>您尚未持有 {stock.symbol}，請先買入後才能賣出。</p>
              </div>
            </div>
          )}

          {/* 數量 */}
          <div>
            <Label htmlFor="quantity">
              數量 <span className="text-red-500">*</span>
              {transactionType === 'SELL' && availableQuantity > 0 && (
                <span className="text-sm font-normal text-gray-500 ml-2">
                  （可賣出: {availableQuantity} 股）
                </span>
              )}
            </Label>
            <Input
              id="quantity"
              type="number"
              min="1"
              max={transactionType === 'SELL' ? availableQuantity : undefined}
              step="1"
              value={formData.quantity}
              onChange={(e) => handleChange('quantity', e.target.value)}
              placeholder={transactionType === 'SELL' ? `可賣出 ${availableQuantity} 股` : '請輸入股數'}
              required
              disabled={transactionType === 'SELL' && availableQuantity === 0}
            />
          </div>

          {/* 價格 */}
          <div>
            <Label htmlFor="price">
              價格 <span className="text-red-500">*</span>
            </Label>
            <Input
              id="price"
              type="number"
              min="0"
              step="0.01"
              value={formData.price}
              onChange={(e) => handleChange('price', e.target.value)}
              placeholder="請輸入成交價格"
              required
            />
            {stock.latest_price?.close && (
              <p className="text-xs text-gray-500 mt-1">
                最新價格: {stock.market === 'TW' ? 'NT$' : '$'}{stock.latest_price.close.toFixed(2)}
              </p>
            )}
          </div>

          {/* 手續費 */}
          <div>
            <Label htmlFor="fee">手續費</Label>
            <Input
              id="fee"
              type="number"
              min="0"
              step="0.01"
              value={formData.fee}
              onChange={(e) => handleChange('fee', e.target.value)}
              placeholder="選填（預設 0）"
            />
          </div>

          {/* 交易稅（僅賣出時顯示） */}
          {transactionType === 'SELL' && (
            <div>
              <Label htmlFor="tax">交易稅</Label>
              <Input
                id="tax"
                type="number"
                min="0"
                step="0.01"
                value={formData.tax}
                onChange={(e) => handleChange('tax', e.target.value)}
                placeholder="選填（預設 0）"
              />
            </div>
          )}

          {/* 交易日期 */}
          <div>
            <Label htmlFor="transaction_date">
              交易日期 <span className="text-red-500">*</span>
            </Label>
            <Input
              id="transaction_date"
              type="date"
              value={formData.transaction_date}
              onChange={(e) => handleChange('transaction_date', e.target.value)}
              required
            />
          </div>

          {/* 備註 */}
          <div>
            <Label htmlFor="note">備註</Label>
            <textarea
              id="note"
              value={formData.note}
              onChange={(e) => handleChange('note', e.target.value)}
              placeholder="選填"
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={2}
            />
          </div>

          {/* 總金額 */}
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium text-gray-700">
                {transactionType === 'BUY' ? '總支出' : '總收入'}
              </span>
              <span className={`text-xl font-bold ${transactionType === 'BUY' ? 'text-green-600' : 'text-red-600'}`}>
                {stock.market === 'TW' ? 'NT$' : '$'}{calculateTotal().toLocaleString('zh-TW', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>
            {formData.quantity && formData.price && (
              <p className="text-xs text-gray-500 mt-2">
                {formData.quantity} 股 × {stock.market === 'TW' ? 'NT$' : '$'}{parseFloat(formData.price).toFixed(2)}
                {(parseFloat(formData.fee) > 0 || parseFloat(formData.tax) > 0) && (
                  <>
                    {transactionType === 'BUY' ? ' + ' : ' - '}
                    手續費 {stock.market === 'TW' ? 'NT$' : '$'}{parseFloat(formData.fee || '0').toFixed(2)}
                    {transactionType === 'SELL' && parseFloat(formData.tax) > 0 && (
                      <> - 稅 {stock.market === 'TW' ? 'NT$' : '$'}{parseFloat(formData.tax).toFixed(2)}</>
                    )}
                  </>
                )}
              </p>
            )}
          </div>

          {/* 按鈕 */}
          <div className="flex gap-3 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isSubmitting}
              className="flex-1"
            >
              取消
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting || (transactionType === 'SELL' && availableQuantity === 0)}
              className={`flex-1 ${transactionType === 'BUY' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'}`}
            >
              {isSubmitting ? '處理中...' : `確認${transactionType === 'BUY' ? '買入' : '賣出'}`}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
