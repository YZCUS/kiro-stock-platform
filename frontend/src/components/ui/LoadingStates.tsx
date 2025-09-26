/**
 * Loading State Components and Skeletons
 */
'use client';

import React from 'react';

// 基礎骨架屏組件
export const Skeleton: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`animate-pulse bg-gray-200 rounded ${className}`} />
);

// 股票卡片骨架屏
export const StockCardSkeleton: React.FC = () => (
  <div className="bg-white shadow rounded-lg p-6">
    <div className="flex items-center justify-between mb-4">
      <div className="space-y-2">
        <Skeleton className="h-5 w-20" />
        <Skeleton className="h-4 w-32" />
      </div>
      <Skeleton className="h-8 w-8 rounded-full" />
    </div>
    <div className="grid grid-cols-2 gap-4">
      <div className="space-y-2">
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-6 w-24" />
      </div>
      <div className="space-y-2">
        <Skeleton className="h-4 w-12" />
        <Skeleton className="h-6 w-20" />
      </div>
    </div>
  </div>
);

// 圖表骨架屏
export const ChartSkeleton: React.FC<{ height?: number }> = ({ height = 400 }) => (
  <div className="bg-white shadow rounded-lg p-6">
    <div className="flex items-center justify-between mb-4">
      <div className="space-y-2">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-4 w-32" />
      </div>
      <div className="flex space-x-2">
        <Skeleton className="h-8 w-16" />
        <Skeleton className="h-8 w-16" />
      </div>
    </div>
    <div className="w-full" style={{ height: `${height}px` }}>
      <Skeleton className="w-full h-full" />
    </div>
    <div className="flex justify-center space-x-6 mt-4">
      <div className="flex items-center space-x-2">
        <Skeleton className="h-3 w-8" />
        <Skeleton className="h-3 w-12" />
      </div>
      <div className="flex items-center space-x-2">
        <Skeleton className="h-3 w-8" />
        <Skeleton className="h-3 w-12" />
      </div>
    </div>
  </div>
);

// 信號列表骨架屏
export const SignalListSkeleton: React.FC = () => (
  <div className="bg-white shadow rounded-lg p-6">
    <div className="flex items-center justify-between mb-4">
      <Skeleton className="h-6 w-32" />
      <Skeleton className="h-8 w-20" />
    </div>
    <div className="space-y-4">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="flex items-center justify-between p-3 border rounded-lg">
          <div className="flex items-center space-x-3">
            <Skeleton className="h-10 w-10 rounded-full" />
            <div className="space-y-2">
              <Skeleton className="h-4 w-16" />
              <Skeleton className="h-3 w-24" />
            </div>
          </div>
          <div className="text-right space-y-2">
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-3 w-16" />
          </div>
        </div>
      ))}
    </div>
  </div>
);

// 表格骨架屏
export const TableSkeleton: React.FC<{ rows?: number; cols?: number }> = ({
  rows = 5,
  cols = 4
}) => (
  <div className="bg-white shadow rounded-lg overflow-hidden">
    {/* Table Header */}
    <div className="bg-gray-50 border-b border-gray-200 px-6 py-3">
      <div className="flex space-x-6">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className="h-4 w-24" />
        ))}
      </div>
    </div>

    {/* Table Body */}
    <div className="divide-y divide-gray-200">
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="px-6 py-4">
          <div className="flex space-x-6">
            {Array.from({ length: cols }).map((_, colIndex) => (
              <Skeleton key={colIndex} className="h-4 w-20" />
            ))}
          </div>
        </div>
      ))}
    </div>
  </div>
);

// 頁面載入組件
export const PageLoader: React.FC<{ message?: string }> = ({
  message = '載入中...'
}) => (
  <div className="min-h-screen flex items-center justify-center bg-gray-50">
    <div className="text-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
      <p className="text-gray-600">{message}</p>
    </div>
  </div>
);

// 按鈕載入狀態
export const ButtonLoader: React.FC<{ size?: 'sm' | 'md' | 'lg' }> = ({
  size = 'md'
}) => {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-5 w-5',
    lg: 'h-6 w-6',
  };

  return (
    <div className={`animate-spin rounded-full border-2 border-white border-t-transparent ${sizeClasses[size]}`} />
  );
};

// 內容載入組件
export const ContentLoader: React.FC<{
  rows?: number;
  className?: string;
}> = ({ rows = 3, className = '' }) => (
  <div className={`space-y-3 ${className}`}>
    {Array.from({ length: rows }).map((_, i) => (
      <Skeleton
        key={i}
        className={`h-4 ${i === rows - 1 ? 'w-3/4' : 'w-full'}`}
      />
    ))}
  </div>
);

// 圓形載入器
export const CircularLoader: React.FC<{
  size?: number;
  color?: string;
}> = ({ size = 40, color = 'blue' }) => (
  <div className="flex items-center justify-center">
    <div
      className={`animate-spin rounded-full border-4 border-${color}-200 border-t-${color}-600`}
      style={{ width: size, height: size }}
    ></div>
  </div>
);

// 儀表板載入狀態
export const DashboardSkeleton: React.FC = () => (
  <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
    {/* Header */}
    <div className="mb-8">
      <Skeleton className="h-8 w-64 mb-2" />
      <Skeleton className="h-4 w-96" />
    </div>

    {/* Stats Cards */}
    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-8 w-16" />
            </div>
            <Skeleton className="h-12 w-12 rounded-full" />
          </div>
        </div>
      ))}
    </div>

    {/* Main Content */}
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
      <div className="xl:col-span-2">
        <ChartSkeleton height={600} />
      </div>
      <div className="xl:col-span-1">
        <SignalListSkeleton />
      </div>
    </div>
  </div>
);

export default {
  Skeleton,
  StockCardSkeleton,
  ChartSkeleton,
  SignalListSkeleton,
  TableSkeleton,
  PageLoader,
  ButtonLoader,
  ContentLoader,
  CircularLoader,
  DashboardSkeleton,
};