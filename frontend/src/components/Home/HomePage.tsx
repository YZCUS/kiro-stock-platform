/**
 * 首頁組件 - Client Component with real data
 */
"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  ArrowRight,
  BarChart3,
  Database,
  Target,
  TrendingUp,
  Wallet,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  MetricCard,
  PageHeader,
  PageSection,
  PageShell,
} from "@/components/ui/page";
import { getStockLists } from "@/services/stockListApi";
import StocksApiService from "@/services/stocksApi";
import { useAppSelector } from "@/store";

type SystemStatus = "checking" | "running" | "degraded" | "error";

const normalizeHealthStatus = (status?: string): SystemStatus => {
  if (status === "healthy") return "running";
  if (status === "degraded") return "degraded";
  return "error";
};

const numberFormatter = new Intl.NumberFormat("zh-TW");

export default function HomePage() {
  const { isAuthenticated } = useAppSelector((state) => state.auth);
  const [systemStatus, setSystemStatus] = useState<
    Record<string, SystemStatus>
  >({
    backend: "checking",
    database: "checking",
    websocket: "checking",
  });
  const [trackedStocksCount, setTrackedStocksCount] = useState<number | null>(
    null,
  );
  const [isMounted, setIsMounted] = useState(false);
  const [totalStocks, setTotalStocks] = useState<number | null>(null);
  const [appVersion, setAppVersion] = useState<string | null>(null);

  useEffect(() => {
    setIsMounted(true);
    setAppVersion(process.env.NEXT_PUBLIC_APP_VERSION || "local");
  }, []);

  useEffect(() => {
    if (!isMounted) return;

    let cancelled = false;

    const loadStockCount = async () => {
      try {
        const response = await StocksApiService.getStocks({
          page: 1,
          pageSize: 1,
        });
        if (!cancelled) setTotalStocks(response.total || 0);
      } catch (error) {
        console.error("載入股票數量失敗:", error);
        if (!cancelled) setTotalStocks(null);
      }
    };

    const timer = setTimeout(loadStockCount, 500);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [isMounted]);

  useEffect(() => {
    let cancelled = false;

    const checkHealth = async () => {
      try {
        const response = await fetch("/api/health");
        const data = await response.json();
        if (cancelled) return;

        setSystemStatus({
          backend: normalizeHealthStatus(data.checks?.api?.status),
          database: normalizeHealthStatus(data.checks?.database?.status),
          websocket: normalizeHealthStatus(data.checks?.websocket?.status),
        });
      } catch {
        if (cancelled) return;
        setSystemStatus({
          backend: "error",
          database: "error",
          websocket: "error",
        });
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    const fetchTrackedStocksCount = async () => {
      if (!isAuthenticated) {
        setTrackedStocksCount(null);
        return;
      }

      setTrackedStocksCount(null);

      try {
        const response = await getStockLists();
        if (!cancelled) {
          setTrackedStocksCount(
            response.items.reduce(
              (total, list) => total + (list.stocks_count ?? 0),
              0,
            ),
          );
        }
      } catch (error) {
        console.error("獲取追蹤股票數量失敗:", error);
        if (!cancelled) setTrackedStocksCount(null);
      }
    };

    fetchTrackedStocksCount();
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated]);

  const getStatusBadge = (status: SystemStatus) => {
    if (status === "running") {
      return (
        <Badge variant="success">
          <span
            aria-hidden="true"
            className="mr-1.5 h-1.5 w-1.5 rounded-full bg-success"
          />
          運行中
        </Badge>
      );
    }

    if (status === "checking") {
      return (
        <Badge variant="warning">
          <span
            aria-hidden="true"
            className="mr-1.5 h-1.5 w-1.5 animate-pulse rounded-full bg-warning"
          />
          檢查中
        </Badge>
      );
    }

    if (status === "degraded") {
      return (
        <Badge variant="warning">
          <span
            aria-hidden="true"
            className="mr-1.5 h-1.5 w-1.5 rounded-full bg-warning"
          />
          服務降級
        </Badge>
      );
    }

    return (
      <Badge variant="destructive">
        <span
          aria-hidden="true"
          className="mr-1.5 h-1.5 w-1.5 rounded-full bg-destructive"
        />
        離線
      </Badge>
    );
  };

  const formatCount = (value: number | null) =>
    value === null ? "—" : numberFormatter.format(value);

  const stats = [
    {
      label: "追蹤項目",
      value: isAuthenticated ? formatCount(trackedStocksCount) : "—",
      detail: isAuthenticated ? "各自選清單項目合計" : "登入後顯示你的追蹤清單",
      icon: TrendingUp,
      tone: "blue" as const,
    },
    {
      label: "可分析標的",
      value: formatCount(totalStocks),
      detail: "目前系統可搜尋的股票資料",
      icon: Database,
      tone: "neutral" as const,
    },
    {
      label: "技術指標",
      value: "6",
      detail: "支援趨勢、動能與波動分析",
      icon: BarChart3,
      tone: "neutral" as const,
    },
  ];

  const workflows = [
    {
      href: "/stocks",
      title: "整理觀察清單",
      description: "新增、分類並維護需要持續追蹤的股票。",
      action: "管理標的",
      icon: Database,
    },
    {
      href: "/strategies",
      title: "檢視策略訊號",
      description: "追蹤策略訂閱與最新交易訊號。",
      action: "前往策略",
      icon: Target,
    },
    {
      href: "/portfolio",
      title: "更新投資組合",
      description: "記錄交易並檢視目前持倉與損益。",
      action: "檢視持倉",
      icon: Wallet,
    },
  ];

  const statusItems = [
    { key: "backend", label: "後端 API" },
    { key: "database", label: "市場資料庫" },
    { key: "websocket", label: "即時連線" },
  ] as const;
  const runningServices = statusItems.filter(
    ({ key }) => systemStatus[key] === "running",
  ).length;
  const isCheckingStatus = statusItems.some(
    ({ key }) => systemStatus[key] === "checking",
  );

  return (
    <PageShell>
      <PageHeader
        title="投資工作台"
        description="集中管理觀察清單、即時行情、策略訊號與持倉，讓每日分析從同一個工作區開始。"
        eyebrow={
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="info">市場工作區</Badge>
            {appVersion && (
              <span
                className="text-xs font-medium text-muted-foreground"
                suppressHydrationWarning
              >
                版本 {appVersion}
              </span>
            )}
          </div>
        }
        actions={
          <>
            <Button asChild>
              <Link href="/dashboard">
                開啟即時分析
                <ArrowRight aria-hidden="true" />
              </Link>
            </Button>
            <Button variant="outline" asChild>
              <Link href="/stocks">管理自選清單</Link>
            </Button>
          </>
        }
      />

      <section aria-label="工作台概況" className="grid gap-4 md:grid-cols-3">
        {stats.map((stat) => (
          <MetricCard
            key={stat.label}
            label={stat.label}
            value={stat.value}
            detail={stat.detail}
            icon={stat.icon}
            tone={stat.tone}
          />
        ))}
      </section>

      <PageSection
        title="今日工作流程"
        description="先確認標的與市場走勢，再進入策略或持倉管理。"
      >
        <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
          <Card>
            <CardHeader className="border-b border-border">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3
                      aria-hidden="true"
                      className="h-4 w-4 text-primary"
                    />
                    即時市場分析
                  </CardTitle>
                  <CardDescription className="mt-1 leading-6">
                    選擇股票後檢視價格走勢、技術指標與最新市場資訊。
                  </CardDescription>
                </div>
                <Button size="sm" asChild>
                  <Link href="/dashboard">
                    開始分析
                    <ArrowRight aria-hidden="true" />
                  </Link>
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <nav aria-label="投資工作流程" className="divide-y divide-border">
                {workflows.map((item) => {
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className="group flex items-center gap-3 px-5 py-4 transition-colors hover:bg-muted/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
                    >
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-border bg-muted text-muted-foreground transition-colors group-hover:border-primary/20 group-hover:bg-primary/10 group-hover:text-primary">
                        <Icon aria-hidden="true" className="h-4 w-4" />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block text-sm font-medium text-foreground">
                          {item.title}
                        </span>
                        <span className="mt-0.5 block text-sm leading-5 text-muted-foreground">
                          {item.description}
                        </span>
                      </span>
                      <span className="hidden shrink-0 items-center gap-1 text-sm font-medium text-primary sm:flex">
                        {item.action}
                        <ArrowRight
                          aria-hidden="true"
                          className="h-4 w-4 transition-transform group-hover:translate-x-0.5"
                        />
                      </span>
                    </Link>
                  );
                })}
              </nav>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="border-b border-border">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Activity
                      aria-hidden="true"
                      className="h-4 w-4 text-muted-foreground"
                    />
                    系統狀態
                  </CardTitle>
                  <CardDescription className="mt-1">
                    {isCheckingStatus
                      ? "正在確認核心服務"
                      : `${runningServices}/${statusItems.length} 項服務正常`}
                  </CardDescription>
                </div>
                {!isCheckingStatus && (
                  <Badge
                    variant={
                      runningServices === statusItems.length
                        ? "success"
                        : "warning"
                    }
                  >
                    {runningServices === statusItems.length ? "可用" : "需留意"}
                  </Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <span className="sr-only" role="status" aria-live="polite">
                {isCheckingStatus
                  ? "正在檢查系統狀態"
                  : `${runningServices} 項服務正常，共 ${statusItems.length} 項`}
              </span>
              <dl className="divide-y divide-border">
                {statusItems.map(({ key, label }) => (
                  <div
                    key={key}
                    className="flex items-center justify-between gap-4 px-5 py-3.5"
                  >
                    <dt className="text-sm text-muted-foreground">{label}</dt>
                    <dd>{getStatusBadge(systemStatus[key])}</dd>
                  </div>
                ))}
              </dl>
            </CardContent>
          </Card>
        </div>
      </PageSection>
    </PageShell>
  );
}
