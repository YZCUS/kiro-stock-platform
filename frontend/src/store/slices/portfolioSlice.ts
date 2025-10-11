/**
 * Portfolio Redux Slice
 * 管理持倉和交易記錄的狀態
 */
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import type {
  Portfolio,
  PortfolioListResponse,
  PortfolioSummary,
  Transaction,
  TransactionCreateRequest,
  TransactionListResponse,
  TransactionSummary,
  TransactionFilter
} from '@/types';
import portfolioApi from '@/services/portfolioApi';

// =============================================================================
// State Interface
// =============================================================================

interface PortfolioState {
  // 持倉列表
  portfolios: Portfolio[];
  portfolioTotal: number;
  totalCost: number;
  totalCurrentValue: number;
  totalProfitLoss: number;
  totalProfitLossPercent: number;

  // 持倉摘要
  summary: PortfolioSummary | null;

  // 交易記錄
  transactions: Transaction[];
  transactionTotal: number;
  transactionPage: number;
  transactionPerPage: number;
  transactionTotalPages: number;

  // 交易摘要
  transactionSummary: TransactionSummary | null;

  // 加載狀態
  loading: boolean;
  portfolioLoading: boolean;
  transactionLoading: boolean;
  error: string | null;
}

const initialState: PortfolioState = {
  portfolios: [],
  portfolioTotal: 0,
  totalCost: 0,
  totalCurrentValue: 0,
  totalProfitLoss: 0,
  totalProfitLossPercent: 0,
  summary: null,
  transactions: [],
  transactionTotal: 0,
  transactionPage: 1,
  transactionPerPage: 50,
  transactionTotalPages: 1,
  transactionSummary: null,
  loading: false,
  portfolioLoading: false,
  transactionLoading: false,
  error: null,
};

// =============================================================================
// Async Thunks
// =============================================================================

/**
 * 獲取持倉列表
 */
export const fetchPortfolioList = createAsyncThunk(
  'portfolio/fetchList',
  async (_, { rejectWithValue }) => {
    try {
      const data = await portfolioApi.getPortfolioList();
      return data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || '獲取持倉列表失敗');
    }
  }
);

/**
 * 獲取持倉摘要
 */
export const fetchPortfolioSummary = createAsyncThunk(
  'portfolio/fetchSummary',
  async (_, { rejectWithValue }) => {
    try {
      const data = await portfolioApi.getPortfolioSummary();
      return data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || '獲取持倉摘要失敗');
    }
  }
);

/**
 * 刪除持倉
 */
export const removePortfolio = createAsyncThunk(
  'portfolio/remove',
  async (portfolioId: number, { rejectWithValue }) => {
    try {
      await portfolioApi.deletePortfolio(portfolioId);
      return portfolioId;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || '刪除持倉失敗');
    }
  }
);

/**
 * 創建交易
 */
export const addTransaction = createAsyncThunk(
  'portfolio/addTransaction',
  async (request: TransactionCreateRequest, { rejectWithValue }) => {
    try {
      const data = await portfolioApi.createTransaction(request);
      return data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || '創建交易失敗');
    }
  }
);

/**
 * 獲取交易列表
 */
export const fetchTransactionList = createAsyncThunk(
  'portfolio/fetchTransactions',
  async (filter: TransactionFilter | undefined, { rejectWithValue }) => {
    try {
      const data = await portfolioApi.getTransactionList(filter);
      return data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || '獲取交易記錄失敗');
    }
  }
);

/**
 * 獲取交易摘要
 */
export const fetchTransactionSummary = createAsyncThunk(
  'portfolio/fetchTransactionSummary',
  async ({ startDate, endDate }: { startDate?: string; endDate?: string }, { rejectWithValue }) => {
    try {
      const data = await portfolioApi.getTransactionSummary(startDate, endDate);
      return data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || '獲取交易摘要失敗');
    }
  }
);

// =============================================================================
// Slice
// =============================================================================

const portfolioSlice = createSlice({
  name: 'portfolio',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    clearPortfolio: (state) => {
      state.portfolios = [];
      state.portfolioTotal = 0;
      state.totalCost = 0;
      state.totalCurrentValue = 0;
      state.totalProfitLoss = 0;
      state.totalProfitLossPercent = 0;
      state.summary = null;
    },
    clearTransactions: (state) => {
      state.transactions = [];
      state.transactionTotal = 0;
      state.transactionSummary = null;
    },
  },
  extraReducers: (builder) => {
    // =========================================================================
    // Fetch Portfolio List
    // =========================================================================
    builder
      .addCase(fetchPortfolioList.pending, (state) => {
        state.portfolioLoading = true;
        state.error = null;
      })
      .addCase(fetchPortfolioList.fulfilled, (state, action: PayloadAction<PortfolioListResponse>) => {
        state.portfolioLoading = false;
        state.portfolios = action.payload.items;
        state.portfolioTotal = action.payload.total;
        state.totalCost = action.payload.total_cost;
        state.totalCurrentValue = action.payload.total_current_value;
        state.totalProfitLoss = action.payload.total_profit_loss;
        state.totalProfitLossPercent = action.payload.total_profit_loss_percent;
      })
      .addCase(fetchPortfolioList.rejected, (state, action) => {
        state.portfolioLoading = false;
        state.error = action.payload as string;
      });

    // =========================================================================
    // Fetch Portfolio Summary
    // =========================================================================
    builder
      .addCase(fetchPortfolioSummary.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchPortfolioSummary.fulfilled, (state, action: PayloadAction<PortfolioSummary>) => {
        state.loading = false;
        state.summary = action.payload;
      })
      .addCase(fetchPortfolioSummary.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });

    // =========================================================================
    // Remove Portfolio
    // =========================================================================
    builder
      .addCase(removePortfolio.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(removePortfolio.fulfilled, (state, action: PayloadAction<number>) => {
        state.loading = false;
        state.portfolios = state.portfolios.filter((p) => p.id !== action.payload);
        state.portfolioTotal = Math.max(0, state.portfolioTotal - 1);
      })
      .addCase(removePortfolio.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });

    // =========================================================================
    // Add Transaction
    // =========================================================================
    builder
      .addCase(addTransaction.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(addTransaction.fulfilled, (state, action: PayloadAction<Transaction>) => {
        state.loading = false;
        state.transactions.unshift(action.payload);
        state.transactionTotal += 1;
      })
      .addCase(addTransaction.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });

    // =========================================================================
    // Fetch Transaction List
    // =========================================================================
    builder
      .addCase(fetchTransactionList.pending, (state) => {
        state.transactionLoading = true;
        state.error = null;
      })
      .addCase(fetchTransactionList.fulfilled, (state, action: PayloadAction<TransactionListResponse>) => {
        state.transactionLoading = false;
        state.transactions = action.payload.items;
        state.transactionTotal = action.payload.total;
        state.transactionPage = action.payload.page;
        state.transactionPerPage = action.payload.per_page;
        state.transactionTotalPages = action.payload.total_pages;
      })
      .addCase(fetchTransactionList.rejected, (state, action) => {
        state.transactionLoading = false;
        state.error = action.payload as string;
      });

    // =========================================================================
    // Fetch Transaction Summary
    // =========================================================================
    builder
      .addCase(fetchTransactionSummary.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchTransactionSummary.fulfilled, (state, action: PayloadAction<TransactionSummary>) => {
        state.loading = false;
        state.transactionSummary = action.payload;
      })
      .addCase(fetchTransactionSummary.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });
  },
});

// =============================================================================
// Exports
// =============================================================================

export const { clearError, clearPortfolio, clearTransactions } = portfolioSlice.actions;

export default portfolioSlice.reducer;
