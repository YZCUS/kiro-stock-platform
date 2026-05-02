/**
 * System Health Check Component
 */
'use client';

import React, { useState, useEffect } from 'react';
import { AlertTriangle, CheckCircle2, XCircle } from 'lucide-react';
import { CircularLoader } from '../ui/LoadingStates';
import { Button } from '../ui/button';

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
      responseTime?: number;
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

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return CheckCircle2;
      case 'unhealthy':
        return XCircle;
      default:
        return AlertTriangle;
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
    const ErrorIcon = getStatusIcon('unhealthy');
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <div className="flex items-center">
          <ErrorIcon className="mr-2 h-5 w-5 text-red-600" />
          <div>
            <h3 className="font-medium text-red-800">健康檢查失敗</h3>
            <p className="text-red-600 text-sm">{error}</p>
          </div>
        </div>
        <Button
          onClick={fetchHealthStatus}
          variant="destructive"
          size="sm"
          className="mt-3"
        >
          重新檢查
        </Button>
      </div>
    );
  }

  if (!healthStatus) {
    return null;
  }

  if (compact) {
    const CompactIcon = getStatusIcon(healthStatus.status);
    return (
      <div className="inline-flex items-center space-x-2">
        <CompactIcon className={`h-4 w-4 ${getStatusColor(healthStatus.status)}`} />
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

  const StatusIcon = getStatusIcon(healthStatus.status);

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-xl font-semibold text-gray-900">系統健康狀態</h2>
        <div className="flex flex-wrap items-center gap-3">
          <div className={`flex items-center gap-2 ${getStatusColor(healthStatus.status)}`}>
            <StatusIcon className="h-5 w-5" />
            <span className="font-medium">
              {healthStatus.status === 'healthy' ? '系統正常' : '系統異常'}
            </span>
          </div>
          <Button
            onClick={fetchHealthStatus}
            disabled={loading}
            size="sm"
          >
            {loading ? '檢查中...' : '重新檢查'}
          </Button>
        </div>
      </div>

      {/* System Info */}
      <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
          <div className="text-sm text-gray-600">版本</div>
          <div className="text-lg font-medium">{healthStatus.version}</div>
        </div>
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
          <div className="text-sm text-gray-600">環境</div>
          <div className="text-lg font-medium">{healthStatus.environment}</div>
        </div>
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
          <div className="text-sm text-gray-600">運行時間</div>
          <div className="text-lg font-medium">{formatUptime(healthStatus.uptime)}</div>
        </div>
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
          <div className="text-sm text-gray-600">記憶體使用</div>
          <div className="text-lg font-medium">
            {formatMemory(healthStatus.memory.heapUsed)} / {formatMemory(healthStatus.memory.heapTotal)}
          </div>
        </div>
      </div>

      {/* Service Checks */}
      <div className="space-y-4">
        <h3 className="text-lg font-medium text-gray-900">服務狀態</h3>

        {Object.entries(healthStatus.checks).map(([service, check]) => {
          const ServiceIcon = getStatusIcon(check.status);

          return (
            <div
              key={service}
              className="flex items-center justify-between rounded-lg border border-gray-200 p-4"
            >
              <div className="flex items-center space-x-3">
                <ServiceIcon className={`h-5 w-5 ${getStatusColor(check.status)}`} />
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
          );
        })}
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
