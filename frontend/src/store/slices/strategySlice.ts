/**
 * Strategy Redux Slice
 * 管理策略訂閱和交易信號的狀態
 */
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import type {
  StrategyInfo,
  Subscription,
  TradingSignal,
  SignalStatistics,
  SubscriptionCreateRequest,
  SubscriptionUpdateRequest,
  SignalQueryParams,
  UpdateSignalStatusRequest,
} from '@/types/strategy';
import * as strategyApi from '@/services/strategyApi';

// =============================================================================
// State Interface
// =============================================================================

interface StrategyState {
  // 策略資訊
  availableStrategies: StrategyInfo[];
  strategiesLoading: boolean;

  // 訂閱管理
  subscriptions: Subscription[];
  subscriptionsLoading: boolean;

  // 信號列表
  signals: TradingSignal[];
  signalsTotal: number;
  signalsLoading: boolean;

  // 信號統計
  statistics: SignalStatistics | null;
  statisticsLoading: boolean;

  // 錯誤處理
  error: string | null;
}

const initialState: StrategyState = {
  availableStrategies: [],
  strategiesLoading: false,

  subscriptions: [],
  subscriptionsLoading: false,

  signals: [],
  signalsTotal: 0,
  signalsLoading: false,

  statistics: null,
  statisticsLoading: false,

  error: null,
};

// =============================================================================
// Async Thunks
// =============================================================================

/**
 * 獲取可用策略
 */
export const fetchAvailableStrategies = createAsyncThunk(
  'strategy/fetchAvailableStrategies',
  async (_, { rejectWithValue }) => {
    try {
      const data = await strategyApi.getAvailableStrategies();
      return data.strategies;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || '獲取策略列表失敗');
    }
  }
);

/**
 * 獲取訂閱列表
 */
export const fetchSubscriptions = createAsyncThunk(
  'strategy/fetchSubscriptions',
  async (activeOnly: boolean = false, { rejectWithValue }) => {
    try {
      const data = await strategyApi.getSubscriptions(activeOnly);
      return data.subscriptions;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || '獲取訂閱列表失敗');
    }
  }
);

/**
 * 創建訂閱
 */
export const createSubscription = createAsyncThunk(
  'strategy/createSubscription',
  async (data: SubscriptionCreateRequest, { rejectWithValue }) => {
    try {
      const subscription = await strategyApi.createSubscription(data);
      return subscription;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || '創建訂閱失敗');
    }
  }
);

/**
 * 更新訂閱
 */
export const updateSubscription = createAsyncThunk(
  'strategy/updateSubscription',
  async ({ id, data }: { id: number; data: SubscriptionUpdateRequest }, { rejectWithValue }) => {
    try {
      const subscription = await strategyApi.updateSubscription(id, data);
      return subscription;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || '更新訂閱失敗');
    }
  }
);

/**
 * 刪除訂閱
 */
export const deleteSubscription = createAsyncThunk(
  'strategy/deleteSubscription',
  async ({ id, hardDelete }: { id: number; hardDelete?: boolean }, { rejectWithValue }) => {
    try {
      await strategyApi.deleteSubscription(id, hardDelete);
      return id;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || '刪除訂閱失敗');
    }
  }
);

/**
 * 切換訂閱
 */
export const toggleSubscription = createAsyncThunk(
  'strategy/toggleSubscription',
  async ({ id, isActive }: { id: number; isActive?: boolean }, { rejectWithValue }) => {
    try {
      const subscription = await strategyApi.toggleSubscription(id, isActive);
      return subscription;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || '切換訂閱狀態失敗');
    }
  }
);

/**
 * 獲取信號列表
 */
export const fetchSignals = createAsyncThunk(
  'strategy/fetchSignals',
  async (params: SignalQueryParams, { rejectWithValue }) => {
    try {
      const data = await strategyApi.getSignals(params);
      return data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || '獲取信號列表失敗');
    }
  }
);

/**
 * 獲取信號統計
 */
export const fetchSignalStatistics = createAsyncThunk(
  'strategy/fetchSignalStatistics',
  async ({ dateFrom, dateTo }: { dateFrom?: string; dateTo?: string }, { rejectWithValue }) => {
    try {
      const data = await strategyApi.getSignalStatistics(dateFrom, dateTo);
      return data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || '獲取統計資訊失敗');
    }
  }
);

/**
 * 更新信號狀態
 */
export const updateSignalStatus = createAsyncThunk(
  'strategy/updateSignalStatus',
  async ({ id, data }: { id: number; data: UpdateSignalStatusRequest }, { rejectWithValue }) => {
    try {
      const signal = await strategyApi.updateSignalStatus(id, data);
      return signal;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || '更新信號狀態失敗');
    }
  }
);

/**
 * 生成信號
 */
export const generateSignals = createAsyncThunk(
  'strategy/generateSignals',
  async (userId: string | undefined, { rejectWithValue }) => {
    try {
      const result = await strategyApi.generateSignals(userId);
      return result;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || '生成信號失敗');
    }
  }
);

// =============================================================================
// Slice
// =============================================================================

