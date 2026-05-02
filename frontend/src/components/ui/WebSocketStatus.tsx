/**
 * WebSocket 連接狀態指示器
 */
'use client';

import React from 'react';
import { useWebSocket } from '../../hooks/useWebSocket';
import { Button } from './button';

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
        <div className="flex items-center space-x-2 text-gray-500" title={error}>
          <div className="w-2 h-2 rounded-full bg-gray-400"></div>
          <span className="text-sm font-medium">離線</span>
          <Button
            onClick={reconnect}
            variant="outline"
            size="xs"
            aria-label="重新連線"
          >
            重試
          </Button>
        </div>
      );
    }

    return (
      <div className="flex items-center space-x-2 text-gray-500">
        <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
        <span className="text-sm font-medium">未連線</span>
        <Button
          onClick={reconnect}
          variant="outline"
          size="xs"
        >
          連線
        </Button>
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
