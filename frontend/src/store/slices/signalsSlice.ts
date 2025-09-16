/**
 * 交易信號管理 Redux Slice - 更新版本
 */
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { TradingSignal, SignalFilter, PaginatedResponse } from '../../types';

// 異步操作
export const fetchSignals = createAsyncThunk(
  'signals/fetchSignals',
  async (params: {
    page?: number;
    pageSize?: number;
    filters?: SignalFilter;
  } = {}) => {
    // 使用 API 集成層，支援真實 API 和 mock 數據回退
    const { fetchSignalsWithFallback } = await import('../../lib/apiIntegration');
    return fetchSignalsWithFallback(params);
  }
);

export const subscribeToSignals = createAsyncThunk(
  'signals/subscribeToSignals',
  async (stockId?: number) => {
    // 使用 WebSocket 訂閱信號
    const { getWebSocketManager } = await import('../../lib/websocket');
    const wsManager = getWebSocketManager();

    if (stockId) {
      await wsManager.subscribe('subscribe_stock', { stock_id: stockId });
    } else {
      await wsManager.subscribe('subscribe_global');
    }

    return { stockId, subscribed: true };
  }
);

export const unsubscribeFromSignals = createAsyncThunk(
  'signals/unsubscribeFromSignals',
  async (stockId?: number) => {
    // 使用 WebSocket 取消訂閱信號
    const { getWebSocketManager } = await import('../../lib/websocket');
    const wsManager = getWebSocketManager();

    if (stockId) {
      await wsManager.unsubscribe('unsubscribe_stock', { stock_id: stockId });
    } else {
      await wsManager.unsubscribe('unsubscribe_global');
    }

    return { stockId, subscribed: false };
  }
);

// 初始狀態
interface SignalsState {
  signals: TradingSignal[];
  pagination: {
    page: number;
    pageSize: number;
    total: number;
    totalPages: number;
  };
  loading: boolean;
  error: string | null;
  filters: SignalFilter;
  subscribedStocks: number[];
  realtimeSignals: TradingSignal[];
}

const initialState: SignalsState = {
  signals: [],
  pagination: {
    page: 1,
    pageSize: 10,
    total: 0,
    totalPages: 0,
  },
  loading: false,
  error: null,
  filters: {},
  subscribedStocks: [],
  realtimeSignals: [],
};

// Slice
const signalsSlice = createSlice({
  name: 'signals',
  initialState,
  reducers: {
    setFilters: (state, action: PayloadAction<SignalFilter>) => {
      state.filters = action.payload;
    },
    clearFilters: (state) => {
      state.filters = {};
    },
    addRealtimeSignal: (state, action: PayloadAction<TradingSignal>) => {
      // 添加即時信號到列表頂部
      state.realtimeSignals.unshift(action.payload);

      // 限制即時信號數量
      if (state.realtimeSignals.length > 50) {
        state.realtimeSignals = state.realtimeSignals.slice(0, 50);
      }

      // 如果是當前頁面的信號，也添加到主列表
      const matchesFilters = (
        !state.filters.signal_type || action.payload.signal_type === state.filters.signal_type
      ) && (
        !state.filters.market || action.payload.market === state.filters.market
      );

      if (matchesFilters) {
        state.signals.unshift(action.payload);
        state.pagination.total += 1;
      }
    },
    removeSignal: (state, action: PayloadAction<number>) => {
      const signalId = action.payload;
      state.signals = state.signals.filter(signal => signal.id !== signalId);
      state.realtimeSignals = state.realtimeSignals.filter(signal => signal.id !== signalId);

      if (state.pagination.total > 0) {
        state.pagination.total -= 1;
      }
    },
    clearRealtimeSignals: (state) => {
      state.realtimeSignals = [];
    },
    updateSignalSubscription: (state, action: PayloadAction<{ stockId: number; subscribed: boolean }>) => {
      const { stockId, subscribed } = action.payload;

      if (subscribed) {
        if (!state.subscribedStocks.includes(stockId)) {
          state.subscribedStocks.push(stockId);
        }
      } else {
        state.subscribedStocks = state.subscribedStocks.filter(id => id !== stockId);
      }
    },
  },
  extraReducers: (builder) => {
    // fetchSignals
    builder
      .addCase(fetchSignals.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchSignals.fulfilled, (state, action) => {
        state.loading = false;
        state.signals = action.payload.data;
        state.pagination = action.payload.pagination;
      })
      .addCase(fetchSignals.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || '獲取交易信號失敗';
      });

    // subscribeToSignals
    builder
      .addCase(subscribeToSignals.fulfilled, (state, action) => {
        const { stockId, subscribed } = action.payload;
        if (stockId && subscribed) {
          if (!state.subscribedStocks.includes(stockId)) {
            state.subscribedStocks.push(stockId);
          }
        }
      })
      .addCase(subscribeToSignals.rejected, (state, action) => {
        state.error = action.error.message || '訂閱信號失敗';
      });

    // unsubscribeFromSignals
    builder
      .addCase(unsubscribeFromSignals.fulfilled, (state, action) => {
        const { stockId } = action.payload;
        if (stockId) {
          state.subscribedStocks = state.subscribedStocks.filter(id => id !== stockId);
        }
      })
      .addCase(unsubscribeFromSignals.rejected, (state, action) => {
        state.error = action.error.message || '取消訂閱信號失敗';
      });
  },
});

// 匯出 actions
export const {
  setFilters,
  clearFilters,
  addRealtimeSignal,
  removeSignal,
  clearRealtimeSignals,
  updateSignalSubscription,
} = signalsSlice.actions;

// 匯出 reducer
export default signalsSlice.reducer;