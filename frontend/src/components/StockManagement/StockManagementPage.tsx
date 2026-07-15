/**
 * 股票管理頁面組件
 */
"use client";

import React, { useState, useMemo, useEffect, useId } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useAppDispatch, useAppSelector } from "../../store";
import { addToast } from "../../store/slices/uiSlice";
import {
  fetchListStocks,
  addStockToList,
  removeStockFromList,
} from "../../store/slices/stockListSlice";
import { useDeleteStock, useCreateStock } from "../../hooks/useStocks";
import StocksApiService from "../../services/stocksApi";
import { getPortfolioList } from "../../services/portfolioApi";
import {
  detectMarket,
  formatStockSymbol,
} from "../../services/stockValidationApi";
import ConfirmDialog from "../ui/ConfirmDialog";
import TransactionModal from "../Portfolio/TransactionModal";
import StockReorderModal from "./StockReorderModal";
import { Button } from "../ui/button";
import { MetricCard, PageHeader, PageShell, ToolbarPanel } from "../ui/page";
import { Badge } from "../ui/badge";
import { Input } from "../ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../ui/table";
import {
  AlertCircle,
  ArrowUpDown,
  BarChart3,
  Bell,
  LoaderCircle,
  Plus,
  RefreshCw,
  Search,
  ShoppingCart,
  Trash2,
  TrendingDown,
} from "lucide-react";
import UnifiedStockSelector from "./UnifiedStockSelector";
import * as stockListApi from "../../services/stockListApi";
import PriceAlertModal from "./PriceAlertModal";
import { useDialogA11y } from "@/hooks/useDialogA11y";
import { formatLocalDateInput, inferMarketFromSymbol } from "@/lib/finance";
import type { Portfolio, Stock } from "@/types";

const PRICE_BACKFILL_YEARS = 3;

const getPriceBackfillRange = () => {
  const endDate = new Date();
  const startDate = new Date(endDate);
  startDate.setFullYear(startDate.getFullYear() - PRICE_BACKFILL_YEARS);

  return {
    start_date: formatLocalDateInput(startDate),
    end_date: formatLocalDateInput(endDate),
  };
};

const portfolioToStock = (portfolio: Portfolio): Stock => {
  const symbol = portfolio.stock_symbol || String(portfolio.stock_id);

  return {
    id: portfolio.stock_id,
    symbol,
    name: portfolio.stock_name || null,
    market: inferMarketFromSymbol(symbol),
    is_active: true,
    created_at: portfolio.created_at,
    updated_at: portfolio.updated_at,
    is_portfolio: true,
    latest_price:
      portfolio.current_price == null
        ? null
        : {
            close: portfolio.current_price,
            change: null,
            change_percent: null,
            date: null,
            volume: null,
          },
  };
};

