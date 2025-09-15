/**
 * 應用程式全局狀態管理
 */
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { systemApi } from '../../utils/api';

export interface AppInfo {
  version: string;
  buildDate: string;
  environment: 'development' | 'staging' | 'production';
  features: string[];
}

export interface SystemStatus {
  api: 'online' | 'offline' | 'maintenance';
  database: 'connected' | 'disconnected' | 'error';
  websocket: 'connected' | 'disconnected' | 'reconnecting';
  lastHealthCheck: string;
  responseTime: number;
}

export interface UserSession {
  isAuthenticated: boolean;
  user: {
    id?: string;
    name?: string;
    email?: string;
    avatar?: string;
    role?: string;
    permissions?: string[];
  } | null;
  sessionExpiry?: string;
  lastActivity: string;
}

interface AppState {
  // 應用程式資訊
  appInfo: AppInfo;
  
  // 系統狀態
  systemStatus: SystemStatus;
  
  // 用戶會話
  session: UserSession;
  
  // 應用程式設定
  config: {
    apiUrl: string;
    wsUrl: string;
    isDevelopment: boolean;
    enableAnalytics: boolean;
    maxRetries: number;
    timeout: number;
    features: {
      realTimeData: boolean;
      notifications: boolean;
      darkMode: boolean;
      multiLanguage: boolean;
    };
  };
  
  // 全局快取
  cache: {
    lastUpdated: Record<string, string>;
    expiryTimes: Record<string, string>;
    data: Record<string, any>;
  };
  
  // 網路狀態
  network: {
    isOnline: boolean;
    connectionSpeed: 'slow' | 'fast' | 'unknown';
    lastDisconnected?: string;
    retryCount: number;
  };
  
  // 效能監控
  performance: {
    pageLoadTime?: number;
    apiResponseTimes: Record<string, number[]>;
    errorCounts: Record<string, number>;
    memoryUsage?: number;
  };
  
  // 初始化狀態
  initialization: {
    isInitialized: boolean;
    isInitializing: boolean;
    initSteps: {
      config: boolean;
      auth: boolean;
      data: boolean;
      websocket: boolean;
    };
    error?: string;
  };
}

const initialState: AppState = {
  appInfo: {
    version: '1.0.0',
    buildDate: new Date().toISOString(),
    environment: 'development',
    features: [],
  },
  
  systemStatus: {
    api: 'offline',
    database: 'disconnected',
    websocket: 'disconnected',
    lastHealthCheck: '',
    responseTime: 0,
  },
  
  session: {
    isAuthenticated: false,
    user: null,
    lastActivity: new Date().toISOString(),
  },
  
  config: {
    apiUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    wsUrl: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000',
    isDevelopment: process.env.NODE_ENV === 'development',
    enableAnalytics: false,
    maxRetries: 3,
    timeout: 30000,
    features: {
      realTimeData: true,
      notifications: true,
      darkMode: true,
      multiLanguage: true,
    },
  },
  
  cache: {
    lastUpdated: {},
    expiryTimes: {},
    data: {},
  },
  
  network: {
    isOnline: true,
    connectionSpeed: 'unknown',
    retryCount: 0,
  },
  
  performance: {
    apiResponseTimes: {},
    errorCounts: {},
  },
  
  initialization: {
    isInitialized: false,
    isInitializing: false,
    initSteps: {
      config: false,
      auth: false,
      data: false,
      websocket: false,
    },
  },
};

// Async thunks
export const initializeApp = createAsyncThunk(
  'app/initialize',
  async (_, { dispatch, getState }) => {
    dispatch(setInitializing(true));
    
    try {
      // 步驟 1: 載入配置
      dispatch(setInitStep({ step: 'config', completed: true }));
      
      // 步驟 2: 檢查認證狀態
      // TODO: 實作認證檢查
      dispatch(setInitStep({ step: 'auth', completed: true }));
      
      // 步驟 3: 載入初始數據
      // TODO: 載入必要的初始數據
      dispatch(setInitStep({ step: 'data', completed: true }));
      
      // 步驟 4: 建立 WebSocket 連接
      // TODO: 建立 WebSocket 連接
      dispatch(setInitStep({ step: 'websocket', completed: true }));
      
      dispatch(setInitialized(true));
      
      return true;
    } catch (error: any) {
      dispatch(setInitializationError(error.message));
      throw error;
    } finally {
      dispatch(setInitializing(false));
    }
  }
);

