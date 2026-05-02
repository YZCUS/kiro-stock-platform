/**
 * System Status Page
 */
'use client';

import React from 'react';
import dynamic from 'next/dynamic';
import { PageHeader, PageShell } from '@/components/ui/page';

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
    <PageShell>
      <PageHeader
        title="系統狀態監控"
        description="監控系統健康狀態、服務連接和性能指標。"
      />

      <HealthCheck />
    </PageShell>
  );
}
