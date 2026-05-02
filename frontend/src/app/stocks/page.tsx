'use client';

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { useRouter } from 'next/navigation';
import { useAppSelector } from '@/store';

const StockManagementPage = dynamic(
  () => import('../../components/StockManagement').then(mod => ({ default: mod.StockManagementPage })),
  {
    ssr: false,
    loading: () => (
      <div className="mx-auto max-w-7xl px-4 py-8 text-sm text-gray-500 sm:px-6 lg:px-8">
        載入股票管理...
      </div>
    ),
  }
);

export default function StocksPage() {
  const router = useRouter();
  const { initialized, isAuthenticated } = useAppSelector((state) => state.auth);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (mounted && initialized && !isAuthenticated) {
      router.replace('/login?redirect=/stocks');
    }
  }, [mounted, initialized, isAuthenticated, router]);

  if (!mounted || !initialized || !isAuthenticated) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-8 text-sm text-gray-500 sm:px-6 lg:px-8">
        正在確認登入狀態...
      </div>
    );
  }

  return <StockManagementPage />;
}
