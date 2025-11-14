/**
 * 即時交易信號組件
 */
'use client';

import React from 'react';
import { useSignalUpdates, useSystemNotifications } from '../../hooks/useWebSocket';

const RealtimeSignals: React.FC = () => {
  const { signals } = useSignalUpdates();
  const { notifications, clearNotification } = useSystemNotifications();

  // 格式化時間
  const formatTime = (dateString: string | Date) => {
    const date = typeof dateString === 'string' ? new Date(dateString) : dateString;
    return date.toLocaleTimeString('zh-TW', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  // 獲取信號類型顏色
  const getSignalColor = (signalType: string) => {
    switch (signalType) {
      case 'BUY':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'SELL':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'GOLDEN_CROSS':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'DEATH_CROSS':
        return 'text-purple-600 bg-purple-50 border-purple-200';
      default:
        return 'text-blue-600 bg-blue-50 border-blue-200';
    }
  };

  // 獲取強度顏色
  const getStrengthColor = (strength: string) => {
    switch (strength) {
      case 'STRONG':
        return 'text-green-700';
      case 'MODERATE':
        return 'text-yellow-700';
      case 'WEAK':
        return 'text-gray-700';
      default:
        return 'text-gray-700';
    }
  };

  return (
    <div className="space-y-6">
      {/* 系統通知 */}
      {notifications.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
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
                  className="text-blue-400 hover:text-blue-600 ml-2"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 即時交易信號 */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-3 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium text-gray-900">即時交易信號</h3>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-sm text-green-600">即時更新</span>
            </div>
          </div>
        </div>

        <div className="p-4">
          {signals.length === 0 ? (
            <div className="text-center py-8">
              <div className="text-gray-500">
                等待即時信號...
              </div>
              <div className="text-xs text-gray-400 mt-2">
                系統會在檢測到新的交易信號時自動顯示
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {signals.slice(0, 10).map((signal, index) => (
                <div
                  key={`${signal.id}-${index}`}
                  className={`p-3 rounded-lg border ${getSignalColor(signal.signal_type)} transition-all duration-300`}
                  style={{
                    animation: index === 0 ? 'fadeInDown 0.5s ease-out' : undefined
                  }}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="font-bold text-gray-900">
                            {signal.symbol}
                          </span>
                          <span className={`px-2 py-1 text-xs font-medium rounded ${getSignalColor(signal.signal_type)}`}>
                            {signal.signal_type}
                          </span>
                          <span className={`text-xs font-medium ${getStrengthColor(signal.strength)}`}>
                            {signal.strength}
                          </span>
                        </div>
                        <div className="text-sm text-gray-600 mt-1">
                          {signal.description}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-medium text-gray-900">
                        ${signal.price.toFixed(2)}
                      </div>
                      <div className="text-xs text-gray-500">
                        信心度: {(signal.confidence * 100).toFixed(1)}%
                      </div>
                      <div className="text-xs text-gray-400">
                        {formatTime(signal.date)}
                      </div>
                    </div>
                  </div>

                  {/* 技術指標詳情 */}
                  {Object.keys(signal.indicators).length > 0 && (
                    <div className="mt-2 pt-2 border-t border-gray-200">
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(signal.indicators).map(([key, value]) => (
                          <span
                            key={key}
                            className="text-xs bg-white bg-opacity-50 rounded px-2 py-1"
                          >
                            {key}: {typeof value === 'number' ? value.toFixed(2) : value}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
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

export default RealtimeSignals;