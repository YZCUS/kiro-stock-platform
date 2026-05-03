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
import { getQlibModels, type QlibModelOption } from '@/services/qlibApi';
import { cn } from '@/lib/utils';

interface SubscriptionModalProps {
  isOpen: boolean;
  onClose: () => void;
  strategies: StrategyInfo[];
  stockLists?: StockList[];
  subscription?: Subscription | null;
  onSubmit: (
    data: SubscriptionCreateRequest | SubscriptionUpdateRequest,
  ) => Promise<void>;
}

const ML_SYSTEM_FIELDS = new Set([
  'model_name',
  'feature_set',
  'universe',
  'horizon',
]);

const FALLBACK_ML_MODEL_OPTIONS: QlibModelOption[] = [
  {
    name: 'lightgbm_alpha158',
    label: 'LightGBM Alpha158',
    model_type: 'lightgbm',
    feature_set: 'alpha158',
    horizon: '1d',
    min_lookback_days: 60,
    description: '短中期 momentum 與波動率調整的樹模型配置。',
    portfolio_strategy: 'rank_percentile',
    status: 'bootstrap',
    config_uri: 'qlib://configs/lightgbm_alpha158.yaml',
  },
  {
    name: 'xgboost_alpha158',
    label: 'XGBoost Alpha158',
    model_type: 'xgboost',
    feature_set: 'alpha158',
    horizon: '1d',
    min_lookback_days: 60,
    description: '較重視多週期 momentum 與回撤懲罰的樹模型配置。',
    portfolio_strategy: 'rank_percentile',
    status: 'bootstrap',
    config_uri: 'qlib://configs/xgboost_alpha158.yaml',
  },
  {
    name: 'catboost_alpha158',
    label: 'CatBoost Alpha158',
    model_type: 'catboost',
    feature_set: 'alpha158',
    horizon: '1d',
    min_lookback_days: 60,
    description: '偏向穩定上漲天數與下行波動控制的樹模型配置。',
    portfolio_strategy: 'rank_percentile',
    status: 'bootstrap',
    config_uri: 'qlib://configs/catboost_alpha158.yaml',
  },
  {
    name: 'mlp_alpha360',
    label: 'MLP Alpha360',
    model_type: 'mlp',
    feature_set: 'alpha360',
    horizon: '1d',
    min_lookback_days: 120,
    description: '使用較長視窗特徵，偏向非線性 momentum/volatility 組合。',
    portfolio_strategy: 'rank_percentile',
    status: 'bootstrap',
    config_uri: 'qlib://configs/mlp_alpha360.yaml',
  },
  {
    name: 'lstm_alpha360',
    label: 'LSTM Alpha360',
    model_type: 'lstm',
    feature_set: 'alpha360',
    horizon: '1d',
    min_lookback_days: 180,
    description: '偏重近期序列趨勢延續性的長視窗模型配置。',
    portfolio_strategy: 'rank_percentile',
    status: 'bootstrap',
    config_uri: 'qlib://configs/lstm_alpha360.yaml',
  },
];

const ML_UNIVERSE_OPTIONS = [{ value: 'active_us', label: '美股活躍股票池' }];

const ML_HORIZON_OPTIONS = [{ value: '1d', label: '1 日預測' }];

