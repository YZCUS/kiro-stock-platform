/**
 * WebSocket 連接狀態指示器
 */
'use client';

import React from 'react';
import { useWebSocket } from '../../hooks/useWebSocket';

export interface WebSocketStatusProps {
  className?: string;
}

const WebSocketStatus: React.FC<WebSocketStatusProps> = ({ className = '' }) => {
  const { isConnected, isReconnecting, error, reconnect } = useWebSocket();

  // 渲染狀態指示器
  const renderStatusIndicator = () => {
    if (isConnected) {
      return (
        <div className="flex items-center space-x-2 text-green-600">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
          <span className="text-sm font-medium">即時連線</span>
        </div>
      );
    }

    if (isReconnecting) {
      return (
        <div className="flex items-center space-x-2 text-yellow-600">
          <div className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse"></div>
          <span className="text-sm font-medium">重新連線中...</span>
        </div>
      );
    }

    if (error) {
      return (
        <div className="flex items-center space-x-2 text-red-600">
          <div className="w-2 h-2 bg-red-500 rounded-full"></div>
          <span className="text-sm font-medium">連線中斷</span>
          <button
            onClick={reconnect}
            className="text-xs px-2 py-1 bg-red-100 hover:bg-red-200 rounded transition-colors"
          >
            重連
          </button>
        </div>
      );
    }

    return (
      <div className="flex items-center space-x-2 text-gray-500">
        <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
        <span className="text-sm font-medium">未連線</span>
        <button
          onClick={reconnect}
          className="text-xs px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded transition-colors"
        >
          連線
        </button>
      </div>
    );
  };

  return (
    <div className={`${className}`}>
      {renderStatusIndicator()}
    </div>
  );
};

export default WebSocketStatus;