export const checkSystemHealth = createAsyncThunk(
  'app/checkSystemHealth',
  async () => {
    const startTime = Date.now();
    try {
      const response = await systemApi.healthCheck();
      const responseTime = Date.now() - startTime;
      
      return {
        api: 'online' as const,
        database: response.database ? 'connected' as const : 'error' as const,
        websocket: response.websocket ? 'connected' as const : 'disconnected' as const,
        responseTime,
        lastHealthCheck: new Date().toISOString(),
      };
    } catch (error) {
      const responseTime = Date.now() - startTime;
      return {
        api: 'offline' as const,
        database: 'disconnected' as const,
        websocket: 'disconnected' as const,
        responseTime,
        lastHealthCheck: new Date().toISOString(),
      };
    }
  }
);

export const trackApiResponse = createAsyncThunk(
  'app/trackApiResponse',
  async (params: { endpoint: string; responseTime: number; success: boolean }) => {
    return params;
  }
);

const appSlice = createSlice({
  name: 'app',
  initialState,
  reducers: {
    // 初始化控制
    setInitializing: (state, action: PayloadAction<boolean>) => {
      state.initialization.isInitializing = action.payload;
    },
    
    setInitialized: (state, action: PayloadAction<boolean>) => {
      state.initialization.isInitialized = action.payload;
    },
    
    setInitStep: (state, action: PayloadAction<{ step: keyof AppState['initialization']['initSteps']; completed: boolean }>) => {
      const { step, completed } = action.payload;
      state.initialization.initSteps[step] = completed;
    },
    
    setInitializationError: (state, action: PayloadAction<string>) => {
      state.initialization.error = action.payload;
    },
    
    clearInitializationError: (state) => {
      state.initialization.error = undefined;
    },
    
    // 用戶會話
    setAuthenticated: (state, action: PayloadAction<boolean>) => {
      state.session.isAuthenticated = action.payload;
      if (!action.payload) {
        state.session.user = null;
      }
    },
    
    setUser: (state, action: PayloadAction<UserSession['user']>) => {
      state.session.user = action.payload;
    },
    
    updateLastActivity: (state) => {
      state.session.lastActivity = new Date().toISOString();
    },
    
    setSessionExpiry: (state, action: PayloadAction<string>) => {
      state.session.sessionExpiry = action.payload;
    },
    
    // 系統狀態
    setSystemStatus: (state, action: PayloadAction<Partial<SystemStatus>>) => {
      state.systemStatus = {
        ...state.systemStatus,
        ...action.payload,
      };
    },
    
    setWebSocketStatus: (state, action: PayloadAction<SystemStatus['websocket']>) => {
      state.systemStatus.websocket = action.payload;
    },
    
    // 網路狀態
    setNetworkStatus: (state, action: PayloadAction<boolean>) => {
      state.network.isOnline = action.payload;
      if (!action.payload) {
        state.network.lastDisconnected = new Date().toISOString();
        state.network.retryCount = 0;
      }
    },
    
    setConnectionSpeed: (state, action: PayloadAction<'slow' | 'fast' | 'unknown'>) => {
      state.network.connectionSpeed = action.payload;
    },
    
    incrementRetryCount: (state) => {
      state.network.retryCount += 1;
    },
    
    resetRetryCount: (state) => {
      state.network.retryCount = 0;
    },
    
    // 快取管理
    setCacheData: (state, action: PayloadAction<{ key: string; data: any; expiresIn?: number }>) => {
      const { key, data, expiresIn = 300000 } = action.payload; // 默認 5 分鐘
      const now = new Date().toISOString();
      const expiry = new Date(Date.now() + expiresIn).toISOString();
      
      state.cache.data[key] = data;
      state.cache.lastUpdated[key] = now;
      state.cache.expiryTimes[key] = expiry;
    },
    
    removeCacheData: (state, action: PayloadAction<string>) => {
      const key = action.payload;
      delete state.cache.data[key];
      delete state.cache.lastUpdated[key];
      delete state.cache.expiryTimes[key];
    },
    
    clearExpiredCache: (state) => {
      const now = new Date().toISOString();
      Object.keys(state.cache.expiryTimes).forEach(key => {
        if (state.cache.expiryTimes[key] < now) {
          delete state.cache.data[key];
          delete state.cache.lastUpdated[key];
          delete state.cache.expiryTimes[key];
        }
      });
    },
    
    clearAllCache: (state) => {
      state.cache.data = {};
      state.cache.lastUpdated = {};
      state.cache.expiryTimes = {};
    },
    
    // 配置更新
    updateConfig: (state, action: PayloadAction<Partial<AppState['config']>>) => {
      state.config = {
        ...state.config,
        ...action.payload,
      };
    },
    
    updateFeatures: (state, action: PayloadAction<Partial<AppState['config']['features']>>) => {
      state.config.features = {
        ...state.config.features,
        ...action.payload,
      };
    },
    
    // 效能監控
    setPageLoadTime: (state, action: PayloadAction<number>) => {
      state.performance.pageLoadTime = action.payload;
    },
    
    addApiResponseTime: (state, action: PayloadAction<{ endpoint: string; time: number }>) => {
      const { endpoint, time } = action.payload;
      if (!state.performance.apiResponseTimes[endpoint]) {
        state.performance.apiResponseTimes[endpoint] = [];
      }
      state.performance.apiResponseTimes[endpoint].push(time);
      
      // 只保留最近 50 筆記錄
      if (state.performance.apiResponseTimes[endpoint].length > 50) {
        state.performance.apiResponseTimes[endpoint] = state.performance.apiResponseTimes[endpoint].slice(-50);
      }
    },
    
    incrementErrorCount: (state, action: PayloadAction<string>) => {
      const endpoint = action.payload;
      state.performance.errorCounts[endpoint] = (state.performance.errorCounts[endpoint] || 0) + 1;
    },
    
    setMemoryUsage: (state, action: PayloadAction<number>) => {
      state.performance.memoryUsage = action.payload;
    },
  },
  extraReducers: (builder) => {
    // System health check
    builder
      .addCase(checkSystemHealth.fulfilled, (state, action) => {
        state.systemStatus = action.payload;
      });
    
    // API response tracking
    builder
      .addCase(trackApiResponse.fulfilled, (state, action) => {
        const { endpoint, responseTime, success } = action.payload;
        
        // 記錄響應時間
        if (!state.performance.apiResponseTimes[endpoint]) {
          state.performance.apiResponseTimes[endpoint] = [];
        }
        state.performance.apiResponseTimes[endpoint].push(responseTime);
        
        // 記錄錯誤
        if (!success) {
          state.performance.errorCounts[endpoint] = (state.performance.errorCounts[endpoint] || 0) + 1;
        }
      });
  },
});

export const {
  // Initialization
  setInitializing,
  setInitialized,
  setInitStep,
  setInitializationError,
  clearInitializationError,
  
  // Session
  setAuthenticated,
  setUser,
  updateLastActivity,
  setSessionExpiry,
  
  // System status
  setSystemStatus,
  setWebSocketStatus,
  
  // Network
  setNetworkStatus,
  setConnectionSpeed,
  incrementRetryCount,
  resetRetryCount,
  
  // Cache
  setCacheData,
  removeCacheData,
  clearExpiredCache,
  clearAllCache,
  
  // Config
  updateConfig,
  updateFeatures,
  
  // Performance
  setPageLoadTime,
  addApiResponseTime,
  incrementErrorCount,
  setMemoryUsage,
} = appSlice.actions;

export default appSlice.reducer;