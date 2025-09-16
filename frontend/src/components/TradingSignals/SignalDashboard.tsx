'use client';

import React, { useState, useEffect } from 'react';
import Card, { CardHeader, CardTitle, CardContent } from '../ui/Card';
import Button from '../ui/Button';
import { 
  Bell,
  TrendingUp,
  TrendingDown,
  Activity,
  BarChart3,
  Calendar,
  Target,
  AlertCircle,
  RefreshCw
} from 'lucide-react';
import type { TradingSignal } from '../../types';

export interface SignalStats {
  total: number;
  today: number;
  thisWeek: number;
  byType: {
    BUY: number;
    SELL: number;
    GOLDEN_CROSS: number;
    DEATH_CROSS: number;
    HOLD: number;
  };
  byMarket: {
    TW: number;
    US: number;
  };
  averageConfidence: number;
  accuracy?: number;
}

export interface SignalDashboardProps {
  signals: TradingSignal[];
  stats: SignalStats;
  loading?: boolean;
  onRefresh?: () => void;
  onViewAll?: () => void;
}

const SignalDashboard: React.FC<SignalDashboardProps> = ({
  signals,
  stats,
  loading = false,
  onRefresh,
  onViewAll
}) => {
  const [timeRange, setTimeRange] = useState<'today' | 'week' | 'month'>('today');

  // 信號類型配置
  const signalTypeConfig = {
    BUY: { color: 'text-green-600 bg-green-100', icon: TrendingUp, label: '買入' },
    SELL: { color: 'text-red-600 bg-red-100', icon: TrendingDown, label: '賣出' },
    GOLDEN_CROSS: { color: 'text-yellow-600 bg-yellow-100', icon: TrendingUp, label: '黃金交叉' },
    DEATH_CROSS: { color: 'text-purple-600 bg-purple-100', icon: TrendingDown, label: '死亡交叉' },
    HOLD: { color: 'text-gray-600 bg-gray-100', icon: Activity, label: '觀望' }
  };

  // 獲取最近的信號
  const recentSignals = React.useMemo(() => {
    return signals
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .slice(0, 5);
  }, [signals]);

  // 計算時間範圍內的信號數量
  const getSignalCountByTimeRange = () => {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const weekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
    const monthAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);

    const filterDate = timeRange === 'today' ? today : 
                      timeRange === 'week' ? weekAgo : monthAgo;

    return signals.filter(signal => 
      new Date(signal.created_at) >= filterDate
    ).length;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('zh-TW', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getSignalConfig = (signalType: string) => {
    return signalTypeConfig[signalType as keyof typeof signalTypeConfig] || signalTypeConfig.HOLD;
  };

  const timeRangeCount = getSignalCountByTimeRange();

  return (
    <div className="space-y-6">
      {/* 統計卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* 總信號數 */}
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">總信號數</p>
                <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
                <p className="text-xs text-gray-500 mt-1">
                  今日 +{stats.today}
                </p>
              </div>
              <Bell className="w-8 h-8 text-blue-600" />
            </div>
          </CardContent>
        </Card>

        {/* 本週信號 */}
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">本週信號</p>
                <p className="text-2xl font-bold text-gray-900">{stats.thisWeek}</p>
                <p className="text-xs text-gray-500 mt-1">
                  每日平均 {(stats.thisWeek / 7).toFixed(1)}
                </p>
              </div>
              <Calendar className="w-8 h-8 text-green-600" />
            </div>
          </CardContent>
        </Card>

        {/* 平均信心度 */}
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">平均信心度</p>
                <p className="text-2xl font-bold text-gray-900">
                  {(stats.averageConfidence * 100).toFixed(1)}%
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  基於所有信號
                </p>
              </div>
              <Target className="w-8 h-8 text-purple-600" />
            </div>
          </CardContent>
        </Card>

        {/* 準確率 */}
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">準確率</p>
                <p className="text-2xl font-bold text-gray-900">
                  {stats.accuracy ? `${(stats.accuracy * 100).toFixed(1)}%` : '-'}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {stats.accuracy ? '歷史表現' : '暫無數據'}
                </p>
              </div>
              <BarChart3 className="w-8 h-8 text-orange-600" />
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 信號類型分佈 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5" />
              信號類型分佈
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {Object.entries(stats.byType).map(([type, count]) => {
              if (count === 0) return null;
              const config = getSignalConfig(type);
              const Icon = config.icon;
              const percentage = stats.total > 0 ? (count / stats.total * 100).toFixed(1) : '0';
              
              return (
                <div key={type} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`flex items-center justify-center w-8 h-8 rounded-full ${config.color}`}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <span className="font-medium">{config.label}</span>
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-gray-900">{count}</div>
                    <div className="text-sm text-gray-500">{percentage}%</div>
                  </div>
                </div>
              );
            })}
            
            {stats.total === 0 && (
              <div className="text-center text-gray-500 py-4">
                <AlertCircle className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                <p>暫無信號數據</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* 市場分佈 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="w-5 h-5" />
              市場分佈
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-4 h-4 bg-blue-500 rounded"></div>
                <span className="font-medium">台股 (TW)</span>
              </div>
              <div className="text-right">
                <div className="font-bold text-gray-900">{stats.byMarket.TW}</div>
                <div className="text-sm text-gray-500">
                  {stats.total > 0 ? ((stats.byMarket.TW / stats.total) * 100).toFixed(1) : '0'}%
                </div>
              </div>
            </div>
            
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-4 h-4 bg-green-500 rounded"></div>
                <span className="font-medium">美股 (US)</span>
              </div>
              <div className="text-right">
                <div className="font-bold text-gray-900">{stats.byMarket.US}</div>
                <div className="text-sm text-gray-500">
                  {stats.total > 0 ? ((stats.byMarket.US / stats.total) * 100).toFixed(1) : '0'}%
                </div>
              </div>
            </div>

            {/* 時間範圍選擇器 */}
            <div className="pt-4 border-t">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm text-gray-600">時間範圍統計:</span>
                <div className="flex gap-1">
                  {(['today', 'week', 'month'] as const).map((range) => (
                    <Button
                      key={range}
                      variant={timeRange === range ? 'primary' : 'outline'}
                      size="sm"
                      onClick={() => setTimeRange(range)}
                    >
                      {range === 'today' ? '今日' : range === 'week' ? '本週' : '本月'}
                    </Button>
                  ))}
                </div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{timeRangeCount}</div>
                <div className="text-sm text-gray-500">
                  {timeRange === 'today' ? '今日信號' : 
                   timeRange === 'week' ? '本週信號' : '本月信號'}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 最新信號 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Bell className="w-5 h-5" />
              最新信號
            </CardTitle>
            
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={onRefresh}
                disabled={loading}
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                刷新
              </Button>
              
              <Button
                variant="outline"
                size="sm"
                onClick={onViewAll}
              >
                查看全部
              </Button>
            </div>
          </div>
        </CardHeader>
        
        <CardContent>
          {recentSignals.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Bell className="w-12 h-12 mx-auto mb-2 text-gray-300" />
              <p>暫無最新信號</p>
            </div>
          ) : (
            <div className="space-y-3">
              {recentSignals.map((signal) => {
                const config = getSignalConfig(signal.signal_type);
                const Icon = config.icon;
                
                return (
                  <div
                    key={signal.id}
                    className="flex items-center gap-4 p-3 border rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <div className={`flex items-center justify-center w-8 h-8 rounded-full ${config.color}`}>
                      <Icon className="w-4 h-4" />
                    </div>
                    
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{signal.symbol}</span>
                        <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                          {signal.market}
                        </span>
                        <span className={`text-xs px-2 py-1 rounded ${config.color}`}>
                          {config.label}
                        </span>
                      </div>
                      <div className="text-sm text-gray-600 mt-1">
                        {signal.description || '交易信號'}
                      </div>
                    </div>
                    
                    <div className="text-right text-sm text-gray-500">
                      <div>{formatDate(signal.created_at)}</div>
                      {signal.confidence && (
                        <div>信心度: {(signal.confidence * 100).toFixed(1)}%</div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default SignalDashboard;