/**
 * 應用程式 Providers
 */
'use client';

import React, { useEffect } from 'react';
import { Provider } from 'react-redux';
import { PersistGate } from 'redux-persist/integration/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { store, persistor } from '../store';
import { useAppDispatch } from '../store';
import { initializeApp } from '../store/slices/appSlice';
import websocketManager from '../utils/websocketManager';

// 創建 React Query 客戶端
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
    },
  },
});

// App 初始化組件
const AppInitializer: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const dispatch = useAppDispatch();

  useEffect(() => {
    // 初始化應用程式
    dispatch(initializeApp());

    // 初始化 WebSocket 連接
    const initWebSocket = async () => {
      try {
        await websocketManager.connect();
      } catch (error) {
        console.error('Failed to initialize WebSocket:', error);
      }
    };

    // 延遲初始化 WebSocket，確保應用程式已經初始化
    setTimeout(initWebSocket, 1000);

    // 監聽網路狀態
    const handleOnline = () => {
      import('../store/slices/appSlice').then(({ setNetworkStatus }) => {
        dispatch(setNetworkStatus(true));
        // 網路恢復時重新連接 WebSocket
        websocketManager.connect().catch(console.error);
      });
    };

    const handleOffline = () => {
      import('../store/slices/appSlice').then(({ setNetworkStatus }) => {
        dispatch(setNetworkStatus(false));
        // 網路斷開時斷開 WebSocket
        websocketManager.disconnect();
      });
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // 監聽用戶活動
    const handleUserActivity = () => {
      import('../store/slices/appSlice').then(({ updateLastActivity }) => {
        dispatch(updateLastActivity());
      });
    };

    const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'];
    events.forEach(event => {
      document.addEventListener(event, handleUserActivity, true);
    });

    // 監聽頁面可見性變化
    const handleVisibilityChange = () => {
      if (document.hidden) {
        // 頁面隱藏時可以選擇性斷開 WebSocket 以節省資源
        // websocketManager.disconnect();
      } else {
        // 頁面可見時重新連接
        websocketManager.connect().catch(console.error);
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      events.forEach(event => {
        document.removeEventListener(event, handleUserActivity, true);
      });
      
      // 清理 WebSocket 連接
      websocketManager.disconnect();
    };
  }, [dispatch]);

  return <>{children}</>;
};

// 載入中組件
const LoadingFallback: React.FC = () => (
  <div className="flex items-center justify-center min-h-screen bg-white">
    <div className="text-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
      <p className="text-gray-600">載入應用程式中...</p>
    </div>
  </div>
);

export interface ProvidersProps {
  children: React.ReactNode;
}

const Providers: React.FC<ProvidersProps> = ({ children }) => {
  return (
    <Provider store={store}>
      <PersistGate loading={<LoadingFallback />} persistor={persistor}>
        <QueryClientProvider client={queryClient}>
          <AppInitializer>
            {children}
          </AppInitializer>
        </QueryClientProvider>
      </PersistGate>
    </Provider>
  );
};

export default Providers;