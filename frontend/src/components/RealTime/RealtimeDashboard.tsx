/**
 * 即時圖表分析 - 單一股票顯示模式
 */
"use client";

import React, {
  useState,
  useEffect,
  useMemo,
  useRef,
  useCallback,
} from "react";
import dynamic from "next/dynamic";
import { useSearchParams } from "next/navigation";
import { useAppDispatch, useAppSelector } from "@/store";
import {
  fetchStockLists,
  fetchListStocks,
} from "@/store/slices/stockListSlice";
import { StocksApiService } from "@/services/stocksApi";
import {
  detectMarket,
  ensureStockExists,
} from "../../services/stockValidationApi";
import {
  getStockQuote,
  searchMarketSymbols,
  type MarketQuote,
} from "@/services/marketInfoApi";
import {
  ChevronDown,
  Activity,
  BarChart3,
  Search,
  X,
  ShoppingCart,
  TrendingDown,
} from "lucide-react";
import TransactionModal from "../Portfolio/TransactionModal";
import { getPortfolioList } from "@/services/portfolioApi";
import type { LatestPriceInfo, Portfolio, Stock } from "@/types";
import MarketNewsPanel from "@/components/Market/MarketNewsPanel";
import { PageHeader, PageShell } from "@/components/ui/page";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { inferMarketFromSymbol } from "@/lib/finance";
import { cn } from "@/lib/utils";

// 動態載入圖表組件
const RealtimePriceChart = dynamic(() => import("./RealtimePriceChart"), {
  ssr: false,
  loading: () => (
    <div
      className="flex h-[440px] items-center justify-center bg-card p-6"
      role="status"
      aria-live="polite"
    >
      <div className="text-center">
        <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2 border-muted border-t-primary" />
        <p className="text-sm text-muted-foreground">載入圖表中...</p>
      </div>
    </div>
  ),
});

const RealtimeSignals = dynamic(() => import("./RealtimeSignals"), {
  ssr: false,
  loading: () => (
    <div
      className="flex h-64 items-center justify-center rounded-lg border border-border bg-card p-6"
      role="status"
      aria-label="載入交易信號"
    >
      <div className="h-7 w-7 animate-spin rounded-full border-2 border-muted border-t-primary" />
    </div>
  ),
});

