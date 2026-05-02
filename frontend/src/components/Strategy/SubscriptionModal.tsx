/**
 * 訂閱 Modal - 新增/編輯策略訂閱
 */
'use client';

import React, { useState, useEffect } from 'react';
import {
  StrategyInfo,
  StrategyParameterMap,
  StrategyParameterSchema,
  StrategyParameterValue,
  Subscription,
  SubscriptionCreateRequest,
  SubscriptionUpdateRequest,
} from '@/types/strategy';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { X } from 'lucide-react';
import type { StockList } from '@/types';

interface SubscriptionModalProps {
  isOpen: boolean;
  onClose: () => void;
  strategies: StrategyInfo[];
  stockLists?: StockList[];
  subscription?: Subscription | null;
  onSubmit: (
    data: SubscriptionCreateRequest | SubscriptionUpdateRequest
  ) => Promise<void>;
}

const ML_SYSTEM_FIELDS = new Set(['model_name', 'feature_set', 'universe', 'horizon']);

const ML_MODEL_PRESETS = [
  {
    value: 'lightgbm_alpha158',
    label: 'LightGBM Alpha158',
    featureSet: 'alpha158',
  },
];

const ML_UNIVERSE_OPTIONS = [
  { value: 'active_us', label: '美股活躍股票池' },
];

const ML_HORIZON_OPTIONS = [
  { value: '1d', label: '1 日預測' },
];

