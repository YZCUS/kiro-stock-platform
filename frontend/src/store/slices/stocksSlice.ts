/**
 * 股票管理 Redux Slice
 */
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { Stock, StockFilter, ApiResponse, PaginatedResponse } from '../../types';

// 異步操作
export const fetchStocks = createAsyncThunk(
  'stocks/fetchStocks',
  async (params: {
    page?: number;
    pageSize?: number;
    filters?: StockFilter;
  } = {}) => {
    // 使用 API 集成層，支援真實 API 和 mock 數據回退
    const { fetchStocksWithFallback } = await import('../../lib/apiIntegration');
    return fetchStocksWithFallback(params);
  }
);

export const createStock = createAsyncThunk(
  'stocks/createStock',
  async (stockData: { symbol: string; market: 'TW' | 'US'; name?: string }) => {
    // 使用 API 集成層
    const { createStockWithFallback } = await import('../../lib/apiIntegration');
    return createStockWithFallback(stockData);
  }
);

export const deleteStock = createAsyncThunk(
  'stocks/deleteStock',
  async (stockId: number) => {
    // 使用 API 集成層
    const { deleteStockWithFallback } = await import('../../lib/apiIntegration');
    await deleteStockWithFallback(stockId);
    return stockId;
  }
);

export const refreshStockData = createAsyncThunk(
  'stocks/refreshStockData',
  async (stockId: number) => {
    // 模擬 API 調用
    await new Promise(resolve => setTimeout(resolve, 2000));

    return { stockId, refreshedAt: new Date().toISOString() };
  }
);

// 介面定義
interface StocksState {
  stocks: Stock[];
  loading: boolean;
  error: string | null;
  pagination: {
    page: number;
    pageSize: number;
    total: number;
    totalPages: number;
  };
  filters: StockFilter;
  selectedStock: Stock | null;
  refreshingStocks: number[]; // 正在刷新數據的股票ID列表
}

// 初始狀態
const initialState: StocksState = {
  stocks: [],
  loading: false,
  error: null,
  pagination: {
    page: 1,
    pageSize: 20,
    total: 0,
    totalPages: 0,
  },
  filters: {},
  selectedStock: null,
  refreshingStocks: [],
};

// Slice 定義
const stocksSlice = createSlice({
  name: 'stocks',
  initialState,
  reducers: {
    setFilters: (state, action: PayloadAction<StockFilter>) => {
      state.filters = action.payload;
    },
    clearFilters: (state) => {
      state.filters = {};
    },
    setSelectedStock: (state, action: PayloadAction<Stock | null>) => {
      state.selectedStock = action.payload;
    },
    clearError: (state) => {
      state.error = null;
    },
    updateStock: (state, action: PayloadAction<Partial<Stock> & { id: number }>) => {
      const index = state.stocks.findIndex(stock => stock.id === action.payload.id);
      if (index !== -1) {
        state.stocks[index] = { ...state.stocks[index], ...action.payload };
      }
    },
  },
  extraReducers: (builder) => {
    builder
      // fetchStocks
      .addCase(fetchStocks.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchStocks.fulfilled, (state, action) => {
        state.loading = false;
        state.stocks = action.payload.data;
        state.pagination = action.payload.pagination;
      })
      .addCase(fetchStocks.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || '獲取股票列表失敗';
      })

      // createStock
      .addCase(createStock.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(createStock.fulfilled, (state, action) => {
        state.loading = false;
        state.stocks.unshift(action.payload);
        state.pagination.total += 1;
      })
      .addCase(createStock.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || '創建股票失敗';
      })

      // deleteStock
      .addCase(deleteStock.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(deleteStock.fulfilled, (state, action) => {
        state.loading = false;
        state.stocks = state.stocks.filter(stock => stock.id !== action.payload);
        state.pagination.total -= 1;
        if (state.selectedStock?.id === action.payload) {
          state.selectedStock = null;
        }
      })
      .addCase(deleteStock.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || '刪除股票失敗';
      })

      // refreshStockData
      .addCase(refreshStockData.pending, (state, action) => {
        const stockId = action.meta.arg;
        if (!state.refreshingStocks.includes(stockId)) {
          state.refreshingStocks.push(stockId);
        }
      })
      .addCase(refreshStockData.fulfilled, (state, action) => {
        const { stockId, refreshedAt } = action.payload;
        state.refreshingStocks = state.refreshingStocks.filter(id => id !== stockId);

        // 更新股票的更新時間
        const index = state.stocks.findIndex(stock => stock.id === stockId);
        if (index !== -1) {
          state.stocks[index].updated_at = refreshedAt;
        }
      })
      .addCase(refreshStockData.rejected, (state, action) => {
        const stockId = action.meta.arg;
        state.refreshingStocks = state.refreshingStocks.filter(id => id !== stockId);
        state.error = action.error.message || '刷新股票數據失敗';
      });
  },
});

export const {
  setFilters,
  clearFilters,
  setSelectedStock,
  clearError,
  updateStock,
} = stocksSlice.actions;

export default stocksSlice.reducer;