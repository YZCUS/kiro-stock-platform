/**
 * 信號卡片組件
 */
'use client';

import React from 'react';
import { TradingSignal } from '@/types/strategy';
import { Button } from '@/components/ui/button';
import { TrendingUp, TrendingDown, Minus, Check, X } from 'lucide-react';

interface SignalCardProps {
  signal: TradingSignal;
  onUpdateStatus: (signalId: number, status: 'triggered' | 'cancelled') => void;
}

export default function SignalCard({ signal, onUpdateStatus }: SignalCardProps) {
  // 方向圖標
  const DirectionIcon = signal.direction === 'LONG' ? TrendingUp : signal.direction === 'SHORT' ? TrendingDown : Minus;
  const directionColor = signal.direction === 'LONG' ? 'text-green-600' : signal.direction === 'SHORT' ? 'text-red-600' : 'text-gray-600';
  const directionBg = signal.direction === 'LONG' ? 'bg-green-50' : signal.direction === 'SHORT' ? 'bg-red-50' : 'bg-gray-50';

  // 信心度顏色
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 80) return 'bg-green-500';
    if (confidence >= 60) return 'bg-yellow-500';
    return 'bg-orange-500';
  };

  // 狀態樣式
  const getStatusStyle = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-blue-100 text-blue-700';
      case 'triggered':
        return 'bg-green-100 text-green-700';
      case 'expired':
        return 'bg-gray-100 text-gray-600';
      case 'cancelled':
        return 'bg-red-100 text-red-700';
      default:
        return 'bg-gray-100 text-gray-600';
    }
  };

  const statusText = {
    active: '活躍',
    triggered: '已觸發',
    expired: '已過期',
    cancelled: '已取消',
  };

  return (
    <div className="border rounded-lg p-4 bg-white hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-start gap-3">
          {/* 方向圖標 */}
          <div className={`p-2 rounded-lg ${directionBg}`}>
            <DirectionIcon className={`h-6 w-6 ${directionColor}`} />
          </div>

          {/* 股票資訊 */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              {signal.stock_symbol}
            </h3>
            <p className="text-sm text-gray-600">{signal.stock_name}</p>
            <p className="text-xs text-gray-500 mt-1">{signal.strategy_name}</p>
          </div>
        </div>

        {/* 狀態標籤 */}
        <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusStyle(signal.status)}`}>
          {statusText[signal.status as keyof typeof statusText]}
        </span>
      </div>

      {/* 信心度 */}
      <div className="mb-3">
        <div className="flex items-center justify-between text-sm mb-1">
          <span className="text-gray-600">信心度</span>
          <span className="font-semibold">{signal.confidence.toFixed(1)}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className={`h-2 rounded-full ${getConfidenceColor(signal.confidence)}`}
            style={{ width: `${signal.confidence}%` }}
          />
        </div>
      </div>

      {/* 價格資訊 */}
      <div className="grid grid-cols-2 gap-4 mb-3 text-sm">
        <div>
          <p className="text-gray-600">進場區間</p>
          <p className="font-semibold">
            ${signal.entry_min.toFixed(2)} - ${signal.entry_max.toFixed(2)}
          </p>
        </div>
        <div>
          <p className="text-gray-600">停損</p>
          <p className="font-semibold text-red-600">
            ${signal.stop_loss.toFixed(2)}
          </p>
        </div>
      </div>

      {/* 止盈目標 */}
      <div className="mb-3">
        <p className="text-sm text-gray-600 mb-1">止盈目標</p>
        <div className="flex gap-2">
          {signal.take_profit_targets.map((target, index) => (
            <span key={index} className="px-2 py-1 text-xs rounded bg-green-50 text-green-700 font-medium">
              TP{index + 1}: ${target.toFixed(2)}
            </span>
          ))}
        </div>
      </div>

      {/* 原因 */}
      {signal.reason && (
        <div className="mb-3 p-2 bg-gray-50 rounded text-sm text-gray-700">
          <p className="font-medium text-gray-900 mb-1">信號原因:</p>
          <p>{signal.reason}</p>
        </div>
      )}

      {/* 日期資訊 */}
      <div className="flex items-center justify-between text-xs text-gray-500 mb-3">
        <span>信號日期: {new Date(signal.signal_date).toLocaleDateString('zh-TW')}</span>
        <span>有效期限: {new Date(signal.valid_until).toLocaleDateString('zh-TW')}</span>
      </div>

      {/* 操作按鈕 */}
      {signal.status === 'active' && (
        <div className="flex gap-2 pt-3 border-t">
          <Button
            size="sm"
            variant="outline"
            className="flex-1 text-green-600 hover:text-green-700 hover:bg-green-50"
            onClick={() => onUpdateStatus(signal.id, 'triggered')}
          >
            <Check className="h-4 w-4 mr-1" />
            標記已觸發
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="flex-1 text-red-600 hover:text-red-700 hover:bg-red-50"
            onClick={() => onUpdateStatus(signal.id, 'cancelled')}
          >
            <X className="h-4 w-4 mr-1" />
            忽略信號
          </Button>
        </div>
      )}
    </div>
  );
}