export default function SubscriptionModal({
  isOpen,
  onClose,
  strategies,
  stockLists = [],
  subscription,
  onSubmit,
}: SubscriptionModalProps) {
  const [formData, setFormData] = useState({
    strategy_type: '',
    parameters: {} as StrategyParameterMap,
    monitor_all_lists: true,
    monitor_portfolio: true,
    monitor_all_stocks: false,
    selected_list_ids: [] as number[],
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedStrategy, setSelectedStrategy] = useState<StrategyInfo | null>(
    null,
  );
  const [mlModelOptions, setMlModelOptions] = useState<QlibModelOption[]>(
    FALLBACK_ML_MODEL_OPTIONS,
  );
  const [mlModelLoading, setMlModelLoading] = useState(false);
  const [mlModelLoadError, setMlModelLoadError] = useState<string | null>(null);

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
          monitor_all_stocks: subscription.monitor_all_stocks || false,
          selected_list_ids: subscription.selected_list_ids || [],
        });
        const strategy = strategies.find(
          (s) => s.type === subscription.strategy_type,
        );
        setSelectedStrategy(strategy || null);
      } else {
        // 新增模式
        setFormData({
          strategy_type: '',
          parameters: {},
          monitor_all_lists: true,
          monitor_portfolio: true,
          monitor_all_stocks: false,
          selected_list_ids: [],
        });
        setSelectedStrategy(null);
      }
    }
  }, [isOpen, subscription, strategies]);

  useEffect(() => {
    if (!isOpen) return;

    let cancelled = false;
    setMlModelLoading(true);
    setMlModelLoadError(null);

    getQlibModels()
      .then((response) => {
        if (cancelled) return;
        if (response.models.length > 0) {
          setMlModelOptions(response.models);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setMlModelLoadError('模型清單暫時無法更新，已使用本地預設。');
        }
      })
      .finally(() => {
        if (!cancelled) {
          setMlModelLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const handleStrategyChange = (strategyType: string) => {
    const strategy = strategies.find((s) => s.type === strategyType);
    setSelectedStrategy(strategy || null);
    setFormData({
      ...formData,
      strategy_type: strategyType,
      parameters: strategy?.default_params || {},
    });
  };

  const handleParameterChange = (
    key: string,
    value: StrategyParameterValue,
  ) => {
    setFormData({
      ...formData,
      parameters: {
        ...formData.parameters,
        [key]: value,
      },
    });
  };

  const handleMlPresetChange = (modelName: string) => {
    const preset = mlModelOptions.find((item) => item.name === modelName);
    setFormData({
      ...formData,
      parameters: {
        ...formData.parameters,
        model_name: modelName,
        feature_set:
          preset?.feature_set || formData.parameters.feature_set || 'alpha158',
        horizon: preset?.horizon || formData.parameters.horizon || '1d',
      },
    });
  };

  const handleMonitorAllListsChange = (monitorAllLists: boolean) => {
    setFormData({
      ...formData,
      monitor_all_lists: monitorAllLists,
      monitor_all_stocks: false,
      selected_list_ids: monitorAllLists ? [] : formData.selected_list_ids,
    });
  };

  const handleMonitorAllStocksChange = (monitorAllStocks: boolean) => {
    setFormData({
      ...formData,
      monitor_all_stocks: monitorAllStocks,
      monitor_all_lists: monitorAllStocks ? false : formData.monitor_all_lists,
      monitor_portfolio: monitorAllStocks ? false : formData.monitor_portfolio,
      selected_list_ids: monitorAllStocks ? [] : formData.selected_list_ids,
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
      monitor_all_stocks: false,
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
      !formData.monitor_all_stocks &&
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
    value: StrategyParameterValue | undefined,
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

    const selectedModelName = String(
      formData.parameters.model_name || 'lightgbm_alpha158',
    );
    const selectedModel = mlModelOptions.find(
      (option) => option.name === selectedModelName,
    );
    const usableModelOptions = mlModelOptions.filter(
      (option) => option.status === 'cpu_trainable',
    );
    const baseModelOptions =
      usableModelOptions.length > 0 ? usableModelOptions : mlModelOptions;
    const selectedModelInOptions = baseModelOptions.some(
      (option) => option.name === selectedModelName,
    );
    const modelOptions = selectedModelInOptions
      ? baseModelOptions
      : [
          selectedModel || {
            name: selectedModelName,
            label: selectedModelName,
            model_type: 'unknown',
            feature_set: String(formData.parameters.feature_set || 'alpha158'),
            horizon: String(formData.parameters.horizon || '1d'),
            min_lookback_days: 60,
            description: '目前訂閱使用的模型不在可用清單中。',
            portfolio_strategy: 'rank_percentile',
            status: 'unknown',
            config_uri: null,
          },
          ...baseModelOptions,
        ];
    const modelDescription = selectedModel || modelOptions[0];

    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
        <div className="mb-3">
          <div className="text-sm font-semibold text-gray-900">模型設定</div>
          {mlModelLoadError && (
            <p className="mt-1 text-xs leading-5 text-amber-700">
              {mlModelLoadError}
            </p>
          )}
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <Label htmlFor="ml_model_preset">模型</Label>
            <select
              id="ml_model_preset"
              value={selectedModelName}
              onChange={(e) => handleMlPresetChange(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2"
            >
              {modelOptions.map((preset) => (
                <option key={preset.name} value={preset.name}>
                  {preset.label}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-gray-500">
              {mlModelLoading
                ? '更新模型清單中'
                : `${modelDescription.feature_set} · ${modelDescription.min_lookback_days} 日資料`}
            </p>
          </div>
          <div>
            <Label htmlFor="ml_universe">股票池</Label>
            <select
              id="ml_universe"
              value={String(formData.parameters.universe || 'active_us')}
              onChange={(e) =>
                handleParameterChange('universe', e.target.value)
              }
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
        <p className="mt-3 text-xs leading-5 text-gray-500">
          {modelDescription.description}
        </p>
      </div>
    );
  };

  const renderParameterInput = (field: StrategyParameterSchema) => {
    const value = formData.parameters[field.key];

    if (field.type === 'boolean') {
      return (
        <div
          key={field.key}
          className="rounded-md border border-gray-200 px-3 py-2"
        >
          <div className="flex items-center gap-2">
            <input
              id={field.key}
              type="checkbox"
              checked={Boolean(value)}
              onChange={(e) =>
                handleParameterChange(field.key, e.target.checked)
              }
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
          value={
            typeof value === 'number' || typeof value === 'string' ? value : ''
          }
          min={field.min}
          max={field.max}
          step={field.step}
          onChange={(e) => {
            const newValue =
              field.type === 'number' ? Number(e.target.value) : e.target.value;
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

            <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-gray-200 px-4 py-3">
              <input
                type="checkbox"
                checked={formData.monitor_all_stocks}
                onChange={(e) => handleMonitorAllStocksChange(e.target.checked)}
                className="mt-1 rounded border-gray-300"
              />
              <span className="min-w-0">
                <span className="block text-sm font-medium text-gray-900">
                  監控資料庫全部股票
                </span>
                <span className="block text-xs text-gray-500">
                  適合 Qlib 預推論或全市場掃描；會使用所有啟用中的股票。
                </span>
              </span>
            </label>

            <div className="rounded-lg border border-gray-200 p-4">
              <div className="mb-3 text-sm font-medium text-gray-900">
                觀察清單
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                <label
                  className={cn(
                    'flex items-center gap-2 rounded-md border border-gray-200 px-3 py-2',
                    formData.monitor_all_stocks
                      ? 'cursor-not-allowed bg-gray-50 text-gray-400'
                      : 'cursor-pointer',
                  )}
                >
                  <input
                    type="radio"
                    name="list_scope"
                    checked={formData.monitor_all_lists}
                    onChange={() => handleMonitorAllListsChange(true)}
                    disabled={formData.monitor_all_stocks}
                    className="border-gray-300"
                  />
                  <span className="text-sm">所有觀察清單</span>
                </label>
                <label
                  className={cn(
                    'flex items-center gap-2 rounded-md border border-gray-200 px-3 py-2',
                    formData.monitor_all_stocks
                      ? 'cursor-not-allowed bg-gray-50 text-gray-400'
                      : 'cursor-pointer',
                  )}
                >
                  <input
                    type="radio"
                    name="list_scope"
                    checked={!formData.monitor_all_lists}
                    onChange={() => handleMonitorAllListsChange(false)}
                    disabled={formData.monitor_all_stocks}
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
                        className={cn(
                          'flex items-center justify-between gap-3 rounded-md bg-gray-50 px-3 py-2',
                          formData.monitor_all_stocks
                            ? 'cursor-not-allowed text-gray-400'
                            : 'cursor-pointer',
                        )}
                      >
                        <span className="min-w-0">
                          <span className="block truncate text-sm font-medium text-gray-900">
                            {list.name}
                          </span>
                          <span className="text-xs text-gray-500">
                            {list.stocks_count} 檔
                          </span>
                        </span>
                        <input
                          type="checkbox"
                          checked={formData.selected_list_ids.includes(list.id)}
                          onChange={() => toggleSelectedList(list.id)}
                          disabled={formData.monitor_all_stocks}
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
                disabled={formData.monitor_all_stocks}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    monitor_all_stocks: false,
                    monitor_portfolio: e.target.checked,
                  })
                }
                className="rounded border-gray-300"
              />
              <Label
                htmlFor="monitor_portfolio"
                className={cn(
                  'font-normal',
                  formData.monitor_all_stocks
                    ? 'cursor-not-allowed text-gray-400'
                    : 'cursor-pointer',
                )}
              >
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
              {isSubmitting ? '處理中...' : subscription ? '更新' : '建立'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
