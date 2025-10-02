/**
 * Watchlist Redux Slice
 */
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { WatchlistStockDetail } from '@/services/watchlistApi';

interface WatchlistState {
  items: WatchlistStockDetail[];
  loading: boolean;
  error: string | null;
}

const initialState: WatchlistState = {
  items: [],
  loading: false,
  error: null,
};

const watchlistSlice = createSlice({
  name: 'watchlist',
  initialState,
  reducers: {
    setWatchlistLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload;
    },
    setWatchlistError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
      state.loading = false;
    },
    setWatchlistItems: (state, action: PayloadAction<WatchlistStockDetail[]>) => {
      state.items = action.payload;
      state.loading = false;
      state.error = null;
    },
    addWatchlistItem: (state, action: PayloadAction<WatchlistStockDetail>) => {
      state.items.push(action.payload);
    },
    removeWatchlistItem: (state, action: PayloadAction<number>) => {
      state.items = state.items.filter(item => item.watchlist_id !== action.payload);
    },
    clearWatchlist: (state) => {
      state.items = [];
      state.loading = false;
      state.error = null;
    },
  },
});

export const {
  setWatchlistLoading,
  setWatchlistError,
  setWatchlistItems,
  addWatchlistItem,
  removeWatchlistItem,
  clearWatchlist,
} = watchlistSlice.actions;

export default watchlistSlice.reducer;