const StockManagementPage: React.FC = () => {
  const addDialogTitleId = useId();
  const addDialogDescriptionId = useId();
  const router = useRouter();
  const dispatch = useAppDispatch();
  const [searchTerm, setSearchTerm] = useState("");
  const [showAddModal, setShowAddModal] = useState(false);
  const [isBackfilling, setIsBackfilling] = useState(false);
  const [isAddingStock, setIsAddingStock] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<{
    isOpen: boolean;
    stockId: number | null;
    stockName: string;
  }>({
    isOpen: false,
    stockId: null,
    stockName: "",
  });
  const [stockSymbol, setStockSymbol] = useState("");
  const [viewMode, setViewMode] = useState<"all" | "portfolio">("all");
  const [transactionModal, setTransactionModal] = useState<{
    isOpen: boolean;
    stock: any | null;
    type: "BUY" | "SELL";
  }>({
    isOpen: false,
    stock: null,
    type: "BUY",
  });
  const [priceAlertModal, setPriceAlertModal] = useState<{
    isOpen: boolean;
    stock: any | null;
  }>({
    isOpen: false,
    stock: null,
  });
  const [isReorderModalOpen, setIsReorderModalOpen] = useState(false);

  // 從 Redux 獲取清單股票和清單列表
  const {
    currentListStocks,
    currentListStocksListId,
    activeStocksListId,
    lists,
    currentList,
    loading: stockListLoading,
    error: stockListError,
  } = useAppSelector((state) => state.stockList);

  // 使用 Redux 的 currentList.id 作為當前清單 ID
  const currentListId = currentList?.id || null;
  const auth = useAppSelector((state) => state.auth);
  const { isAuthenticated } = auth;
  const authInitialized = auth.initialized ?? true;

  // 檢查登入狀態，未登入則重定向到登入頁面
  useEffect(() => {
    if (authInitialized && !isAuthenticated) {
      router.replace("/login?redirect=/stocks");
    }
  }, [authInitialized, isAuthenticated, router]);

  // 當清單改變時，載入清單中的股票
  useEffect(() => {
    if (currentListId && viewMode === "all") {
      dispatch(fetchListStocks(currentListId));
    }
  }, [currentListId, viewMode, dispatch]);

  const shouldFetchPortfolio = isAuthenticated && viewMode === "portfolio";

  // 持倉端點回傳完整清單；搜尋在客戶端完成，避免依賴全域股票的 is_portfolio 欄位。
  const {
    data: portfolioResponse,
    isLoading,
    error: queryError,
    refetch,
  } = useQuery({
    queryKey: ["portfolio", "stock-management"],
    queryFn: getPortfolioList,
    enabled: shouldFetchPortfolio,
    staleTime: 60 * 1000,
    gcTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  });

  const startBackgroundPriceBackfill = (
    stockId: number,
    symbol: string,
    listId: number | null = currentListId,
  ) => {
    void StocksApiService.backfillStockData(stockId, getPriceBackfillRange())
      .then(() => {
        if (listId) {
          dispatch(fetchListStocks(listId));
        } else {
          void refetch();
        }
      })
      .catch((backfillError) => {
        console.warn("背景價格回填失敗:", backfillError);
        dispatch(
          addToast({
            type: "warning",
            title: "價格資料更新中",
            message: `${symbol} 已加入清單，但價格資料暫時無法完成回填，稍後可重新載入。`,
          }),
        );
      });
  };

  // 使用 React Query 刪除 mutation
  const deleteStockMutation = useDeleteStock({
    onSuccess: () => {
      dispatch(
        addToast({
          type: "success",
          title: "成功",
          message: "已成功移除股票",
        }),
      );
      // 立即重新獲取列表
      refetch();
    },
    onError: () => {
      dispatch(
        addToast({
          type: "error",
          title: "錯誤",
          message: "移除股票失敗，請稍後再試",
        }),
      );
    },
  });

  // 使用 React Query 新增 mutation
  const createStockMutation = useCreateStock({
    onSuccess: async (newStock) => {
      // 如果有選中的清單，自動添加到清單並重新獲取清單股票（包含最新價格）
      if (currentListId && newStock?.id) {
        try {
          await dispatch(
            addStockToList({
              listId: currentListId,
              data: { stock_id: newStock.id },
            }),
          ).unwrap();

          // 重新獲取清單股票（包含最新價格）
          await dispatch(fetchListStocks(currentListId));

          startBackgroundPriceBackfill(
            newStock.id,
            newStock.symbol,
            currentListId,
          );

          dispatch(
            addToast({
              type: "success",
              title: "成功",
              message: `已將 ${newStock.symbol} 添加到清單，價格資料正在背景更新`,
            }),
          );
        } catch (error) {
          console.error("添加股票到清單失敗:", error);
          dispatch(
            addToast({
              type: "error",
              title: "錯誤",
              message: "已新增股票，但添加到清單失敗",
            }),
          );
        }
      } else {
        // 如果不在清單視圖，刷新所有股票列表
        await refetch();
        if (newStock?.id) {
          startBackgroundPriceBackfill(newStock.id, newStock.symbol, null);
        }
        dispatch(
          addToast({
            type: "success",
            title: "成功",
            message: "已新增股票，價格資料正在背景更新",
          }),
        );
      }
    },
    onError: (error: any) => {
      dispatch(
        addToast({
          type: "error",
          title: "錯誤",
          message: error.response?.data?.detail || "新增股票失敗，請稍後再試",
        }),
      );
    },
  });

  const portfolioStocks = useMemo(
    () => (portfolioResponse?.items || []).map(portfolioToStock),
    [portfolioResponse?.items],
  );
  const stocks = useMemo(() => {
    if (viewMode === "portfolio") {
      const trimmedSearchTerm = searchTerm.trim().toLowerCase();
      if (!trimmedSearchTerm) {
        return portfolioStocks;
      }

      return portfolioStocks.filter((stock) => {
        const symbol = stock.symbol.toLowerCase();
        const name = stock.name?.toLowerCase() || "";
        return (
          symbol.includes(trimmedSearchTerm) || name.includes(trimmedSearchTerm)
        );
      });
    } else if (viewMode === "all" && currentListId) {
      // 清單視圖：直接使用 Redux 中的 currentListStocks（已包含完整 Stock 對象和 latest_price）
      // 若狀態仍標記為另一份清單，先不要顯示，避免切換清單時閃過舊資料。
      if (
        currentListStocksListId !== null &&
        currentListStocksListId !== undefined &&
        currentListStocksListId !== currentListId
      ) {
        return [];
      }

      const trimmedSearchTerm = searchTerm.trim().toLowerCase();
      if (!trimmedSearchTerm) {
        return currentListStocks;
      }

      return currentListStocks.filter((stock) => {
        const symbol = stock.symbol?.toLowerCase() || "";
        const name = stock.name?.toLowerCase() || "";
        return (
          symbol.includes(trimmedSearchTerm) || name.includes(trimmedSearchTerm)
        );
      });
    }
    // 如果沒有選擇清單，不顯示任何股票
    return [];
  }, [
    portfolioStocks,
    viewMode,
    currentListId,
    currentListStocks,
    currentListStocksListId,
    searchTerm,
  ]);
  const listLoading =
    viewMode === "all" &&
    Boolean(currentListId) &&
    currentListStocks.length === 0 &&
    (stockListLoading || activeStocksListId === currentListId);
  const loading =
    listLoading ||
    (shouldFetchPortfolio && isLoading) ||
    deleteStockMutation.isPending;
  const addStockPending = isAddingStock || createStockMutation.isPending;
  const error =
    viewMode === "all"
      ? stockListError
      : shouldFetchPortfolio
        ? queryError?.message || null
        : null;

  const closeAddDialog = () => {
    setShowAddModal(false);
    setStockSymbol("");
  };
  const addDialogRef = useDialogA11y(showAddModal, closeAddDialog);

  // 打開刪除確認對話框
  const handleDeleteStock = (stockId: number, stockName: string) => {
    setDeleteConfirm({
      isOpen: true,
      stockId,
      stockName,
    });
  };

  // 確認刪除/移除
  const confirmDelete = async () => {
    if (!deleteConfirm.stockId) {
      return;
    }

    // 只在清單模式允許移除股票
    if (viewMode === "all" && currentListId) {
      try {
        await dispatch(
          removeStockFromList({
            listId: currentListId,
            stockId: deleteConfirm.stockId,
          }),
        ).unwrap();

        dispatch(
          addToast({
            type: "success",
            title: "成功",
            message: "已從清單中移除股票",
          }),
        );

        // 重新載入清單股票
        if (currentListId) {
          dispatch(fetchListStocks(currentListId));
        }
      } catch (error: any) {
        dispatch(
          addToast({
            type: "error",
            title: "錯誤",
            message: error?.message || error?.toString() || "移除失敗",
          }),
        );
      }
    } else if (viewMode === "portfolio") {
      // 持倉不允許直接刪除，應該通過賣出交易
      dispatch(
        addToast({
          type: "warning",
          title: "提示",
          message: "持倉股票請使用「賣出」功能來清倉，不能直接移除",
        }),
      );
    }

    setDeleteConfirm({ isOpen: false, stockId: null, stockName: "" });
  };

  // 取消刪除
  const cancelDelete = () => {
    setDeleteConfirm({ isOpen: false, stockId: null, stockName: "" });
  };

  // 處理搜尋（防抖處理在實際應用中可以使用 useDebounce）
  const handleSearchChange = (value: string) => {
    setSearchTerm(value);
  };

  // 處理重新載入並刷新當前視圖的股票價格
  const handleRefreshWithBackfill = async () => {
    setIsBackfilling(true);

    try {
      // 獲取當前視圖的股票列表
      const currentStocks = stocks;

      if (currentStocks.length === 0) {
        dispatch(
          addToast({
            type: "info",
            title: "提示",
            message: "目前沒有股票需要刷新",
          }),
        );
        return;
      }

      const stockIds = currentStocks.map((s) => s.id);

      // 只預抓當前視圖中的股票，避免刷新全部活躍股票造成等待時間過長
      const refreshResult = await StocksApiService.prefetchStockPrices({
        stock_ids: stockIds,
        days: 30,
        stale_after_days: 0,
      });

      if (!refreshResult) {
        throw new Error("刷新結果無效");
      }

      const successCount = refreshResult.results.filter(
        (r) => r.success && !r.skipped,
      ).length;
      const skippedCount = refreshResult.results.filter(
        (r) => r.skipped,
      ).length;
      const failedResults = refreshResult.results.filter((r) => !r.success);

      // 顯示刷新成功訊息
      if (successCount > 0) {
        const viewName = viewMode === "portfolio" ? "持倉" : "清單";
        dispatch(
          addToast({
            type: "success",
            title: "刷新完成",
            message: `成功刷新 ${viewName} 中 ${successCount} 支股票的價格數據`,
          }),
        );
      } else if (skippedCount > 0 && failedResults.length === 0) {
        dispatch(
          addToast({
            type: "info",
            title: "資料已是最新",
            message: `${skippedCount} 支股票使用本地快取`,
          }),
        );
      } else {
        dispatch(
          addToast({
            type: "info",
            title: "已更新",
            message: "股票列表已刷新",
          }),
        );
      }

      // 顯示失敗的股票（如果有）
      if (failedResults.length > 0) {
        const failedSymbols = failedResults.map((r) => r.symbol).join(", ");

        dispatch(
          addToast({
            type: "warning",
            title: "部分失敗",
            message: `${failedResults.length} 支股票刷新失敗: ${failedSymbols}`,
          }),
        );
      }

      // 刷新後重新載入列表
      if (viewMode === "all" && currentListId) {
        // 如果在清單視圖，重新獲取清單股票（包含最新價格）
        await dispatch(fetchListStocks(currentListId));
      } else {
        // 否則刷新全局股票列表
        await refetch();
      }
    } catch (error: any) {
      console.error("❌ 操作失敗:", error);

      const errorMessage =
        error.response?.data?.detail || error.message || "操作失敗，請稍後再試";

      dispatch(
        addToast({
          type: "error",
          title: "錯誤",
          message: errorMessage,
        }),
      );
    } finally {
      setIsBackfilling(false);
    }
  };

  // 處理新增股票
  const handleAddStock = async () => {
    const trimmedSymbol = stockSymbol.trim();

    if (!trimmedSymbol) {
      dispatch(
        addToast({
          type: "error",
          title: "錯誤",
          message: "請填寫股票代號",
        }),
      );
      return;
    }

    // 驗證格式
    if (!/^[A-Za-z0-9.]+$/.test(trimmedSymbol)) {
      dispatch(
        addToast({
          type: "error",
          title: "錯誤",
          message: "股票代號只能包含英文字母和數字",
        }),
      );
      return;
    }

    try {
      setIsAddingStock(true);

      const market = detectMarket(trimmedSymbol);
      const formattedSymbol = formatStockSymbol(trimmedSymbol, market);

      // 先檢查股票是否已經存在於資料庫中
      const existingStocksResponse = await StocksApiService.getStocks({
        search: formattedSymbol,
        page: 1,
        pageSize: 20,
      });

      let stockToAdd = null;

      // 檢查搜尋結果中是否有完全匹配的股票
      if (existingStocksResponse?.items?.length > 0) {
        stockToAdd = existingStocksResponse.items.find(
          (s: any) => s.symbol === formattedSymbol && s.market === market,
        );
      }

      if (stockToAdd) {
        // 股票已存在，直接添加到清單
        if (currentListId) {
          if (currentListStocks.some((stock) => stock.id === stockToAdd.id)) {
            dispatch(
              addToast({
                type: "warning",
                title: "提示",
                message: `${formattedSymbol} 已在此清單中`,
              }),
            );
            setStockSymbol("");
            setShowAddModal(false);
            return;
          }

          try {
            await dispatch(
              addStockToList({
                listId: currentListId,
                data: { stock_id: stockToAdd.id },
              }),
            ).unwrap();

            dispatch(
              addToast({
                type: "success",
                title: "成功",
                message: `已將 ${stockToAdd.name || formattedSymbol} (${formattedSymbol}) 添加到清單，價格資料正在背景更新`,
              }),
            );

            // 刷新清單
            dispatch(fetchListStocks(currentListId));
            startBackgroundPriceBackfill(
              stockToAdd.id,
              formattedSymbol,
              currentListId,
            );
          } catch (error: any) {
            // 檢查是否是重複添加的錯誤
            const errorMsg = error?.message || error?.toString() || "";
            if (
              errorMsg.includes("已存在") ||
              errorMsg.includes("已在清單中")
            ) {
              dispatch(
                addToast({
                  type: "warning",
                  title: "提示",
                  message: "該股票已在此清單中",
                }),
              );
            } else {
              dispatch(
                addToast({
                  type: "error",
                  title: "錯誤",
                  message: errorMsg || "添加股票到清單失敗",
                }),
              );
            }
          }
        } else {
          dispatch(
            addToast({
              type: "info",
              title: "提示",
              message: "股票已存在於資料庫中，請選擇清單後再添加",
            }),
          );
        }
      } else {
        // 股票不存在，創建新股票
        createStockMutation.mutate({
          symbol: formattedSymbol,
          market: market as "TW" | "US",
        });
      }

      // 清空輸入並關閉 modal
      setStockSymbol("");
      setShowAddModal(false);
    } catch (error) {
      console.error("添加股票失敗:", error);
      dispatch(
        addToast({
          type: "error",
          title: "錯誤",
          message: "添加股票失敗，請稍後再試",
        }),
      );
    } finally {
      setIsAddingStock(false);
    }
  };

  // 處理股票排序
  const handleSaveStockReorder = async (reorderedStocks: any[]) => {
    if (!currentListId) return;

    try {
      // 準備排序數據
      const stock_orders = reorderedStocks.map((stock, index) => ({
        stock_id: stock.id,
        sort_order: index,
      }));

      // 調用 API
      await stockListApi.reorderListStocks(currentListId, { stock_orders });

      // 重新載入清單股票
      await dispatch(fetchListStocks(currentListId));

      dispatch(
        addToast({
          type: "success",
          title: "成功",
          message: "股票順序已更新",
        }),
      );

      setIsReorderModalOpen(false);
    } catch (error: any) {
      dispatch(
        addToast({
          type: "error",
          title: "錯誤",
          message: error?.message || error?.toString() || "更新順序失敗",
        }),
      );
    }
  };

  if (!authInitialized) {
    return (
      <PageShell>
        <div className="flex min-h-48 items-center justify-center gap-2 text-sm text-muted-foreground">
          <LoaderCircle className="h-4 w-4 animate-spin" />
          正在確認登入狀態...
        </div>
      </PageShell>
    );
  }

  if (!isAuthenticated) {
    return (
      <PageShell>
        <div className="flex min-h-48 items-center justify-center gap-2 text-sm text-muted-foreground">
          <LoaderCircle className="h-4 w-4 animate-spin" />
          正在前往登入頁...
        </div>
      </PageShell>
    );
  }

  return (
    <PageShell>
      <PageHeader
        title="投資標的"
        description="在同一個工作區整理觀察清單與持倉，快速進入行情、交易與價格提醒。"
        actions={
          <>
            <Button
              onClick={handleRefreshWithBackfill}
              disabled={isBackfilling || loading || stocks.length === 0}
              variant="outline"
            >
              <RefreshCw className={isBackfilling ? "animate-spin" : ""} />
              {isBackfilling ? "更新中..." : "更新行情"}
            </Button>
            {viewMode === "all" && currentListId && (
              <Button onClick={() => setShowAddModal(true)}>
                <Plus />
                新增股票
              </Button>
            )}
          </>
        }
      />

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <MetricCard
          label={
            viewMode === "all" && currentListId
              ? "當前清單股票數"
              : viewMode === "portfolio"
                ? "持倉股票數"
                : "追蹤股票總數"
          }
          value={stocks.length}
        />
        <MetricCard
          label="台股數量"
          value={stocks.filter((s) => s.market === "TW").length}
        />
        <MetricCard
          label="美股數量"
          value={stocks.filter((s) => s.market === "US").length}
        />
      </div>

      <ToolbarPanel className="overflow-visible p-0">
        <div className="grid gap-4 border-b border-border p-4 lg:grid-cols-[auto_minmax(16rem,1fr)_auto] lg:items-end">
          <div className="min-w-0">
            <p className="mb-1.5 text-xs font-medium uppercase tracking-[0.12em] text-muted-foreground">
              資料範圍
            </p>
            <UnifiedStockSelector
              viewMode={viewMode}
              onViewModeChange={setViewMode}
            />
          </div>

          <div>
            <label
              htmlFor="stock-workspace-search"
              className="mb-1.5 block text-xs font-medium uppercase tracking-[0.12em] text-muted-foreground"
            >
              搜尋標的
            </label>
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="stock-workspace-search"
                type="search"
                placeholder="搜尋股票名稱或代號..."
                value={searchTerm}
                onChange={(event) => handleSearchChange(event.target.value)}
                className="pl-9"
              />
            </div>
          </div>

          <div className="flex items-center gap-2 lg:justify-end">
            {viewMode === "all" && currentListId && stocks.length > 1 && (
              <Button
                onClick={() => setIsReorderModalOpen(true)}
                variant="outline"
                size="sm"
                title="調整股票順序"
              >
                <ArrowUpDown />
                調整順序
              </Button>
            )}
          </div>
        </div>

        {loading && (
          <div
            className="flex min-h-72 flex-col items-center justify-center gap-3 p-6 text-sm text-muted-foreground"
            role="status"
          >
            <LoaderCircle className="h-6 w-6 animate-spin text-primary" />
            <span>載入中...</span>
          </div>
        )}

        {!loading && error && (
          <div
            className="flex min-h-72 flex-col items-center justify-center p-6 text-center"
            role="alert"
          >
            <span className="mb-4 flex h-10 w-10 items-center justify-center rounded-full bg-destructive/10 text-destructive">
              <AlertCircle className="h-5 w-5" />
            </span>
            <p className="font-medium text-foreground">無法載入股票資料</p>
            <p className="mt-1 max-w-md text-sm text-muted-foreground">
              {error}
            </p>
            <Button
              onClick={() => {
                if (viewMode === "all" && currentListId) {
                  void dispatch(fetchListStocks(currentListId));
                } else {
                  void refetch();
                }
              }}
              variant="outline"
              size="sm"
              className="mt-4"
            >
              <RefreshCw />
              重新載入
            </Button>
          </div>
        )}

        {!loading && !error && stocks.length === 0 && (
          <div className="flex min-h-72 flex-col items-center justify-center p-6 text-center">
            <span className="mb-4 flex h-11 w-11 items-center justify-center rounded-lg border border-border bg-muted text-muted-foreground">
              <BarChart3 className="h-5 w-5" />
            </span>
            {viewMode === "all" && lists.length === 0 ? (
              <>
                <p className="font-medium text-foreground">尚未建立觀察清單</p>
                <p className="mt-1 max-w-md text-sm leading-6 text-muted-foreground">
                  請使用上方清單選擇器的「新建清單」，建立第一份投資觀察清單。
                </p>
              </>
            ) : viewMode === "all" && !currentListId ? (
              <>
                <p className="font-medium text-foreground">請先選擇一個清單</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  從上方選擇要管理的股票清單。
                </p>
              </>
            ) : searchTerm ? (
              <>
                <p className="font-medium text-foreground">
                  找不到符合條件的股票
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  請調整股票名稱或代號後再試一次。
                </p>
              </>
            ) : viewMode === "portfolio" ? (
              <>
                <p className="font-medium text-foreground">目前沒有持倉</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  完成買入交易後，持倉會顯示在這裡。
                </p>
              </>
            ) : (
              <>
                <p className="font-medium text-foreground">此清單還沒有股票</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  使用頁面右上方的「新增股票」開始追蹤。
                </p>
              </>
            )}
          </div>
        )}

        {!loading && !error && stocks.length > 0 && (
          <>
            <Table className="block md:table">
              <TableHeader className="hidden md:table-header-group">
                <TableRow>
                  <TableHead className="w-[34%]">投資標的</TableHead>
                  <TableHead>最新價格</TableHead>
                  <TableHead>當日漲跌</TableHead>
                  <TableHead className="text-right">快捷操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody className="block space-y-3 p-3 md:table-row-group md:space-y-0 md:p-0">
                {stocks.map((stock) => (
                  <TableRow
                    key={stock.id}
                    className="block rounded-lg border border-border bg-card md:table-row md:rounded-none md:border-x-0 md:border-t-0"
                  >
                    <TableCell className="block px-4 pb-3 pt-4 md:table-cell md:py-3">
                      <div className="flex items-start justify-between gap-3 md:justify-start">
                        <div className="min-w-0">
                          <p className="truncate font-mono text-sm font-semibold text-foreground">
                            {stock.symbol}
                          </p>
                          <p className="mt-0.5 truncate text-sm text-muted-foreground">
                            {stock.name || stock.symbol}
                          </p>
                        </div>
                        <Badge variant="outline" className="shrink-0">
                          {stock.market === "TW" ? "台股" : "美股"}
                        </Badge>
                      </div>
                    </TableCell>

                    <TableCell className="inline-flex w-1/2 flex-col gap-1 px-4 py-2 md:table-cell md:w-auto md:py-3">
                      <span className="text-xs text-muted-foreground md:hidden">
                        最新價格
                      </span>
                      {typeof stock.latest_price?.close === "number" ? (
                        <span className="font-mono text-sm font-semibold tabular-nums text-foreground">
                          {stock.market === "TW" ? "NT$" : "$"}
                          {stock.latest_price.close.toFixed(2)}
                        </span>
                      ) : (
                        <Badge variant="warning" className="w-fit">
                          價格更新中
                        </Badge>
                      )}
                    </TableCell>

                    <TableCell className="inline-flex w-1/2 flex-col gap-1 px-4 py-2 text-right md:table-cell md:w-auto md:py-3 md:text-left">
                      <span className="text-xs text-muted-foreground md:hidden">
                        當日漲跌
                      </span>
                      {stock.latest_price?.change_percent !== null &&
                      stock.latest_price?.change_percent !== undefined ? (
                        <span
                          className={`font-mono text-sm font-semibold tabular-nums ${
                            stock.latest_price.change_percent >= 0
                              ? "text-success"
                              : "text-destructive"
                          }`}
                        >
                          {stock.latest_price.change_percent >= 0 ? "+" : ""}
                          {stock.latest_price.change_percent.toFixed(2)}%
                        </span>
                      ) : (
                        <span className="text-sm text-muted-foreground">
                          待更新
                        </span>
                      )}
                    </TableCell>

                    <TableCell className="block border-t border-border px-4 py-3 md:table-cell md:border-0 md:text-right">
                      <div className="flex flex-wrap items-center gap-1.5 md:justify-end">
                        <Button
                          asChild
                          variant="outline"
                          size="sm"
                          className="md:h-8 md:w-8 md:px-0"
                          title="查看圖表"
                        >
                          <Link
                            href={`/dashboard?stock=${stock.id}`}
                            aria-label={`查看 ${stock.symbol} 圖表`}
                          >
                            <BarChart3 />
                            <span className="md:sr-only">圖表</span>
                          </Link>
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="md:h-8 md:w-8 md:px-0"
                          onClick={() =>
                            setTransactionModal({
                              isOpen: true,
                              stock,
                              type: "BUY",
                            })
                          }
                          aria-label={`買入 ${stock.symbol}`}
                          title="買入"
                        >
                          <ShoppingCart />
                          <span className="md:sr-only">買入</span>
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="md:h-8 md:w-8 md:px-0"
                          onClick={() =>
                            setTransactionModal({
                              isOpen: true,
                              stock,
                              type: "SELL",
                            })
                          }
                          aria-label={`賣出 ${stock.symbol}`}
                          title="賣出"
                        >
                          <TrendingDown />
                          <span className="md:sr-only">賣出</span>
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="md:h-8 md:w-8 md:px-0"
                          onClick={() =>
                            setPriceAlertModal({ isOpen: true, stock })
                          }
                          aria-label={`設定 ${stock.symbol} 價格提醒`}
                          title="價格提醒"
                        >
                          <Bell />
                          <span className="md:sr-only">提醒</span>
                        </Button>
                        {viewMode === "all" && currentListId && (
                          <Button
                            type="button"
                            variant="destructiveOutline"
                            size="sm"
                            className="md:h-8 md:w-8 md:px-0"
                            onClick={() =>
                              handleDeleteStock(
                                stock.id,
                                stock.name || stock.symbol,
                              )
                            }
                            aria-label={`移除 ${stock.symbol}`}
                            title="從清單移除"
                          >
                            <Trash2 />
                            <span className="md:sr-only">移除</span>
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </>
        )}
      </ToolbarPanel>

      {/* 新增股票 Modal */}
      {showAddModal && (
        <div
          className="fixed inset-0 z-[10000] flex items-center justify-center bg-foreground/35 p-4 backdrop-blur-[1px]"
          onMouseDown={closeAddDialog}
        >
          <div
            ref={addDialogRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby={addDialogTitleId}
            aria-describedby={addDialogDescriptionId}
            tabIndex={-1}
            className="w-full max-w-md animate-scale-in rounded-xl border border-border bg-card p-6 shadow-overlay outline-none"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <span className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Plus className="h-5 w-5" />
            </span>
            <h2
              id={addDialogTitleId}
              className="text-lg font-semibold text-foreground"
            >
              新增股票
            </h2>
            <p
              id={addDialogDescriptionId}
              className="mt-1 text-sm leading-6 text-muted-foreground"
            >
              台股請輸入數字代號，美股請輸入英文代碼；系統會自動判斷市場並更新公司資料。
            </p>

            <div className="mt-5 rounded-lg border border-primary/15 bg-primary/5 p-3 text-sm text-foreground">
              <p className="font-medium">輸入範例</p>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">
                台股：2330　·　美股：AAPL
              </p>
            </div>

            <div className="mt-5">
              <label
                htmlFor="new-stock-symbol"
                className="mb-1.5 block text-sm font-medium text-foreground"
              >
                股票代號{" "}
                <span className="text-destructive" aria-hidden="true">
                  *
                </span>
              </label>
              <Input
                id="new-stock-symbol"
                type="text"
                value={stockSymbol}
                onChange={(event) =>
                  setStockSymbol(event.target.value.toUpperCase())
                }
                placeholder="台股輸入數字（如 2330）或美股英文（如 AAPL）"
                disabled={addStockPending}
                required
                aria-required="true"
                onKeyDown={(event) => {
                  if (
                    event.key === "Enter" &&
                    stockSymbol.trim() &&
                    !addStockPending
                  ) {
                    event.preventDefault();
                    void handleAddStock();
                  }
                }}
              />
              {stockSymbol && (
                <div className="mt-2">
                  <Badge variant="outline">
                    已辨識為
                    {detectMarket(stockSymbol) === "TW" ? "台股" : "美股"}
                  </Badge>
                </div>
              )}
            </div>

            <div className="mt-6 flex justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={closeAddDialog}
                disabled={addStockPending}
              >
                取消
              </Button>
              <Button
                type="button"
                onClick={() => void handleAddStock()}
                disabled={addStockPending || !stockSymbol.trim()}
              >
                {addStockPending && <LoaderCircle className="animate-spin" />}
                {addStockPending ? "新增中..." : "確認新增"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* 刪除確認對話框 */}
      <ConfirmDialog
        isOpen={deleteConfirm.isOpen}
        title={
          viewMode === "all" && currentListId
            ? "確認從清單移除"
            : "確認刪除股票"
        }
        message={
          viewMode === "all" && currentListId
            ? `確定要從清單中移除股票「${deleteConfirm.stockName}」嗎？股票本身不會被刪除。`
            : `確定要刪除股票「${deleteConfirm.stockName}」嗎？此操作無法復原。`
        }
        confirmText="確定"
        cancelText="取消"
        type="danger"
        onConfirm={confirmDelete}
        onCancel={cancelDelete}
      />

      {/* 交易 Modal */}
      <TransactionModal
        isOpen={transactionModal.isOpen}
        onClose={() =>
          setTransactionModal({ isOpen: false, stock: null, type: "BUY" })
        }
        stock={transactionModal.stock}
        transactionType={transactionModal.type}
        onSuccess={() => {
          // 交易成功後重新載入列表
          refetch();
        }}
      />

      <PriceAlertModal
        isOpen={priceAlertModal.isOpen}
        stock={priceAlertModal.stock}
        onClose={() => setPriceAlertModal({ isOpen: false, stock: null })}
        onSuccess={() => {
          dispatch(
            addToast({
              type: "success",
              title: "成功",
              message: "價格提醒已建立",
            }),
          );
        }}
      />

      {/* 股票排序 Modal */}
      <StockReorderModal
        isOpen={isReorderModalOpen}
        onClose={() => setIsReorderModalOpen(false)}
        stocks={stocks}
        onSave={handleSaveStockReorder}
      />
    </PageShell>
  );
};

export default StockManagementPage;
