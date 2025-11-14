/**
 * 訂閱 Modal - 新增/編輯策略訂閱
 */
'use client';

import React, { useState, useEffect } from 'react';
import { StrategyInfo, Subscription, SubscriptionCreateRequest, SubscriptionUpdateRequest } from '@/types/strategy';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { X } from 'lucide-react';

interface SubscriptionModalProps {
  isOpen: boolean;
  onClose: () => void;
  strategies: StrategyInfo[];
  subscription?: Subscription | null;
  onSubmit: (data: SubscriptionCreateRequest | SubscriptionUpdateRequest) => Promise<void>;
}

export default function SubscriptionModal({
  isOpen,
  onClose,
  strategies,
  subscription,
  onSubmit
}: SubscriptionModalProps) {
  const [formData, setFormData] = useState({
    strategy_type: '',
    parameters: {} as Record<string, any>,
    monitor_all_lists: true,
    monitor_portfolio: true,
    selected_list_ids: [] as number[],
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedStrategy, setSelectedStrategy] = useState<StrategyInfo | null>(null);

  // 重置表單當 modal 開啟時
  useEffect(() => {
    if (isOpen) {
      if (subscription) {
        // 編輯模式
        setFormData({
          strategy_type: subscription.strategy_type,
          parameters: subscription.parameters || {},
          monitor_all_lists: subscription.monitor_all_lists,
          monitor_portfolio: subscription.monitor_portfolio,
          selected_list_ids: subscription.selected_list_ids || [],
        });
        const strategy = strategies.find(s => s.type === subscription.strategy_type);
        setSelectedStrategy(strategy || null);
      } else {
        // 新增模式
        setFormData({
          strategy_type: '',
          parameters: {},
          monitor_all_lists: true,
          monitor_portfolio: true,
          selected_list_ids: [],
        });
        setSelectedStrategy(null);
      }
    }
  }, [isOpen, subscription, strategies]);

  if (!isOpen) return null;

  const handleStrategyChange = (strategyType: string) => {
    const strategy = strategies.find(s => s.type === strategyType);
    setSelectedStrategy(strategy || null);
    setFormData({
      ...formData,
      strategy_type: strategyType,
      parameters: strategy?.default_params || {},
    });
  };

  const handleParameterChange = (key: string, value: any) => {
    setFormData({
      ...formData,
      parameters: {
        ...formData.parameters,
        [key]: value,
      },
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.strategy_type) {
      alert('請選擇策略');
      return;
    }

    setIsSubmitting(true);
    try {
      await onSubmit(formData);
      onClose();
    } catch (error) {
      console.error('提交失敗:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold">
            {subscription ? '編輯訂閱' : '新增策略訂閱'}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* 策略選擇 */}
          {!subscription && (
            <div>
              <Label htmlFor="strategy_type">選擇策略 *</Label>
              <select
                id="strategy_type"
                value={formData.strategy_type}
                onChange={(e) => handleStrategyChange(e.target.value)}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2"
                required
              >
                <option value="">請選擇策略</option>
                {strategies.map((strategy) => (
                  <option key={strategy.type} value={strategy.type}>
                    {strategy.name}
                  </option>
                ))}
              </select>
              {selectedStrategy && (
                <p className="mt-1 text-sm text-gray-500">
                  {selectedStrategy.description}
                </p>
              )}
            </div>
          )}

          {/* 策略參數 */}
          {selectedStrategy && (
            <div className="space-y-4">
              <Label className="text-base font-semibold">策略參數</Label>
              {Object.entries(formData.parameters).map(([key, value]) => (
                <div key={key}>
                  <Label htmlFor={key}>{key}</Label>
                  <Input
                    id={key}
                    type={typeof value === 'number' ? 'number' : 'text'}
                    value={value}
                    onChange={(e) => {
                      const newValue = typeof value === 'number'
                        ? parseFloat(e.target.value) || 0
                        : e.target.value;
                      handleParameterChange(key, newValue);
                    }}
                    className="mt-1"
                  />
                </div>
              ))}
            </div>
          )}

          {/* 監控配置 */}
          <div className="space-y-4">
            <Label className="text-base font-semibold">監控範圍</Label>

            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="monitor_all_lists"
                checked={formData.monitor_all_lists}
                onChange={(e) => setFormData({ ...formData, monitor_all_lists: e.target.checked })}
                className="rounded border-gray-300"
              />
              <Label htmlFor="monitor_all_lists" className="font-normal cursor-pointer">
                監控所有清單
              </Label>
            </div>

            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="monitor_portfolio"
                checked={formData.monitor_portfolio}
                onChange={(e) => setFormData({ ...formData, monitor_portfolio: e.target.checked })}
                className="rounded border-gray-300"
              />
              <Label htmlFor="monitor_portfolio" className="font-normal cursor-pointer">
                監控我的持倉
              </Label>
            </div>

            {/* 可以在這裡添加選擇特定清單的功能 */}
          </div>

          {/* 按鈕 */}
          <div className="flex justify-end gap-3 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isSubmitting}
            >
              取消
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting || !formData.strategy_type}
            >
              {isSubmitting ? '處理中...' : (subscription ? '更新' : '建立')}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
