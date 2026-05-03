/**
 * 即時圖表分析 - 單一股票顯示模式
 */
'use client';

import React, { useState, useEffect, useMemo, useRef } from 'react';
import dynamic from 'next/dynamic';
import { useSearchParams } from 'next/navigation';
import { useAppDispatch, useAppSelector } from '@/store';
import { fetchStockLists, fetchListStocks } from '@/store/slices/stockListSlice';
import { StocksApiService } from '@/services/stocksApi';
import { detectMarket, ensureStockExists } from '../../services/stockValidationApi';
import { getStockQuote, searchMarketSymbols, type MarketQuote } from '@/services/marketInfoApi';
import { ChevronDown, TrendingUp, Activity, BarChart3, Search, X, ShoppingCart, TrendingDown } from 'lucide-react';
import TransactionModal from '../Portfolio/TransactionModal';
import { getPortfolioList } from '@/services/portfolioApi';
import type { LatestPriceInfo, Portfolio, Stock } from '@/types';
import MarketNewsPanel from '@/components/Market/MarketNewsPanel';
import { PageHeader, PageShell } from '@/components/ui/page';
import { cn } from '@/lib/utils';

// 動態載入圖表組件
const RealtimePriceChart = dynamic(() => import('./RealtimePriceChart'), {
  ssr: false,
  loading: () => (
    <div className="flex h-[600px] items-center justify-center rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-500">載入圖表中...</p>
      </div>
    </div>
  ),
});

const RealtimeSignals = dynamic(() => import('./RealtimeSignals'), {
  ssr: false,
  loading: () => (
    <div className="flex h-64 items-center justify-center rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
    </div>
  ),
});

const quoteToLatestPrice = (
  quote: MarketQuote,
  fallback?: LatestPriceInfo | null
): LatestPriceInfo | null => {
  if (typeof quote.price !== 'number') {
    return fallback ?? null;
  }

  return {
    close: quote.price,
    change: quote.change ?? null,
    change_percent: quote.change_percent ?? null,
    date: quote.timestamp ?? fallback?.date ?? null,
    volume: fallback?.volume ?? null,
    source: quote.source,
    is_realtime: quote.is_realtime,
  };
};

const normalizeUrlMarket = (market: string | null, symbol: string): 'TW' | 'US' => {
  const normalized = market?.toUpperCase();
  if (normalized === 'TW' || normalized === 'US') {
    return normalized;
  }
  return detectMarket(symbol);
};

