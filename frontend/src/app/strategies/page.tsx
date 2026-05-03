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
      getStockCompositeScores(12),
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
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">策略可信度</CardTitle>
          </CardHeader>
          <CardContent>
            {evaluationLoading ? (
              <Skeleton className="h-32 w-full" />
            ) : reliabilityScores.length === 0 ? (
              <p className="text-sm text-muted-foreground">尚未完成策略回測。</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-left text-muted-foreground">
                    <tr>
                      <th className="pb-2 font-medium">策略</th>
                      <th className="pb-2 font-medium">週期</th>
                      <th className="pb-2 font-medium">可信度</th>
                      <th className="pb-2 font-medium">樣本</th>
                      <th className="pb-2 font-medium">狀態</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reliabilityScores.slice(0, 10).map((score) => (
                      <tr
                        key={`${score.strategy_type}-${score.horizon}`}
                        className="border-t"
                      >
                        <td className="py-2 font-medium">{score.strategy_type}</td>
                        <td className="py-2">{score.horizon}</td>
                        <td className="py-2">
                          {(score.reliability_score * 100).toFixed(1)}%
                        </td>
                        <td className="py-2">{score.sample_size}</td>
                        <td className="py-2 text-muted-foreground">
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

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">股票綜合走勢</CardTitle>
          </CardHeader>
          <CardContent>
            {evaluationLoading ? (
              <Skeleton className="h-32 w-full" />
            ) : compositeScores.length === 0 ? (
              <p className="text-sm text-muted-foreground">尚未產生綜合評分。</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-left text-muted-foreground">
                    <tr>
                      <th className="pb-2 font-medium">股票</th>
                      <th className="pb-2 font-medium">方向</th>
                      <th className="pb-2 font-medium">分數</th>
                      <th className="pb-2 font-medium">可信度</th>
                    </tr>
                  </thead>
                  <tbody>
                    {compositeScores.map((score) => (
                      <tr key={score.stock_id} className="border-t">
                        <td className="py-2 font-medium">{score.symbol}</td>
                        <td className="py-2">{score.direction}</td>
                        <td className="py-2">
                          {(score.composite_score * 100).toFixed(1)}
                        </td>
                        <td className="py-2">
                          {(score.confidence * 100).toFixed(1)}%
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
