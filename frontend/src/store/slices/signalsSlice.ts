/**
 * 交易信號狀態管理
 */
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import type { TradingSignal, SignalFilter, LoadingState } from '../../types';
import { signalsApi } from '../../utils/api';

interface SignalsState {
  signals: TradingSignal[];
  stockSignals: Record<number, TradingSignal[]>; // stockId -> signals
  filters: SignalFilter;
  loading: boolean;
  error: string | null;
  stats: {
    total_signals: number;
    buy_signals: number;
    sell_signals: number;
    hold_signals: number;
    cross_signals: number;
    avg_confidence: number;
  };
  pagination: {
    page: number;
    pageSize: number;
    total: number;
    totalPages: number;
  };
}

const initialState: SignalsState = {
  signals: [],
  stockSignals: {},
  filters: {
    signal_type: '',
    market: '',
    min_confidence: 0,
    start_date: '',
    end_date: '',
  },
  loading: false,
  error: null,
  stats: {
    total_signals: 0,
    buy_signals: 0,
    sell_signals: 0,
    hold_signals: 0,
    cross_signals: 0,
    avg_confidence: 0,
  },
  pagination: {
    page: 1,
    pageSize: 50,
    total: 0,
    totalPages: 0,
  },
};

// Async thunks
export const fetchSignals = createAsyncThunk(
  'signals/fetchSignals',
  async (params: {
    page?: number;
    pageSize?: number;
    filters?: SignalFilter;
  } = {}) => {
    const { page = 1, pageSize = 50, filters = {} } = params;
    const response = await signalsApi.getAllSignals({
      signal_type: filters.signal_type,
      market: filters.market,
      min_confidence: filters.min_confidence,
      start_date: filters.start_date,
      end_date: filters.end_date,
      page,
      page_size: pageSize,
    });
    return response;
  }
);

export const fetchStockSignals = createAsyncThunk(
  'signals/fetchStockSignals',
  async (params: {
    stockId: number;
    signalType?: string;
    days?: number;
    limit?: number;
  }) => {
    const { stockId, ...otherParams } = params;
    const response = await signalsApi.getStockSignals(stockId, otherParams);
    return { stockId, signals: response };
  }
);

export const fetchSignalStats = createAsyncThunk(
  'signals/fetchSignalStats',
  async (params: { days?: number; market?: string } = {}) => {
    const response = await signalsApi.getSignalStats(params);
    return response;
  }
);

export const fetchSignalHistory = createAsyncThunk(
  'signals/fetchSignalHistory',
  async (params: {
    days?: number;
    signalType?: string;
    market?: string;
    limit?: number;
  } = {}) => {
    const response = await signalsApi.getSignalHistory(params);
    return response;
  }
);

export const detectStockSignals = createAsyncThunk(
  'signals/detectStockSignals',
  async (params: {
    stockId: number;
    signalTypes?: string[];
    saveResults?: boolean;
  }) => {
    const { stockId, ...otherParams } = params;
    const response = await signalsApi.detectStockSignals(stockId, otherParams);
    return { stockId, signals: response };
  }
);

export const deleteSignal = createAsyncThunk(
  'signals/deleteSignal',
  async (signalId: number) => {
    await signalsApi.deleteSignal(signalId);
    return signalId;
  }
);

// 新增 fetchAllSignals，作為 fetchSignals 的別名
export const fetchAllSignals = fetchSignals;

// Slice
const signalsSlice = createSlice({
  name: 'signals',
  initialState,
  reducers: {
    setFilters: (state, action: PayloadAction<Partial<SignalFilter>>) => {
      state.filters = { ...state.filters, ...action.payload };
    },
    clearFilters: (state) => {
      state.filters = initialState.filters;
    },
    clearError: (state) => {
      state.error = null;
    },
    setPage: (state, action: PayloadAction<number>) => {
      state.pagination.page = action.payload;
    },
    setPageSize: (state, action: PayloadAction<number>) => {
      state.pagination.pageSize = action.payload;
      state.pagination.page = 1;
    },
    addRealTimeSignal: (state, action: PayloadAction<TradingSignal>) => {
      // Add real-time signal from WebSocket
      state.signals.unshift(action.payload);
      
      // Also add to stock-specific signals if exists
      const stockId = action.payload.stock_id;
      if (state.stockSignals[stockId]) {
        state.stockSignals[stockId].unshift(action.payload);
      }
      
      // Update stats
      switch (action.payload.signal_type) {
        case 'BUY':
          state.stats.buy_signals++;
          break;
        case 'SELL':
          state.stats.sell_signals++;
          break;
        case 'HOLD':
          state.stats.hold_signals++;
          break;
        case 'GOLDEN_CROSS':
        case 'DEATH_CROSS':
          state.stats.cross_signals++;
          break;
      }
      state.stats.total_signals++;
    },
    clearStockSignals: (state, action: PayloadAction<number>) => {
      delete state.stockSignals[action.payload];
    },
  },
  extraReducers: (builder) => {
    // Fetch all signals
    builder
      .addCase(fetchSignals.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchSignals.fulfilled, (state, action) => {
        state.loading = false;
        state.signals = action.payload.signals || action.payload;
        if (action.payload.pagination) {
          state.pagination = action.payload.pagination;
        }
        if (action.payload.stats) {
          state.stats = action.payload.stats;
        }
      })
      .addCase(fetchSignals.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || '取得交易信號失敗';
      });

    // Fetch stock signals
    builder
      .addCase(fetchStockSignals.fulfilled, (state, action) => {
        const { stockId, signals } = action.payload;
        state.stockSignals[stockId] = signals;
      });

    // Fetch signal stats
    builder
      .addCase(fetchSignalStats.fulfilled, (state, action) => {
        state.stats = action.payload;
      });

    // Fetch signal history
    builder
      .addCase(fetchSignalHistory.fulfilled, (state, action) => {
        state.signals = action.payload;
      });

    // Detect stock signals
    builder
      .addCase(detectStockSignals.fulfilled, (state, action) => {
        const { stockId, signals } = action.payload;
        
        // Add detected signals to general signals list
        state.signals.unshift(...signals);
        
        // Update stock-specific signals
        if (state.stockSignals[stockId]) {
          state.stockSignals[stockId].unshift(...signals);
        } else {
          state.stockSignals[stockId] = signals;
        }
      });

    // Delete signal
    builder
      .addCase(deleteSignal.fulfilled, (state, action) => {
        const signalId = action.payload;
        
        // Remove from general signals
        state.signals = state.signals.filter(signal => signal.id !== signalId);
        
        // Remove from stock-specific signals
        Object.keys(state.stockSignals).forEach(stockIdStr => {
          const stockId = parseInt(stockIdStr);
          state.stockSignals[stockId] = state.stockSignals[stockId].filter(
            signal => signal.id !== signalId
          );
        });
      });
  },
});

export const {
  setFilters,
  clearFilters,
  clearError,
  setPage,
  setPageSize,
  addRealTimeSignal,
  clearStockSignals,
} = signalsSlice.actions;

export default signalsSlice.reducer;