export default function SubscriptionModal({
  isOpen,
  onClose,
  strategies,
  stockLists = [],
  subscription,
  onSubmit
}: SubscriptionModalProps) {
  const [formData, setFormData] = useState({
    strategy_type: '',
    parameters: {} as StrategyParameterMap,
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

  const handleParameterChange = (key: string, value: StrategyParameterValue) => {
    setFormData({
      ...formData,
      parameters: {
        ...formData.parameters,
        [key]: value,
      },
    });
  };

  const handleMlPresetChange = (modelName: string) => {
    const preset = ML_MODEL_PRESETS.find((item) => item.value === modelName);
    setFormData({
      ...formData,
      parameters: {
        ...formData.parameters,
        model_name: modelName,
        feature_set: preset?.featureSet || formData.parameters.feature_set || 'alpha158',
      },
    });
  };

  const handleMonitorAllListsChange = (monitorAllLists: boolean) => {
    setFormData({
      ...formData,
      monitor_all_lists: monitorAllLists,
      selected_list_ids: monitorAllLists ? [] : formData.selected_list_ids,
    });
  };

  const toggleSelectedList = (listId: number) => {
    const selected = new Set(formData.selected_list_ids);
    if (selected.has(listId)) {
      selected.delete(listId);
    } else {
      selected.add(listId);
    }

    setFormData({
      ...formData,
      monitor_all_lists: false,
      selected_list_ids: Array.from(selected),
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.strategy_type) {
      alert('請選擇策略');
      return;
    }

    if (
      !formData.monitor_all_lists &&
      !formData.monitor_portfolio &&
      formData.selected_list_ids.length === 0
    ) {
      alert('請至少選擇一個監控範圍');
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

  const inferParameterType = (
    value: StrategyParameterValue | undefined
  ): StrategyParameterSchema['type'] => {
    if (typeof value === 'boolean') return 'boolean';
    if (typeof value === 'number') return 'number';
    return 'text';
  };

  const parameterFields: StrategyParameterSchema[] = selectedStrategy
    ? (() => {
        const schema = selectedStrategy.parameter_schema || [];
        const schemaKeys = new Set(schema.map((field) => field.key));
        const fallbackFields = Object.entries(formData.parameters)
          .filter(([key]) => !schemaKeys.has(key))
          .map(([key, value]) => ({
            key,
            label: key,
            type: inferParameterType(value),
          }));

        const fields = [...schema, ...fallbackFields];
        if (selectedStrategy.type === 'ml_prediction') {
          return fields.filter((field) => !ML_SYSTEM_FIELDS.has(field.key));
        }

        return fields;
      })()
    : [];

  const renderMlPredictionPreset = () => {
    if (selectedStrategy?.type !== 'ml_prediction') return null;

    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
        <div className="mb-3">
          <div className="text-sm font-semibold text-gray-900">模型設定</div>
          <p className="mt-1 text-xs leading-5 text-gray-500">
            模型、特徵集與股票池由系統每日產生，使用者只需要選擇可用預設。
          </p>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <Label htmlFor="ml_model_preset">模型</Label>
            <select
              id="ml_model_preset"
              value={String(formData.parameters.model_name || 'lightgbm_alpha158')}
              onChange={(e) => handleMlPresetChange(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2"
            >
              {ML_MODEL_PRESETS.map((preset) => (
                <option key={preset.value} value={preset.value}>
                  {preset.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="ml_universe">股票池</Label>
            <select
              id="ml_universe"
              value={String(formData.parameters.universe || 'active_us')}
              onChange={(e) => handleParameterChange('universe', e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2"
            >
              {ML_UNIVERSE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="ml_horizon">預測週期</Label>
            <select
              id="ml_horizon"
              value={String(formData.parameters.horizon || '1d')}
              onChange={(e) => handleParameterChange('horizon', e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2"
            >
              {ML_HORIZON_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>
    );
  };

  const renderParameterInput = (field: StrategyParameterSchema) => {
    const value = formData.parameters[field.key];

    if (field.type === 'boolean') {
      return (
        <div key={field.key} className="rounded-md border border-gray-200 px-3 py-2">
          <div className="flex items-center gap-2">
            <input
              id={field.key}
              type="checkbox"
              checked={Boolean(value)}
              onChange={(e) => handleParameterChange(field.key, e.target.checked)}
              className="rounded border-gray-300"
            />
            <Label htmlFor={field.key} className="font-normal cursor-pointer">
              {field.label}
            </Label>
          </div>
          {field.description && (
            <p className="mt-1 text-xs text-gray-500">{field.description}</p>
          )}
        </div>
      );
    }

    return (
      <div key={field.key}>
        <Label htmlFor={field.key}>{field.label}</Label>
        <Input
          id={field.key}
          type={field.type === 'number' ? 'number' : 'text'}
          value={typeof value === 'number' || typeof value === 'string' ? value : ''}
          min={field.min}
          max={field.max}
          step={field.step}
          onChange={(e) => {
            const newValue = field.type === 'number'
              ? Number(e.target.value)
              : e.target.value;
            handleParameterChange(field.key, newValue);
          }}
          className="mt-1"
        />
        {field.description && (
          <p className="mt-1 text-xs text-gray-500">{field.description}</p>
        )}
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold">
            {subscription ? '編輯訂閱' : '新增策略訂閱'}
          </h2>
          <Button
            type="button"
            variant="ghost"
            size="iconSm"
            onClick={onClose}
            aria-label="關閉"
          >
            <X className="h-6 w-6" />
          </Button>
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
              {renderMlPredictionPreset()}
              {parameterFields.map(renderParameterInput)}
            </div>
          )}

          {/* 監控配置 */}
          <div className="space-y-4">
            <Label className="text-base font-semibold">監控範圍</Label>

            <div className="rounded-lg border border-gray-200 p-4">
              <div className="mb-3 text-sm font-medium text-gray-900">觀察清單</div>
              <div className="grid gap-2 sm:grid-cols-2">
                <label className="flex cursor-pointer items-center gap-2 rounded-md border border-gray-200 px-3 py-2">
                  <input
                    type="radio"
                    name="list_scope"
                    checked={formData.monitor_all_lists}
                    onChange={() => handleMonitorAllListsChange(true)}
                    className="border-gray-300"
                  />
                  <span className="text-sm">所有觀察清單</span>
                </label>
                <label className="flex cursor-pointer items-center gap-2 rounded-md border border-gray-200 px-3 py-2">
                  <input
                    type="radio"
                    name="list_scope"
                    checked={!formData.monitor_all_lists}
                    onChange={() => handleMonitorAllListsChange(false)}
                    className="border-gray-300"
                  />
                  <span className="text-sm">指定觀察清單</span>
                </label>
              </div>

              {!formData.monitor_all_lists && (
                <div className="mt-3 space-y-2">
                  {stockLists.length === 0 ? (
                    <div className="rounded-md bg-gray-50 px-3 py-3 text-sm text-gray-500">
                      尚無可選清單
                    </div>
                  ) : (
                    stockLists.map((list) => (
                      <label
                        key={list.id}
                        className="flex cursor-pointer items-center justify-between gap-3 rounded-md bg-gray-50 px-3 py-2"
                      >
                        <span className="min-w-0">
                          <span className="block truncate text-sm font-medium text-gray-900">
                            {list.name}
                          </span>
                          <span className="text-xs text-gray-500">{list.stocks_count} 檔</span>
                        </span>
                        <input
                          type="checkbox"
                          checked={formData.selected_list_ids.includes(list.id)}
                          onChange={() => toggleSelectedList(list.id)}
                          className="rounded border-gray-300"
                        />
                      </label>
                    ))
                  )}
                </div>
              )}
            </div>

            <div className="flex items-center space-x-2 rounded-lg border border-gray-200 px-4 py-3">
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
