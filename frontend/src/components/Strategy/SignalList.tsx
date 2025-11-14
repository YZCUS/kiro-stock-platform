/**
 * 信號列表組件
 */
'use client';

import React, { useState, useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '@/store';
import {
  fetchSignals,
  updateSignalStatus,
  selectSignals,
  selectSignalsLoading,
} from '@/store/slices/strategySlice';
import { addToast } from '@/store/slices/uiSlice';
import { Button } from '@/components/ui/button';
import { RefreshCw, Filter } from 'lucide-react';
import SignalCard from './SignalCard';
import { SignalQueryParams, SignalStatus } from '@/types/strategy';

export default function SignalList() {
  const dispatch = useAppDispatch();
  const signals = useAppSelector(selectSignals);
  const loading = useAppSelector(selectSignalsLoading);

  const [filters, setFilters] = useState<SignalQueryParams>({
    status: 'active',
    sort_by: 'signal_date',
    sort_order: 'desc',
    limit: 20,
  });
  const [showFilters, setShowFilters] = useState(false);

  // 載入信號
  useEffect(() => {
    dispatch(fetchSignals(filters));
  }, [dispatch, filters]);

  // 刷新信號列表
  const handleRefresh = () => {
    dispatch(fetchSignals(filters));
  };

  // 更新信號狀態
  const handleUpdateStatus = async (signalId: number, status: 'triggered' | 'cancelled') => {
    try {
      await dispatch(updateSignalStatus({
        id: signalId,
        data: { status }
      })).unwrap();

      dispatch(addToast({
        type: 'success',
        title: '成功',
        message: `信號已標記為${status === 'triggered' ? '已觸發' : '已取消'}`
      }));

      // 刷新列表
      dispatch(fetchSignals(filters));
    } catch (error: any) {
      dispatch(addToast({
        type: 'error',
        title: '錯誤',
        message: error || '更新失敗'
      }));
    }
  };

  // 更改過濾器
  const handleFilterChange = (key: keyof SignalQueryParams, value: any) => {
    setFilters({ ...filters, [key]: value });
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">交易信號</h2>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowFilters(!showFilters)}
          >
            <Filter className="h-4 w-4 mr-2" />
            過濾器
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </Button>
        </div>
      </div>

      {/* 過濾器 */}
      {showFilters && (
        <div className="bg-gray-50 rounded-lg p-4 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* 狀態過濾 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                狀態
              </label>
              <select
                value={filters.status || 'all'}
                onChange={(e) => handleFilterChange('status', e.target.value === 'all' ? undefined : e.target.value as SignalStatus)}
                className="w-full rounded-md border border-gray-300 px-3 py-2"
              >
                <option value="all">全部</option>
                <option value="active">活躍</option>
                <option value="triggered">已觸發</option>
                <option value="expired">已過期</option>
                <option value="cancelled">已取消</option>
              </select>
            </div>

            {/* 排序 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                排序方式
              </label>
              <select
                value={filters.sort_by || 'signal_date'}
                onChange={(e) => handleFilterChange('sort_by', e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2"
              >
                <option value="signal_date">信號日期</option>
                <option value="confidence">信心度</option>
              </select>
            </div>

            {/* 排序方向 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                排序方向
              </label>
              <select
                value={filters.sort_order || 'desc'}
                onChange={(e) => handleFilterChange('sort_order', e.target.value as 'asc' | 'desc')}
                className="w-full rounded-md border border-gray-300 px-3 py-2"
              >
                <option value="desc">降序</option>
                <option value="asc">升序</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* 信號列表 */}
      {loading && signals.length === 0 ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
          <p className="mt-2 text-gray-600">載入中...</p>
        </div>
      ) : signals.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg border-2 border-dashed">
          <p className="text-gray-600">目前沒有交易信號</p>
          <p className="text-sm text-gray-500 mt-2">
            請確保已訂閱策略並且有符合條件的股票
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {signals.map((signal) => (
            <SignalCard
              key={signal.id}
              signal={signal}
              onUpdateStatus={handleUpdateStatus}
            />
          ))}
        </div>
      )}

      {/* 載入更多按鈕 */}
      {signals.length > 0 && signals.length >= (filters.limit || 20) && (
        <div className="text-center pt-4">
          <Button
            variant="outline"
            onClick={() => handleFilterChange('limit', (filters.limit || 20) + 20)}
            disabled={loading}
          >
            載入更多
          </Button>
        </div>
      )}
    </div>
  );
}
