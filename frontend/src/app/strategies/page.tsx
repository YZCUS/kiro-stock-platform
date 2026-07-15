/**
 * 策略工作台
 */
"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAppSelector, useAppDispatch } from "@/store";
import {
  fetchSignalStatistics,
  selectSignalStatistics,
  selectStatisticsLoading,
} from "@/store/slices/strategySlice";
import {
  getStockCompositeScores,
  getStrategyReliabilityScores,
} from "@/services/strategyApi";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MetricCard, PageHeader, PageShell } from "@/components/ui/page";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SubscriptionManager, SignalList } from "@/components/Strategy";
import {
  Activity,
  AlertCircle,
  BarChart3,
  Calendar,
  LayoutDashboard,
  ListChecks,
  Radio,
  RefreshCw,
  Target,
  TrendingUp,
} from "lucide-react";
import type {
  StockCompositeScore,
  StrategyReliabilityScore,
} from "@/types/strategy";

const formatPercent = (value: number) => `${(value * 100).toFixed(1)}%`;

const formatCompositeScore = (value: number) => {
  const score = value * 100;
  return `${score > 0 ? "+" : ""}${score.toFixed(1)}`;
};

const getErrorMessage = (error: unknown, fallback: string) => {
  if (typeof error === "string") return error;
  if (error instanceof Error && error.message) return error.message;
  return fallback;
};

const directionLabels: Record<StockCompositeScore["direction"], string> = {
  bullish: "看多",
  neutral: "中性",
  bearish: "看空",
};

const directionClasses: Record<StockCompositeScore["direction"], string> = {
  bullish: "text-emerald-700 bg-emerald-50",
  neutral: "text-gray-700 bg-gray-100",
  bearish: "text-red-700 bg-red-50",
};

