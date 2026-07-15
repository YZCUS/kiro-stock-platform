/**
 * 信號工作台組件
 */
"use client";

import Link from "next/link";
import React, { useEffect, useMemo, useState } from "react";
import { useAppDispatch, useAppSelector } from "@/store";
import {
  fetchSignals,
  updateSignalStatus,
  selectSignals,
  selectSignalsLoading,
} from "@/store/slices/strategySlice";
import { addToast } from "@/store/slices/uiSlice";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  AlertCircle,
  Check,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Filter,
  RefreshCw,
  Search,
  X,
} from "lucide-react";
import StocksApiService from "@/services/stocksApi";
import { inferMarketFromSymbol } from "@/lib/finance";
import type { PriceData } from "@/types";
import type {
  SignalDirection,
  SignalQueryParams,
  SignalStatus,
  TradingSignal,
} from "@/types/strategy";

type StatusUpdate = "triggered" | "cancelled";

interface SignalGroup {
  key: string;
  stockId: number;
  symbol: string;
  name?: string | null;
  signals: TradingSignal[];
  latestSignalDate: string;
  latestValidUntil?: string | null;
  dominantDirection: SignalDirection;
  signalStrength: number;
  primaryStrategy: string;
  primaryHorizon?: string;
}

const statusText: Record<SignalStatus, string> = {
  active: "活躍",
  triggered: "已觸發",
  expired: "已過期",
  cancelled: "已取消",
};

const directionText: Record<SignalDirection, string> = {
  LONG: "看多",
  SHORT: "看空",
  NEUTRAL: "中性",
};

const directionClasses: Record<SignalDirection, string> = {
  LONG: "bg-emerald-50 text-emerald-700",
  SHORT: "bg-red-50 text-red-700",
  NEUTRAL: "bg-gray-100 text-gray-700",
};

const statusClasses: Record<SignalStatus, string> = {
  active: "bg-blue-50 text-blue-700",
  triggered: "bg-emerald-50 text-emerald-700",
  expired: "bg-gray-100 text-gray-600",
  cancelled: "bg-red-50 text-red-700",
};

const formatDate = (value?: string | null) =>
  value ? new Date(value).toLocaleDateString("zh-TW") : "-";

const formatPrice = (
  value: number | undefined | null,
  symbol?: string | null,
) =>
  typeof value === "number" && Number.isFinite(value)
    ? `${inferMarketFromSymbol(symbol || undefined) === "TW" ? "NT$" : "$"}${value.toFixed(2)}`
    : "-";

const directionValue = (direction: SignalDirection) => {
  if (direction === "LONG") return 1;
  if (direction === "SHORT") return -1;
  return 0;
};

const getEntryRange = (signal: TradingSignal) => {
  const entryMin = signal.entry_zone?.min ?? signal.entry_min;
  const entryMax = signal.entry_zone?.max ?? signal.entry_max;
  return `${formatPrice(entryMin, signal.stock_symbol)} - ${formatPrice(entryMax, signal.stock_symbol)}`;
};

const getTakeProfitTargets = (signal: TradingSignal) =>
  signal.take_profit ?? signal.take_profit_targets ?? [];

const sortByLatestDate = (a: TradingSignal, b: TradingSignal) =>
  new Date(b.signal_date).getTime() - new Date(a.signal_date).getTime();

const getTimestamp = (value?: string | null) => {
  const timestamp = value ? new Date(value).getTime() : 0;
  return Number.isFinite(timestamp) ? timestamp : 0;
};

const isExpiredActiveSignal = (signal: TradingSignal) => {
  if (signal.status !== "active") return false;
  if (signal.is_valid === false) return true;
  if (!signal.valid_until) return false;

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const validUntil = new Date(signal.valid_until);
  validUntil.setHours(0, 0, 0, 0);

  return validUntil.getTime() < today.getTime();
};

const getEffectiveStatus = (signal: TradingSignal): SignalStatus =>
  isExpiredActiveSignal(signal) ? "expired" : signal.status;

const getErrorMessage = (error: unknown, fallback: string) =>
  typeof error === "string" ? error : fallback;

