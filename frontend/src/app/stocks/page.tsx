'use client';

import dynamic from 'next/dynamic';
import type { Metadata } from 'next';

// 客戶端元件無法直接 export metadata，需在 layout 或使用 generateMetadata
const StockManagementPage = dynamic(
  () => import('../../components/StockManagement').then(mod => ({ default: mod.StockManagementPage })),
  {
    ssr: false,
  }
);

export default function StocksPage() {
    return <StockManagementPage />;
}