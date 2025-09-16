/**
 * UI 狀態管理 Redux Slice
 */
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { NotificationState, ToastMessage, LoadingState } from '../../types';

// UI 相關狀態介面
interface UIState {
  // 通知系統
  notifications: NotificationState[];
  toasts: ToastMessage[];

  // 載入狀態
  globalLoading: boolean;
  loadingStates: Record<string, LoadingState>;

  // 模態框和彈窗
  modals: {
    stockCreate: boolean;
    stockEdit: boolean;
    stockDelete: boolean;
    signalDetails: boolean;
    chartSettings: boolean;
  };

  // 側邊欄和導航
  sidebar: {
    isOpen: boolean;
    activeTab: string;
  };

  // 主題和外觀
  theme: 'light' | 'dark' | 'auto';

  // 表格和列表設置
  tableSettings: {
    pageSize: number;
    sortBy: string;
    sortOrder: 'asc' | 'desc';
  };

  // 圖表設置
  chartSettings: {
    timeframe: string;
    enabledIndicators: string[];
    autoRefresh: boolean;
    refreshInterval: number; // 秒
  };

  // WebSocket 連接狀態
  websocket: {
    connected: boolean;
    reconnecting: boolean;
    lastConnected: string | null;
    connectionError: string | null;
  };

  // 錯誤處理
  errors: {
    global: string | null;
    api: Record<string, string>;
  };
}

// 初始狀態
const initialState: UIState = {
  notifications: [],
  toasts: [],
  globalLoading: false,
  loadingStates: {},
  modals: {
    stockCreate: false,
    stockEdit: false,
    stockDelete: false,
    signalDetails: false,
    chartSettings: false,
  },
  sidebar: {
    isOpen: true,
    activeTab: 'stocks',
  },
  theme: 'light',
  tableSettings: {
    pageSize: 20,
    sortBy: 'created_at',
    sortOrder: 'desc',
  },
  chartSettings: {
    timeframe: '1D',
    enabledIndicators: ['SMA', 'RSI'],
    autoRefresh: true,
    refreshInterval: 30,
  },
  websocket: {
    connected: false,
    reconnecting: false,
    lastConnected: null,
    connectionError: null,
  },
  errors: {
    global: null,
    api: {},
  },
};

// Slice 定義
const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    // 通知管理
    addNotification: (state, action: PayloadAction<Omit<NotificationState, 'id' | 'timestamp'>>) => {
      const notification: NotificationState = {
        ...action.payload,
        id: Date.now().toString(),
        timestamp: Date.now(),
      };
      state.notifications.push(notification);
    },
    removeNotification: (state, action: PayloadAction<string>) => {
      state.notifications = state.notifications.filter(n => n.id !== action.payload);
    },
    clearNotifications: (state) => {
      state.notifications = [];
    },

    // Toast 消息管理
    addToast: (state, action: PayloadAction<Omit<ToastMessage, 'id'>>) => {
      const toast: ToastMessage = {
        ...action.payload,
        id: Date.now().toString(),
        duration: action.payload.duration || 5000,
      };
      state.toasts.push(toast);
    },
    removeToast: (state, action: PayloadAction<string>) => {
      state.toasts = state.toasts.filter(t => t.id !== action.payload);
    },
    clearToasts: (state) => {
      state.toasts = [];
    },

    // 載入狀態管理
    setGlobalLoading: (state, action: PayloadAction<boolean>) => {
      state.globalLoading = action.payload;
    },
    setLoadingState: (state, action: PayloadAction<{ key: string; loading: LoadingState }>) => {
      state.loadingStates[action.payload.key] = action.payload.loading;
    },
    removeLoadingState: (state, action: PayloadAction<string>) => {
      delete state.loadingStates[action.payload];
    },

    // 模態框管理
    openModal: (state, action: PayloadAction<keyof UIState['modals']>) => {
      state.modals[action.payload] = true;
    },
    closeModal: (state, action: PayloadAction<keyof UIState['modals']>) => {
      state.modals[action.payload] = false;
    },
    closeAllModals: (state) => {
      Object.keys(state.modals).forEach(key => {
        state.modals[key as keyof UIState['modals']] = false;
      });
    },

    // 側邊欄管理
    toggleSidebar: (state) => {
      state.sidebar.isOpen = !state.sidebar.isOpen;
    },
    setSidebarOpen: (state, action: PayloadAction<boolean>) => {
      state.sidebar.isOpen = action.payload;
    },
    setActiveTab: (state, action: PayloadAction<string>) => {
      state.sidebar.activeTab = action.payload;
    },

    // 主題管理
    setTheme: (state, action: PayloadAction<'light' | 'dark' | 'auto'>) => {
      state.theme = action.payload;
    },

    // 表格設置
    setTableSettings: (state, action: PayloadAction<Partial<UIState['tableSettings']>>) => {
      state.tableSettings = { ...state.tableSettings, ...action.payload };
    },

    // 圖表設置
    setChartSettings: (state, action: PayloadAction<Partial<UIState['chartSettings']>>) => {
      state.chartSettings = { ...state.chartSettings, ...action.payload };
    },
    toggleIndicator: (state, action: PayloadAction<string>) => {
      const indicator = action.payload;
      const index = state.chartSettings.enabledIndicators.indexOf(indicator);
      if (index > -1) {
        state.chartSettings.enabledIndicators.splice(index, 1);
      } else {
        state.chartSettings.enabledIndicators.push(indicator);
      }
    },

    // WebSocket 狀態管理
    setWebSocketConnected: (state, action: PayloadAction<boolean>) => {
      state.websocket.connected = action.payload;
      if (action.payload) {
        state.websocket.lastConnected = new Date().toISOString();
        state.websocket.connectionError = null;
        state.websocket.reconnecting = false;
      }
    },
    setWebSocketReconnecting: (state, action: PayloadAction<boolean>) => {
      state.websocket.reconnecting = action.payload;
    },
    setWebSocketError: (state, action: PayloadAction<string | null>) => {
      state.websocket.connectionError = action.payload;
      if (action.payload) {
        state.websocket.connected = false;
        state.websocket.reconnecting = false;
      }
    },

    // 錯誤管理
    setGlobalError: (state, action: PayloadAction<string | null>) => {
      state.errors.global = action.payload;
    },
    setApiError: (state, action: PayloadAction<{ key: string; error: string }>) => {
      state.errors.api[action.payload.key] = action.payload.error;
    },
    clearApiError: (state, action: PayloadAction<string>) => {
      delete state.errors.api[action.payload];
    },
    clearAllErrors: (state) => {
      state.errors.global = null;
      state.errors.api = {};
    },

    // 重置 UI 狀態
    resetUIState: (state) => {
      return initialState;
    },
  },
});

export const {
  // 通知
  addNotification,
  removeNotification,
  clearNotifications,

  // Toast
  addToast,
  removeToast,
  clearToasts,

  // 載入狀態
  setGlobalLoading,
  setLoadingState,
  removeLoadingState,

  // 模態框
  openModal,
  closeModal,
  closeAllModals,

  // 側邊欄
  toggleSidebar,
  setSidebarOpen,
  setActiveTab,

  // 主題
  setTheme,

  // 表格設置
  setTableSettings,

  // 圖表設置
  setChartSettings,
  toggleIndicator,

  // WebSocket
  setWebSocketConnected,
  setWebSocketReconnecting,
  setWebSocketError,

  // 錯誤
  setGlobalError,
  setApiError,
  clearApiError,
  clearAllErrors,

  // 重置
  resetUIState,
} = uiSlice.actions;

export default uiSlice.reducer;