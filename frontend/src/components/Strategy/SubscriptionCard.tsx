/**
 * 訂閱卡片組件
 */
'use client';

import React from 'react';
import { Subscription } from '@/types/strategy';
import { Button } from '@/components/ui/button';
import { Settings, Trash2, Power, PowerOff } from 'lucide-react';

interface SubscriptionCardProps {
  subscription: Subscription;
  onEdit: (subscription: Subscription) => void;
  onDelete: (subscriptionId: number) => void;
  onToggle: (subscriptionId: number) => void;
}

export default function SubscriptionCard({
  subscription,
  onEdit,
  onDelete,
  onToggle,
}: SubscriptionCardProps) {
  return (
    <div className={`border rounded-lg p-4 ${subscription.is_active ? 'bg-white' : 'bg-gray-50'}`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            {subscription.strategy_name}
            {subscription.is_active ? (
              <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-green-100 text-green-700">
                啟用中
              </span>
            ) : (
              <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-gray-100 text-gray-600">
                已停用
              </span>
            )}
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            策略類型: {subscription.strategy_type}
          </p>
        </div>

        <div className="flex gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onToggle(subscription.id)}
            title={subscription.is_active ? '停用訂閱' : '啟用訂閱'}
          >
            {subscription.is_active ? (
              <PowerOff className="h-4 w-4 text-orange-600" />
            ) : (
              <Power className="h-4 w-4 text-green-600" />
            )}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onEdit(subscription)}
            title="編輯訂閱"
          >
            <Settings className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDelete(subscription.id)}
            title="刪除訂閱"
          >
            <Trash2 className="h-4 w-4 text-red-600" />
          </Button>
        </div>
      </div>

      {/* 策略參數 */}
      {subscription.parameters && Object.keys(subscription.parameters).length > 0 && (
        <div className="mb-3">
          <p className="text-sm font-medium text-gray-700 mb-1">策略參數:</p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(subscription.parameters).map(([key, value]) => (
              <span key={key} className="px-2 py-1 text-xs rounded bg-blue-50 text-blue-700">
                {key}: {String(value)}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* 監控配置 */}
      <div className="border-t pt-3">
        <p className="text-sm font-medium text-gray-700 mb-2">監控範圍:</p>
        <div className="flex flex-wrap gap-2 text-xs">
          {subscription.monitor_all_lists && (
            <span className="px-2 py-1 rounded bg-purple-50 text-purple-700">
              所有清單
            </span>
          )}
          {subscription.monitor_portfolio && (
            <span className="px-2 py-1 rounded bg-indigo-50 text-indigo-700">
              持倉
            </span>
          )}
          {subscription.stock_lists && subscription.stock_lists.length > 0 && (
            <>
              {subscription.stock_lists.map((list) => (
                <span key={list.id} className="px-2 py-1 rounded bg-cyan-50 text-cyan-700">
                  {list.name} ({list.stocks_count})
                </span>
              ))}
            </>
          )}
        </div>
      </div>

      {/* 建立時間 */}
      <div className="mt-3 text-xs text-gray-400">
        建立於 {new Date(subscription.created_at).toLocaleString('zh-TW')}
      </div>
    </div>
  );
}
