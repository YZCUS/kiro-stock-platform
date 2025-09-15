/**
 * 股票狀態管理
 */
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import type { Stock, StockFilter, LoadingState } from '../../types';
import { stocksApi } from '../../utils/api';

interface StocksState {
  stocks: Stock[];
  selectedStock: Stock | null;
  filters: StockFilter;
  loading: boolean;
  error: string | null;
  pagination: {
    page: number;
    pageSize: number;
    total: number;
    totalPages: number;
  };
}

const initialState: StocksState = {
  stocks: [],
  selectedStock: null,
  filters: {
    market: '',
    active_only: true,
    search: '',
  },
  loading: false,
  error: null,
  pagination: {
    page: 1,
    pageSize: 50,
    total: 0,
    totalPages: 0,
  },
};

// Async thunks
export const fetchStocks = createAsyncThunk(
  'stocks/fetchStocks',
  async (params: { page?: number; pageSize?: number; filters?: StockFilter } = {}) => {
    const { page = 1, pageSize = 50, filters = {} } = params;
    const response = await stocksApi.getStocks({
      market: filters.market,
      active_only: filters.active_only,
      limit: pageSize,
      // Note: API doesn't support pagination yet, this is for future implementation
    });
    return {
      stocks: response,
      pagination: {
        page,
        pageSize,
        total: response.length,
        totalPages: Math.ceil(response.length / pageSize),
      },
    };
  }
);

export const fetchStock = createAsyncThunk(
  'stocks/fetchStock',
  async (stockId: number) => {
    const response = await stocksApi.getStock(stockId);
    return response;
  }
);

export const createStock = createAsyncThunk(
  'stocks/createStock',
  async (stockData: { symbol: string; market: string; name?: string }) => {
    const response = await stocksApi.createStock(stockData);
    return response;
  }
);

export const updateStock = createAsyncThunk(
  'stocks/updateStock',
  async ({ id, data }: { id: number; data: { name?: string; is_active?: boolean } }) => {
    const response = await stocksApi.updateStock(id, data);
    return response;
  }
);

export const deleteStock = createAsyncThunk(
  'stocks/deleteStock',
  async (stockId: number) => {
    await stocksApi.deleteStock(stockId);
    return stockId;
  }
);

export const batchCreateStocks = createAsyncThunk(
  'stocks/batchCreateStocks',
  async (stocksData: { stocks: Array<{ symbol: string; market: string; name?: string }> }) => {
    const response = await stocksApi.batchCreateStocks(stocksData);
    return response;
  }
);

export const batchDeleteStocks = createAsyncThunk(
  'stocks/batchDeleteStocks',
  async (stockIds: number[]) => {
    // 由於 API 沒有批次刪除端點，我們逐一刪除
    await Promise.all(stockIds.map(id => stocksApi.deleteStock(id)));
    return stockIds;
  }
);

export const refreshStockData = createAsyncThunk(
  'stocks/refreshStockData',
  async ({ stockId, days }: { stockId: number; days?: number }) => {
    const response = await stocksApi.refreshStockData(stockId, { days });
    return { stockId, result: response };
  }
);

export const searchStocks = createAsyncThunk(
  'stocks/searchStocks',
  async ({ symbol, market }: { symbol: string; market?: string }) => {
    const response = await stocksApi.searchStocks(symbol, market);
    return response;
  }
);

// Slice
const stocksSlice = createSlice({
  name: 'stocks',
  initialState,
  reducers: {
    setFilters: (state, action: PayloadAction<Partial<StockFilter>>) => {
      state.filters = { ...state.filters, ...action.payload };
    },
    clearFilters: (state) => {
      state.filters = initialState.filters;
    },
    setSelectedStock: (state, action: PayloadAction<Stock | null>) => {
      state.selectedStock = action.payload;
    },
    clearError: (state) => {
      state.error = null;
    },
    setPage: (state, action: PayloadAction<number>) => {
      state.pagination.page = action.payload;
    },
    setPageSize: (state, action: PayloadAction<number>) => {
      state.pagination.pageSize = action.payload;
      state.pagination.page = 1; // Reset to first page when changing page size
    },
  },
  extraReducers: (builder) => {
    // Fetch stocks
    builder
      .addCase(fetchStocks.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchStocks.fulfilled, (state, action) => {
        state.loading = false;
        state.stocks = action.payload.stocks;
        state.pagination = action.payload.pagination;
      })
      .addCase(fetchStocks.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || '取得股票列表失敗';
      });

    // Fetch single stock
    builder
      .addCase(fetchStock.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchStock.fulfilled, (state, action) => {
        state.loading = false;
        state.selectedStock = action.payload;
      })
      .addCase(fetchStock.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || '取得股票資訊失敗';
      });

    // Create stock
    builder
      .addCase(createStock.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(createStock.fulfilled, (state, action) => {
        state.loading = false;
        state.stocks.push(action.payload);
      })
      .addCase(createStock.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || '新增股票失敗';
      });

    // Update stock
    builder
      .addCase(updateStock.fulfilled, (state, action) => {
        const index = state.stocks.findIndex(stock => stock.id === action.payload.id);
        if (index !== -1) {
          state.stocks[index] = action.payload;
        }
        if (state.selectedStock?.id === action.payload.id) {
          state.selectedStock = action.payload;
        }
      });

    // Delete stock
    builder
      .addCase(deleteStock.fulfilled, (state, action) => {
        state.stocks = state.stocks.filter(stock => stock.id !== action.payload);
        if (state.selectedStock?.id === action.payload) {
          state.selectedStock = null;
        }
      });

    // Batch create stocks
    builder
      .addCase(batchCreateStocks.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(batchCreateStocks.fulfilled, (state, action) => {
        state.loading = false;
        // 添加成功建立的股票到列表
        if (action.payload.created) {
          state.stocks.push(...action.payload.created);
        }
      })
      .addCase(batchCreateStocks.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || '批次新增股票失敗';
      });

    // Batch delete stocks
    builder
      .addCase(batchDeleteStocks.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(batchDeleteStocks.fulfilled, (state, action) => {
        state.loading = false;
        state.stocks = state.stocks.filter(stock => !action.payload.includes(stock.id));
        if (state.selectedStock && action.payload.includes(state.selectedStock.id)) {
          state.selectedStock = null;
        }
      })
      .addCase(batchDeleteStocks.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || '批次刪除股票失敗';
      });

    // Refresh stock data
    builder
      .addCase(refreshStockData.fulfilled, (state, action) => {
        // 刷新數據成功，可以更新最後更新時間等資訊
        const stock = state.stocks.find(s => s.id === action.payload.stockId);
        if (stock) {
          stock.updated_at = new Date().toISOString();
        }
      });

    // Search stocks
    builder
      .addCase(searchStocks.fulfilled, (state, action) => {
        // 搜尋結果不直接更新 stocks 列表，而是由組件處理
        state.loading = false;
      });
  },
});

export const {
  setFilters,
  clearFilters,
  setSelectedStock,
  clearError,
  setPage,
  setPageSize,
} = stocksSlice.actions;

export default stocksSlice.reducer;