'use client';

import dynamic from 'next/dynamic';

const StockManagementPage = dynamic(
  () => import('../../components/StockManagement').then(mod => ({ default: mod.StockManagementPage })),
  {
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    ),
  }
);

export default function StocksPage() {
    return <StockManagementPage />;
}