const buildSignalGroups = (signals: TradingSignal[]): SignalGroup[] => {
  const grouped = new Map<string, TradingSignal[]>();

  signals.forEach((signal) => {
    const key = String(signal.stock_id);
    grouped.set(key, [...(grouped.get(key) ?? []), signal]);
  });

  return Array.from(grouped.entries()).map(([key, groupSignals]) => {
    const sortedSignals = [...groupSignals].sort(sortByLatestDate);
    const weightedScore =
      sortedSignals.reduce(
        (total, signal) =>
          total + directionValue(signal.direction) * signal.confidence,
        0,
      ) / Math.max(sortedSignals.length, 1);
    const dominantDirection: SignalDirection =
      weightedScore > 5 ? "LONG" : weightedScore < -5 ? "SHORT" : "NEUTRAL";
    const primarySignal = [...sortedSignals].sort(
      (a, b) => b.confidence - a.confidence,
    )[0];

    return {
      key,
      stockId: primarySignal.stock_id,
      symbol: primarySignal.stock_symbol || "-",
      name: primarySignal.stock_name,
      signals: sortedSignals,
      latestSignalDate: sortedSignals[0]?.signal_date,
      latestValidUntil: sortedSignals[0]?.valid_until,
      dominantDirection,
      signalStrength: Math.abs(weightedScore),
      primaryStrategy:
        primarySignal.strategy_name || primarySignal.strategy_type,
      primaryHorizon: primarySignal.signal_horizon,
    };
  });
};

