/**
 * System Health Check Component
 */
'use client';

import React, { useState, useEffect } from 'react';
import { CircularLoader } from '../ui/LoadingStates';

interface HealthCheckStatus {
  status: 'healthy' | 'unhealthy';
  timestamp: string;
  version: string;
  environment: string;
  uptime: number;
  memory: {
    rss: number;
    heapTotal: number;
    heapUsed: number;
    external: number;
  };
  checks: {
    database: {
      status: string;
      responseTime?: number;
      error?: string;
    };
    api: {
      status: string;
      responseTime?: number;
      error?: string;
    };
    websocket: {
      status: string;
      error?: string;
    };
  };
}

interface HealthCheckProps {
  autoRefresh?: boolean;
  refreshInterval?: number;
  compact?: boolean;
}

export const HealthCheck: React.FC<HealthCheckProps> = ({
  autoRefresh = true,
  refreshInterval = 30000, // 30 seconds
  compact = false,
}) => {
  const [healthStatus, setHealthStatus] = useState<HealthCheckStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const fetchHealthStatus = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/health');

      if (!response.ok) {
        throw new Error(`Health check failed: ${response.status}`);
      }

      const data = await response.json();
      setHealthStatus(data);
      setError(null);
      setLastChecked(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch health status');
      console.error('Health check error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealthStatus();

    if (autoRefresh) {
      const interval = setInterval(fetchHealthStatus, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, refreshInterval]);

  const formatUptime = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
      return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${secs}s`;
    } else {
      return `${secs}s`;
    }
  };

  const formatMemory = (bytes: number): string => {
    const mb = bytes / 1024 / 1024;
    return `${mb.toFixed(1)} MB`;
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'healthy':
        return 'text-green-600';
      case 'unhealthy':
        return 'text-red-600';
      default:
        return 'text-yellow-600';
    }
  };

  const getStatusIcon = (status: string): string => {
    switch (status) {
      case 'healthy':
        return '✅';
      case 'unhealthy':
        return '❌';
      default:
        return '⚠️';
    }
  };

  if (loading && !healthStatus) {
    return (
      <div className="flex items-center justify-center p-4">
        <CircularLoader size={32} />
        <span className="ml-2 text-gray-600">檢查系統狀態...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-center">
          <span className="text-red-600 mr-2">❌</span>
          <div>
            <h3 className="font-medium text-red-800">健康檢查失敗</h3>
            <p className="text-red-600 text-sm">{error}</p>
          </div>
        </div>
        <button
          onClick={fetchHealthStatus}
          className="mt-3 px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700 transition-colors"
        >
          重新檢查
        </button>
      </div>
    );
  }

  if (!healthStatus) {
    return null;
  }

  if (compact) {
    return (
      <div className="inline-flex items-center space-x-2">
        <span className={`${getStatusColor(healthStatus.status)}`}>
          {getStatusIcon(healthStatus.status)}
        </span>
        <span className={`text-sm font-medium ${getStatusColor(healthStatus.status)}`}>
          {healthStatus.status === 'healthy' ? '系統正常' : '系統異常'}
        </span>
        {lastChecked && (
          <span className="text-xs text-gray-500">
            ({lastChecked.toLocaleTimeString('zh-TW')})
          </span>
        )}
      </div>
    );
  }

  return (
    <div className="bg-white shadow rounded-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-gray-900">系統健康狀態</h2>
        <div className="flex items-center space-x-3">
          <div className={`flex items-center space-x-2 ${getStatusColor(healthStatus.status)}`}>
            <span>{getStatusIcon(healthStatus.status)}</span>
            <span className="font-medium">
              {healthStatus.status === 'healthy' ? '系統正常' : '系統異常'}
            </span>
          </div>
          <button
            onClick={fetchHealthStatus}
            disabled={loading}
            className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {loading ? '檢查中...' : '重新檢查'}
          </button>
        </div>
      </div>

      {/* System Info */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="text-sm text-gray-600">版本</div>
          <div className="text-lg font-medium">{healthStatus.version}</div>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="text-sm text-gray-600">環境</div>
          <div className="text-lg font-medium">{healthStatus.environment}</div>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="text-sm text-gray-600">運行時間</div>
          <div className="text-lg font-medium">{formatUptime(healthStatus.uptime)}</div>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="text-sm text-gray-600">記憶體使用</div>
          <div className="text-lg font-medium">
            {formatMemory(healthStatus.memory.heapUsed)} / {formatMemory(healthStatus.memory.heapTotal)}
          </div>
        </div>
      </div>

      {/* Service Checks */}
      <div className="space-y-4">
        <h3 className="text-lg font-medium text-gray-900">服務狀態</h3>

        {Object.entries(healthStatus.checks).map(([service, check]) => (
          <div
            key={service}
            className="flex items-center justify-between p-4 border border-gray-200 rounded-lg"
          >
            <div className="flex items-center space-x-3">
              <span className={getStatusColor(check.status)}>
                {getStatusIcon(check.status)}
              </span>
              <div>
                <div className="font-medium text-gray-900">
                  {service === 'database' ? '資料庫' :
                   service === 'api' ? 'API服務' :
                   service === 'websocket' ? 'WebSocket' : service}
                </div>
                {check.error && (
                  <div className="text-sm text-red-600">{check.error}</div>
                )}
              </div>
            </div>
            <div className="text-right">
              <div className={`font-medium ${getStatusColor(check.status)}`}>
                {check.status === 'healthy' ? '正常' : '異常'}
              </div>
              {check.responseTime && (
                <div className="text-sm text-gray-500">
                  {check.responseTime}ms
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {lastChecked && (
        <div className="mt-6 text-sm text-gray-500 text-center">
          最後檢查時間: {lastChecked.toLocaleString('zh-TW')}
        </div>
      )}
    </div>
  );
};

export default HealthCheck;