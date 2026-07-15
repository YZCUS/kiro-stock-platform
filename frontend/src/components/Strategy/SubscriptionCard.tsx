/**
 * 訂閱卡片組件
 */
"use client";

import React from "react";
import {
  StrategyInfo,
  StrategyParameterValue,
  Subscription,
} from "@/types/strategy";
import { Button } from "@/components/ui/button";
import {
  Activity,
  Briefcase,
  Database,
  FolderKanban,
  Power,
  PowerOff,
  Settings,
  Trash2,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface SubscriptionCardProps {
  subscription: Subscription;
  strategies?: StrategyInfo[];
  onEdit: (subscription: Subscription) => void;
  onDelete: (subscriptionId: number) => void;
  onToggle: (subscriptionId: number) => void;
}

const PARAMETER_LABELS: Record<string, string> = {
  model_name: "模型",
  feature_set: "特徵集",
  universe: "股票池",
  horizon: "週期",
  min_score: "最低分數",
};

const PARAMETER_VALUES: Record<string, string> = {
  active_us: "美股活躍",
  "1d": "1 日",
};

export default function SubscriptionCard({
  subscription,
  strategies = [],
  onEdit,
  onDelete,
  onToggle,
}: SubscriptionCardProps) {
  const strategyInfo = strategies.find(
    (strategy) => strategy.type === subscription.strategy_type,
  );
  const strategyName =
    subscription.strategy_name ||
    strategyInfo?.name ||
    subscription.strategy_type;
  const parameterLabels = new Map(
    (strategyInfo?.parameter_schema || []).map((field) => [
      field.key,
      field.label,
    ]),
  );
  const formatParameterValue = (value: StrategyParameterValue) => {
    if (typeof value === "boolean") return value ? "是" : "否";
    return PARAMETER_VALUES[String(value)] || String(value);
  };
  const getParameterLabel = (key: string) =>
    parameterLabels.get(key) || PARAMETER_LABELS[key] || key;

  const parameterEntries = Object.entries(subscription.parameters || {}).filter(
    ([, value]) => value !== null && value !== undefined && value !== "",
  );
  const visibleParameters = parameterEntries.slice(0, 3);
  const hiddenParameterCount = Math.max(
    parameterEntries.length - visibleParameters.length,
    0,
  );
  const stockLists = subscription.stock_lists || [];
  const visibleStockLists = stockLists.slice(0, 2);
  const hiddenStockListCount = Math.max(
    stockLists.length - visibleStockLists.length,
    0,
  );

  return (
    <article
      className={cn(
        "grid gap-3 px-4 py-3 transition-colors lg:grid-cols-[minmax(190px,1.2fr)_minmax(220px,1.4fr)_minmax(260px,1.5fr)_minmax(140px,auto)] lg:items-center",
        subscription.is_active
          ? "bg-white hover:bg-gray-50"
          : "bg-gray-50 text-gray-500",
      )}
    >
      <div className="min-w-0">
        <div className="flex min-w-0 items-center gap-2">
          <span
            className={cn(
              "inline-flex h-2.5 w-2.5 shrink-0 rounded-full",
              subscription.is_active ? "bg-emerald-500" : "bg-gray-300",
            )}
            aria-hidden="true"
          />
          <h3 className="min-w-0 truncate text-sm font-semibold text-gray-900">
            {strategyName}
          </h3>
        </div>
        <div className="mt-1 flex min-w-0 items-center gap-2 text-xs text-gray-500">
          <span className="truncate">{subscription.strategy_type}</span>
          <span className="shrink-0 text-gray-300">|</span>
          <span className="shrink-0">
            {subscription.is_active ? "啟用中" : "已停用"}
          </span>
        </div>
      </div>

      <div className="min-w-0">
        <div className="mb-1 text-xs font-medium text-gray-500 lg:hidden">
          參數
        </div>
        {visibleParameters.length === 0 ? (
          <span className="text-sm text-gray-400">使用預設值</span>
        ) : (
          <div className="flex min-w-0 items-center gap-1.5 overflow-hidden">
            {visibleParameters.map(([key, value]) => (
              <span
                key={key}
                className="min-w-0 truncate rounded bg-gray-100 px-2 py-1 text-xs text-gray-700"
                title={`${getParameterLabel(key)}: ${formatParameterValue(value)}`}
              >
                {getParameterLabel(key)}: {formatParameterValue(value)}
              </span>
            ))}
            {hiddenParameterCount > 0 && (
              <span className="shrink-0 rounded bg-gray-100 px-2 py-1 text-xs text-gray-500">
                +{hiddenParameterCount}
              </span>
            )}
          </div>
        )}
      </div>

      <div className="min-w-0">
        <div className="mb-1 text-xs font-medium text-gray-500 lg:hidden">
          監控範圍
        </div>
        <div className="flex min-w-0 items-center gap-1.5 overflow-hidden text-xs">
          {subscription.monitor_all_stocks ? (
            <span className="inline-flex min-w-0 items-center gap-1 rounded bg-emerald-50 px-2 py-1 font-medium text-emerald-700">
              <Database className="h-3.5 w-3.5 shrink-0" />
              <span className="truncate">DB 全部股票</span>
            </span>
          ) : (
            <>
              {subscription.monitor_all_lists && (
                <span className="inline-flex min-w-0 items-center gap-1 rounded bg-purple-50 px-2 py-1 text-purple-700">
                  <FolderKanban className="h-3.5 w-3.5 shrink-0" />
                  <span className="truncate">所有清單</span>
                </span>
              )}
              {visibleStockLists.map((list) => (
                <span
                  key={list.id}
                  className="inline-flex min-w-0 items-center gap-1 rounded bg-cyan-50 px-2 py-1 text-cyan-700"
                  title={`${list.name}${list.stocks_count ? ` (${list.stocks_count})` : ""}`}
                >
                  <FolderKanban className="h-3.5 w-3.5 shrink-0" />
                  <span className="truncate">{list.name}</span>
                </span>
              ))}
              {hiddenStockListCount > 0 && (
                <span className="shrink-0 rounded bg-cyan-50 px-2 py-1 text-cyan-700">
                  +{hiddenStockListCount} 清單
                </span>
              )}
              {subscription.monitor_portfolio && (
                <span className="inline-flex shrink-0 items-center gap-1 rounded bg-indigo-50 px-2 py-1 text-indigo-700">
                  <Briefcase className="h-3.5 w-3.5" />
                  持倉
                </span>
              )}
              {!subscription.monitor_all_lists &&
                !subscription.monitor_portfolio &&
                stockLists.length === 0 && (
                  <span className="inline-flex shrink-0 items-center gap-1 rounded bg-amber-50 px-2 py-1 text-amber-700">
                    <Activity className="h-3.5 w-3.5" />
                    未設定
                  </span>
                )}
            </>
          )}
        </div>
      </div>

      <div className="flex items-center justify-end gap-1">
        <Button
          variant="ghost"
          size="iconSm"
          onClick={() => onToggle(subscription.id)}
          title={subscription.is_active ? "停用訂閱" : "啟用訂閱"}
          aria-label={`${subscription.is_active ? "停用" : "啟用"} ${strategyName} 訂閱`}
        >
          {subscription.is_active ? (
            <PowerOff className="h-4 w-4 text-orange-600" />
          ) : (
            <Power className="h-4 w-4 text-green-600" />
          )}
        </Button>
        <Button
          variant="ghost"
          size="iconSm"
          onClick={() => onEdit(subscription)}
          title="編輯訂閱"
          aria-label={`編輯 ${strategyName} 訂閱`}
        >
          <Settings className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="iconSm"
          onClick={() => onDelete(subscription.id)}
          title="刪除訂閱"
          aria-label={`刪除 ${strategyName} 訂閱`}
        >
          <Trash2 className="h-4 w-4 text-red-600" />
        </Button>
      </div>
    </article>
  );
}
