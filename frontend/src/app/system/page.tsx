/**
 * System Status Page
 */
'use client';

import React from 'react';
import dynamic from 'next/dynamic';

const HealthCheck = dynamic(
  () => import('../../components/SystemHealth/HealthCheck'),
  {
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    ),
  }
);

export default function SystemPage() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          系統狀態監控
        </h1>
        <p className="text-gray-600">
          監控系統健康狀態、服務連接和性能指標
        </p>
      </div>

      <HealthCheck />
    </div>
  );
}