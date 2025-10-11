/**
 * 股票清單 Redux Slice
 */
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import type {
  StockList,
  StockListCreateRequest,
  StockListUpdateRequest,
  StockListItem,
  StockListItemAddRequest,
  StockListItemBatchAddRequest
} from '@/types';
import * as stockListApi from '@/services/stockListApi';

// State 接口
interface StockListState {
  lists: StockList[];
  currentList: StockList | null;
  currentListStocks: StockListItem[];
  loading: boolean;
  error: string | null;
}

// 初始狀態
const initialState: StockListState = {
  lists: [],
  currentList: null,
  currentListStocks: [],
  loading: false,
  error: null,
};

// =============================================================================
// Async Thunks
// =============================================================================

/**
 * 獲取所有清單
 */
export const fetchStockLists = createAsyncThunk(
  'stockList/fetchLists',
  async (_, { rejectWithValue }) => {
    try {
      const response = await stockListApi.getStockLists();
      return response.items;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || '獲取清單失敗');
    }
  }
);

/**
 * 創建清單
 */
export const createStockList = createAsyncThunk(
  'stockList/create',
  async (data: StockListCreateRequest, { rejectWithValue }) => {
    try {
      return await stockListApi.createStockList(data);
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || '創建清單失敗');
    }
  }
);

/**
 * 更新清單
 */
export const updateStockList = createAsyncThunk(
  'stockList/update',
  async ({ listId, data }: { listId: number; data: StockListUpdateRequest }, { rejectWithValue }) => {
    try {
      return await stockListApi.updateStockList(listId, data);
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || '更新清單失敗');
    }
  }
);

/**
 * 刪除清單
 */
export const deleteStockList = createAsyncThunk(
  'stockList/delete',
  async (listId: number, { rejectWithValue }) => {
    try {
      await stockListApi.deleteStockList(listId);
      return listId;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || '刪除清單失敗');
    }
  }
);

/**
 * 獲取清單中的股票
 */
export const fetchListStocks = createAsyncThunk(
  'stockList/fetchStocks',
  async (listId: number, { rejectWithValue }) => {
    try {
      const response = await stockListApi.getListStocks(listId);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || '獲取清單股票失敗');
    }
  }
);

/**
 * 添加股票到清單
 */
export const addStockToList = createAsyncThunk(
  'stockList/addStock',
  async ({ listId, data }: { listId: number; data: StockListItemAddRequest }, { rejectWithValue }) => {
    try {
      return await stockListApi.addStockToList(listId, data);
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || '添加股票失敗');
    }
  }
);

/**
 * 批量添加股票
 */
export const batchAddStocksToList = createAsyncThunk(
  'stockList/batchAddStocks',
  async ({ listId, data }: { listId: number; data: StockListItemBatchAddRequest }, { rejectWithValue }) => {
    try {
      return await stockListApi.batchAddStocksToList(listId, data);
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || '批量添加失敗');
    }
  }
);

/**
 * 從清單移除股票
 */
export const removeStockFromList = createAsyncThunk(
  'stockList/removeStock',
  async ({ listId, stockId }: { listId: number; stockId: number }, { rejectWithValue }) => {
    try {
      await stockListApi.removeStockFromList(listId, stockId);
      return { listId, stockId };
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || '移除股票失敗');
    }
  }
);

// =============================================================================
// Slice
// =============================================================================

const stockListSlice = createSlice({
  name: 'stockList',
  initialState,
  reducers: {
    // 設置當前清單
    setCurrentList: (state, action: PayloadAction<StockList | null>) => {
      state.currentList = action.payload;
    },
    // 清除錯誤
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    // 獲取清單列表
    builder
      .addCase(fetchStockLists.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchStockLists.fulfilled, (state, action) => {
        state.loading = false;
        state.lists = action.payload;
      })
      .addCase(fetchStockLists.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });

    // 創建清單
    builder
      .addCase(createStockList.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(createStockList.fulfilled, (state, action) => {
        state.loading = false;
        state.lists.push(action.payload);
        // 如果是預設清單，取消其他清單的預設狀態
        if (action.payload.is_default) {
          state.lists.forEach(list => {
            if (list.id !== action.payload.id) {
              list.is_default = false;
            }
          });
        }
      })
      .addCase(createStockList.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });

    // 更新清單
    builder
      .addCase(updateStockList.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(updateStockList.fulfilled, (state, action) => {
        state.loading = false;
        const index = state.lists.findIndex(list => list.id === action.payload.id);
        if (index !== -1) {
          state.lists[index] = action.payload;
        }
        if (state.currentList?.id === action.payload.id) {
          state.currentList = action.payload;
        }
        // 如果是預設清單，取消其他清單的預設狀態
        if (action.payload.is_default) {
          state.lists.forEach(list => {
            if (list.id !== action.payload.id) {
              list.is_default = false;
            }
          });
        }
      })
      .addCase(updateStockList.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });

    // 刪除清單
    builder
      .addCase(deleteStockList.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(deleteStockList.fulfilled, (state, action) => {
        state.loading = false;
        state.lists = state.lists.filter(list => list.id !== action.payload);
        if (state.currentList?.id === action.payload) {
          state.currentList = null;
        }
      })
      .addCase(deleteStockList.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });

    // 獲取清單股票
    builder
      .addCase(fetchListStocks.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchListStocks.fulfilled, (state, action) => {
        state.loading = false;
        state.currentListStocks = action.payload.items;
      })
      .addCase(fetchListStocks.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });

    // 添加股票
    builder
      .addCase(addStockToList.fulfilled, (state, action) => {
        state.currentListStocks.push(action.payload);
        // 更新清單的股票數量
        const list = state.lists.find(l => l.id === action.payload.list_id);
        if (list) {
          list.stocks_count += 1;
        }
      });

    // 移除股票
    builder
      .addCase(removeStockFromList.fulfilled, (state, action) => {
        const { listId, stockId } = action.payload;
        state.currentListStocks = state.currentListStocks.filter(item => item.stock_id !== stockId);
        // 更新清單的股票數量
        const list = state.lists.find(l => l.id === listId);
        if (list) {
          list.stocks_count = Math.max(0, list.stocks_count - 1);
        }
      });
  },
});

export const { setCurrentList, clearError } = stockListSlice.actions;
export default stockListSlice.reducer;
