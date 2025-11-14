/**
 * Redux Store 配置
 */
import { configureStore } from '@reduxjs/toolkit';
import { TypedUseSelectorHook, useDispatch, useSelector } from 'react-redux';

// 導入所有 slice reducers
import stocksReducer from './slices/stocksSlice';
import signalsReducer from './slices/signalsSlice';
import indicatorsReducer from './slices/indicatorsSlice';
import uiReducer from './slices/uiSlice';
import authReducer from './slices/authSlice';
import portfolioReducer from './slices/portfolioSlice';
import stockListReducer from './slices/stockListSlice';
import strategyReducer from './slices/strategySlice';

// 創建 store 的工廠函數（用於客戶端和測試）
export const makeStore = () => {
  return configureStore({
    reducer: {
      stocks: stocksReducer,
      signals: signalsReducer,
      indicators: indicatorsReducer,
      ui: uiReducer,
      auth: authReducer,
      portfolio: portfolioReducer,
      stockList: stockListReducer,
      strategy: strategyReducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware({
        serializableCheck: {
          // 忽略這些 action types 的序列化檢查
          ignoredActions: [
            'persist/FLUSH',
            'persist/REHYDRATE',
            'persist/PAUSE',
            'persist/PERSIST',
            'persist/PURGE',
            'persist/REGISTER',
          ],
          // 忽略這些路徑的序列化檢查
          ignoredPaths: ['ui.toasts', 'ui.notifications'],
        },
      }),
    devTools: process.env.NODE_ENV !== 'production',
  });
};

// 導出 store 類型
export type AppStore = ReturnType<typeof makeStore>;
export type RootState = ReturnType<AppStore['getState']>;
export type AppDispatch = AppStore['dispatch'];

// 導出類型化的 hooks
export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;

// 為了向後兼容，導出一個 store 實例（僅用於非 Next.js 環境）
export const store = makeStore();

// 導出 store 作為默認導出
export default store;
