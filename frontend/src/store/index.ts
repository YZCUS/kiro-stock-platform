/**
 * Redux Store 配置
 */
import { configureStore } from '@reduxjs/toolkit';
import { useDispatch, useSelector, TypedUseSelectorHook } from 'react-redux';
import { persistStore, persistReducer } from 'redux-persist';
import storage from 'redux-persist/lib/storage';
import { combineReducers } from '@reduxjs/toolkit';

// Import slices
import stocksReducer from './slices/stocksSlice';
import signalsReducer from './slices/signalsSlice';
import uiReducer from './slices/uiSlice';
import appReducer from './slices/appSlice';

// UI 持久化配置 (保存用戶偏好)
const uiPersistConfig = {
  key: 'ui',
  storage,
  whitelist: ['theme', 'preferences', 'sidebar'], // 只保存這些設定
  blacklist: ['loading', 'toasts', 'modals', 'errors'], // 不保存臨時狀態
};

// App 持久化配置 (保存配置和會話)
const appPersistConfig = {
  key: 'app',
  storage,
  whitelist: ['config', 'session'], // 保存配置和會話
  blacklist: ['cache', 'performance', 'initialization'], // 不保存動態數據
};

const rootReducer = combineReducers({
  stocks: stocksReducer,
  signals: signalsReducer,
  ui: persistReducer(uiPersistConfig, uiReducer),
  app: persistReducer(appPersistConfig, appReducer),
});

// Configure store
export const store = configureStore({
  reducer: rootReducer,
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: [
          'persist/PERSIST',
          'persist/REHYDRATE',
          'persist/PAUSE',
          'persist/PURGE',
          'persist/REGISTER',
        ],
        ignoredActionPaths: ['meta.arg', 'payload.timestamp'],
        ignoredPaths: ['register'],
      },
    }),
  devTools: process.env.NODE_ENV !== 'production',
});

export const persistor = persistStore(store);

// Export types
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

// Export typed hooks
export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;

// 選擇器 helpers
export const selectIsLoading = (state: RootState, component?: string) => {
  if (component) {
    return state.ui.loading.components[component] || false;
  }
  return state.ui.loading.global;
};

export const selectError = (state: RootState, component?: string) => {
  if (component) {
    return state.ui.errors.components[component] || null;
  }
  return state.ui.errors.global;
};

export const selectTheme = (state: RootState) => state.ui.theme;
export const selectPreferences = (state: RootState) => state.ui.preferences;
export const selectSystemStatus = (state: RootState) => state.app.systemStatus;
export const selectNetworkStatus = (state: RootState) => state.app.network;
export const selectIsAuthenticated = (state: RootState) => state.app.session.isAuthenticated;
export const selectUser = (state: RootState) => state.app.session.user;

export default store;