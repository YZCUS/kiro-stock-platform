'use client';

import React, { useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Layout } from '../Layout';
import { Button } from '../ui/Button';
import { 
  Bell,
  BarChart3,
  List,
  Grid3X3,
  Download,
  Settings,
  Plus,
  RefreshCw
} from 'lucide-react';
import { AppDispatch, RootState } from '../../store';
import { fetchAllSignals } from '../../store/slices/signalsSlice';
import SignalDashboard from './SignalDashboard';
import SignalList from './SignalList';
import SignalChart from './SignalChart';
import type { TradingSignal } from '../../types';
import type { SignalStats } from './SignalDashboard';

const SignalPage: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { signals, loading, error } = useSelector((state: RootState) => state.signals);
  
  const [viewMode, setViewMode] = useState<'dashboard' | 'list' | 'chart'>('dashboard');
  const [selectedStock, setSelectedStock] = useState<string | null>(null);

  useEffect(() => {
    dispatch(fetchAllSignals({
      page: 1,
      page_size: 100,
      // 可以添加更多篩選條件
    }));
  }, [dispatch]);

  // 計算統計資料
  const stats: SignalStats = React.useMemo(() => {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const weekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);

    const todaySignals = signals.filter(signal => 
      new Date(signal.created_at) >= today
    );

    const thisWeekSignals = signals.filter(signal => 
      new Date(signal.created_at) >= weekAgo
    );

    const byType = {
      BUY: signals.filter(s => s.signal_type === 'BUY').length,
      SELL: signals.filter(s => s.signal_type === 'SELL').length,
      GOLDEN_CROSS: signals.filter(s => s.signal_type === 'GOLDEN_CROSS').length,
      DEATH_CROSS: signals.filter(s => s.signal_type === 'DEATH_CROSS').length,
      HOLD: signals.filter(s => s.signal_type === 'HOLD').length,
    };

    const byMarket = {
      TW: signals.filter(s => s.market === 'TW').length,
      US: signals.filter(s => s.market === 'US').length,
    };

    const averageConfidence = signals.length > 0 
      ? signals.reduce((sum, signal) => sum + (signal.confidence || 0), 0) / signals.length
      : 0;

    return {
      total: signals.length,
      today: todaySignals.length,
      thisWeek: thisWeekSignals.length,
      byType,
      byMarket,
      averageConfidence,
      accuracy: 0.75 // 模擬數據，實際應該從 API 獲取
    };
  }, [signals]);

  // 模擬圖表數據
  const chartData = React.useMemo(() => {
    // 這裡應該從 API 獲取特定股票的 K 線數據
    const mockCandleData = Array.from({ length: 30 }, (_, i) => {
      const date = new Date();
      date.setDate(date.getDate() - (29 - i));
      const basePrice = 100 + Math.random() * 20;
      const open = basePrice + (Math.random() - 0.5) * 2;
      const close = open + (Math.random() - 0.5) * 4;
      const high = Math.max(open, close) + Math.random() * 2;
      const low = Math.min(open, close) - Math.random() * 2;
      
      return {
        time: date.toISOString().split('T')[0],
        open,
        high,
        low,
        close,
        volume: Math.floor(Math.random() * 1000000) + 100000
      };
    });

    // 將信號轉換為圖表信號點
    const signalPoints = selectedStock 
      ? signals
          .filter(signal => signal.symbol === selectedStock)
          .map(signal => ({
            time: signal.created_at.split('T')[0],
            price: signal.price || 100,
            type: signal.signal_type as any,
            signal
          }))
      : [];

    return { candleData: mockCandleData, signalPoints };
  }, [signals, selectedStock]);

  const handleRefresh = () => {
    dispatch(fetchAllSignals({
      page: 1,
      page_size: 100,
    }));
  };

  const handleSignalView = (signal: TradingSignal) => {
    setSelectedStock(signal.symbol);
    setViewMode('chart');
  };

  const handleSignalDelete = (signal: TradingSignal) => {
    if (confirm(`確定要刪除 ${signal.symbol} 的 ${signal.signal_type} 信號嗎？`)) {
      // TODO: 實作刪除信號功能
      console.log('刪除信號:', signal);
    }
  };

  const handleExport = () => {
    // TODO: 實作匯出功能
    console.log('匯出信號數據');
  };

  const handleDetectSignals = () => {
    // TODO: 實作手動偵測信號功能
    console.log('手動偵測信號');
  };

  return (
    <Layout>
      <div className="space-y-6">
        {/* 標題列 */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">交易信號</h1>
            <p className="text-gray-600 mt-1">監控和分析股票交易信號</p>
          </div>
          
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              onClick={handleExport}
            >
              <Download className="w-4 h-4 mr-2" />
              匯出數據
            </Button>

            <Button
              variant="outline"
              onClick={handleDetectSignals}
            >
              <Plus className="w-4 h-4 mr-2" />
              手動偵測
            </Button>
            
            <Button
              onClick={handleRefresh}
              disabled={loading}
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              刷新數據
            </Button>
          </div>
        </div>

        {/* 檢視模式切換 */}
        <div className="flex items-center justify-between">
          <div className="flex gap-1 border rounded-lg p-1">
            <Button
              variant={viewMode === 'dashboard' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setViewMode('dashboard')}
            >
              <BarChart3 className="w-4 h-4 mr-2" />
              儀表板
            </Button>
            <Button
              variant={viewMode === 'list' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setViewMode('list')}
            >
              <List className="w-4 h-4 mr-2" />
              信號清單
            </Button>
            <Button
              variant={viewMode === 'chart' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setViewMode('chart')}
            >
              <Grid3X3 className="w-4 h-4 mr-2" />
              圖表分析
            </Button>
          </div>

          {viewMode === 'chart' && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">分析股票:</span>
              <select
                value={selectedStock || ''}
                onChange={(e) => setSelectedStock(e.target.value || null)}
                className="px-3 py-1 border border-gray-300 rounded text-sm"
              >
                <option value="">請選擇股票</option>
                {Array.from(new Set(signals.map(s => s.symbol))).map(symbol => (
                  <option key={symbol} value={symbol}>{symbol}</option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* 錯誤提示 */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-center gap-2 text-red-600">
              <Bell className="w-4 h-4" />
              <span>載入交易信號失敗: {error}</span>
            </div>
          </div>
        )}

        {/* 內容區域 */}
        {viewMode === 'dashboard' && (
          <SignalDashboard
            signals={signals}
            stats={stats}
            loading={loading}
            onRefresh={handleRefresh}
            onViewAll={() => setViewMode('list')}
          />
        )}

        {viewMode === 'list' && (
          <SignalList
            signals={signals}
            loading={loading}
            onSignalView={handleSignalView}
            onSignalDelete={handleSignalDelete}
            onRefresh={handleRefresh}
          />
        )}

        {viewMode === 'chart' && (
          <div className="space-y-6">
            {selectedStock ? (
              <SignalChart
                candleData={chartData.candleData}
                signals={chartData.signalPoints}
                symbol={selectedStock}
                loading={loading}
                onRefresh={handleRefresh}
                height={500}
                showSignalLabels={true}
                theme="light"
              />
            ) : (
              <div className="text-center py-12">
                <Bell className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">請選擇股票</h3>
                <p className="text-gray-500 mb-4">選擇一支股票來查看其交易信號圖表分析</p>
                <Button
                  variant="outline"
                  onClick={() => setViewMode('list')}
                >
                  查看信號清單
                </Button>
              </div>
            )}
          </div>
        )}
      </div>
    </Layout>
  );
};

export default SignalPage;