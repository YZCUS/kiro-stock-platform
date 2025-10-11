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
import watchlistReducer from './slices/watchlistSlice';
import portfolioReducer from './slices/portfolioSlice';
import stockListReducer from './slices/stockListSlice';

// 配置 Redux store
export const store = configureStore({
  reducer: {
    stocks: stocksReducer,
    signals: signalsReducer,
    indicators: indicatorsReducer,
    ui: uiReducer,
    auth: authReducer,
    watchlist: watchlistReducer,
    portfolio: portfolioReducer,
    stockList: stockListReducer,
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

// 導出 store 類型
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

// 導出類型化的 hooks
export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;

// 導出 store 作為默認導出
export default store;