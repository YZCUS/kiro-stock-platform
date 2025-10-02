/**
 * Watchlist API Service
 */
import { apiClient, API_ENDPOINTS } from '@/lib/api';

export interface WatchlistItemResponse {
  id: number;
  stock_id: number;
  user_id: string;
  created_at: string;
  stock: any;
}

export interface WatchlistResponse {
  total: number;
  items: WatchlistItemResponse[];
}

export interface WatchlistStockDetail {
  watchlist_id: number;
  stock: any;
  added_at: string;
  latest_price?: any;
}

export interface PopularStock {
  stock: any;
  watchlist_count: number;
}

/**
 * Get user's watchlist
 */
export const getWatchlist = async (token: string): Promise<WatchlistResponse> => {
  const response = await apiClient.get<WatchlistResponse>(
    API_ENDPOINTS.WATCHLIST.LIST,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );
  return response.data;
};

/**
 * Get user's watchlist with detailed stock info
 */
export const getWatchlistDetailed = async (token: string): Promise<WatchlistStockDetail[]> => {
  const response = await apiClient.get<WatchlistStockDetail[]>(
    API_ENDPOINTS.WATCHLIST.DETAILED,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );
  return response.data;
};

/**
 * Add stock to watchlist
 */
export const addToWatchlist = async (
  stockId: number,
  token: string
): Promise<WatchlistItemResponse> => {
  const response = await apiClient.post<WatchlistItemResponse>(
    API_ENDPOINTS.WATCHLIST.ADD,
    { stock_id: stockId },
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );
  return response.data;
};

/**
 * Remove stock from watchlist
 */
export const removeFromWatchlist = async (
  stockId: number,
  token: string
): Promise<void> => {
  await apiClient.delete(
    API_ENDPOINTS.WATCHLIST.REMOVE(stockId),
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );
};

/**
 * Check if stock is in watchlist
 */
export const checkInWatchlist = async (
  stockId: number,
  token: string
): Promise<{ in_watchlist: boolean; stock_id: number }> => {
  const response = await apiClient.get(
    API_ENDPOINTS.WATCHLIST.CHECK(stockId),
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );
  return response.data;
};

/**
 * Get popular stocks
 */
export const getPopularStocks = async (limit: number = 10): Promise<PopularStock[]> => {
  const response = await apiClient.get<PopularStock[]>(
    `${API_ENDPOINTS.WATCHLIST.POPULAR}?limit=${limit}`
  );
  return response.data;
};
