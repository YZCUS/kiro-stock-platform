/**
 * UI 狀態管理
 */
import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message?: string;
  duration?: number;
  actions?: Array<{
    label: string;
    action: () => void;
  }>;
}

export interface Modal {
  id: string;
  component: string;
  props?: Record<string, any>;
  options?: {
    closeOnOverlayClick?: boolean;
    showCloseButton?: boolean;
    size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  };
}

interface UIState {
  // 側邊欄狀態
  sidebar: {
    isOpen: boolean;
    isCollapsed: boolean;
    activeSection: string;
  };
  
  // 主題設定
  theme: {
    mode: 'light' | 'dark' | 'auto';
    primaryColor: string;
    fontSize: 'sm' | 'md' | 'lg';
  };
  
  // 載入狀態
  loading: {
    global: boolean;
    components: Record<string, boolean>;
  };
  
  // Toast 通知
  toasts: ToastMessage[];
  
  // Modal 狀態
  modals: Modal[];
  
  // 頁面設定
  page: {
    title: string;
    breadcrumbs: Array<{ label: string; href?: string }>;
    actions: Array<{
      label: string;
      icon?: string;
      variant?: 'primary' | 'secondary' | 'outline';
      action: () => void;
    }>;
  };
  
  // 偏好設定
  preferences: {
    language: 'zh-TW' | 'en-US';
    dateFormat: string;
    timeFormat: '12h' | '24h';
    currency: 'TWD' | 'USD';
    autoRefresh: boolean;
    refreshInterval: number; // seconds
    notifications: {
      enabled: boolean;
      sound: boolean;
      desktop: boolean;
      email: boolean;
    };
    dashboard: {
      layout: 'grid' | 'list';
      itemsPerPage: number;
      defaultTimeRange: '1D' | '1W' | '1M' | '3M' | '6M' | '1Y';
    };
  };
  
  // 錯誤狀態
  errors: {
    global: string | null;
    components: Record<string, string | null>;
  };
}

