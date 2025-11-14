/**
 * Redux Provider 組件
 */
'use client';

import { useRef } from 'react';
import { Provider } from 'react-redux';
import { QueryClientProvider } from '@tanstack/react-query';
import { makeStore } from './index';
import { queryClient } from '../lib/queryClient';
import type { AppStore } from './index';

interface ProvidersProps {
  children: React.ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  const storeRef = useRef<AppStore>();

  if (!storeRef.current) {
    // 只在客戶端創建一次 store
    storeRef.current = makeStore();
  }

  return (
    <Provider store={storeRef.current}>
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    </Provider>
  );
}