/**
 * 首頁組件 - Client Component with real data
 */
'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { MetricCard, PageHeader, PageSection, PageShell } from '@/components/ui/page';
import { ArrowRight, BarChart3, TrendingUp, Activity, Database, Target, Wallet } from 'lucide-react';
import { useAppSelector } from '@/store';
import { getListStocks, getStockLists } from '@/services/stockListApi';
import StocksApiService from '@/services/stocksApi';

type SystemStatus = 'checking' | 'running' | 'error';

export default function HomePage() {
  const { isAuthenticated } = useAppSelector((state) => state.auth);
  const [systemStatus, setSystemStatus] = useState<Record<string, SystemStatus>>({
    backend: 'checking',
    database: 'checking',
    websocket: 'checking',
  });
  const [trackedStocksCount, setTrackedStocksCount] = useState<number>(0);
  const [isMounted, setIsMounted] = useState(false);
  const [totalStocks, setTotalStocks] = useState<number>(0);
  const [appVersion, setAppVersion] = useState<string | null>(null);

  useEffect(() => {
    setIsMounted(true);
    setAppVersion(process.env.NEXT_PUBLIC_APP_VERSION || 'local');
  }, []);

  useEffect(() => {
    if (!isMounted) return;

    const loadStockCount = async () => {
      try {
        const response = await StocksApiService.getStocks({ page: 1, pageSize: 1 });
        setTotalStocks(response.total || 0);
      } catch (error) {
        console.error('載入股票數量失敗:', error);
      }
    };

    const timer = setTimeout(loadStockCount, 500);
    return () => clearTimeout(timer);
  }, [isMounted]);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await fetch('/api/health');
        const data = await response.json();
        setSystemStatus({
          backend: data.checks?.api?.status === 'healthy' ? 'running' : 'error',
          database: data.checks?.database?.status === 'healthy' ? 'running' : 'error',
          websocket: data.checks?.websocket?.status === 'healthy' ? 'running' : 'error',
        });
      } catch {
        setSystemStatus({
          backend: 'error',
          database: 'error',
          websocket: 'error'
        });
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const fetchTrackedStocksCount = async () => {
      if (!isAuthenticated) {
        setTrackedStocksCount(0);
        return;
      }

      try {
        const response = await getStockLists();
        const uniqueStockIds = new Set<number>();

        for (const list of response.items) {
          try {
            const listStocks = await getListStocks(list.id);
            listStocks.items.forEach((stock) => {
              uniqueStockIds.add(stock.id);
            });
          } catch (error) {
            console.error(`獲取清單 ${list.id} 的股票失敗:`, error);
          }
        }

        setTrackedStocksCount(uniqueStockIds.size);
      } catch (error) {
        console.error('獲取追蹤股票數量失敗:', error);
        setTrackedStocksCount(0);
      }
    };

    fetchTrackedStocksCount();
  }, [isAuthenticated]);

  const getStatusBadge = (status: SystemStatus) => {
    if (status === 'running') {
      return (
        <Badge variant="outline" className="border-green-200 bg-green-50 text-green-700">
          <div className="mr-2 h-2 w-2 rounded-full bg-green-500"></div>
          運行中
        </Badge>
      );
    }

    if (status === 'checking') {
      return (
        <Badge variant="outline" className="border-amber-200 bg-amber-50 text-amber-700">
          <div className="mr-2 h-2 w-2 animate-pulse rounded-full bg-amber-500"></div>
          檢查中
        </Badge>
      );
    }

    return (
      <Badge variant="outline" className="border-red-200 bg-red-50 text-red-700">
        <div className="mr-2 h-2 w-2 rounded-full bg-red-500"></div>
        離線
      </Badge>
    );
  };

  const stats = [
    {
      label: '追蹤股票',
      value: !isMounted || !isAuthenticated ? '—' : trackedStocksCount,
      icon: TrendingUp,
    },
    {
      label: '系統股票',
      value: totalStocks,
      icon: Database,
    },
    {
      label: '技術指標',
      value: 6,
      icon: BarChart3,
    },
  ];

  const quickLinks = [
    {
      href: '/stocks',
      title: '股票管理',
      description: '維護自選清單、排序與追蹤標的。',
      icon: Database,
    },
    {
      href: '/dashboard',
      title: '即時分析',
      description: '查詢股票並查看價格走勢與技術指標。',
      icon: BarChart3,
    },
    {
      href: '/portfolio',
      title: '持倉管理',
      description: '檢視持倉、買賣紀錄與投資組合表現。',
      icon: Wallet,
    },
    {
      href: '/strategies',
      title: '策略中心',
      description: '管理策略訂閱並追蹤交易信號。',
      icon: Target,
    },
  ];

  return (
    <PageShell>
      <PageHeader
        title="股票分析平台"
        description="以清單、即時圖表、持倉與策略信號為核心的股票分析工作台。"
        eyebrow={appVersion ? (
          <Badge variant="outline" className="border-gray-200 bg-white text-gray-600" suppressHydrationWarning>
            {appVersion}
          </Badge>
        ) : null}
        actions={
          <>
          <Button asChild>
            <Link href="/stocks">管理股票</Link>
          </Button>
          <Button variant="outline" asChild>
            <Link href="/dashboard">查看即時分析</Link>
          </Button>
          </>
        }
      />

      <section className="grid gap-4 md:grid-cols-3">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <MetricCard
              key={stat.label}
              label={stat.label}
              value={stat.value}
              icon={Icon}
            />
          );
        })}
      </section>

      <PageSection title="主要工作流">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {quickLinks.map((item) => {
            const Icon = item.icon;
            return (
              <Link key={item.href} href={item.href} className="group block">
                <Card className="h-full rounded-lg shadow-sm transition-colors hover:border-gray-300">
                  <CardHeader className="p-5">
                    <CardTitle className="flex items-center justify-between text-base">
                      <span className="flex items-center gap-2">
                        <Icon className="h-4 w-4 text-gray-500" />
                        {item.title}
                      </span>
                      <ArrowRight className="h-4 w-4 text-gray-400 transition-transform group-hover:translate-x-0.5" />
                    </CardTitle>
                    <CardDescription className="pt-1 leading-6">
                      {item.description}
                    </CardDescription>
                  </CardHeader>
                </Card>
              </Link>
            );
          })}
        </div>
      </PageSection>

      <PageSection>
        <Card className="rounded-lg shadow-sm">
          <CardHeader className="p-5">
            <CardTitle className="flex items-center gap-2 text-base">
              <Activity className="h-4 w-4 text-gray-500" />
              系統狀態
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 p-5 pt-0 md:grid-cols-3">
            <div className="flex items-center justify-between rounded-md border border-gray-200 bg-white px-4 py-3">
              <span className="text-sm text-gray-600">後端 API</span>
              {getStatusBadge(systemStatus.backend)}
            </div>
            <div className="flex items-center justify-between rounded-md border border-gray-200 bg-white px-4 py-3">
              <span className="text-sm text-gray-600">資料庫</span>
              {getStatusBadge(systemStatus.database)}
            </div>
            <div className="flex items-center justify-between rounded-md border border-gray-200 bg-white px-4 py-3">
              <span className="text-sm text-gray-600">WebSocket</span>
              {getStatusBadge(systemStatus.websocket)}
            </div>
          </CardContent>
        </Card>
      </PageSection>
    </PageShell>
  );
}
