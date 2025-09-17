/**
 * Advanced Charts Page with Dynamic Imports
 */
'use client';

import React from 'react';
import dynamic from 'next/dynamic';

// 動態載入重型圖表組件
const ChartPage = dynamic(
  () => import('../../components/Charts').then(mod => ({ default: mod.ChartPage })),
  {
    ssr: false,
    loading: () => (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            股票圖表分析
          </h1>
          <p className="text-gray-600">
            載入圖表組件中...
          </p>
        </div>
        <div className="flex items-center justify-center min-h-[500px]">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </div>
    ),
  }
);

export default function AdvancedChartsPage() {
  return <ChartPage />;
}