const quoteToLatestPrice = (
  quote: MarketQuote,
  fallback?: LatestPriceInfo | null,
): LatestPriceInfo | null => {
  if (typeof quote.price !== "number") {
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

const portfolioToStock = (portfolio: Portfolio): Stock => ({
  id: portfolio.stock_id,
  symbol: portfolio.stock_symbol || "",
  name: portfolio.stock_name || portfolio.stock_symbol || null,
  market: inferMarketFromSymbol(portfolio.stock_symbol),
  is_active: true,
  created_at: portfolio.created_at,
  updated_at: portfolio.updated_at,
  latest_price:
    portfolio.latest_price ??
    (portfolio.current_price != null
      ? {
          close: portfolio.current_price,
          change: null,
          change_percent: null,
          date: portfolio.updated_at,
          volume: null,
        }
      : null),
});

const normalizeUrlMarket = (
  market: string | null,
  symbol: string,
): "TW" | "US" => {
  const normalized = market?.toUpperCase();
  if (normalized === "TW" || normalized === "US") {
    return normalized;
  }
  return detectMarket(symbol);
};

const RealtimeDashboard: React.FC = () => {
  const dispatch = useAppDispatch();
  const searchParams = useSearchParams();
  const { isAuthenticated } = useAppSelector((state) => state.auth);
  const {
    lists,
    currentListStocks,
    loading,
    error: stockListError,
  } = useAppSelector((state) => state.stockList);

  const [viewMode, setViewMode] = useState<"list" | "portfolio">("list"); // 視圖模式：清單 or 持倉
  const [selectedListId, setSelectedListId] = useState<number | null>(null);
  const [selectedStockId, setSelectedStockId] = useState<number | null>(null);
  const [showListDropdown, setShowListDropdown] = useState(false);
  const [urlStockProcessed, setUrlStockProcessed] = useState(false);

  // 持倉相關狀態
  const [portfolioStocks, setPortfolioStocks] = useState<Portfolio[]>([]);
  const [portfolioLoading, setPortfolioLoading] = useState(false);
  const [portfolioError, setPortfolioError] = useState<string | null>(null);

  // 直接輸入股票代號的狀態
  const [symbolInput, setSymbolInput] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [directStock, setDirectStock] = useState<any | null>(null);
  const [realtimeQuotes, setRealtimeQuotes] = useState<
    Record<number, LatestPriceInfo>
  >({});

  // 交易 Modal 狀態
  const [transactionModal, setTransactionModal] = useState<{
    isOpen: boolean;
    stock: any | null;
    type: "BUY" | "SELL";
  }>({
    isOpen: false,
    stock: null,
    type: "BUY",
  });

  // Refs for dropdown containers
  const listDropdownRef = useRef<HTMLDivElement>(null);
  const hasRequestedListsRef = useRef(false);

  // 從 URL 參數讀取股票 ID 和來源
  const stockIdFromUrl = searchParams.get("stock");
  const symbolFromUrl = searchParams.get("symbol");
  const marketFromUrl = searchParams.get("market");
  const nameFromUrl = searchParams.get("name");
  const sourceFromUrl = searchParams.get("source"); // 新增：檢測來源（如 'portfolio'）

  useEffect(() => {
    setUrlStockProcessed(false);
  }, [
    stockIdFromUrl,
    symbolFromUrl,
    marketFromUrl,
    nameFromUrl,
    sourceFromUrl,
  ]);

  // 載入清單
  useEffect(() => {
    if (!isAuthenticated) {
      hasRequestedListsRef.current = false;
      return;
    }

    if (!hasRequestedListsRef.current) {
      hasRequestedListsRef.current = true;
      void dispatch(fetchStockLists());
    }
  }, [isAuthenticated, dispatch]);

  // 當從持倉管理跳轉時，自動切換到持倉視圖
  useEffect(() => {
    if (sourceFromUrl === "portfolio" && isAuthenticated) {
      setViewMode("portfolio");
    }
  }, [sourceFromUrl, isAuthenticated]);

  const loadPortfolioStocks = useCallback(async () => {
    if (!isAuthenticated || viewMode !== "portfolio") return;

    setPortfolioLoading(true);
    setPortfolioError(null);
    try {
      const response = await getPortfolioList();
      setPortfolioStocks(response.items || []);
    } catch (error) {
      console.error("載入持倉失敗:", error);
      setPortfolioStocks([]);
      setPortfolioError("無法載入持倉，請稍後再試。");
    } finally {
      setPortfolioLoading(false);
    }
  }, [isAuthenticated, viewMode]);

  // 載入持倉數據（當切換到持倉視圖時）
  useEffect(() => {
    void loadPortfolioStocks();
  }, [loadPortfolioStocks]);

  // 當選擇清單時載入該清單的股票
  useEffect(() => {
    if (viewMode === "list" && selectedListId) {
      dispatch(fetchListStocks(selectedListId));
    }
  }, [selectedListId, viewMode, dispatch]);

  // 當清單載入後，自動選擇第一個清單
  useEffect(() => {
    if (
      viewMode === "list" &&
      lists.length > 0 &&
      !selectedListId &&
      !directStock &&
      !stockIdFromUrl &&
      !symbolFromUrl
    ) {
      setSelectedListId(lists[0].id);
    }
  }, [
    lists,
    selectedListId,
    viewMode,
    directStock,
    stockIdFromUrl,
    symbolFromUrl,
  ]);

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

    if (sourceFromUrl !== "portfolio" && hintedSymbol && hintedMarket) {
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
          const quote = await getStockQuote(
            stock.market,
            stock.symbol,
            stock.id,
            true,
          );
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
    if (
      sourceFromUrl === "portfolio" &&
      isAuthenticated &&
      portfolioStocks.length === 0
    ) {
      return;
    }

    if (sourceFromUrl === "portfolio" && portfolioStocks.length > 0) {
      setUrlStockProcessed(true);
      const portfolioStock = portfolioStocks.find(
        (p) => p.stock_id === targetStockId,
      );
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
          const quote = await getStockQuote(
            stock.market,
            stock.symbol,
            stock.id,
            true,
          );
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
    if (viewMode !== "list") return;

    // 只有在 URL 參數未處理或已處理完成時才執行自動選擇
    const shouldAutoSelect =
      (!stockIdFromUrl && !symbolFromUrl) || urlStockProcessed;

    if (currentListStocks.length > 0 && shouldAutoSelect) {
      // 如果沒有選擇股票，或選擇的股票不在當前清單中，則自動選擇第一個股票
      if (!selectedStockId) {
        setSelectedStockId(currentListStocks[0].id);
      } else {
        const stockInList = currentListStocks.find(
          (s) => s.id === selectedStockId,
        );
        if (!stockInList) {
          // 當前選擇的股票不在新清單中，選擇第一個股票
          setSelectedStockId(currentListStocks[0].id);
        }
      }
    }
  }, [
    currentListStocks,
    selectedStockId,
    stockIdFromUrl,
    symbolFromUrl,
    urlStockProcessed,
    viewMode,
  ]);

  // 切換到持倉視圖後，讓右側清單直接帶出第一檔持倉
  useEffect(() => {
    if (viewMode !== "portfolio" || portfolioStocks.length === 0) return;

    if (!selectedStockId) {
      setSelectedStockId(portfolioStocks[0].stock_id);
      return;
    }

    const stockInPortfolio = portfolioStocks.some(
      (portfolio) => portfolio.stock_id === selectedStockId,
    );
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

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setShowListDropdown(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  const selectedList = useMemo(() => {
    return lists.find((list) => list.id === selectedListId);
  }, [lists, selectedListId]);

  const selectedStock = useMemo(() => {
    // 如果有直接查詢的股票，優先使用
    if (directStock) {
      return directStock;
    }
    // 如果是持倉視圖，從持倉列表中查找並轉換格式
    if (viewMode === "portfolio" && selectedStockId) {
      const portfolio = portfolioStocks.find(
        (p) => p.stock_id === selectedStockId,
      );
      if (portfolio) {
        return portfolioToStock(portfolio);
      }
    }
    // 否則從清單中選擇
    return currentListStocks.find((stock) => stock.id === selectedStockId);
  }, [
    currentListStocks,
    selectedStockId,
    directStock,
    viewMode,
    portfolioStocks,
  ]);

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
    if (!selectedStockDisplay) return { is_open: false, market: "" };

    const now = new Date();
    const utcHour = now.getUTCHours();
    const utcMinute = now.getUTCMinutes();
    const utcDay = now.getUTCDay(); // 0 = 週日, 1 = 週一, ..., 6 = 週六

    if (selectedStockDisplay.market === "US") {
      // 美股交易時間（UTC）：週一至週五 14:30-21:00（夏令時）或 15:30-22:00（冬令時）
      // 簡化版本：使用 14:30-21:00
      const isWeekday = utcDay >= 1 && utcDay <= 5;
      const isOpen =
        isWeekday &&
        ((utcHour === 14 && utcMinute >= 30) ||
          (utcHour > 14 && utcHour < 21) ||
          (utcHour === 21 && utcMinute === 0));
      return { is_open: isOpen, market: "US" };
    } else {
      // 台股交易時間（UTC）：週一至週五 01:00-05:30（UTC = 台北時間 09:00-13:30）
      const isWeekday = utcDay >= 1 && utcDay <= 5;
      const isOpen =
        isWeekday &&
        (utcHour === 1 ||
          (utcHour > 1 && utcHour < 5) ||
          (utcHour === 5 && utcMinute <= 30));
      return { is_open: isOpen, market: "TW" };
    }
  };

  const currentMarketStatus = getCurrentMarketStatus();
  const isPriceUp =
    priceChange !== null && priceChange !== undefined && priceChange >= 0;

  const sidebarStocks = useMemo<Stock[]>(() => {
    if (viewMode !== "portfolio") {
      return currentListStocks;
    }

    return portfolioStocks.map(portfolioToStock);
  }, [currentListStocks, portfolioStocks, viewMode]);

  const sidebarQuoteSignature = useMemo(
    () =>
      sidebarStocks
        .map((stock) => `${stock.id}:${stock.market}:${stock.symbol}`)
        .join("|"),
    [sidebarStocks],
  );

  useEffect(() => {
    if (!sidebarQuoteSignature) return;

    let cancelled = false;
    const stocksToQuote = sidebarStocks.slice(0, 30);

    const loadRealtimeQuotes = async () => {
      const results = await Promise.allSettled(
        stocksToQuote.map(async (stock) => {
          const quote = await getStockQuote(
            stock.market,
            stock.symbol,
            stock.id,
            true,
          );
          const latestPrice = quoteToLatestPrice(quote, stock.latest_price);
          return latestPrice ? ([stock.id, latestPrice] as const) : null;
        }),
      );

      if (cancelled) return;

      const nextQuotes = results.reduce<Record<number, LatestPriceInfo>>(
        (acc, result) => {
          if (result.status === "fulfilled" && result.value) {
            const [stockId, latestPrice] = result.value;
            acc[stockId] = latestPrice;
          }
          return acc;
        },
        {},
      );

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

  const sidebarTitle =
    viewMode === "portfolio"
      ? "我的持倉"
      : selectedList?.name || "我的觀察清單";
  const sidebarLoading = viewMode === "portfolio" ? portfolioLoading : loading;
  const sidebarError =
    viewMode === "portfolio" ? portfolioError : stockListError;

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
          return (
            normalizedSymbol === normalizedQuery ||
            normalizedSymbol.replace(/\.(TW|TWO)$/, "") === normalizedQuery
          );
        });
        const target = exactResult ?? results[0];
        if (target) {
          targetSymbol = target.symbol;
          targetMarket = normalizeUrlMarket(target.market, target.symbol);
        }
      } catch (error) {
        console.warn("市場搜尋失敗，改用股票代號直接查詢:", error);
      }

      const result = await ensureStockExists(targetSymbol, targetMarket);
      let stock: any = result.stock;

      try {
        const quote = await getStockQuote(
          stock.market,
          stock.symbol,
          stock.id,
          true,
        );
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
      setSearchError(error.message || "查詢股票失敗");
      setDirectStock(null);
    } finally {
      setIsSearching(false);
    }
  };

  const resetDirectSearch = () => {
    setSymbolInput("");
    setDirectStock(null);
    setSearchError(null);
  };

  // 清除直接查詢
  const handleClearSearch = () => {
    resetDirectSearch();
  };

  const handleSelectPortfolioView = () => {
    setViewMode("portfolio");
    setSelectedListId(null);
    setSelectedStockId(null);
    setShowListDropdown(false);
    resetDirectSearch();
  };

  const handleSelectStockList = (listId: number) => {
    setViewMode("list");
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
        title="即時研究工作台"
        description="整合即時價格、技術走勢、策略信號與市場資訊，集中完成標的研判。"
      />

      <section
        aria-labelledby="instrument-search-title"
        className="rounded-lg border border-border bg-card px-4 py-3 sm:px-5"
      >
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="min-w-0">
            <h2
              id="instrument-search-title"
              className="text-sm font-semibold text-foreground"
            >
              標的查詢
            </h2>
            <p className="mt-0.5 text-xs leading-5 text-muted-foreground">
              輸入美股或台股代號，直接切換研究標的。
            </p>
          </div>

          <form
            className="w-full lg:max-w-md"
            role="search"
            onSubmit={(event) => {
              event.preventDefault();
              void handleSearch();
            }}
          >
            <label htmlFor="realtime-symbol-search" className="sr-only">
              股票代號
            </label>
            <div className="flex gap-2">
              <Input
                id="realtime-symbol-search"
                type="text"
                value={symbolInput}
                onChange={(event) => {
                  setSymbolInput(event.target.value.toUpperCase());
                  if (searchError) setSearchError(null);
                }}
                onFocus={() => setShowListDropdown(false)}
                placeholder="例如 AAPL、2330"
                className={cn(
                  "min-w-0 flex-1",
                  searchError && "border-destructive",
                )}
                disabled={isSearching}
                aria-invalid={Boolean(searchError)}
                aria-describedby={
                  searchError ? "realtime-search-error" : undefined
                }
              />
              <Button
                type="submit"
                size="icon"
                disabled={isSearching || !symbolInput.trim()}
                aria-label={isSearching ? "正在查詢股票" : "查詢股票"}
              >
                {isSearching ? (
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground/40 border-t-primary-foreground" />
                ) : (
                  <Search />
                )}
              </Button>
              {(directStock || symbolInput) && (
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={handleClearSearch}
                  aria-label="清除查詢"
                >
                  <X />
                </Button>
              )}
            </div>
            {searchError && (
              <p
                id="realtime-search-error"
                className="mt-2 text-sm text-destructive"
                role="alert"
              >
                {searchError}
              </p>
            )}
          </form>
        </div>
      </section>

      <div className="grid min-w-0 grid-cols-1 gap-5 lg:grid-cols-[280px_minmax(0,1fr)] lg:items-start">
        <aside
          className="order-1 lg:sticky lg:top-20"
          aria-label="研究標的清單"
        >
          <section className="overflow-visible rounded-lg border border-border bg-card">
            <div className="border-b border-border p-4">
              <div className="mb-3 flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-sm font-semibold text-foreground">
                    研究標的
                  </h2>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {sidebarStocks.length} 檔標的
                    {sidebarLoading && sidebarStocks.length > 0
                      ? " · 更新中"
                      : ""}
                  </p>
                </div>
                <span
                  className={cn(
                    "h-2 w-2 rounded-full",
                    sidebarError
                      ? "bg-destructive"
                      : sidebarLoading
                        ? "animate-pulse bg-warning"
                        : sidebarStocks.length > 0
                          ? "bg-success"
                          : "bg-muted-foreground/40",
                  )}
                  aria-hidden="true"
                />
              </div>

              <div ref={listDropdownRef} className="relative">
                <button
                  type="button"
                  onClick={() => {
                    if (isAuthenticated) {
                      setShowListDropdown((isOpen) => !isOpen);
                    }
                  }}
                  disabled={!isAuthenticated}
                  className="flex h-9 w-full items-center justify-between rounded-md border border-input bg-card px-3 text-left text-sm font-medium text-foreground outline-none transition-colors hover:border-primary/30 focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-60"
                  aria-expanded={showListDropdown}
                  aria-controls="realtime-list-menu"
                  aria-haspopup="menu"
                >
                  <span className="min-w-0 truncate">
                    {isAuthenticated ? sidebarTitle : "登入後使用觀察清單"}
                  </span>
                  <ChevronDown
                    className={cn(
                      "h-4 w-4 shrink-0 text-muted-foreground transition-transform",
                      showListDropdown && "rotate-180",
                    )}
                  />
                </button>

                {showListDropdown && (
                  <div
                    id="realtime-list-menu"
                    role="menu"
                    className="absolute z-30 mt-1 max-h-72 w-full overflow-auto rounded-md border border-border bg-popover py-1 text-popover-foreground shadow-lg"
                  >
                    <button
                      type="button"
                      role="menuitem"
                      onClick={handleSelectPortfolioView}
                      className={cn(
                        "flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm hover:bg-accent focus-visible:bg-accent focus-visible:outline-none",
                        viewMode === "portfolio" &&
                          "bg-primary/10 text-primary",
                      )}
                    >
                      <span>我的持倉</span>
                      <span className="text-xs text-muted-foreground">
                        {portfolioStocks.length} 檔
                      </span>
                    </button>
                    <div className="my-1 border-t border-border" />
                    {loading && lists.length === 0 ? (
                      <div
                        className="px-3 py-3 text-sm text-muted-foreground"
                        role="status"
                      >
                        載入清單中...
                      </div>
                    ) : lists.length === 0 ? (
                      <div className="px-3 py-3 text-sm text-muted-foreground">
                        尚無觀察清單
                      </div>
                    ) : (
                      lists.map((list) => (
                        <button
                          key={list.id}
                          type="button"
                          role="menuitem"
                          onClick={() => handleSelectStockList(list.id)}
                          className={cn(
                            "flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm hover:bg-accent focus-visible:bg-accent focus-visible:outline-none",
                            viewMode === "list" &&
                              selectedListId === list.id &&
                              "bg-primary/10 text-primary",
                          )}
                        >
                          <span className="truncate">{list.name}</span>
                          <span className="shrink-0 text-xs text-muted-foreground">
                            {list.stocks_count} 檔
                          </span>
                        </button>
                      ))
                    )}
                  </div>
                )}
              </div>

              <p className="mt-2 text-xs leading-5 text-muted-foreground">
                {isAuthenticated
                  ? "優先顯示即時報價，無法取得時改用最新入庫價。"
                  : "仍可使用上方查詢研究單一標的。"}
              </p>
            </div>

            {sidebarError && (
              <div
                className="m-3 rounded-md border border-destructive/20 bg-destructive/5 px-3 py-2 text-sm text-destructive"
                role="alert"
              >
                {sidebarError}
              </div>
            )}

            <div className="max-h-[440px] overflow-y-auto" aria-live="polite">
              {sidebarLoading && sidebarStocks.length === 0 ? (
                <div
                  className="px-4 py-10 text-center text-sm text-muted-foreground"
                  role="status"
                >
                  載入研究標的中...
                </div>
              ) : !sidebarError && sidebarStocks.length === 0 ? (
                <div className="px-4 py-10 text-center">
                  <p className="text-sm font-medium text-foreground">
                    尚無可研究標的
                  </p>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">
                    使用上方查詢，或先在股票管理建立觀察清單。
                  </p>
                </div>
              ) : sidebarStocks.length > 0 ? (
                <div className="divide-y divide-border">
                  {sidebarStocks.map((stock) => {
                    const latestPrice =
                      realtimeQuotes[stock.id] ?? stock.latest_price;
                    const isSelected = selectedStockId === stock.id;

                    return (
                      <button
                        key={stock.id}
                        type="button"
                        onClick={() => handleSelectSidebarStock(stock.id)}
                        className={cn(
                          "w-full px-4 py-3 text-left transition-colors hover:bg-accent/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring",
                          isSelected && "bg-primary/5",
                        )}
                        aria-pressed={isSelected}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <span
                                className={cn(
                                  "truncate text-sm font-semibold",
                                  isSelected
                                    ? "text-primary"
                                    : "text-foreground",
                                )}
                              >
                                {stock.symbol}
                              </span>
                              {latestPrice?.is_realtime && (
                                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-success">
                                  <span className="sr-only">即時報價</span>
                                </span>
                              )}
                            </div>
                            <p className="mt-0.5 truncate text-xs text-muted-foreground">
                              {stock.name || stock.market}
                            </p>
                          </div>
                          <div className="shrink-0 text-right tabular-nums">
                            <div className="text-sm font-medium text-foreground">
                              {typeof latestPrice?.close === "number" ? (
                                <>
                                  {stock.market === "TW" ? "NT$" : "$"}
                                  {latestPrice.close.toFixed(2)}
                                </>
                              ) : (
                                "--"
                              )}
                            </div>
                            {typeof latestPrice?.change_percent ===
                              "number" && (
                              <div
                                className={cn(
                                  "mt-0.5 text-xs font-medium",
                                  latestPrice.change_percent >= 0
                                    ? "text-success"
                                    : "text-destructive",
                                )}
                              >
                                {latestPrice.change_percent >= 0 ? "+" : ""}
                                {latestPrice.change_percent.toFixed(2)}%
                              </div>
                            )}
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              ) : null}
            </div>
          </section>
        </aside>

        <div className="order-2 min-w-0 space-y-5">
          {selectedStockDisplay ? (
            <section
              className="overflow-hidden rounded-lg border border-border bg-card"
              aria-labelledby="selected-instrument-title"
            >
              <div className="px-4 py-4 sm:px-5">
                <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2
                        id="selected-instrument-title"
                        className="text-xl font-semibold tracking-tight text-foreground sm:text-2xl"
                      >
                        {selectedStockDisplay.symbol}
                      </h2>
                      <span className="rounded border border-border bg-muted px-1.5 py-0.5 text-[11px] font-medium text-muted-foreground">
                        {selectedStockDisplay.market === "TW" ? "台股" : "美股"}
                      </span>
                      <span
                        title="依一般交易時段估算，不含市場假日與提前收盤"
                        className={cn(
                          "inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] font-medium",
                          currentMarketStatus.is_open
                            ? "bg-success/10 text-success"
                            : "bg-warning/10 text-warning",
                        )}
                      >
                        <Activity className="h-3 w-3" />
                        {currentMarketStatus.is_open ? "估算開盤" : "估算休市"}
                      </span>
                    </div>

                    <p className="mt-1 truncate text-sm text-muted-foreground">
                      {selectedStockDisplay.name || "未提供公司名稱"}
                    </p>
                    <div className="mt-3 flex flex-wrap items-baseline gap-x-3 gap-y-1 tabular-nums">
                      <span className="text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
                        {selectedStockDisplay.market === "TW" ? "NT$" : "$"}
                        {typeof currentPrice === "number"
                          ? currentPrice.toFixed(2)
                          : "--"}
                      </span>
                      <span
                        className={cn(
                          "text-sm font-semibold",
                          priceChange === null || priceChange === undefined
                            ? "text-muted-foreground"
                            : isPriceUp
                              ? "text-success"
                              : "text-destructive",
                        )}
                      >
                        {priceChange !== null && priceChange !== undefined ? (
                          <>
                            {priceChange >= 0 ? "+" : ""}
                            {priceChange.toFixed(2)}
                          </>
                        ) : (
                          "--"
                        )}
                        {" · "}
                        {priceChangePercent !== null &&
                        priceChangePercent !== undefined ? (
                          <>
                            {priceChangePercent >= 0 ? "+" : ""}
                            {priceChangePercent.toFixed(2)}%
                          </>
                        ) : (
                          "--"
                        )}
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-col gap-2 xl:items-end">
                    {isAuthenticated && (
                      <div className="flex gap-2">
                        <Button
                          type="button"
                          variant="successOutline"
                          size="sm"
                          onClick={() =>
                            setTransactionModal({
                              isOpen: true,
                              stock: selectedStockDisplay,
                              type: "BUY",
                            })
                          }
                        >
                          <ShoppingCart />
                          買入
                        </Button>
                        <Button
                          type="button"
                          variant="destructiveOutline"
                          size="sm"
                          onClick={() =>
                            setTransactionModal({
                              isOpen: true,
                              stock: selectedStockDisplay,
                              type: "SELL",
                            })
                          }
                        >
                          <TrendingDown />
                          賣出
                        </Button>
                      </div>
                    )}
                    {selectedStockDisplay.latest_price?.date && (
                      <p className="text-xs text-muted-foreground">
                        最後更新 {selectedStockDisplay.latest_price.date}
                      </p>
                    )}
                  </div>
                </div>
              </div>

              <div className="border-t border-border p-2 sm:p-4">
                <RealtimePriceChart
                  key={selectedStockDisplay.id}
                  stock={{
                    id: selectedStockDisplay.id,
                    symbol: selectedStockDisplay.symbol,
                    name: selectedStockDisplay.name,
                    market: selectedStockDisplay.market,
                  }}
                  height={440}
                  allowBackfill={isAuthenticated}
                />
              </div>
            </section>
          ) : isSearching || sidebarLoading ? (
            <section
              className="flex h-[500px] items-center justify-center rounded-lg border border-border bg-card p-6"
              role="status"
            >
              <div className="text-center">
                <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2 border-muted border-t-primary" />
                <p className="text-sm font-medium text-foreground">
                  {isSearching ? "正在查詢標的" : "正在載入研究標的"}
                </p>
              </div>
            </section>
          ) : (
            <section className="flex h-[500px] items-center justify-center rounded-lg border border-border bg-card p-6">
              <div className="max-w-sm text-center">
                <span className="mx-auto flex h-11 w-11 items-center justify-center rounded-md border border-border bg-muted text-muted-foreground">
                  <BarChart3 className="h-5 w-5" />
                </span>
                <h2 className="mt-4 text-base font-semibold text-foreground">
                  選擇一檔標的開始研究
                </h2>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">
                  {isAuthenticated
                    ? "先從上方查詢，或從研究標的清單選擇股票。"
                    : "可直接查詢股票；登入後可同步持倉與觀察清單。"}
                </p>
              </div>
            </section>
          )}

          <section
            className={cn(
              "grid min-w-0 gap-5",
              selectedStockDisplay &&
                "2xl:grid-cols-[minmax(0,1fr)_minmax(300px,0.72fr)]",
            )}
            aria-label="即時研究資訊"
          >
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
          </section>
        </div>
      </div>

      {transactionModal.isOpen && transactionModal.stock && (
        <TransactionModal
          isOpen={transactionModal.isOpen}
          onClose={() =>
            setTransactionModal({
              isOpen: false,
              stock: null,
              type: "BUY",
            })
          }
          stock={transactionModal.stock}
          transactionType={transactionModal.type}
          onSuccess={() => void loadPortfolioStocks()}
        />
      )}
    </PageShell>
  );
};

export default RealtimeDashboard;