const strategySlice = createSlice({
  name: 'strategy',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    clearSignals: (state) => {
      state.signals = [];
      state.signalsTotal = 0;
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    // 獲取可用策略
    builder
      .addCase(fetchAvailableStrategies.pending, (state) => {
        state.strategiesLoading = true;
        state.error = null;
      })
      .addCase(fetchAvailableStrategies.fulfilled, (state, action) => {
        state.strategiesLoading = false;
        state.availableStrategies = action.payload;
      })
      .addCase(fetchAvailableStrategies.rejected, (state, action) => {
        state.strategiesLoading = false;
        state.error = action.payload as string;
      });

    // 獲取訂閱列表
    builder
      .addCase(fetchSubscriptions.pending, (state) => {
        state.subscriptionsLoading = true;
        state.error = null;
      })
      .addCase(fetchSubscriptions.fulfilled, (state, action) => {
        state.subscriptionsLoading = false;
        state.subscriptions = action.payload;
      })
      .addCase(fetchSubscriptions.rejected, (state, action) => {
        state.subscriptionsLoading = false;
        state.error = action.payload as string;
      });

    // 創建訂閱
    builder
      .addCase(createSubscription.fulfilled, (state, action) => {
        state.subscriptions.push(action.payload);
        state.error = null;
      })
      .addCase(createSubscription.rejected, (state, action) => {
        state.error = action.payload as string;
      });

    // 更新訂閱
    builder
      .addCase(updateSubscription.fulfilled, (state, action) => {
        const index = state.subscriptions.findIndex(s => s.id === action.payload.id);
        if (index !== -1) {
          state.subscriptions[index] = action.payload;
        }
        state.error = null;
      })
      .addCase(updateSubscription.rejected, (state, action) => {
        state.error = action.payload as string;
      });

    // 刪除訂閱
    builder
      .addCase(deleteSubscription.fulfilled, (state, action) => {
        state.subscriptions = state.subscriptions.filter(s => s.id !== action.payload);
        state.error = null;
      })
      .addCase(deleteSubscription.rejected, (state, action) => {
        state.error = action.payload as string;
      });

    // 切換訂閱
    builder
      .addCase(toggleSubscription.fulfilled, (state, action) => {
        const index = state.subscriptions.findIndex(s => s.id === action.payload.id);
        if (index !== -1) {
          state.subscriptions[index] = action.payload;
        }
        state.error = null;
      })
      .addCase(toggleSubscription.rejected, (state, action) => {
        state.error = action.payload as string;
      });

    // 獲取信號列表
    builder
      .addCase(fetchSignals.pending, (state) => {
        state.signalsLoading = true;
        state.error = null;
      })
      .addCase(fetchSignals.fulfilled, (state, action) => {
        state.signalsLoading = false;
        state.signals = action.payload.signals;
        state.signalsTotal = action.payload.total;
      })
      .addCase(fetchSignals.rejected, (state, action) => {
        state.signalsLoading = false;
        state.error = action.payload as string;
      });

    // 獲取信號統計
    builder
      .addCase(fetchSignalStatistics.pending, (state) => {
        state.statisticsLoading = true;
        state.error = null;
      })
      .addCase(fetchSignalStatistics.fulfilled, (state, action) => {
        state.statisticsLoading = false;
        state.statistics = action.payload;
      })
      .addCase(fetchSignalStatistics.rejected, (state, action) => {
        state.statisticsLoading = false;
        state.error = action.payload as string;
      });

    // 更新信號狀態
    builder
      .addCase(updateSignalStatus.fulfilled, (state, action) => {
        const index = state.signals.findIndex(s => s.id === action.payload.id);
        if (index !== -1) {
          state.signals[index] = action.payload;
        }
        state.error = null;
      })
      .addCase(updateSignalStatus.rejected, (state, action) => {
        state.error = action.payload as string;
      });

    // 生成信號
    builder
      .addCase(generateSignals.pending, (state) => {
        state.signalsLoading = true;
        state.error = null;
      })
      .addCase(generateSignals.fulfilled, (state) => {
        state.signalsLoading = false;
        state.error = null;
      })
      .addCase(generateSignals.rejected, (state, action) => {
        state.signalsLoading = false;
        state.error = action.payload as string;
      });
  },
});

// =============================================================================
// Actions & Selectors
// =============================================================================

export const { clearError, clearSignals } = strategySlice.actions;

// Selectors
export const selectAvailableStrategies = (state: { strategy: StrategyState }) =>
  state.strategy.availableStrategies;

export const selectSubscriptions = (state: { strategy: StrategyState }) =>
  state.strategy.subscriptions;

export const selectActiveSubscriptions = (state: { strategy: StrategyState }) =>
  state.strategy.subscriptions.filter(s => s.is_active);

export const selectSignals = (state: { strategy: StrategyState }) =>
  state.strategy.signals;

export const selectSignalStatistics = (state: { strategy: StrategyState }) =>
  state.strategy.statistics;

export const selectStrategyError = (state: { strategy: StrategyState }) =>
  state.strategy.error;

export const selectStrategiesLoading = (state: { strategy: StrategyState }) =>
  state.strategy.strategiesLoading;

export const selectSubscriptionsLoading = (state: { strategy: StrategyState }) =>
  state.strategy.subscriptionsLoading;

export const selectSignalsLoading = (state: { strategy: StrategyState }) =>
  state.strategy.signalsLoading;

export const selectStatisticsLoading = (state: { strategy: StrategyState }) =>
  state.strategy.statisticsLoading;

export default strategySlice.reducer;
