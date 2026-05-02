'use client';

import { useEffect, useState } from 'react';
import { Bell, X } from 'lucide-react';
import { createPriceAlert } from '@/services/priceAlertsApi';
import { Stock } from '@/types';
import { Button } from '@/components/ui/button';

interface PriceAlertModalProps {
  isOpen: boolean;
  stock: Stock | null;
  onClose: () => void;
  onSuccess?: () => void;
}

export default function PriceAlertModal({
  isOpen,
  stock,
  onClose,
  onSuccess,
}: PriceAlertModalProps) {
  const [condition, setCondition] = useState<'ABOVE' | 'BELOW'>('ABOVE');
  const [targetPrice, setTargetPrice] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !stock) return;
    const current = stock.latest_price?.close;
    setTargetPrice(typeof current === 'number' ? current.toFixed(2) : '');
    setCondition('ABOVE');
    setError(null);
  }, [isOpen, stock]);

  if (!isOpen || !stock) {
    return null;
  }

  const submit = async () => {
    const price = Number(targetPrice);
    if (!Number.isFinite(price) || price <= 0) {
      setError('請輸入有效價格');
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await createPriceAlert({
        stock_id: stock.id,
        condition,
        target_price: price,
        source_timeframe: stock.market === 'TW' ? '5m' : '1d',
      });
      onSuccess?.();
      onClose();
    } catch (submitError: any) {
      setError(submitError?.response?.data?.detail || '建立提醒失敗');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <div className="mb-5 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bell className="h-5 w-5 text-blue-600" />
            <h3 className="text-lg font-semibold text-gray-900">價格提醒</h3>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} aria-label="關閉">
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="mb-4 rounded-md bg-gray-50 px-3 py-2">
          <div className="text-sm font-semibold text-gray-900">{stock.symbol}</div>
          <div className="text-xs text-gray-500">{stock.name || stock.market}</div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">
              條件
            </label>
            <div className="grid grid-cols-2 gap-2">
              <Button
                type="button"
                variant={condition === 'ABOVE' ? 'default' : 'outline'}
                onClick={() => setCondition('ABOVE')}
              >
                高於
              </Button>
              <Button
                type="button"
                variant={condition === 'BELOW' ? 'default' : 'outline'}
                onClick={() => setCondition('BELOW')}
              >
                低於
              </Button>
            </div>
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">
              目標價
            </label>
            <input
              type="number"
              min="0"
              step="0.01"
              value={targetPrice}
              onChange={(event) => setTargetPrice(event.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {error && (
            <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <Button variant="outline" onClick={onClose} disabled={saving}>
            取消
          </Button>
          <Button onClick={submit} disabled={saving}>
            {saving ? '建立中...' : '建立提醒'}
          </Button>
        </div>
      </div>
    </div>
  );
}