const RealtimeDashboard: React.FC = () => {
  const dispatch = useAppDispatch();
  const searchParams = useSearchParams();
  const { isAuthenticated } = useAppSelector((state) => state.auth);
  const { lists, currentListStocks, loading } = useAppSelector((state) => state.stockList);

  const [viewMode, setViewMode] = useState<'list' | 'portfolio'>('list'); // 視圖模式：清單 or 持倉
  const [selectedListId, setSelectedListId] = useState<number | null>(null);
  const [selectedStockId, setSelectedStockId] = useState<number | null>(null);
  const [showListDropdown, setShowListDropdown] = useState(false);
  const [urlStockProcessed, setUrlStockProcessed] = useState(false);

  // 持倉相關狀態
  const [portfolioStocks, setPortfolioStocks] = useState<Portfolio[]>([]);
  const [portfolioLoading, setPortfolioLoading] = useState(false);

  // 直接輸入股票代號的狀態
  const [symbolInput, setSymbolInput] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [directStock, setDirectStock] = useState<any | null>(null);
  const [realtimeQuotes, setRealtimeQuotes] = useState<Record<number, LatestPriceInfo>>({});

  // 交易 Modal 狀態
  const [transactionModal, setTransactionModal] = useState<{
    isOpen: boolean;
    stock: any | null;
    type: 'BUY' | 'SELL';
  }>({
    isOpen: false,
    stock: null,
    type: 'BUY'
  });

  // Refs for dropdown containers
  const listDropdownRef = useRef<HTMLDivElement>(null);

  // 從 URL 參數讀取股票 ID 和來源
  const stockIdFromUrl = searchParams.get('stock');
  const symbolFromUrl = searchParams.get('symbol');
  const marketFromUrl = searchParams.get('market');
  const nameFromUrl = searchParams.get('name');
  const sourceFromUrl = searchParams.get('source'); // 新增：檢測來源（如 'portfolio'）

  useEffect(() => {
    setUrlStockProcessed(false);
  }, [stockIdFromUrl, symbolFromUrl, marketFromUrl, nameFromUrl, sourceFromUrl]);

  // 載入清單
  useEffect(() => {
    if (isAuthenticated && lists.length === 0 && !loading) {
      dispatch(fetchStockLists());
    }
  }, [isAuthenticated, dispatch, lists.length, loading]);

  // 當從持倉管理跳轉時，自動切換到持倉視圖
  useEffect(() => {
    if (sourceFromUrl === 'portfolio' && isAuthenticated) {
      setViewMode('portfolio');
    }
  }, [sourceFromUrl, isAuthenticated]);

  // 載入持倉數據（當切換到持倉視圖時）
  useEffect(() => {
    const loadPortfolioStocks = async () => {
      if (!isAuthenticated || viewMode !== 'portfolio') return;

      setPortfolioLoading(true);
      try {
        const response = await getPortfolioList();
        setPortfolioStocks(response.items || []);
      } catch (error) {
        console.error('載入持倉失敗:', error);
        setPortfolioStocks([]);
      } finally {
        setPortfolioLoading(false);
      }
    };

    loadPortfolioStocks();
  }, [isAuthenticated, viewMode]);

  // 當選擇清單時載入該清單的股票
  useEffect(() => {
    if (viewMode === 'list' && selectedListId) {
      dispatch(fetchListStocks(selectedListId));
    }
  }, [selectedListId, viewMode, dispatch]);

  // 當清單載入後，自動選擇第一個清單
  useEffect(() => {
    if (
      viewMode === 'list' &&
      lists.length > 0 &&
      !selectedListId &&
      !directStock &&
      !stockIdFromUrl &&
      !symbolFromUrl
    ) {
      setSelectedListId(lists[0].id);
    }
  }, [lists, selectedListId, viewMode, directStock, stockIdFromUrl, symbolFromUrl]);

  // 搜尋或跨頁連到 stock id 時，直接載入該股票，避免先掃描所有觀察清單阻塞圖表。
  useEffect(() => {
    if (!stockIdFromUrl || urlStockProcessed) return;

    const targetStockId = parseInt(stockIdFromUrl, 10);
    if (Number.isNaN(targetStockId)) {
      setUrlStockProcessed(true);
      return;
    }

    let cancelled = false;
    const hintedSymbol = symbolFromUrl?.trim().toUpperCase();
    const hintedMarket = hintedSymbol
      ? normalizeUrlMarket(marketFromUrl, hintedSymbol)
      : null;

    if (sourceFromUrl !== 'portfolio' && hintedSymbol && hintedMarket) {
      setDirectStock({
        id: targetStockId,
        symbol: hintedSymbol,
        name: nameFromUrl || hintedSymbol,
        market: hintedMarket,
        latest_price: null,
      });
      setSelectedListId(null);
      setSelectedStockId(targetStockId);
    }

    const selectDirectStockById = async () => {
      try {
        const stock = await StocksApiService.getStock(targetStockId);
        let latestPrice = stock.latest_price;

        try {
          const quote = await getStockQuote(stock.market, stock.symbol, stock.id, true);
          latestPrice = quoteToLatestPrice(quote, latestPrice);
          if (!cancelled && latestPrice) {
            setRealtimeQuotes((quotes) => ({
              ...quotes,
              [stock.id]: latestPrice,
            }));
          }
        } catch (error) {
          console.warn(`載入股票 ${targetStockId} 即時報價失敗:`, error);
        }

        if (cancelled) return;

        setDirectStock({
          ...stock,
          latest_price: latestPrice,
        });
        setSelectedListId(null);
        setSelectedStockId(targetStockId);
      } catch (error) {
        console.error(`載入股票 ${targetStockId} 失敗:`, error);
        if (!cancelled) {
          setSelectedStockId(targetStockId);
        }
      } finally {
        if (!cancelled) {
          setUrlStockProcessed(true);
        }
      }
    };

    // 如果來源是持倉，從持倉列表中查找
    if (sourceFromUrl === 'portfolio' && isAuthenticated && portfolioStocks.length === 0) {
      return;
    }

    if (sourceFromUrl === 'portfolio' && portfolioStocks.length > 0) {
      setUrlStockProcessed(true);
      const portfolioStock = portfolioStocks.find((p) => p.stock_id === targetStockId);
      if (portfolioStock) {
        setDirectStock(null);
        setSelectedStockId(targetStockId);
      }
      return;
    }

    selectDirectStockById();

    return () => {
      cancelled = true;
    };
  }, [
    stockIdFromUrl,
    symbolFromUrl,
    marketFromUrl,
    nameFromUrl,
    sourceFromUrl,
    portfolioStocks,
    urlStockProcessed,
    isAuthenticated,
  ]);

  // DB 外部搜尋結果會先帶 symbol/market 進來，再由這裡匯入成本地股票供圖表使用。
  useEffect(() => {
    if (stockIdFromUrl || !symbolFromUrl || urlStockProcessed) return;

    let cancelled = false;
    const symbol = symbolFromUrl.trim().toUpperCase();
    const market = normalizeUrlMarket(marketFromUrl, symbol);

    const loadStockFromSymbol = async () => {
      setIsSearching(true);
      setSearchError(null);
      try {
        const result = await ensureStockExists(symbol, market);
        if (cancelled) return;

        let stock: any = result.stock;
        try {
          const quote = await getStockQuote(stock.market, stock.symbol, stock.id, true);
          const latestPrice = quoteToLatestPrice(quote, stock.latest_price);
          if (latestPrice) {
            stock = { ...stock, latest_price: latestPrice };
            if (!cancelled) {
              setRealtimeQuotes((quotes) => ({
                ...quotes,
                [stock.id]: latestPrice,
              }));
            }
          }
        } catch (error) {
          console.warn(`載入 ${symbol} 即時報價失敗:`, error);
        }

        if (cancelled) return;
        setDirectStock(stock);
        setSelectedListId(null);
        setSelectedStockId(stock.id);
      } catch (error: any) {
        if (!cancelled) {
          setSearchError(error.message || `查詢 ${symbol} 失敗`);
        }
      } finally {
        if (!cancelled) {
          setIsSearching(false);
          setUrlStockProcessed(true);
        }
      }
    };

    loadStockFromSymbol();

    return () => {
      cancelled = true;
    };
  }, [stockIdFromUrl, symbolFromUrl, marketFromUrl, urlStockProcessed]);

  // 當股票列表載入後，自動選擇第一個股票
  useEffect(() => {
    if (viewMode !== 'list') return;

    // 只有在 URL 參數未處理或已處理完成時才執行自動選擇
    const shouldAutoSelect = (!stockIdFromUrl && !symbolFromUrl) || urlStockProcessed;

    if (currentListStocks.length > 0 && shouldAutoSelect) {
      // 如果沒有選擇股票，或選擇的股票不在當前清單中，則自動選擇第一個股票
      if (!selectedStockId) {
        setSelectedStockId(currentListStocks[0].id);
      } else {
        const stockInList = currentListStocks.find(s => s.id === selectedStockId);
        if (!stockInList) {
          // 當前選擇的股票不在新清單中，選擇第一個股票
          setSelectedStockId(currentListStocks[0].id);
        }
      }
    }
  }, [currentListStocks, selectedStockId, stockIdFromUrl, symbolFromUrl, urlStockProcessed, viewMode]);

  // 切換到持倉視圖後，讓右側清單直接帶出第一檔持倉
  useEffect(() => {
    if (viewMode !== 'portfolio' || portfolioStocks.length === 0) return;

    if (!selectedStockId) {
      setSelectedStockId(portfolioStocks[0].stock_id);
      return;
    }

    const stockInPortfolio = portfolioStocks.some((portfolio) => portfolio.stock_id === selectedStockId);
    if (!stockInPortfolio) {
      setSelectedStockId(portfolioStocks[0].stock_id);
    }
  }, [portfolioStocks, selectedStockId, viewMode]);

  // 點擊外部關閉下拉選單
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        listDropdownRef.current &&
        !listDropdownRef.current.contains(event.target as Node)
      ) {
        setShowListDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const selectedList = useMemo(() => {
    return lists.find(list => list.id === selectedListId);
  }, [lists, selectedListId]);

  const selectedStock = useMemo(() => {
    // 如果有直接查詢的股票，優先使用
    if (directStock) {
      return directStock;
    }
    // 如果是持倉視圖，從持倉列表中查找並轉換格式
    if (viewMode === 'portfolio' && selectedStockId) {
      const portfolio = portfolioStocks.find(p => p.stock_id === selectedStockId);
      if (portfolio) {
        // 將 Portfolio 轉換為 Stock 格式
        return {
          id: portfolio.stock_id,
          symbol: portfolio.stock_symbol || '',
          name: portfolio.stock_name || '',
          market: portfolio.stock_symbol?.match(/^\d+$/) ? 'TW' : 'US',
          latest_price: portfolio.latest_price
        };
      }
    }
    // 否則從清單中選擇
    return currentListStocks.find(stock => stock.id === selectedStockId);
  }, [currentListStocks, selectedStockId, directStock, viewMode, portfolioStocks]);

  const selectedStockDisplay = useMemo(() => {
    if (!selectedStock) return selectedStock;
    const realtimePrice = realtimeQuotes[selectedStock.id];
    if (!realtimePrice) return selectedStock;
    return {
      ...selectedStock,
      latest_price: realtimePrice,
    };
  }, [selectedStock, realtimeQuotes]);

  // 計算價格變動百分比
  const priceChangePercent = selectedStockDisplay?.latest_price?.change_percent;
  const priceChange = selectedStockDisplay?.latest_price?.change;
  const currentPrice = selectedStockDisplay?.latest_price?.close;

  // 計算當前市場狀態（基於選中股票的市場）
  const getCurrentMarketStatus = () => {
    if (!selectedStockDisplay) return { is_open: false, market: '' };

    const now = new Date();
    const utcHour = now.getUTCHours();
    const utcMinute = now.getUTCMinutes();
    const utcDay = now.getUTCDay(); // 0 = 週日, 1 = 週一, ..., 6 = 週六

    if (selectedStockDisplay.market === 'US') {
      // 美股交易時間（UTC）：週一至週五 14:30-21:00（夏令時）或 15:30-22:00（冬令時）
      // 簡化版本：使用 14:30-21:00
      const isWeekday = utcDay >= 1 && utcDay <= 5;
      const isOpen = isWeekday &&
                     ((utcHour === 14 && utcMinute >= 30) ||
                      (utcHour > 14 && utcHour < 21) ||
                      (utcHour === 21 && utcMinute === 0));
      return { is_open: isOpen, market: 'US' };
    } else {
      // 台股交易時間（UTC）：週一至週五 01:00-05:30（UTC = 台北時間 09:00-13:30）
      const isWeekday = utcDay >= 1 && utcDay <= 5;
      const isOpen = isWeekday &&
                     ((utcHour === 1) ||
                      (utcHour > 1 && utcHour < 5) ||
                      (utcHour === 5 && utcMinute <= 30));
      return { is_open: isOpen, market: 'TW' };
    }
  };

  const currentMarketStatus = getCurrentMarketStatus();
  const isPriceUp = priceChange !== null && priceChange !== undefined && priceChange >= 0;
  const isPercentUp = priceChangePercent !== null && priceChangePercent !== undefined && priceChangePercent >= 0;

  const sidebarStocks = useMemo<Stock[]>(() => {
    if (viewMode !== 'portfolio') {
      return currentListStocks;
    }

    return portfolioStocks.map((portfolio) => ({
      id: portfolio.stock_id,
      symbol: portfolio.stock_symbol || '',
      name: portfolio.stock_name || '',
      market: portfolio.stock_symbol?.endsWith('.TW') || portfolio.stock_symbol?.match(/^\d+$/) ? 'TW' : 'US',
      is_active: true,
      created_at: portfolio.created_at,
      updated_at: portfolio.updated_at,
      latest_price: portfolio.latest_price ?? (
        portfolio.current_price
          ? {
              close: portfolio.current_price,
              change: null,
              change_percent: portfolio.profit_loss_percent ?? null,
              date: portfolio.updated_at,
              volume: null,
            }
          : null
      ),
    }));
  }, [currentListStocks, portfolioStocks, viewMode]);

  const sidebarQuoteSignature = useMemo(() => (
    sidebarStocks
      .map((stock) => `${stock.id}:${stock.market}:${stock.symbol}`)
      .join('|')
  ), [sidebarStocks]);

  useEffect(() => {
    if (!sidebarQuoteSignature) return;

    let cancelled = false;
    const stocksToQuote = sidebarStocks.slice(0, 30);

    const loadRealtimeQuotes = async () => {
      const results = await Promise.allSettled(
        stocksToQuote.map(async (stock) => {
          const quote = await getStockQuote(stock.market, stock.symbol, stock.id, true);
          const latestPrice = quoteToLatestPrice(quote, stock.latest_price);
          return latestPrice ? [stock.id, latestPrice] as const : null;
        })
      );

      if (cancelled) return;

      const nextQuotes = results.reduce<Record<number, LatestPriceInfo>>((acc, result) => {
        if (result.status === 'fulfilled' && result.value) {
          const [stockId, latestPrice] = result.value;
          acc[stockId] = latestPrice;
        }
        return acc;
      }, {});

      if (Object.keys(nextQuotes).length > 0) {
        setRealtimeQuotes((quotes) => ({
          ...quotes,
          ...nextQuotes,
        }));
      }
    };

    loadRealtimeQuotes();
    const intervalId = window.setInterval(loadRealtimeQuotes, 60_000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [sidebarQuoteSignature, sidebarStocks]);

  const sidebarTitle = viewMode === 'portfolio'
    ? '我的持倉'
    : selectedList?.name || '我的觀察清單';
  const sidebarLoading = viewMode === 'portfolio' ? portfolioLoading : loading;

  // 處理股票查詢
  const handleSearch = async () => {
    const query = symbolInput.trim();
    if (!query) return;

    // 先清除舊狀態，避免訂閱時序問題
    setDirectStock(null);
    setSelectedListId(null);
    setSelectedStockId(null);
    setIsSearching(true);
    setSearchError(null);

    try {
      const normalizedQuery = query.toUpperCase();
      let targetSymbol = normalizedQuery;
      let targetMarket = detectMarket(normalizedQuery);

      try {
        const results = await searchMarketSymbols({
          q: query,
          include_external: true,
          limit: 8,
        });
        const exactResult = results.find((item) => {
          const normalizedSymbol = item.symbol.toUpperCase();
          return normalizedSymbol === normalizedQuery
            || normalizedSymbol.replace(/\.(TW|TWO)$/, '') === normalizedQuery;
        });
        const target = exactResult ?? results[0];
        if (target) {
          targetSymbol = target.symbol;
          targetMarket = normalizeUrlMarket(target.market, target.symbol);
        }
      } catch (error) {
        console.warn('市場搜尋失敗，改用股票代號直接查詢:', error);
      }

      const result = await ensureStockExists(targetSymbol, targetMarket);
      let stock: any = result.stock;

      try {
        const quote = await getStockQuote(stock.market, stock.symbol, stock.id, true);
        const latestPrice = quoteToLatestPrice(quote, stock.latest_price);
        if (latestPrice) {
          stock = { ...stock, latest_price: latestPrice };
          setRealtimeQuotes((quotes) => ({
            ...quotes,
            [stock.id]: latestPrice,
          }));
        }
      } catch (error) {
        console.warn(`載入 ${targetSymbol} 即時報價失敗:`, error);
      }

      // 確保 API 返回後才設置新股票
      // 使用 setTimeout 確保狀態清除後才設置新值，避免 WebSocket 訂閱時序問題
      setTimeout(() => {
        setDirectStock(stock);
        setSelectedStockId(stock.id);
      }, 100);

    } catch (error: any) {
      setSearchError(error.message || '查詢股票失敗');
      setDirectStock(null);
    } finally {
      setIsSearching(false);
    }
  };

  // 處理 Enter 鍵搜尋
  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const resetDirectSearch = () => {
    setSymbolInput('');
    setDirectStock(null);
    setSearchError(null);
  };

  // 清除直接查詢
  const handleClearSearch = () => {
    resetDirectSearch();
  };

  const handleSelectPortfolioView = () => {
    setViewMode('portfolio');
    setSelectedListId(null);
    setSelectedStockId(null);
    setShowListDropdown(false);
    resetDirectSearch();
  };

  const handleSelectStockList = (listId: number) => {
    setViewMode('list');
    setSelectedListId(listId);
    setSelectedStockId(null);
    setShowListDropdown(false);
    resetDirectSearch();
  };

  const handleSelectSidebarStock = (stockId: number) => {
    setSelectedStockId(stockId);
    resetDirectSearch();
  };

  return (
    <PageShell>
      <PageHeader
        title="即時圖表分析"
        description="查看即時價格走勢、均線與交易信號。"
      />

      {/* 主要內容區域 */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
        {/* 主圖表 */}
        <div className={cn('min-w-0 space-y-6', selectedStockDisplay ? 'order-1' : 'order-2 xl:order-1')}>
          {selectedStockDisplay ? (
            <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
              <div className="px-6 py-4 border-b border-gray-200">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div className="min-w-0">
                    <h2 className="text-2xl font-bold leading-tight text-gray-900">
                      {selectedStockDisplay.symbol} - {selectedStockDisplay.name}
                    </h2>
                    <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
                      <span className="inline-flex items-center gap-1 rounded-md bg-gray-50 px-2.5 py-1 font-semibold text-gray-900">
                        <TrendingUp className="h-3.5 w-3.5 text-blue-600" />
                        {selectedStockDisplay.market === 'TW' ? 'NT$' : '$'}
                        {currentPrice?.toFixed(2) || '--'}
                      </span>
                      <span
                        className={cn(
                          'inline-flex items-center gap-1 rounded-md px-2.5 py-1 font-semibold',
                          priceChange === null || priceChange === undefined
                            ? 'bg-gray-50 text-gray-600'
                            : isPriceUp
                              ? 'bg-green-50 text-green-700'
                              : 'bg-red-50 text-red-700'
                        )}
                      >
                        <Activity className="h-3.5 w-3.5" />
                        {priceChange !== null && priceChange !== undefined
                          ? `${priceChange >= 0 ? '+' : ''}${priceChange.toFixed(2)}`
                          : '--'}
                      </span>
                      <span
                        className={cn(
                          'inline-flex items-center gap-1 rounded-md px-2.5 py-1 font-semibold',
                          priceChangePercent === null || priceChangePercent === undefined
                            ? 'bg-gray-50 text-gray-600'
                            : isPercentUp
                              ? 'bg-green-50 text-green-700'
                              : 'bg-red-50 text-red-700'
                        )}
                      >
                        <BarChart3 className="h-3.5 w-3.5" />
                        {priceChangePercent !== null && priceChangePercent !== undefined
                          ? `${priceChangePercent >= 0 ? '+' : ''}${priceChangePercent.toFixed(2)}%`
                          : '--'}
                      </span>
                      <span
                        className={cn(
                          'inline-flex items-center gap-1 rounded-md px-2.5 py-1 font-semibold',
                          currentMarketStatus.is_open
                            ? 'bg-green-50 text-green-700'
                            : 'bg-orange-50 text-orange-700'
                        )}
                      >
                        <Activity className="h-3.5 w-3.5" />
                        {currentMarketStatus.is_open ? '開盤' : '休市'}
                      </span>
                    </div>
                  </div>
                  <div className="flex shrink-0 flex-wrap items-center gap-3">
                    {isAuthenticated && (
                      <div className="flex gap-2">
                        <button
                          onClick={() => setTransactionModal({
                            isOpen: true,
                            stock: selectedStockDisplay,
                            type: 'BUY'
                          })}
                          className="inline-flex h-10 min-w-20 items-center justify-center gap-2 whitespace-nowrap rounded-md bg-green-600 px-4 text-sm font-medium text-white transition-colors hover:bg-green-700"
                        >
                          <ShoppingCart className="w-4 h-4" />
                          買入
                        </button>
                        <button
                          onClick={() => setTransactionModal({
                            isOpen: true,
                            stock: selectedStockDisplay,
                            type: 'SELL'
                          })}
                          className="inline-flex h-10 min-w-20 items-center justify-center gap-2 whitespace-nowrap rounded-md bg-red-600 px-4 text-sm font-medium text-white transition-colors hover:bg-red-700"
                        >
                          <TrendingDown className="w-4 h-4" />
                          賣出
                        </button>
                      </div>
                    )}
                    {selectedStockDisplay.latest_price?.date && (
                      <div className="text-sm text-gray-500">
                        更新時間: {selectedStockDisplay.latest_price.date}
                      </div>
                    )}
                  </div>
                </div>
              </div>
              <div className="p-6">
                <RealtimePriceChart
                  key={selectedStockDisplay.id}
                  stock={{
                    id: selectedStockDisplay.id,
                    symbol: selectedStockDisplay.symbol,
                    name: selectedStockDisplay.name,
                    market: selectedStockDisplay.market,
                  }}
                  height={440}
                />
              </div>
            </div>
          ) : (
            <div className="flex h-[500px] items-center justify-center rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
              <div className="text-center text-gray-500">
                <BarChart3 className="mx-auto mb-4 h-12 w-12 text-gray-400" />
                <div className="text-xl font-medium mb-2">請選擇股票</div>
                <div className="text-sm">
                  {isAuthenticated
                    ? '從清單選擇股票，或使用上方快速查詢'
                    : '登入後可使用觀察清單，也可以使用上方快速查詢'}
                </div>
              </div>
            </div>
          )}
        </div>

        <aside className={cn('space-y-4', selectedStockDisplay ? 'order-2 xl:order-2' : 'order-1 xl:order-2')}>
          <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm xl:hidden">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              直接查詢
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={symbolInput}
                onChange={(e) => {
                  setSymbolInput(e.target.value.toUpperCase());
                  if (searchError) setSearchError(null);
                }}
                onKeyPress={handleKeyPress}
                onFocus={() => setShowListDropdown(false)}
                placeholder="AAPL, 2330"
                className={`min-w-0 flex-1 rounded-md border px-3 py-2 focus:border-blue-500 focus:ring-2 focus:ring-blue-500 ${
                  searchError ? 'border-red-500' : 'border-gray-300'
                }`}
                disabled={isSearching}
              />
              <button
                onClick={handleSearch}
                disabled={isSearching || !symbolInput.trim()}
                className="inline-flex h-10 w-10 items-center justify-center rounded-md bg-blue-600 text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-300"
                aria-label="查詢股票"
              >
                {isSearching ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                ) : (
                  <Search className="w-4 h-4" />
                )}
              </button>
              {directStock && (
                <button
                  onClick={handleClearSearch}
                  className="inline-flex h-10 w-10 items-center justify-center rounded-md bg-gray-200 text-gray-700 hover:bg-gray-300"
                  aria-label="清除查詢"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
            {searchError && (
              <p className="mt-1.5 flex items-center gap-1 text-sm text-red-600">
                {searchError}
              </p>
            )}
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <div ref={listDropdownRef} className="relative">
              <button
                type="button"
                onClick={() => {
                  if (!isAuthenticated) return;
                  setShowListDropdown(!showListDropdown);
                }}
                disabled={!isAuthenticated}
                className={`flex w-full items-center justify-between rounded-md border border-gray-300 bg-white px-3 py-2 text-left text-base font-semibold text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  isAuthenticated ? 'hover:border-gray-400' : 'cursor-not-allowed opacity-60'
                }`}
              >
                <span className="min-w-0 truncate">
                  {isAuthenticated ? sidebarTitle : '請先登入'}
                </span>
                <ChevronDown className="h-5 w-5 flex-shrink-0 text-gray-400" />
              </button>
              {!isAuthenticated && (
                <p className="mt-2 text-xs leading-5 text-gray-500">
                  登入後可使用觀察清單；價格優先顯示即時報價。
                </p>
              )}
              {isAuthenticated && (
                <p className="mt-2 text-xs leading-5 text-gray-500">
                  價格優先顯示即時報價，無法取得時顯示最新入庫價。
                </p>
              )}

              {showListDropdown && (
                <div className="absolute z-20 mt-1 max-h-72 w-full overflow-auto rounded-md border border-gray-300 bg-white shadow-lg">
                  <button
                    type="button"
                    onClick={handleSelectPortfolioView}
                    className={`w-full px-3 py-2 text-left hover:bg-gray-100 ${
                      viewMode === 'portfolio' ? 'bg-blue-50 text-blue-700' : 'text-gray-900'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="truncate">我的持倉</span>
                      <span className="flex-shrink-0 text-xs text-gray-500">
                        {portfolioStocks.length} 檔
                      </span>
                    </div>
                  </button>

                  <div className="border-t border-gray-200">
                    {loading && lists.length === 0 ? (
                      <div className="px-3 py-3 text-sm text-gray-500">載入中...</div>
                    ) : lists.length === 0 ? (
                      <div className="px-3 py-3 text-sm text-gray-500">尚無清單</div>
                    ) : (
                      lists.map((list) => (
                        <button
                          key={list.id}
                          type="button"
                          onClick={() => handleSelectStockList(list.id)}
                          className={`w-full px-3 py-2 text-left hover:bg-gray-100 ${
                            viewMode === 'list' && selectedListId === list.id
                              ? 'bg-blue-50 text-blue-700'
                              : 'text-gray-900'
                          }`}
                        >
                          <div className="flex items-center justify-between gap-3">
                            <span className="truncate">{list.name}</span>
                            <span className="flex-shrink-0 text-xs text-gray-500">
                              {list.stocks_count} 檔
                            </span>
                          </div>
                        </button>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            <div className="mt-3 max-h-[360px] space-y-2 overflow-y-auto">
              {sidebarLoading && sidebarStocks.length === 0 ? (
                <div className="rounded-lg bg-gray-50 px-3 py-4 text-sm text-gray-500">
                  載入中...
                </div>
              ) : sidebarStocks.length === 0 ? (
                <div className="rounded-lg bg-gray-50 px-3 py-4 text-sm text-gray-500">
                  尚無股票
                </div>
              ) : (
                sidebarStocks.map((stock) => {
                  const latestPrice = realtimeQuotes[stock.id] ?? stock.latest_price;
                  const priceLabel = latestPrice?.is_realtime ? '即時報價' : '最新入庫價';

                  return (
                    <button
                      key={stock.id}
                      onClick={() => handleSelectSidebarStock(stock.id)}
                      className={`w-full p-3 rounded-lg text-left transition-colors ${
                        selectedStockId === stock.id
                          ? 'bg-blue-50 border border-blue-200'
                          : 'bg-gray-50 hover:bg-gray-100 border border-transparent'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-gray-900 truncate">
                            {stock.symbol}
                          </div>
                          <div className="text-sm text-gray-600 truncate">
                            {stock.name}
                          </div>
                        </div>
                        {typeof latestPrice?.close === 'number' && (
                          <div className="ml-3 shrink-0 text-right">
                            <div className="text-[11px] text-gray-500">
                              {priceLabel}
                            </div>
                            <div className="text-sm font-medium text-gray-900">
                              {stock.market === 'TW' ? 'NT$' : '$'}
                              {latestPrice.close.toFixed(2)}
                            </div>
                            {typeof latestPrice.change_percent === 'number' && (
                              <div
                                className={cn(
                                  'text-xs font-medium',
                                  latestPrice.change_percent >= 0
                                    ? 'text-green-600'
                                    : 'text-red-600'
                                )}
                              >
                                {latestPrice.change_percent >= 0 ? '+' : ''}
                                {latestPrice.change_percent.toFixed(2)}%
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </div>

          <RealtimeSignals
            stockId={selectedStockDisplay?.id ?? null}
            symbol={selectedStockDisplay?.symbol}
            market={selectedStockDisplay?.market}
            enabled={isAuthenticated}
          />

          {selectedStockDisplay && (
            <MarketNewsPanel
              market={selectedStockDisplay.market}
              symbol={selectedStockDisplay.symbol}
            />
          )}
        </aside>
      </div>

      {/* 交易 Modal */}
      {transactionModal.isOpen && transactionModal.stock && (
        <TransactionModal
          isOpen={transactionModal.isOpen}
          onClose={() => setTransactionModal({
            isOpen: false,
            stock: null,
            type: 'BUY'
          })}
          stock={transactionModal.stock}
          transactionType={transactionModal.type}
        />
      )}
    </PageShell>
  );
};

export default RealtimeDashboard;
