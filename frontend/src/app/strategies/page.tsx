/**
 * 策略訂閱頁面
 */
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAppSelector, useAppDispatch } from '@/store';
import { fetchSignalStatistics, selectSignalStatistics, selectStatisticsLoading } from '@/store/slices/strategySlice';
import { Card, CardContent } from '@/components/ui/card';
import { MetricCard, PageHeader, PageShell } from '@/components/ui/page';
import { Skeleton } from '@/components/ui/skeleton';
import { SubscriptionManager, SignalList } from '@/components/Strategy';
import { TrendingUp, Target, Calendar, Activity } from 'lucide-react';

export default function StrategiesPage() {
  const router = useRouter();
  const dispatch = useAppDispatch();
  const { isAuthenticated } = useAppSelector((state) => state.auth);
  const statistics = useAppSelector(selectSignalStatistics);
  const statisticsLoading = useAppSelector(selectStatisticsLoading);
  const [isMounted, setIsMounted] = useState(false);

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
            value={statisticsLoading ? <Skeleton className="h-8 w-16" /> : statistics?.active_count || 0}
            icon={Activity}
            tone="blue"
          />
          <MetricCard
            label="總信號數"
            value={statisticsLoading ? <Skeleton className="h-8 w-16" /> : statistics?.total_count || 0}
            icon={Target}
          />
          <MetricCard
            label="本週新信號"
            value={statisticsLoading ? <Skeleton className="h-8 w-16" /> : statistics?.this_week_count || 0}
            icon={Calendar}
            tone="green"
          />
          <MetricCard
            label="平均信心度"
            value={statisticsLoading ? <Skeleton className="h-8 w-16" /> : statistics?.avg_confidence ? `${statistics.avg_confidence.toFixed(1)}%` : '0%'}
            icon={TrendingUp}
            tone="purple"
          />
        </div>

        {/* 主內容區 - 訂閱管理和信號列表 */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* 左側 - 訂閱管理 */}
          <div className="lg:col-span-1">
            <Card>
              <CardContent className="p-6">
                <SubscriptionManager />
              </CardContent>
            </Card>
          </div>

          {/* 右側 - 信號列表 */}
          <div className="lg:col-span-2">
            <SignalList />
          </div>
        </div>
    </PageShell>
  );
}