export default function SignalList() {
  const dispatch = useAppDispatch();
  const signals = useAppSelector(selectSignals);
  const loading = useAppSelector(selectSignalsLoading);
  const signalsTotal = useAppSelector((state) => state.strategy.signalsTotal);

  const [filters, setFilters] = useState<SignalQueryParams>({
    status: "active",
    sort_by: "signal_date",
    sort_order: "desc",
    limit: 100,
  });
  const [showFilters, setShowFilters] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [expandedGroup, setExpandedGroup] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [refreshRevision, setRefreshRevision] = useState(0);

  useEffect(() => {
    let active = true;
    setLoadError(null);
    const request = dispatch(fetchSignals(filters));

    request.unwrap().catch((error) => {
      if (active) {
        setLoadError(getErrorMessage(error, "無法載入交易信號"));
      }
    });

    return () => {
      active = false;
      request.abort();
    };
  }, [dispatch, filters, refreshRevision]);

  const displaySignals = useMemo(
    () =>
      signals.filter((signal) => {
        if (filters.direction && signal.direction !== filters.direction) {
          return false;
        }
        if (!filters.status) return true;
        return getEffectiveStatus(signal) === filters.status;
      }),
    [filters.direction, filters.status, signals],
  );

  const signalGroups = useMemo(
    () => buildSignalGroups(displaySignals),
    [displaySignals],
  );

  const visibleGroups = useMemo(() => {
    const keyword = searchTerm.trim().toLowerCase();
    const filteredGroups = keyword
      ? signalGroups.filter((group) => {
          const haystack = [
            group.symbol,
            group.name,
            group.primaryStrategy,
            ...group.signals.map((signal) => signal.strategy_type),
          ]
            .filter(Boolean)
            .join(" ")
            .toLowerCase();
          return haystack.includes(keyword);
        })
      : signalGroups;

    const direction = filters.sort_order === "asc" ? 1 : -1;

    return [...filteredGroups].sort((a, b) => {
      if (filters.sort_by === "signal_date") {
        const dateSort =
          direction *
          (getTimestamp(a.latestSignalDate) - getTimestamp(b.latestSignalDate));
        if (dateSort !== 0) return dateSort;
        return b.signalStrength - a.signalStrength;
      }

      return direction * (a.signalStrength - b.signalStrength);
    });
  }, [filters.sort_by, filters.sort_order, searchTerm, signalGroups]);

  const handleRefresh = () => {
    setRefreshRevision((revision) => revision + 1);
  };

  const handleUpdateStatus = async (signalId: number, status: StatusUpdate) => {
    try {
      await dispatch(
        updateSignalStatus({
          id: signalId,
          data: { status },
        }),
      ).unwrap();

      dispatch(
        addToast({
          type: "success",
          title: "成功",
          message: `信號已標記為${status === "triggered" ? "已觸發" : "已取消"}`,
        }),
      );

      setRefreshRevision((revision) => revision + 1);
    } catch (error: unknown) {
      dispatch(
        addToast({
          type: "error",
          title: "錯誤",
          message: typeof error === "string" ? error : "更新失敗",
        }),
      );
    }
  };

  const handleFilterChange = <K extends keyof SignalQueryParams>(
    key: K,
    value: SignalQueryParams[K],
  ) => {
    setFilters((current) => ({
      ...current,
      [key]: value,
      ...(key === "offset" ? {} : { offset: 0 }),
    }));
    setExpandedGroup(null);
  };

  const handleStatusQuickFilter = (status?: SignalStatus) => {
    setFilters((current) => ({ ...current, status, offset: 0 }));
    setExpandedGroup(null);
  };

  const handleDirectionQuickFilter = (direction?: SignalDirection) => {
    setFilters((current) => ({ ...current, direction, offset: 0 }));
    setExpandedGroup(null);
  };

  const pageSize = filters.limit ?? 100;
  const currentOffset = filters.offset ?? 0;
  const currentPage = Math.floor(currentOffset / pageSize) + 1;
  const totalPages = Math.max(1, Math.ceil(signalsTotal / pageSize));

  const handlePageChange = (page: number) => {
    const nextPage = Math.min(Math.max(page, 1), totalPages);
    handleFilterChange("offset", (nextPage - 1) * pageSize);
  };

  return (
    <section className="space-y-4" aria-labelledby="signal-list-title">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h2
            id="signal-list-title"
            className="text-lg font-semibold text-gray-950"
          >
            交易信號
          </h2>
          <p className="mt-1 text-sm text-gray-600">
            依股票彙總信號，展開後查看各策略的進場、停損與原因。
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowFilters((value) => !value)}
            aria-expanded={showFilters}
            aria-controls="signal-advanced-filters"
          >
            <Filter className="h-4 w-4" />
            過濾器
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            刷新
          </Button>
        </div>
      </div>

      <div className="flex flex-col gap-3 rounded-lg border bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-col gap-2">
            <div className="flex flex-wrap gap-2">
              {[
                { label: "活躍", value: "active" as SignalStatus },
                { label: "已觸發", value: "triggered" as SignalStatus },
                { label: "已過期", value: "expired" as SignalStatus },
                { label: "已忽略", value: "cancelled" as SignalStatus },
                { label: "全部狀態", value: undefined },
              ].map((item) => (
                <Button
                  key={item.label}
                  variant={
                    filters.status === item.value ? "default" : "outline"
                  }
                  size="sm"
                  onClick={() => handleStatusQuickFilter(item.value)}
                  aria-pressed={filters.status === item.value}
                >
                  {item.label}
                </Button>
              ))}
            </div>
            <div className="flex flex-wrap gap-2">
              {[
                { label: "全部方向", value: undefined },
                { label: "看多", value: "LONG" as SignalDirection },
                { label: "看空", value: "SHORT" as SignalDirection },
                { label: "中性", value: "NEUTRAL" as SignalDirection },
              ].map((item) => (
                <Button
                  key={item.label}
                  variant={
                    filters.direction === item.value ? "default" : "outline"
                  }
                  size="sm"
                  onClick={() => handleDirectionQuickFilter(item.value)}
                  aria-pressed={filters.direction === item.value}
                >
                  {item.label}
                </Button>
              ))}
            </div>
          </div>

          <div className="relative w-full xl:w-80">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
            <input
              aria-label="搜尋交易信號"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder="搜尋股票、公司或策略"
              className="h-9 w-full rounded-md border border-gray-300 pl-9 pr-3 text-sm outline-none focus:border-gray-900"
            />
          </div>
        </div>

        {showFilters && (
          <div
            id="signal-advanced-filters"
            className="grid grid-cols-1 gap-4 border-t pt-4 md:grid-cols-4"
          >
            <div>
              <label
                htmlFor="signal-status-filter"
                className="mb-1 block text-sm font-medium text-gray-700"
              >
                狀態
              </label>
              <select
                id="signal-status-filter"
                value={filters.status || "all"}
                onChange={(event) =>
                  handleFilterChange(
                    "status",
                    event.target.value === "all"
                      ? undefined
                      : (event.target.value as SignalStatus),
                  )
                }
                className="h-9 w-full rounded-md border border-gray-300 px-3 text-sm"
              >
                <option value="all">全部</option>
                <option value="active">活躍</option>
                <option value="triggered">已觸發</option>
                <option value="expired">已過期</option>
                <option value="cancelled">已忽略</option>
              </select>
            </div>

            <div>
              <label
                htmlFor="signal-direction-filter"
                className="mb-1 block text-sm font-medium text-gray-700"
              >
                方向
              </label>
              <select
                id="signal-direction-filter"
                value={filters.direction || "all"}
                onChange={(event) =>
                  handleFilterChange(
                    "direction",
                    event.target.value === "all"
                      ? undefined
                      : (event.target.value as SignalDirection),
                  )
                }
                className="h-9 w-full rounded-md border border-gray-300 px-3 text-sm"
              >
                <option value="all">全部方向</option>
                <option value="LONG">看多</option>
                <option value="SHORT">看空</option>
                <option value="NEUTRAL">中性</option>
              </select>
            </div>

            <div>
              <label
                htmlFor="signal-sort-filter"
                className="mb-1 block text-sm font-medium text-gray-700"
              >
                排序方式
              </label>
              <select
                id="signal-sort-filter"
                value={filters.sort_by || "signal_date"}
                onChange={(event) =>
                  handleFilterChange(
                    "sort_by",
                    event.target.value as SignalQueryParams["sort_by"],
                  )
                }
                className="h-9 w-full rounded-md border border-gray-300 px-3 text-sm"
              >
                <option value="signal_date">信號日期</option>
                <option value="confidence">訊號強度</option>
              </select>
            </div>

            <div>
              <label
                htmlFor="signal-sort-direction"
                className="mb-1 block text-sm font-medium text-gray-700"
              >
                排序方向
              </label>
              <select
                id="signal-sort-direction"
                value={filters.sort_order || "desc"}
                onChange={(event) =>
                  handleFilterChange(
                    "sort_order",
                    event.target.value as "asc" | "desc",
                  )
                }
                className="h-9 w-full rounded-md border border-gray-300 px-3 text-sm"
              >
                <option value="desc">降序</option>
                <option value="asc">升序</option>
              </select>
            </div>
          </div>
        )}
      </div>

      {loadError && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <span>{loadError}</span>
            <Button variant="outline" size="sm" onClick={handleRefresh}>
              <RefreshCw className="h-4 w-4" />
              重試
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {loading && signals.length === 0 ? (
        <div
          className="rounded-lg border bg-white py-12 text-center"
          role="status"
        >
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-b-2 border-gray-900" />
          <p className="mt-2 text-gray-600">載入中...</p>
        </div>
      ) : loadError && signals.length === 0 ? null : visibleGroups.length ===
        0 ? (
        <div className="rounded-lg border-2 border-dashed bg-gray-50 py-12 text-center">
          <p className="text-gray-700">
            {signals.length === 0
              ? "目前沒有交易信號"
              : "沒有符合搜尋條件的信號"}
          </p>
          <p className="mt-2 text-sm text-gray-500">
            {signals.length === 0
              ? "等待策略排程產生新信號，或切換其他狀態。"
              : "請調整搜尋或篩選條件。"}
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border bg-white shadow-sm">
          <div className="max-h-[720px] overflow-auto">
            <table className="w-full min-w-[980px] text-sm">
              <caption className="sr-only">依股票彙總的交易信號</caption>
              <thead className="sticky top-0 z-10 bg-gray-50 text-left text-gray-600 shadow-sm">
                <tr>
                  <th className="px-4 py-3 font-medium">股票</th>
                  <th className="px-3 py-3 font-medium">方向</th>
                  <th className="px-3 py-3 text-right font-medium">訊號強度</th>
                  <th className="px-3 py-3 text-right font-medium">信號數</th>
                  <th className="px-3 py-3 font-medium">主要策略</th>
                  <th className="px-3 py-3 font-medium">週期</th>
                  <th className="px-3 py-3 font-medium">最新信號</th>
                  <th className="px-3 py-3 font-medium">有效期限</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {visibleGroups.map((group) => {
                  const expanded = expandedGroup === group.key;
                  return (
                    <React.Fragment key={group.key}>
                      <tr className="hover:bg-gray-50">
                        <td className="px-4 py-3">
                          <button
                            type="button"
                            className="flex min-w-0 items-center gap-2 rounded text-left outline-none focus-visible:ring-2 focus-visible:ring-gray-900 focus-visible:ring-offset-2"
                            onClick={() =>
                              setExpandedGroup(expanded ? null : group.key)
                            }
                            aria-expanded={expanded}
                            aria-controls={`signal-details-${group.key}`}
                            aria-label={`${expanded ? "收合" : "展開"} ${group.symbol} 信號明細`}
                          >
                            {expanded ? (
                              <ChevronDown className="h-4 w-4 shrink-0 text-gray-500" />
                            ) : (
                              <ChevronRight className="h-4 w-4 shrink-0 text-gray-500" />
                            )}
                            <span className="min-w-0">
                              <span className="block font-semibold text-gray-950">
                                {group.symbol}
                              </span>
                              <span className="block max-w-[220px] truncate text-xs text-gray-500">
                                {group.name || "-"}
                              </span>
                            </span>
                          </button>
                        </td>
                        <td className="whitespace-nowrap px-3 py-3">
                          <span
                            className={`rounded-md px-2 py-1 text-xs font-medium ${directionClasses[group.dominantDirection]}`}
                          >
                            {directionText[group.dominantDirection]}
                          </span>
                        </td>
                        <td className="whitespace-nowrap px-3 py-3 text-right font-medium tabular-nums">
                          {group.signalStrength.toFixed(1)}%
                        </td>
                        <td className="whitespace-nowrap px-3 py-3 text-right tabular-nums text-gray-600">
                          {group.signals.length}
                        </td>
                        <td className="max-w-[180px] truncate px-3 py-3">
                          {group.primaryStrategy}
                        </td>
                        <td className="whitespace-nowrap px-3 py-3 text-gray-600">
                          {group.primaryHorizon || "-"}
                        </td>
                        <td className="whitespace-nowrap px-3 py-3 text-gray-600">
                          {formatDate(group.latestSignalDate)}
                        </td>
                        <td className="whitespace-nowrap px-3 py-3 text-gray-600">
                          {formatDate(group.latestValidUntil)}
                        </td>
                      </tr>

                      {expanded && (
                        <tr>
                          <td
                            id={`signal-details-${group.key}`}
                            colSpan={8}
                            className="bg-gray-50 px-4 py-4"
                          >
                            <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
                              <section className="rounded-lg border bg-white p-4">
                                <div className="flex flex-wrap items-end justify-between gap-2">
                                  <div>
                                    <h3 className="text-base font-semibold text-gray-950">
                                      信號明細
                                    </h3>
                                    <p className="mt-1 text-sm text-gray-500">
                                      {group.signals.length} 個策略信號
                                    </p>
                                  </div>
                                  <span
                                    className={`rounded-md px-2 py-1 text-xs font-medium ${directionClasses[group.dominantDirection]}`}
                                  >
                                    綜合{directionText[group.dominantDirection]}
                                  </span>
                                </div>
                                <div className="mt-4 grid gap-2">
                                  {group.signals.map((signal) => (
                                    <SignalDetailCard
                                      key={signal.id}
                                      signal={signal}
                                      onUpdateStatus={handleUpdateStatus}
                                    />
                                  ))}
                                </div>
                              </section>
                              <PricePreviewCard group={group} />
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!loadError && signalsTotal > 0 && totalPages > 1 && (
        <nav
          className="flex flex-col items-center justify-between gap-3 rounded-lg border bg-white px-4 py-3 sm:flex-row"
          aria-label="交易信號分頁"
        >
          <p className="text-sm text-gray-500">
            第 {currentPage} / {totalPages} 頁，共{" "}
            {signalsTotal.toLocaleString()} 個信號
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={loading || currentPage <= 1}
            >
              上一頁
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={loading || currentPage >= totalPages}
            >
              下一頁
            </Button>
          </div>
        </nav>
      )}
    </section>
  );
}

function PricePreviewCard({ group }: { group: SignalGroup }) {
  const [prices, setPrices] = useState<PriceData[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    StocksApiService.getStockPrices(group.stockId, { limit: 90 })
      .then((data) => {
        if (cancelled) return;
        setPrices(
          Array.isArray(data)
            ? [...data].sort(
                (a, b) =>
                  new Date(a.date).getTime() - new Date(b.date).getTime(),
              )
            : [],
        );
      })
      .catch(() => {
        if (!cancelled) setPrices([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [group.stockId]);

  const chart = useMemo(() => buildPreviewChart(prices), [prices]);
  const firstClose = prices[0]?.close;
  const lastClose = prices[prices.length - 1]?.close;
  const changePercent =
    firstClose && lastClose ? (lastClose / firstClose - 1) * 100 : null;
  const isPositive = (changePercent ?? 0) >= 0;

  return (
    <aside className="rounded-lg border bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-gray-950">
            {group.symbol} 價格預覽
          </h3>
          <p className="mt-1 text-sm text-gray-500">最近 90 根日線</p>
        </div>
        <Button asChild size="sm" variant="outline">
          <Link
            href={`/dashboard?stock=${group.stockId}&source=strategy-signal`}
          >
            <ExternalLink className="h-4 w-4" />
            完整圖表
          </Link>
        </Button>
      </div>

      <div className="mt-4 rounded-md border bg-gray-50 p-3">
        <div className="mb-3 flex items-baseline justify-between">
          <div>
            <p className="text-xs text-gray-500">最新收盤</p>
            <p className="text-xl font-semibold tabular-nums text-gray-950">
              {formatPrice(lastClose, group.symbol)}
            </p>
          </div>
          {changePercent !== null && (
            <p
              className={`text-sm font-semibold tabular-nums ${
                isPositive ? "text-emerald-600" : "text-red-600"
              }`}
            >
              {isPositive ? "+" : ""}
              {changePercent.toFixed(2)}%
            </p>
          )}
        </div>

        <div className="h-48">
          {loading ? (
            <div className="flex h-full items-center justify-center text-sm text-gray-500">
              載入價格...
            </div>
          ) : chart.path ? (
            <svg
              viewBox="0 0 360 160"
              preserveAspectRatio="none"
              className="h-full w-full"
              role="img"
              aria-label={`${group.symbol} 最近日線預覽`}
            >
              <defs>
                <linearGradient
                  id={`area-${group.stockId}`}
                  x1="0"
                  x2="0"
                  y1="0"
                  y2="1"
                >
                  <stop
                    offset="0%"
                    stopColor={isPositive ? "#10b981" : "#ef4444"}
                    stopOpacity="0.22"
                  />
                  <stop
                    offset="100%"
                    stopColor={isPositive ? "#10b981" : "#ef4444"}
                    stopOpacity="0"
                  />
                </linearGradient>
              </defs>
              <path
                d={`${chart.path} L 360 150 L 0 150 Z`}
                fill={`url(#area-${group.stockId})`}
              />
              <path
                d={chart.path}
                fill="none"
                stroke={isPositive ? "#059669" : "#dc2626"}
                strokeWidth="2.5"
                strokeLinecap="round"
              />
            </svg>
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-gray-500">
              尚無可用價格資料
            </div>
          )}
        </div>
      </div>

      <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
        <div className="rounded-md bg-gray-50 p-2">
          <p className="text-gray-500">信號方向</p>
          <p className="mt-1 font-semibold text-gray-950">
            {directionText[group.dominantDirection]}
          </p>
        </div>
        <div className="rounded-md bg-gray-50 p-2">
          <p className="text-gray-500">訊號強度</p>
          <p className="mt-1 font-semibold tabular-nums text-gray-950">
            {group.signalStrength.toFixed(1)}%
          </p>
        </div>
        <div className="rounded-md bg-gray-50 p-2">
          <p className="text-gray-500">策略數</p>
          <p className="mt-1 font-semibold tabular-nums text-gray-950">
            {group.signals.length}
          </p>
        </div>
      </div>
    </aside>
  );
}

function buildPreviewChart(prices: PriceData[]) {
  const closes = prices
    .map((price) => price.close)
    .filter((value) => Number.isFinite(value));

  if (closes.length < 2) {
    return { path: "" };
  }

  const min = Math.min(...closes);
  const max = Math.max(...closes);
  const range = max - min || 1;
  const width = 360;
  const height = 140;
  const topPadding = 10;

  const points = closes.map((close, index) => {
    const x = (index / (closes.length - 1)) * width;
    const y = topPadding + (1 - (close - min) / range) * height;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  return { path: `M ${points.join(" L ")}` };
}

function SignalDetailCard({
  signal,
  onUpdateStatus,
}: {
  signal: TradingSignal;
  onUpdateStatus: (signalId: number, status: StatusUpdate) => void;
}) {
  const takeProfitTargets = getTakeProfitTargets(signal);
  const effectiveStatus = getEffectiveStatus(signal);

  return (
    <article className="rounded-md border bg-gray-50 p-3">
      <div className="grid gap-3 xl:grid-cols-[220px_minmax(0,1fr)_150px] xl:items-start">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`rounded-md px-2 py-1 text-xs font-medium ${directionClasses[signal.direction]}`}
            >
              {directionText[signal.direction]}
            </span>
            <span
              className={`rounded-md px-2 py-1 text-xs font-medium ${statusClasses[effectiveStatus]}`}
            >
              {statusText[effectiveStatus]}
            </span>
            {signal.signal_horizon && (
              <span className="rounded-md bg-gray-100 px-2 py-1 text-xs font-medium text-gray-600">
                {signal.signal_horizon}
              </span>
            )}
          </div>
          <h3 className="mt-2 truncate text-sm font-semibold text-gray-950">
            {signal.strategy_name || signal.strategy_type}
          </h3>
          <p className="mt-1 text-xs text-gray-500">
            {formatDate(signal.signal_date)} 至 {formatDate(signal.valid_until)}
          </p>
        </div>

        <div className="grid gap-3 text-sm sm:grid-cols-3">
          <div>
            <p className="text-xs text-gray-500">進場區間</p>
            <p className="font-medium text-gray-950">{getEntryRange(signal)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">停損</p>
            <p className="font-medium text-red-600">
              {formatPrice(signal.stop_loss, signal.stock_symbol)}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500">止盈目標</p>
            <div className="mt-1 flex flex-wrap gap-1">
              {takeProfitTargets.length === 0 ? (
                <span className="text-xs text-gray-400">-</span>
              ) : (
                takeProfitTargets.map((target, index) => (
                  <span
                    key={`${signal.id}-tp-${index}`}
                    className="rounded-md bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700"
                  >
                    TP{index + 1}: {formatPrice(target, signal.stock_symbol)}
                  </span>
                ))
              )}
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-2 xl:items-end">
          <div className="text-left xl:text-right">
            <p className="text-xs text-gray-500">訊號強度</p>
            <p className="text-base font-semibold tabular-nums">
              {signal.confidence.toFixed(1)}%
            </p>
          </div>
          {effectiveStatus === "active" && (
            <div className="flex w-full gap-2 xl:w-auto">
              <Button
                size="sm"
                variant="successOutline"
                className="flex-1 xl:flex-none"
                onClick={() => onUpdateStatus(signal.id, "triggered")}
              >
                <Check className="h-4 w-4" />
                已觸發
              </Button>
              <Button
                size="sm"
                variant="destructiveOutline"
                className="flex-1 xl:flex-none"
                onClick={() => onUpdateStatus(signal.id, "cancelled")}
              >
                <X className="h-4 w-4" />
                忽略
              </Button>
            </div>
          )}
        </div>
      </div>

      {signal.reason && (
        <p className="mt-3 border-t pt-3 text-sm leading-6 text-gray-700">
          <span className="font-medium text-gray-950">信號原因：</span>
          {signal.reason}
        </p>
      )}
    </article>
  );
}
