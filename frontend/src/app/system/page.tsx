/**
 * System Status Page
 */
'use client';

import React from 'react';
import HealthCheck from '../../components/SystemHealth/HealthCheck';

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