/**
 * 即時交易信號組件
 */
'use client';

import React, { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { useSystemNotifications } from '../../hooks/useWebSocket';
import { useMarketStream } from '../../hooks/useMarketStream';
import { getSignals } from '@/services/strategyApi';
import type { TradingSignal } from '@/types/strategy';

interface RealtimeSignalsProps {
  stockId?: number | null;
  symbol?: string;
  market?: string;
  enabled?: boolean;
}

const RealtimeSignals: React.FC<RealtimeSignalsProps> = ({
  stockId,
  symbol,
  market,
  enabled = true,
}) => {
  const { notifications, clearNotification } = useSystemNotifications();
  const { signal: intradaySignal, status: streamStatus } = useMarketStream(
    market,
    symbol,
    enabled && Boolean(market && symbol)
  );
  const [signals, setSignals] = useState<TradingSignal[]>([]);
  const [intradaySignals, setIntradaySignals] = useState<TradingSignal[]>([]);
  const [loading, setLoading] = useState(false);

  // 格式化時間
  const formatTime = (dateString: string | Date | null | undefined) => {
    if (!dateString) return '-';
    const date = typeof dateString === 'string' ? new Date(dateString) : dateString;
    return date.toLocaleTimeString('zh-TW', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const formatDate = (dateString?: string | null) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('zh-TW');
  };

  const formatPrice = (value?: number | null) =>
    typeof value === 'number' && Number.isFinite(value)
      ? `$${value.toFixed(2)}`
      : '-';

  const formatConfidence = (value: number) => {
    const percent = value <= 1 ? value * 100 : value;
    return `${percent.toFixed(1)}%`;
  };

  // 獲取方向顏色
  const getDirectionColor = (direction: TradingSignal['direction']) => {
    switch (direction) {
      case 'LONG':
        return 'text-green-700 bg-green-50 border-green-200';
      case 'SHORT':
        return 'text-red-700 bg-red-50 border-red-200';
      default:
        return 'text-gray-700 bg-gray-50 border-gray-200';
    }
  };

  const getDirectionText = (direction: TradingSignal['direction']) => {
    switch (direction) {
      case 'LONG':
        return '看多';
      case 'SHORT':
        return '看空';
      default:
        return '中性';
    }
  };

  useEffect(() => {
    let cancelled = false;

    if (!enabled || !stockId) {
      setSignals([]);
      return;
    }

    setLoading(true);
    getSignals({
      status: 'active',
      stock_id: stockId,
      sort_by: 'signal_date',
      sort_order: 'desc',
      limit: 5,
    })
      .then((response) => {
        if (!cancelled) setSignals(response.signals);
      })
      .catch(() => {
        if (!cancelled) setSignals([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [enabled, stockId]);

  useEffect(() => {
    if (!intradaySignal || !stockId) return;
    setIntradaySignals((current) => {
      if (current.some((signal) => signal.id === intradaySignal.id)) {
        return current;
      }
      return [intradaySignal, ...current].slice(0, 5);
    });
  }, [intradaySignal, stockId]);

  return (
    <div className="space-y-6">
      {/* 系統通知 */}
      {notifications.length > 0 && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-blue-900">系統通知</h3>
            <button
              onClick={() => notifications.forEach(n => clearNotification(n.id))}
              className="text-xs text-blue-600 hover:text-blue-800"
            >
              清除全部
            </button>
          </div>
          <div className="space-y-2">
            {notifications.slice(0, 3).map((notification) => (
              <div
                key={notification.id}
                className="flex items-center justify-between bg-white rounded p-2"
              >
                <div className="flex-1">
                  <p className="text-sm text-blue-900">{notification.message}</p>
                  <p className="text-xs text-blue-600">
                    {formatTime(notification.timestamp)}
                  </p>
                </div>
                <button
                  onClick={() => clearNotification(notification.id)}
                  className="ml-2 inline-flex h-7 w-7 items-center justify-center rounded-md text-blue-400 hover:bg-blue-50 hover:text-blue-600"
                  aria-label="清除通知"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 日內即時信號 */}
      <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
        <div className="flex items-start justify-between gap-3 border-b border-gray-200 px-4 py-3">
          <div>
            <h3 className="text-sm font-semibold text-gray-900">日內即時信號</h3>
            <p className="mt-1 text-xs text-gray-500">
              由 5m K 即時串流產生，偏向短線觀察
            </p>
          </div>
          <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
            {streamStatus === 'connected' ? '串流中' : '等待'}
          </span>
        </div>

        <div className="p-4">
          {!enabled ? (
            <div className="py-5 text-center text-gray-500">
              登入後顯示日內信號
            </div>
          ) : !stockId ? (
            <div className="py-5 text-center text-gray-500">
              選擇股票後顯示日內信號
            </div>
          ) : intradaySignals.length === 0 ? (
            <div className="py-5 text-center text-gray-500">
              等待 5m 即時信號...
            </div>
          ) : (
            <div className="space-y-2">
              {intradaySignals.map((signal) => (
                <SignalCard
                  key={signal.id}
                  signal={signal}
                  getDirectionColor={getDirectionColor}
                  getDirectionText={getDirectionText}
                  formatConfidence={formatConfidence}
                  formatDate={formatDate}
                  formatPrice={formatPrice}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 策略交易信號 */}
      <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
        <div className="px-4 py-3 border-b border-gray-200">
          <h3 className="text-sm font-semibold text-gray-900">策略交易信號</h3>
          <p className="mt-1 text-xs text-gray-500">
            {symbol ? `${symbol} 的活躍策略信號` : '隨訂閱策略與排程更新'}
          </p>
        </div>

        <div className="p-4">
          {!enabled ? (
            <div className="py-6 text-center text-gray-500">
              登入後顯示策略信號
            </div>
          ) : !stockId ? (
            <div className="text-center py-6">
              <div className="text-gray-500">選擇股票後顯示策略信號</div>
            </div>
          ) : loading ? (
            <div className="py-6 text-center text-gray-500">
              載入策略信號...
            </div>
          ) : signals.length === 0 ? (
            <div className="py-6 text-center text-gray-500">
              目前沒有活躍策略信號
            </div>
          ) : (
            <div className="space-y-2">
              {signals.map((signal) => (
                <SignalCard
                  key={signal.id}
                  signal={signal}
                  getDirectionColor={getDirectionColor}
                  getDirectionText={getDirectionText}
                  formatConfidence={formatConfidence}
                  formatDate={formatDate}
                  formatPrice={formatPrice}
                />
              ))}
            </div>
          )}

          {enabled && stockId && signals.length > 0 && (
            <p className="mt-3 text-xs text-gray-500">
              信號由策略訂閱、手動刷新或排程產生，不是每筆報價 tick 即時計算。
            </p>
          )}
        </div>
      </div>

      {/* 添加一些 CSS 動畫 */}
      <style jsx>{`
        @keyframes fadeInDown {
          from {
            opacity: 0;
            transform: translate3d(0, -20px, 0);
          }
          to {
            opacity: 1;
            transform: translate3d(0, 0, 0);
          }
        }
      `}</style>
    </div>
  );
};

interface SignalCardProps {
  signal: TradingSignal;
  getDirectionColor: (direction: TradingSignal['direction']) => string;
  getDirectionText: (direction: TradingSignal['direction']) => string;
  formatConfidence: (value: number) => string;
  formatDate: (dateString?: string | null) => string;
  formatPrice: (value?: number | null) => string;
}

const SignalCard: React.FC<SignalCardProps> = ({
  signal,
  getDirectionColor,
  getDirectionText,
  formatConfidence,
  formatDate,
  formatPrice,
}) => (
  <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
    <div className="flex items-start justify-between gap-3">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={`rounded-md border px-2 py-0.5 text-xs font-medium ${getDirectionColor(signal.direction)}`}
          >
            {getDirectionText(signal.direction)}
          </span>
          {signal.signal_horizon && (
            <span className="rounded-md bg-white px-2 py-0.5 text-xs font-medium text-gray-600">
              {signal.signal_horizon}
            </span>
          )}
        </div>
        <p className="mt-2 truncate text-sm font-semibold text-gray-950">
          {signal.strategy_name || signal.strategy_type}
        </p>
        <p className="mt-1 text-xs text-gray-500">
          {formatDate(signal.signal_date)} 至 {formatDate(signal.valid_until)}
        </p>
      </div>
      <div className="shrink-0 text-right">
        <p className="text-xs text-gray-500">強度</p>
        <p className="font-semibold tabular-nums text-gray-950">
          {formatConfidence(signal.confidence)}
        </p>
      </div>
    </div>

    <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
      <div>
        <p className="text-gray-500">進場</p>
        <p className="font-medium text-gray-900">
          {formatPrice(signal.entry_zone?.min ?? signal.entry_min)}
        </p>
      </div>
      <div>
        <p className="text-gray-500">停損</p>
        <p className="font-medium text-red-600">
          {formatPrice(signal.stop_loss)}
        </p>
      </div>
    </div>

    {signal.reason && (
      <p className="mt-3 border-t border-gray-200 pt-2 text-xs leading-5 text-gray-600">
        {signal.reason}
      </p>
    )}
  </div>
);

export default RealtimeSignals;
