/**
 * 自動刷新 Hook
 */
import { useEffect, useRef, useCallback } from 'react';
import { useAppSelector } from '../store';

export interface UseAutoRefreshOptions {
  enabled?: boolean;
  interval?: number; // seconds
  immediate?: boolean;
  onRefresh: () => void | Promise<void>;
  dependencies?: any[];
}

export const useAutoRefresh = ({
  enabled = true,
  interval = 30,
  immediate = true,
  onRefresh,
  dependencies = []
}: UseAutoRefreshOptions) => {
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const lastRefreshRef = useRef<number>(0);
  
  // 從用戶偏好設定取得自動刷新設定
  const userPreferences = useAppSelector(state => state.ui.preferences);
  const isAutoRefreshEnabled = userPreferences.autoRefresh && enabled;
  const refreshInterval = userPreferences.refreshInterval || interval;

  const executeRefresh = useCallback(async () => {
    try {
      await onRefresh();
      lastRefreshRef.current = Date.now();
    } catch (error) {
      console.error('Auto refresh failed:', error);
    }
  }, [onRefresh]);

  const startInterval = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }

    if (isAutoRefreshEnabled && refreshInterval > 0) {
      intervalRef.current = setInterval(executeRefresh, refreshInterval * 1000);
    }
  }, [isAutoRefreshEnabled, refreshInterval, executeRefresh]);

  const stopInterval = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const manualRefresh = useCallback(async () => {
    stopInterval();
    await executeRefresh();
    startInterval();
  }, [executeRefresh, startInterval, stopInterval]);

  // 重設定時器
  useEffect(() => {
    startInterval();
    return stopInterval;
  }, [startInterval, stopInterval, ...dependencies]);

  // 立即執行一次
  useEffect(() => {
    if (immediate) {
      executeRefresh();
    }
  }, [immediate, executeRefresh]);

  // 監聽頁面可見性變化
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        stopInterval();
      } else {
        // 頁面變為可見時，檢查是否需要刷新
        const timeSinceLastRefresh = Date.now() - lastRefreshRef.current;
        const shouldRefresh = timeSinceLastRefresh > refreshInterval * 1000;
        
        if (shouldRefresh && isAutoRefreshEnabled) {
          executeRefresh();
        }
        startInterval();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [isAutoRefreshEnabled, refreshInterval, executeRefresh, startInterval, stopInterval]);

  // 監聽網路狀態變化
  useEffect(() => {
    const handleOnline = () => {
      if (isAutoRefreshEnabled) {
        executeRefresh();
        startInterval();
      }
    };

    const handleOffline = () => {
      stopInterval();
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [isAutoRefreshEnabled, executeRefresh, startInterval, stopInterval]);

  return {
    isEnabled: isAutoRefreshEnabled,
    interval: refreshInterval,
    lastRefresh: lastRefreshRef.current,
    manualRefresh,
    startInterval,
    stopInterval,
  };
};