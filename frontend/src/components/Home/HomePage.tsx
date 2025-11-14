/**
 * 首頁組件 - Client Component with real data
 */
'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ArrowRight, BarChart3, TrendingUp, Bell, Activity, Database, Zap } from 'lucide-react';
import { useAppSelector } from '@/store';
import { getStockLists } from '@/services/stockListApi';

export default function HomePage() {
  const { isAuthenticated } = useAppSelector((state) => state.auth);
  const [systemStatus, setSystemStatus] = useState({
    backend: 'checking',
    database: 'checking',
    websocket: 'checking'
  });
  const [trackedStocksCount, setTrackedStocksCount] = useState<number>(0);
  const [isMounted, setIsMounted] = useState(false);

  const [totalStocks, setTotalStocks] = useState<number>(0);

  // 處理客戶端掛載
  useEffect(() => {
    setIsMounted(true);
  }, []);

  // 延遲載入股票統計數據（非關鍵數據）
  useEffect(() => {
    if (!isMounted) return;

    const loadStockCount = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/v1/stocks?page=1&per_page=1');
        const data = await response.json();
        setTotalStocks(data.total || 0);
      } catch (error) {
        console.error('載入股票數量失敗:', error);
      }
    };

    // 延遲 500ms 載入，讓關鍵內容先渲染
    const timer = setTimeout(loadStockCount, 500);
    return () => clearTimeout(timer);
  }, [isMounted]);

  // 檢查系統狀態
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await fetch('http://localhost:8000/health');
        const data = await response.json();
        setSystemStatus({
          backend: data.status === 'healthy' ? 'running' : 'error',
          database: data.components?.database?.status === 'healthy' ? 'running' : 'error',
          websocket: data.components?.websocket?.status === 'healthy' ? 'running' : 'error'
        });
      } catch (error) {
        setSystemStatus({
          backend: 'error',
          database: 'error',
          websocket: 'error'
        });
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000); // 每 30 秒檢查一次
    return () => clearInterval(interval);
  }, []);

  // 獲取追蹤股票數量（當前用戶所有 stock lists 中不重複的股票數）
  useEffect(() => {
    const fetchTrackedStocksCount = async () => {
      if (!isAuthenticated) {
        setTrackedStocksCount(0);
        return;
      }

      try {
        // 獲取用戶的所有清單
        const response = await getStockLists();

        // 收集所有清單中的不重複股票 ID
        const uniqueStockIds = new Set<number>();

        // 遍歷每個清單，獲取其中的股票
        for (const list of response.items) {
          try {
            // 動態導入 getListStocks 避免循環依賴
            const { getListStocks } = await import('@/services/stockListApi');
            const listStocks = await getListStocks(list.id);

            // 收集股票 ID
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
  }, [isAuthenticated]); // 依賴 isAuthenticated

  const getStatusBadge = (status: string) => {
    if (status === 'running') {
      return (
        <Badge variant="default" className="bg-green-500">
          <div className="w-2 h-2 bg-white rounded-full mr-2"></div>
          運行中
        </Badge>
      );
    } else if (status === 'checking') {
      return (
        <Badge variant="default" className="bg-yellow-500">
          <div className="w-2 h-2 bg-white rounded-full mr-2 animate-pulse"></div>
          檢查中
        </Badge>
      );
    } else {
      return (
        <Badge variant="destructive">
          <div className="w-2 h-2 bg-white rounded-full mr-2"></div>
          離線
        </Badge>
      );
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      {/* Hero Section */}
      <div className="text-center mb-16">
        <Badge variant="secondary" className="mb-4">
          v1.0.0
        </Badge>
        <h1 className="text-5xl font-bold text-gray-900 mb-6 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
          股票分析平台
        </h1>
        <p className="text-xl text-gray-600 max-w-3xl mx-auto">
          自動化股票數據收集與技術分析平台，支援台股和美股市場的即時監控與分析
        </p>
      </div>

      {/* Feature Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
        <Card className="hover:shadow-lg transition-shadow">
          <CardHeader>
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
              <Database className="w-6 h-6 text-blue-600" />
            </div>
            <CardTitle>自動數據收集</CardTitle>
            <CardDescription>
              每日自動從 Yahoo Finance 收集台股和美股數據
            </CardDescription>
          </CardHeader>
        </Card>

        <Card className="hover:shadow-lg transition-shadow">
          <CardHeader>
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4">
              <BarChart3 className="w-6 h-6 text-green-600" />
            </div>
            <CardTitle>技術指標分析</CardTitle>
            <CardDescription>
              RSI、MACD、布林通道等多種技術指標計算
            </CardDescription>
          </CardHeader>
        </Card>

        <Card className="hover:shadow-lg transition-shadow">
          <CardHeader>
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
              <Bell className="w-6 h-6 text-purple-600" />
            </div>
            <CardTitle>交易信號偵測</CardTitle>
            <CardDescription>
              自動偵測黃金交叉、死亡交叉等交易信號
            </CardDescription>
          </CardHeader>
        </Card>
      </div>

      {/* System Status */}
      <Card className="mb-12">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="w-5 h-5" />
            系統狀態
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
              <span className="text-gray-600">後端 API</span>
              {getStatusBadge(systemStatus.backend)}
            </div>
            <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
              <span className="text-gray-600">資料庫</span>
              {getStatusBadge(systemStatus.database)}
            </div>
            <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
              <span className="text-gray-600">WebSocket</span>
              {getStatusBadge(systemStatus.websocket)}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-16">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">追蹤股票</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">
                  {!isMounted || !isAuthenticated ? '—' : trackedStocksCount}
                </p>
              </div>
              <TrendingUp className="h-8 w-8 text-blue-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">系統股票</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">{totalStocks}</p>
              </div>
              <Database className="h-8 w-8 text-green-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">技術指標</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">6</p>
              </div>
              <BarChart3 className="h-8 w-8 text-purple-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">數據更新</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">即時</p>
              </div>
              <Zap className="h-8 w-8 text-orange-600" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Links */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Link href="/stocks">
          <Card className="hover:shadow-lg transition-all hover:scale-105 cursor-pointer">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                股票管理
                <ArrowRight className="w-5 h-5" />
              </CardTitle>
              <CardDescription>
                管理和監控股票列表
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>

        <Link href="/dashboard">
          <Card className="hover:shadow-lg transition-all hover:scale-105 cursor-pointer">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                圖表分析
                <ArrowRight className="w-5 h-5" />
              </CardTitle>
              <CardDescription>
                查看 K 線圖表和技術指標
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>

        <Link href="/portfolio">
          <Card className="hover:shadow-lg transition-all hover:scale-105 cursor-pointer">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                投資組合
                <ArrowRight className="w-5 h-5" />
              </CardTitle>
              <CardDescription>
                監控交易信號和買賣點
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>
      </div>
    </div>
  );
}
