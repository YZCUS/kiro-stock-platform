"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ChartNoAxesCombined,
  Plus,
  ShoppingCart,
  Trash2,
  TrendingDown,
  TrendingUp,
} from "lucide-react";

import { useAppDispatch, useAppSelector } from "@/store";
import {
  fetchPortfolioList,
  removePortfolio,
} from "@/store/slices/portfolioSlice";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import {
  MetricCard,
  PageHeader,
  PageShell,
  PageSection,
} from "@/components/ui/page";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  aggregatePortfolioByMarket,
  formatLocalDateInput,
  formatMarketCurrency,
  inferMarketFromSymbol,
} from "@/lib/finance";
import type { Portfolio, Stock } from "@/types";

const TransactionModal = dynamic(
  () => import("@/components/Portfolio/TransactionModal"),
  { ssr: false, loading: () => null },
);

type PortfolioMetric = "cost" | "value" | "profitLoss";

export default function PortfolioPage() {
  const router = useRouter();
  const dispatch = useAppDispatch();
  const { isAuthenticated } = useAppSelector((state) => state.auth);
  const { portfolios, portfolioLoading, error } = useAppSelector(
    (state) => state.portfolio,
  );
  const [isMounted, setIsMounted] = useState(false);
  const [pendingRemoval, setPendingRemoval] = useState<Portfolio | null>(null);
  const [transactionModal, setTransactionModal] = useState<{
    isOpen: boolean;
    stock: Stock | null;
    type: "BUY" | "SELL";
  }>({ isOpen: false, stock: null, type: "BUY" });

  const marketTotals = useMemo(
    () => aggregatePortfolioByMarket(portfolios),
    [portfolios],
  );

  useEffect(() => {
    setIsMounted(true);
  }, []);

  useEffect(() => {
    if (!isMounted) return;
    if (!isAuthenticated) {
      router.replace("/login?redirect=/portfolio");
      return;
    }
    dispatch(fetchPortfolioList());
  }, [dispatch, isAuthenticated, isMounted, router]);

  const loadPortfolio = () => {
    dispatch(fetchPortfolioList());
  };

  const confirmRemoval = async () => {
    if (!pendingRemoval) return;
    const portfolioId = pendingRemoval.id;
    setPendingRemoval(null);

    try {
      await dispatch(removePortfolio(portfolioId)).unwrap();
      loadPortfolio();
    } catch {
      // Redux keeps the API error visible in the page alert.
    }
  };

  const toTransactionStock = (portfolio: Portfolio): Stock => ({
    id: portfolio.stock_id,
    symbol: portfolio.stock_symbol || "",
    name: portfolio.stock_name || portfolio.stock_symbol || null,
    market: inferMarketFromSymbol(portfolio.stock_symbol),
    is_active: true,
    created_at: portfolio.created_at,
    updated_at: portfolio.updated_at,
    latest_price:
      portfolio.current_price != null
        ? {
            close: portfolio.current_price,
            change: 0,
            change_percent: 0,
            date: formatLocalDateInput(),
            volume: 0,
          }
        : null,
  });

  const openTransaction = (portfolio: Portfolio, type: "BUY" | "SELL") => {
    setTransactionModal({
      isOpen: true,
      stock: toTransactionStock(portfolio),
      type,
    });
  };

  const formatPercent = (percent: number) =>
    `${percent >= 0 ? "+" : ""}${percent.toFixed(2)}%`;

  const renderMarketMetric = (metric: PortfolioMetric) => {
    if (marketTotals.length === 0) return "—";
    if (marketTotals.length === 1) {
      const total = marketTotals[0];
      if (metric !== "cost" && !total.hasCompleteValuation) return "—";
      return formatMarketCurrency(total[metric], total.market);
    }

    return (
      <span className="flex flex-col gap-1 text-base">
        {marketTotals.map((total) => (
          <span
            key={total.market}
            className="flex items-baseline justify-between gap-3"
          >
            <span className="text-xs font-medium text-muted-foreground">
              {total.market === "TW" ? "TWD" : "USD"}
            </span>
            <span>
              {metric !== "cost" && !total.hasCompleteValuation
                ? "—"
                : formatMarketCurrency(total[metric], total.market)}
            </span>
          </span>
        ))}
      </span>
    );
  };

  const renderReturns = () => {
    if (marketTotals.length === 0) return "—";
    if (marketTotals.length === 1) {
      if (!marketTotals[0].hasCompleteValuation) return "—";
      return formatPercent(marketTotals[0].profitLossPercent);
    }

    return (
      <span className="flex flex-col gap-1 text-base">
        {marketTotals.map((total) => (
          <span
            key={total.market}
            className="flex items-baseline justify-between gap-3"
          >
            <span className="text-xs font-medium text-muted-foreground">
              {total.market === "TW" ? "TWD" : "USD"}
            </span>
            <span
              className={
                !total.hasCompleteValuation
                  ? "text-muted-foreground"
                  : total.profitLoss < 0
                    ? "text-destructive"
                    : "text-success"
              }
            >
              {total.hasCompleteValuation
                ? formatPercent(total.profitLossPercent)
                : "—"}
            </span>
          </span>
        ))}
      </span>
    );
  };

  if (!isMounted) {
    return <PortfolioSkeleton />;
  }

  if (!isAuthenticated) return null;

  return (
    <PageShell>
      <PageHeader
        title="投資組合"
        description="按市場分開計價，快速掌握持倉、曝險與未實現損益。"
        actions={
          <Button asChild>
            <Link href="/stocks">
              <Plus className="h-4 w-4" />
              新增投資標的
            </Link>
          </Button>
        }
      />

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="投入成本"
          value={renderMarketMetric("cost")}
          detail={marketTotals.length > 1 ? "依市場幣別分列" : undefined}
        />
        <MetricCard
          label="目前市值"
          value={renderMarketMetric("value")}
          detail={marketTotals.length > 1 ? "未進行匯率換算" : undefined}
        />
        <MetricCard
          label="未實現損益"
          value={renderMarketMetric("profitLoss")}
          icon={
            marketTotals.length === 0 ||
            marketTotals.some((item) => !item.hasCompleteValuation)
              ? ChartNoAxesCombined
              : marketTotals.every((item) => item.profitLoss >= 0)
                ? TrendingUp
                : TrendingDown
          }
        />
        <MetricCard
          label="報酬率"
          value={renderReturns()}
          icon={ChartNoAxesCombined}
        />
      </div>

      <PageSection
        title="目前持倉"
        description={
          portfolios.length > 0 ? `${portfolios.length} 個標的` : undefined
        }
      >
        {portfolioLoading ? (
          <PortfolioRowsSkeleton />
        ) : error ? (
          <Alert variant="destructive">
            <AlertDescription className="flex flex-wrap items-center justify-between gap-3">
              <span>{error}</span>
              <Button size="sm" variant="outline" onClick={loadPortfolio}>
                重新載入
              </Button>
            </AlertDescription>
          </Alert>
        ) : portfolios.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center px-6 py-14 text-center">
              <div className="mb-4 rounded-full bg-primary/10 p-3 text-primary">
                <ChartNoAxesCombined className="h-5 w-5" />
              </div>
              <h2 className="font-semibold text-foreground">尚未建立持倉</h2>
              <p className="mt-1 max-w-sm text-sm text-muted-foreground">
                從股票工作區選擇標的並記錄第一筆買入交易。
              </p>
              <Button asChild className="mt-5">
                <Link href="/stocks">前往股票工作區</Link>
              </Button>
            </CardContent>
          </Card>
        ) : (
          <PortfolioTable
            portfolios={portfolios}
            onBuy={(portfolio) => openTransaction(portfolio, "BUY")}
            onSell={(portfolio) => openTransaction(portfolio, "SELL")}
            onRemove={setPendingRemoval}
          />
        )}
      </PageSection>

      <TransactionModal
        isOpen={transactionModal.isOpen}
        onClose={() =>
          setTransactionModal({ isOpen: false, stock: null, type: "BUY" })
        }
        stock={transactionModal.stock}
        transactionType={transactionModal.type}
        onSuccess={loadPortfolio}
      />

      <ConfirmDialog
        isOpen={pendingRemoval !== null}
        title="刪除持倉"
        message={`確定要刪除 ${pendingRemoval?.stock_symbol || "此標的"} 的持倉嗎？此操作不會刪除既有交易紀錄。`}
        confirmText="刪除持倉"
        onConfirm={confirmRemoval}
        onCancel={() => setPendingRemoval(null)}
      />
    </PageShell>
  );
}

