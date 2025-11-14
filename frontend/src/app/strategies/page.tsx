/**
 * 策略訂閱頁面
 */
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAppSelector, useAppDispatch } from '@/store';
import { fetchSignalStatistics, selectSignalStatistics, selectStatisticsLoading } from '@/store/slices/strategySlice';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
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
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-7xl mx-auto">
          <div className="mb-8">
            <h1 className="text-3xl font-bold mb-2">交易策略中心</h1>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            {[1, 2, 3, 4].map((i) => (
              <Card key={i}>
                <CardContent className="p-6">
                  <Skeleton className="h-6 w-32 mb-2" />
                  <Skeleton className="h-4 w-48" />
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">交易策略中心</h1>
          <p className="text-muted-foreground">
            訂閱策略，接收智能交易信號，把握最佳進場時機
          </p>
        </div>

        {/* 統計卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription className="flex items-center gap-2">
                <Activity className="h-4 w-4" />
                活躍信號
              </CardDescription>
              {statisticsLoading ? (
                <Skeleton className="h-8 w-16" />
              ) : (
                <CardTitle className="text-2xl text-blue-600">
                  {statistics?.active_count || 0}
                </CardTitle>
              )}
            </CardHeader>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardDescription className="flex items-center gap-2">
                <Target className="h-4 w-4" />
                總信號數
              </CardDescription>
              {statisticsLoading ? (
                <Skeleton className="h-8 w-16" />
              ) : (
                <CardTitle className="text-2xl">
                  {statistics?.total_count || 0}
                </CardTitle>
              )}
            </CardHeader>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardDescription className="flex items-center gap-2">
                <Calendar className="h-4 w-4" />
                本週新信號
              </CardDescription>
              {statisticsLoading ? (
                <Skeleton className="h-8 w-16" />
              ) : (
                <CardTitle className="text-2xl text-green-600">
                  {statistics?.this_week_count || 0}
                </CardTitle>
              )}
            </CardHeader>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardDescription className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4" />
                平均信心度
              </CardDescription>
              {statisticsLoading ? (
                <Skeleton className="h-8 w-16" />
              ) : (
                <CardTitle className="text-2xl text-purple-600">
                  {statistics?.avg_confidence ? `${statistics.avg_confidence.toFixed(1)}%` : '0%'}
                </CardTitle>
              )}
            </CardHeader>
          </Card>
        </div>

        {/* 主內容區 - 訂閱管理和信號列表 */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
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
      </div>
    </div>
  );
}