const initialState: UIState = {
  sidebar: {
    isOpen: true,
    isCollapsed: false,
    activeSection: 'dashboard',
  },
  
  theme: {
    mode: 'light',
    primaryColor: '#3b82f6',
    fontSize: 'md',
  },
  
  loading: {
    global: false,
    components: {},
  },
  
  toasts: [],
  
  modals: [],
  
  page: {
    title: '',
    breadcrumbs: [],
    actions: [],
  },
  
  preferences: {
    language: 'zh-TW',
    dateFormat: 'YYYY-MM-DD',
    timeFormat: '24h',
    currency: 'TWD',
    autoRefresh: true,
    refreshInterval: 30,
    notifications: {
      enabled: true,
      sound: true,
      desktop: true,
      email: false,
    },
    dashboard: {
      layout: 'grid',
      itemsPerPage: 20,
      defaultTimeRange: '1M',
    },
  },
  
  errors: {
    global: null,
    components: {},
  },
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    // 側邊欄控制
    toggleSidebar: (state) => {
      state.sidebar.isOpen = !state.sidebar.isOpen;
    },
    
    setSidebarOpen: (state, action: PayloadAction<boolean>) => {
      state.sidebar.isOpen = action.payload;
    },
    
    toggleSidebarCollapse: (state) => {
      state.sidebar.isCollapsed = !state.sidebar.isCollapsed;
    },
    
    setSidebarCollapsed: (state, action: PayloadAction<boolean>) => {
      state.sidebar.isCollapsed = action.payload;
    },
    
    setActiveSection: (state, action: PayloadAction<string>) => {
      state.sidebar.activeSection = action.payload;
    },
    
    // 主題控制
    setThemeMode: (state, action: PayloadAction<'light' | 'dark' | 'auto'>) => {
      state.theme.mode = action.payload;
    },
    
    setPrimaryColor: (state, action: PayloadAction<string>) => {
      state.theme.primaryColor = action.payload;
    },
    
    setFontSize: (state, action: PayloadAction<'sm' | 'md' | 'lg'>) => {
      state.theme.fontSize = action.payload;
    },
    
    // 載入狀態控制
    setGlobalLoading: (state, action: PayloadAction<boolean>) => {
      state.loading.global = action.payload;
    },
    
    setComponentLoading: (state, action: PayloadAction<{ component: string; loading: boolean }>) => {
      const { component, loading } = action.payload;
      state.loading.components[component] = loading;
    },
    
    clearComponentLoading: (state, action: PayloadAction<string>) => {
      delete state.loading.components[action.payload];
    },
    
    // Toast 控制
    addToast: (state, action: PayloadAction<Omit<ToastMessage, 'id'>>) => {
      const toast: ToastMessage = {
        id: Date.now().toString(),
        duration: 5000,
        ...action.payload,
      };
      state.toasts.push(toast);
    },
    
    removeToast: (state, action: PayloadAction<string>) => {
      state.toasts = state.toasts.filter(toast => toast.id !== action.payload);
    },
    
    clearToasts: (state) => {
      state.toasts = [];
    },
    
    // Modal 控制
    openModal: (state, action: PayloadAction<Omit<Modal, 'id'>>) => {
      const modal: Modal = {
        id: Date.now().toString(),
        options: {
          closeOnOverlayClick: true,
          showCloseButton: true,
          size: 'md',
        },
        ...action.payload,
      };
      state.modals.push(modal);
    },
    
    closeModal: (state, action: PayloadAction<string>) => {
      state.modals = state.modals.filter(modal => modal.id !== action.payload);
    },
    
    closeAllModals: (state) => {
      state.modals = [];
    },
    
    // 頁面設定
    setPageTitle: (state, action: PayloadAction<string>) => {
      state.page.title = action.payload;
    },
    
    setBreadcrumbs: (state, action: PayloadAction<Array<{ label: string; href?: string }>>) => {
      state.page.breadcrumbs = action.payload;
    },
    
    setPageActions: (state, action: PayloadAction<UIState['page']['actions']>) => {
      state.page.actions = action.payload;
    },
    
    // 偏好設定
    setLanguage: (state, action: PayloadAction<'zh-TW' | 'en-US'>) => {
      state.preferences.language = action.payload;
    },
    
    setCurrency: (state, action: PayloadAction<'TWD' | 'USD'>) => {
      state.preferences.currency = action.payload;
    },
    
    setAutoRefresh: (state, action: PayloadAction<boolean>) => {
      state.preferences.autoRefresh = action.payload;
    },
    
    setRefreshInterval: (state, action: PayloadAction<number>) => {
      state.preferences.refreshInterval = action.payload;
    },
    
    setNotificationSettings: (state, action: PayloadAction<Partial<UIState['preferences']['notifications']>>) => {
      state.preferences.notifications = {
        ...state.preferences.notifications,
        ...action.payload,
      };
    },
    
    setDashboardSettings: (state, action: PayloadAction<Partial<UIState['preferences']['dashboard']>>) => {
      state.preferences.dashboard = {
        ...state.preferences.dashboard,
        ...action.payload,
      };
    },
    
    updatePreferences: (state, action: PayloadAction<Partial<UIState['preferences']>>) => {
      state.preferences = {
        ...state.preferences,
        ...action.payload,
      };
    },
    
    // 錯誤處理
    setGlobalError: (state, action: PayloadAction<string | null>) => {
      state.errors.global = action.payload;
    },
    
    setComponentError: (state, action: PayloadAction<{ component: string; error: string | null }>) => {
      const { component, error } = action.payload;
      state.errors.components[component] = error;
    },
    
    clearComponentError: (state, action: PayloadAction<string>) => {
      delete state.errors.components[action.payload];
    },
    
    clearAllErrors: (state) => {
      state.errors.global = null;
      state.errors.components = {};
    },
  },
});

export const {
  // Sidebar
  toggleSidebar,
  setSidebarOpen,
  toggleSidebarCollapse,
  setSidebarCollapsed,
  setActiveSection,
  
  // Theme
  setThemeMode,
  setPrimaryColor,
  setFontSize,
  
  // Loading
  setGlobalLoading,
  setComponentLoading,
  clearComponentLoading,
  
  // Toast
  addToast,
  removeToast,
  clearToasts,
  
  // Modal
  openModal,
  closeModal,
  closeAllModals,
  
  // Page
  setPageTitle,
  setBreadcrumbs,
  setPageActions,
  
  // Preferences
  setLanguage,
  setCurrency,
  setAutoRefresh,
  setRefreshInterval,
  setNotificationSettings,
  setDashboardSettings,
  updatePreferences,
  
  // Errors
  setGlobalError,
  setComponentError,
  clearComponentError,
  clearAllErrors,
} = uiSlice.actions;

export default uiSlice.reducer;