/**
 * 策略訂閱頁面
 */
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAppSelector, useAppDispatch } from '@/store';
import {
  fetchSignalStatistics,
  selectSignalStatistics,
  selectStatisticsLoading,
} from '@/store/slices/strategySlice';
import {
  getStockCompositeScores,
  getStrategyReliabilityScores,
} from '@/services/strategyApi';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { MetricCard, PageHeader, PageShell } from '@/components/ui/page';
import { Skeleton } from '@/components/ui/skeleton';
import { SubscriptionManager, SignalList } from '@/components/Strategy';
import { TrendingUp, Target, Calendar, Activity } from 'lucide-react';
import type {
  StockCompositeScore,
  StrategyReliabilityScore,
} from '@/types/strategy';

const formatPercent = (value: number) => `${(value * 100).toFixed(1)}%`;

const formatCompositeScore = (value: number) => {
  const score = value * 100;
  return `${score > 0 ? '+' : ''}${score.toFixed(1)}`;
};

const directionLabels: Record<StockCompositeScore['direction'], string> = {
  bullish: '看多',
  neutral: '中性',
  bearish: '看空',
};

const directionClasses: Record<StockCompositeScore['direction'], string> = {
  bullish: 'text-emerald-700 bg-emerald-50',
  neutral: 'text-gray-700 bg-gray-100',
  bearish: 'text-red-700 bg-red-50',
};

export default function StrategiesPage() {
  const router = useRouter();
  const dispatch = useAppDispatch();
  const { isAuthenticated } = useAppSelector((state) => state.auth);
  const statistics = useAppSelector(selectSignalStatistics);
  const statisticsLoading = useAppSelector(selectStatisticsLoading);
  const [isMounted, setIsMounted] = useState(false);
  const [reliabilityScores, setReliabilityScores] = useState<StrategyReliabilityScore[]>([]);
  const [compositeScores, setCompositeScores] = useState<StockCompositeScore[]>([]);
  const [evaluationLoading, setEvaluationLoading] = useState(false);

  // 確保只在客戶端渲染，避免 hydration 錯誤
  useEffect(() => {
    setIsMounted(true);
  }, []);

  useEffect(() => {
    if (!isMounted) return;

    if (!isAuthenticated) {
      router.push('/login');
      return;
    }

    // 載入統計資訊
    dispatch(fetchSignalStatistics({}));
    setEvaluationLoading(true);
    Promise.all([
      getStrategyReliabilityScores(),
      getStockCompositeScores(50),
    ])
      .then(([reliability, composite]) => {
        setReliabilityScores(reliability.items);
        setCompositeScores(composite.items);
      })
      .catch(() => {
        setReliabilityScores([]);
        setCompositeScores([]);
      })
      .finally(() => setEvaluationLoading(false));
  }, [isAuthenticated, isMounted, dispatch, router]);

  // 在客戶端渲染前顯示 loading 狀態，避免 hydration 錯誤
  if (!isMounted) {
    return (
      <PageShell>
        <PageHeader title="交易策略中心" />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardContent className="p-6">
                <Skeleton className="h-6 w-32 mb-2" />
                <Skeleton className="h-4 w-48" />
              </CardContent>
            </Card>
          ))}
        </div>
      </PageShell>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <PageShell>
      <PageHeader
        title="交易策略中心"
        description="訂閱策略，接收智能交易信號，把握最佳進場時機。"
      />

      {/* 統計卡片 */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <MetricCard
          label="活躍信號"
          value={
            statisticsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              statistics?.active_count || 0
            )
          }
          icon={Activity}
          tone="blue"
        />
        <MetricCard
          label="總信號數"
          value={
            statisticsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              statistics?.total_count || 0
            )
          }
          icon={Target}
        />
        <MetricCard
          label="本週新信號"
          value={
            statisticsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              statistics?.this_week_count || 0
            )
          }
          icon={Calendar}
          tone="green"
        />
        <MetricCard
          label="平均信心度"
          value={
            statisticsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : statistics?.avg_confidence ? (
              `${statistics.avg_confidence.toFixed(1)}%`
            ) : (
              '0%'
            )
          }
          icon={TrendingUp}
          tone="purple"
        />
      </div>

      <Card>
        <CardContent className="p-6">
          <SubscriptionManager />
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card className="min-w-0">
          <CardHeader className="pb-3">
            <div className="flex items-start justify-between gap-4">
              <div>
                <CardTitle className="text-lg">策略可信度</CardTitle>
                <p className="mt-1 text-sm text-muted-foreground">
                  回測可靠度，按策略與週期拆分
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
              <p className="text-sm text-muted-foreground">尚未完成策略回測。</p>
            ) : (
              <div className="max-h-[420px] overflow-auto rounded-md border">
                <table className="w-full min-w-[640px] text-sm">
                  <thead className="sticky top-0 z-10 bg-card text-left text-muted-foreground shadow-sm">
                    <tr>
                      <th className="whitespace-nowrap px-4 py-3 font-medium">策略</th>
                      <th className="whitespace-nowrap px-3 py-3 font-medium">週期</th>
                      <th className="whitespace-nowrap px-3 py-3 text-right font-medium">
                        可信度
                      </th>
                      <th className="whitespace-nowrap px-3 py-3 text-right font-medium">
                        樣本
                      </th>
                      <th className="whitespace-nowrap px-4 py-3 font-medium">狀態</th>
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
                <CardTitle className="text-lg">股票綜合走勢</CardTitle>
                <p className="mt-1 text-sm text-muted-foreground">
                  多策略加權後的方向與一致性
                </p>
              </div>
              {!evaluationLoading && compositeScores.length > 0 && (
                <span className="shrink-0 rounded-md bg-gray-100 px-2 py-1 text-xs font-medium text-gray-600">
                  前 {compositeScores.length} 支
                </span>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {evaluationLoading ? (
              <Skeleton className="h-80 w-full" />
            ) : compositeScores.length === 0 ? (
              <p className="text-sm text-muted-foreground">尚未產生綜合評分。</p>
            ) : (
              <div className="max-h-[420px] overflow-auto rounded-md border">
                <table className="w-full min-w-[600px] text-sm">
                  <thead className="sticky top-0 z-10 bg-card text-left text-muted-foreground shadow-sm">
                    <tr>
                      <th className="whitespace-nowrap px-4 py-3 font-medium">股票</th>
                      <th className="whitespace-nowrap px-3 py-3 font-medium">方向</th>
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
                      <tr key={score.stock_id} className="hover:bg-gray-50">
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

      <SignalList />
    </PageShell>
  );
}