export default function StrategiesPage() {
  const router = useRouter();
  const dispatch = useAppDispatch();
  const { initialized, isAuthenticated } = useAppSelector(
    (state) => state.auth,
  );
  const statistics = useAppSelector(selectSignalStatistics);
  const statisticsLoading = useAppSelector(selectStatisticsLoading);
  const [isMounted, setIsMounted] = useState(false);
  const [statisticsError, setStatisticsError] = useState<string | null>(null);
  const [reliabilityScores, setReliabilityScores] = useState<
    StrategyReliabilityScore[]
  >([]);
  const [compositeScores, setCompositeScores] = useState<StockCompositeScore[]>(
    [],
  );
  const [evaluationLoading, setEvaluationLoading] = useState(false);
  const [evaluationError, setEvaluationError] = useState<string | null>(null);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  const loadStatistics = useCallback(async () => {
    setStatisticsError(null);
    try {
      await dispatch(fetchSignalStatistics({})).unwrap();
    } catch (error) {
      setStatisticsError(getErrorMessage(error, "無法載入信號統計"));
    }
  }, [dispatch]);

  const loadEvaluation = useCallback(async () => {
    setEvaluationLoading(true);
    setEvaluationError(null);

    try {
      const [reliability, composite] = await Promise.all([
        getStrategyReliabilityScores(),
        getStockCompositeScores(50),
      ]);
      setReliabilityScores(reliability.items);
      setCompositeScores(composite.items);
    } catch (error) {
      setReliabilityScores([]);
      setCompositeScores([]);
      setEvaluationError(getErrorMessage(error, "無法載入策略評估"));
    } finally {
      setEvaluationLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isMounted || !initialized) return;

    if (!isAuthenticated) {
      router.replace("/login?redirect=/strategies");
      return;
    }

    void loadStatistics();
    void loadEvaluation();
  }, [
    initialized,
    isAuthenticated,
    isMounted,
    loadEvaluation,
    loadStatistics,
    router,
  ]);

  if (!isMounted || !initialized) {
    return (
      <PageShell>
        <PageHeader title="交易策略中心" />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
          {[1, 2, 3, 4].map((item) => (
            <Card key={item}>
              <CardContent className="p-5">
                <Skeleton className="mb-2 h-5 w-24" />
                <Skeleton className="h-8 w-16" />
              </CardContent>
            </Card>
          ))}
        </div>
      </PageShell>
    );
  }

  if (!isAuthenticated) return null;

  const statisticValue = (value: number | undefined) => {
    if (statisticsLoading) return <Skeleton className="h-8 w-16" />;
    if (statisticsError) return "—";
    return value ?? 0;
  };

  return (
    <PageShell>
      <PageHeader
        title="交易策略中心"
        description="統一管理策略訂閱、評估結果與交易信號。"
      />

      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="grid h-auto w-full grid-cols-2 gap-1 p-1 sm:grid-cols-4">
          <TabsTrigger value="overview" className="h-9 gap-2">
            <LayoutDashboard className="h-4 w-4" />
            總覽
          </TabsTrigger>
          <TabsTrigger value="subscriptions" className="h-9 gap-2">
            <ListChecks className="h-4 w-4" />
            訂閱
          </TabsTrigger>
          <TabsTrigger value="evaluation" className="h-9 gap-2">
            <BarChart3 className="h-4 w-4" />
            評估
          </TabsTrigger>
          <TabsTrigger value="signals" className="h-9 gap-2">
            <Radio className="h-4 w-4" />
            信號
          </TabsTrigger>
        </TabsList>

        <TabsContent
          forceMount
          value="overview"
          className="mt-5 space-y-4 data-[state=inactive]:hidden"
        >
          {statisticsError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <span>{statisticsError}</span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => void loadStatistics()}
                >
                  <RefreshCw className="h-4 w-4" />
                  重試
                </Button>
              </AlertDescription>
            </Alert>
          )}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              label="活躍信號"
              value={statisticValue(statistics?.active_count)}
              icon={Activity}
              tone="blue"
            />
            <MetricCard
              label="總信號數"
              value={statisticValue(statistics?.total_count)}
              icon={Target}
            />
            <MetricCard
              label="本週新信號"
              value={statisticValue(statistics?.this_week_count)}
              icon={Calendar}
              tone="green"
            />
            <MetricCard
              label="平均信心度"
              value={
                statisticsLoading ? (
                  <Skeleton className="h-8 w-16" />
                ) : statisticsError ? (
                  "—"
                ) : (
                  `${statistics?.avg_confidence?.toFixed(1) ?? "0.0"}%`
                )
              }
              icon={TrendingUp}
              tone="purple"
            />
          </div>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">評估摘要</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-md border bg-gray-50 px-4 py-3">
                <div className="text-xs font-medium text-gray-500">
                  資料狀態
                </div>
                <div className="mt-1 text-sm font-semibold text-gray-900">
                  {evaluationLoading
                    ? "更新中"
                    : evaluationError
                      ? "載入失敗"
                      : "已更新"}
                </div>
              </div>
              <div className="rounded-md border bg-gray-50 px-4 py-3">
                <div className="text-xs font-medium text-gray-500">
                  策略可信度
                </div>
                <div className="mt-1 text-sm font-semibold text-gray-900">
                  {evaluationLoading ? "—" : `${reliabilityScores.length} 組`}
                </div>
              </div>
              <div className="rounded-md border bg-gray-50 px-4 py-3">
                <div className="text-xs font-medium text-gray-500">
                  股票綜合評分
                </div>
                <div className="mt-1 text-sm font-semibold text-gray-900">
                  {evaluationLoading ? "—" : `${compositeScores.length} 檔`}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent
          forceMount
          value="subscriptions"
          className="mt-5 data-[state=inactive]:hidden"
        >
          <Card>
            <CardContent className="p-4 sm:p-5">
              <SubscriptionManager />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent
          forceMount
          value="evaluation"
          className="mt-5 space-y-4 data-[state=inactive]:hidden"
        >
          {evaluationError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <span>{evaluationError}</span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => void loadEvaluation()}
                >
                  <RefreshCw className="h-4 w-4" />
                  重試
                </Button>
              </AlertDescription>
            </Alert>
          )}

          {!evaluationError && (
            <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
              <Card className="min-w-0">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <CardTitle className="text-base">策略可信度</CardTitle>
                      <p className="mt-1 text-sm text-muted-foreground">
                        按策略與週期檢視回測可靠度
                      </p>
                    </div>
                    {!evaluationLoading && reliabilityScores.length > 0 && (
                      <span className="shrink-0 rounded-md bg-gray-100 px-2 py-1 text-xs font-medium text-gray-600">
                        {reliabilityScores.length} 組
                      </span>
                    )}
                  </div>
                </CardHeader>
                <CardContent>
                  {evaluationLoading ? (
                    <Skeleton className="h-80 w-full" />
                  ) : reliabilityScores.length === 0 ? (
                    <div className="rounded-md border border-dashed px-4 py-10 text-center">
                      <p className="text-sm font-medium text-gray-700">
                        尚無策略回測評估
                      </p>
                      <p className="mt-1 text-xs text-gray-500">
                        完成回測後會在此顯示可信度。
                      </p>
                    </div>
                  ) : (
                    <div className="max-h-[420px] overflow-auto rounded-md border">
                      <table className="w-full min-w-[640px] text-sm">
                        <caption className="sr-only">策略可信度評估</caption>
                        <thead className="sticky top-0 z-10 bg-card text-left text-muted-foreground shadow-sm">
                          <tr>
                            <th className="whitespace-nowrap px-4 py-3 font-medium">
                              策略
                            </th>
                            <th className="whitespace-nowrap px-3 py-3 font-medium">
                              週期
                            </th>
                            <th className="whitespace-nowrap px-3 py-3 text-right font-medium">
                              可信度
                            </th>
                            <th className="whitespace-nowrap px-3 py-3 text-right font-medium">
                              樣本
                            </th>
                            <th className="whitespace-nowrap px-4 py-3 font-medium">
                              狀態
                            </th>
                          </tr>
                        </thead>
                        <tbody className="divide-y">
                          {reliabilityScores.map((score) => (
                            <tr
                              key={`${score.strategy_type}-${score.horizon}`}
                              className="hover:bg-gray-50"
                            >
                              <td className="max-w-[220px] truncate px-4 py-3 font-medium">
                                {score.strategy_type}
                              </td>
                              <td className="whitespace-nowrap px-3 py-3">
                                <span className="rounded-md bg-gray-100 px-2 py-1 text-xs font-medium">
                                  {score.horizon}
                                </span>
                              </td>
                              <td className="whitespace-nowrap px-3 py-3 text-right font-medium tabular-nums">
                                {formatPercent(score.reliability_score)}
                              </td>
                              <td className="whitespace-nowrap px-3 py-3 text-right tabular-nums text-muted-foreground">
                                {score.sample_size.toLocaleString()}
                              </td>
                              <td className="whitespace-nowrap px-4 py-3 text-muted-foreground">
                                {score.validation_status}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card className="min-w-0">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <CardTitle className="text-base">股票綜合走勢</CardTitle>
                      <p className="mt-1 text-sm text-muted-foreground">
                        比較多策略加權後的方向與一致性
                      </p>
                    </div>
                    {!evaluationLoading && compositeScores.length > 0 && (
                      <span className="shrink-0 rounded-md bg-gray-100 px-2 py-1 text-xs font-medium text-gray-600">
                        {compositeScores.length} 檔
                      </span>
                    )}
                  </div>
                </CardHeader>
                <CardContent>
                  {evaluationLoading ? (
                    <Skeleton className="h-80 w-full" />
                  ) : compositeScores.length === 0 ? (
                    <div className="rounded-md border border-dashed px-4 py-10 text-center">
                      <p className="text-sm font-medium text-gray-700">
                        尚無股票綜合評分
                      </p>
                      <p className="mt-1 text-xs text-gray-500">
                        策略產生足夠信號後會在此彙總。
                      </p>
                    </div>
                  ) : (
                    <div className="max-h-[420px] overflow-auto rounded-md border">
                      <table className="w-full min-w-[600px] text-sm">
                        <caption className="sr-only">股票綜合走勢評分</caption>
                        <thead className="sticky top-0 z-10 bg-card text-left text-muted-foreground shadow-sm">
                          <tr>
                            <th className="whitespace-nowrap px-4 py-3 font-medium">
                              股票
                            </th>
                            <th className="whitespace-nowrap px-3 py-3 font-medium">
                              方向
                            </th>
                            <th className="whitespace-nowrap px-3 py-3 text-right font-medium">
                              分數
                            </th>
                            <th className="whitespace-nowrap px-3 py-3 text-right font-medium">
                              一致性
                            </th>
                            <th className="whitespace-nowrap px-4 py-3 text-right font-medium">
                              訊號
                            </th>
                          </tr>
                        </thead>
                        <tbody className="divide-y">
                          {compositeScores.map((score) => (
                            <tr
                              key={score.stock_id}
                              className="hover:bg-gray-50"
                            >
                              <td className="whitespace-nowrap px-4 py-3 font-medium">
                                {score.symbol}
                              </td>
                              <td className="whitespace-nowrap px-3 py-3">
                                <span
                                  className={`rounded-md px-2 py-1 text-xs font-medium ${directionClasses[score.direction]}`}
                                >
                                  {directionLabels[score.direction]}
                                </span>
                              </td>
                              <td className="whitespace-nowrap px-3 py-3 text-right font-medium tabular-nums">
                                {formatCompositeScore(score.composite_score)}
                              </td>
                              <td className="whitespace-nowrap px-3 py-3 text-right tabular-nums">
                                {formatPercent(score.confidence)}
                              </td>
                              <td className="whitespace-nowrap px-4 py-3 text-right text-muted-foreground tabular-nums">
                                {score.positive_count}/{score.negative_count}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>

        <TabsContent
          forceMount
          value="signals"
          className="mt-5 data-[state=inactive]:hidden"
        >
          <SignalList />
        </TabsContent>
      </Tabs>
    </PageShell>
  );
}