interface PortfolioTableProps {
  portfolios: Portfolio[];
  onBuy: (portfolio: Portfolio) => void;
  onSell: (portfolio: Portfolio) => void;
  onRemove: (portfolio: Portfolio) => void;
}

function PortfolioTable({
  portfolios,
  onBuy,
  onSell,
  onRemove,
}: PortfolioTableProps) {
  return (
    <Card className="overflow-hidden">
      <div className="hidden md:block">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>標的</TableHead>
              <TableHead className="text-right">持有數量</TableHead>
              <TableHead className="text-right">平均成本</TableHead>
              <TableHead className="text-right">目前價格</TableHead>
              <TableHead className="text-right">市值</TableHead>
              <TableHead className="text-right">未實現損益</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {portfolios.map((portfolio) => {
              const market = inferMarketFromSymbol(portfolio.stock_symbol);
              const profitLoss = portfolio.profit_loss;
              const profitLossPercent = portfolio.profit_loss_percent;

              return (
                <TableRow key={portfolio.id}>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <div>
                        <div className="font-semibold text-foreground">
                          {portfolio.stock_symbol}
                        </div>
                        <div className="max-w-40 truncate text-xs text-muted-foreground">
                          {portfolio.stock_name || "—"}
                        </div>
                      </div>
                      <Badge variant="outline">
                        {market === "TW" ? "TW" : "US"}
                      </Badge>
                    </div>
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    {portfolio.quantity.toLocaleString()}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatMarketCurrency(portfolio.avg_cost, market)}
                  </TableCell>
                  <TableCell className="text-right">
                    {portfolio.current_price == null
                      ? "—"
                      : formatMarketCurrency(portfolio.current_price, market)}
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    {portfolio.current_value == null
                      ? "—"
                      : formatMarketCurrency(portfolio.current_value, market)}
                  </TableCell>
                  <TableCell
                    className={`text-right font-medium ${
                      profitLoss == null
                        ? "text-muted-foreground"
                        : profitLoss >= 0
                          ? "text-success"
                          : "text-destructive"
                    }`}
                  >
                    <div>
                      {profitLoss == null
                        ? "—"
                        : formatMarketCurrency(profitLoss, market)}
                    </div>
                    <div className="text-xs">
                      {profitLossPercent == null
                        ? "—"
                        : formatSignedPercent(profitLossPercent)}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex justify-end gap-1">
                      <Button
                        size="xs"
                        variant="outline"
                        onClick={() => onBuy(portfolio)}
                      >
                        加倉
                      </Button>
                      <Button
                        size="xs"
                        variant="destructiveOutline"
                        onClick={() => onSell(portfolio)}
                      >
                        減倉
                      </Button>
                      <Button size="iconSm" variant="ghost" asChild>
                        <Link
                          href={`/dashboard?stock=${portfolio.stock_id}&source=portfolio`}
                          aria-label={`查看 ${portfolio.stock_symbol} 圖表`}
                        >
                          <ChartNoAxesCombined className="h-4 w-4" />
                        </Link>
                      </Button>
                      <Button
                        size="iconSm"
                        variant="ghost"
                        onClick={() => onRemove(portfolio)}
                        aria-label={`刪除 ${portfolio.stock_symbol} 持倉`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      <div className="divide-y divide-border md:hidden">
        {portfolios.map((portfolio) => {
          const market = inferMarketFromSymbol(portfolio.stock_symbol);
          const profitLoss = portfolio.profit_loss;
          const profitLossPercent = portfolio.profit_loss_percent;
          return (
            <article key={portfolio.id} className="p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-foreground">
                      {portfolio.stock_symbol}
                    </h3>
                    <Badge variant="outline">{market}</Badge>
                  </div>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {portfolio.stock_name || "—"}
                  </p>
                </div>
                <div
                  className={`text-right ${
                    profitLoss == null
                      ? "text-muted-foreground"
                      : profitLoss >= 0
                        ? "text-success"
                        : "text-destructive"
                  }`}
                >
                  <div className="font-semibold tabular-nums">
                    {profitLossPercent == null
                      ? "—"
                      : formatSignedPercent(profitLossPercent)}
                  </div>
                  <div className="text-xs tabular-nums">
                    {profitLoss == null
                      ? "—"
                      : formatMarketCurrency(profitLoss, market)}
                  </div>
                </div>
              </div>

              <dl className="mt-4 grid grid-cols-3 gap-3 text-sm">
                <div>
                  <dt className="text-xs text-muted-foreground">持有</dt>
                  <dd className="mt-1 font-medium tabular-nums">
                    {portfolio.quantity.toLocaleString()} 股
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">平均成本</dt>
                  <dd className="mt-1 font-medium tabular-nums">
                    {formatMarketCurrency(portfolio.avg_cost, market)}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">目前市值</dt>
                  <dd className="mt-1 font-medium tabular-nums">
                    {portfolio.current_value == null
                      ? "—"
                      : formatMarketCurrency(portfolio.current_value, market)}
                  </dd>
                </div>
              </dl>

              <div className="mt-4 grid grid-cols-3 gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => onBuy(portfolio)}
                >
                  <ShoppingCart className="h-4 w-4" />
                  加倉
                </Button>
                <Button
                  size="sm"
                  variant="destructiveOutline"
                  onClick={() => onSell(portfolio)}
                >
                  <TrendingDown className="h-4 w-4" />
                  減倉
                </Button>
                <Button size="sm" variant="outline" asChild>
                  <Link
                    href={`/dashboard?stock=${portfolio.stock_id}&source=portfolio`}
                  >
                    <ChartNoAxesCombined className="h-4 w-4" />
                    圖表
                  </Link>
                </Button>
              </div>
              <Button
                size="sm"
                variant="ghost"
                className="mt-2 w-full text-muted-foreground"
                onClick={() => onRemove(portfolio)}
              >
                <Trash2 className="h-4 w-4" />
                刪除持倉
              </Button>
            </article>
          );
        })}
      </div>
    </Card>
  );
}

function formatSignedPercent(percent: number) {
  return `${percent >= 0 ? "+" : ""}${percent.toFixed(2)}%`;
}

function PortfolioSkeleton() {
  return (
    <PageShell>
      <PageHeader title="投資組合" />
      <PortfolioRowsSkeleton />
    </PageShell>
  );
}

function PortfolioRowsSkeleton() {
  return (
    <Card>
      <CardContent className="space-y-4 p-5">
        {[1, 2, 3].map((item) => (
          <div key={item} className="flex items-center justify-between gap-4">
            <div className="space-y-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-3 w-36" />
            </div>
            <Skeleton className="h-8 w-28" />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
