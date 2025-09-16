'use client';

import React, { useState, useEffect } from 'react';
import Card, { CardHeader, CardTitle, CardContent } from '../ui/Card';
import Button from '../ui/Button';
import { 
  BarChart3, 
  TrendingUp, 
  Activity,
  Settings,
  Maximize2,
  RefreshCw
} from 'lucide-react';
import CandlestickChart, { CandleData } from './CandlestickChart';
import TechnicalIndicatorChart, { IndicatorSeries } from './TechnicalIndicatorChart';
import LineChart, { LineDataPoint } from './LineChart';

export interface MultiChartProps {
  symbol: string;
  candleData: CandleData[];
  indicators: {
    rsi?: LineDataPoint[];
    macd?: {
      macd: LineDataPoint[];
      signal: LineDataPoint[];
      histogram: LineDataPoint[];
    };
    ma?: {
      ma5: LineDataPoint[];
      ma10: LineDataPoint[];
      ma20: LineDataPoint[];
    };
    bollinger?: {
      upper: LineDataPoint[];
      middle: LineDataPoint[];
      lower: LineDataPoint[];
    };
  };
  loading?: boolean;
  onRefresh?: () => void;
  theme?: 'light' | 'dark';
}

const MultiChart: React.FC<MultiChartProps> = ({
  symbol,
  candleData,
  indicators,
  loading = false,
  onRefresh,
  theme = 'light'
}) => {
  const [activeCharts, setActiveCharts] = useState<Set<string>>(
    new Set(['candlestick', 'volume'])
  );
  const [isFullscreen, setIsFullscreen] = useState(false);

  const chartTypes = [
    { id: 'candlestick', name: 'K線圖', icon: BarChart3 },
    { id: 'volume', name: '成交量', icon: Activity },
    { id: 'rsi', name: 'RSI', icon: TrendingUp },
    { id: 'macd', name: 'MACD', icon: TrendingUp },
    { id: 'ma', name: '移動平均', icon: TrendingUp },
    { id: 'bollinger', name: '布林通道', icon: TrendingUp },
  ];

  const toggleChart = (chartId: string) => {
    setActiveCharts(prev => {
      const newSet = new Set(prev);
      if (newSet.has(chartId)) {
        newSet.delete(chartId);
      } else {
        newSet.add(chartId);
      }
      return newSet;
    });
  };

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  // 準備 RSI 數據
  const rsiSeries: IndicatorSeries[] = indicators.rsi ? [
    {
      name: 'RSI',
      data: indicators.rsi,
      color: '#ff6b35',
    },
    // RSI 參考線
    {
      name: '超買線 (70)',
      data: indicators.rsi.map(item => ({ time: item.time, value: 70 })),
      color: '#ef5350',
    },
    {
      name: '超賣線 (30)',
      data: indicators.rsi.map(item => ({ time: item.time, value: 30 })),
      color: '#26a69a',
    },
  ] : [];

  // 準備 MACD 數據
  const macdSeries: IndicatorSeries[] = indicators.macd ? [
    {
      name: 'MACD',
      data: indicators.macd.macd,
      color: '#2196F3',
    },
    {
      name: 'Signal',
      data: indicators.macd.signal,
      color: '#ff9800',
    },
    {
      name: 'Histogram',
      data: indicators.macd.histogram,
      color: '#9c27b0',
    },
  ] : [];

  // 準備移動平均數據
  const maSeries: IndicatorSeries[] = indicators.ma ? [
    {
      name: 'MA5',
      data: indicators.ma.ma5,
      color: '#f44336',
    },
    {
      name: 'MA10',
      data: indicators.ma.ma10,
      color: '#2196F3',
    },
    {
      name: 'MA20',
      data: indicators.ma.ma20,
      color: '#4caf50',
    },
  ] : [];

  // 準備布林通道數據
  const bollingerSeries: IndicatorSeries[] = indicators.bollinger ? [
    {
      name: '上軌',
      data: indicators.bollinger.upper,
      color: '#ff5722',
    },
    {
      name: '中軌',
      data: indicators.bollinger.middle,
      color: '#607d8b',
    },
    {
      name: '下軌',
      data: indicators.bollinger.lower,
      color: '#ff5722',
    },
  ] : [];

  // 準備成交量數據
  const volumeData: LineDataPoint[] = candleData
    .filter(item => item.volume !== undefined)
    .map(item => ({
      time: item.time,
      value: item.volume!,
    }));

  return (
    <div className={isFullscreen ? 'fixed inset-4 z-50 bg-white rounded-lg shadow-2xl' : ''}>
      <Card className="h-full">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5" />
              {symbol} 綜合圖表分析
            </CardTitle>
            
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={onRefresh}
                disabled={loading}
                title="刷新數據"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              </Button>
              
              <Button
                variant="outline"
                size="sm"
                onClick={toggleFullscreen}
                title={isFullscreen ? '退出全屏' : '全屏顯示'}
              >
                <Maximize2 className="w-4 h-4" />
              </Button>
            </div>
          </div>

          {/* 圖表類型選擇 */}
          <div className="flex flex-wrap gap-2 mt-3">
            {chartTypes.map(({ id, name, icon: Icon }) => (
              <button
                key={id}
                onClick={() => toggleChart(id)}
                className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm border transition-colors ${
                  activeCharts.has(id)
                    ? 'bg-blue-50 border-blue-200 text-blue-700'
                    : 'bg-gray-50 border-gray-200 text-gray-500'
                }`}
                disabled={id === 'rsi' && !indicators.rsi}
                title={
                  id === 'rsi' && !indicators.rsi ? '暫無 RSI 數據' :
                  id === 'macd' && !indicators.macd ? '暫無 MACD 數據' :
                  id === 'ma' && !indicators.ma ? '暫無移動平均數據' :
                  id === 'bollinger' && !indicators.bollinger ? '暫無布林通道數據' :
                  undefined
                }
              >
                <Icon className="w-3 h-3" />
                {name}
              </button>
            ))}
          </div>
        </CardHeader>
        
        <CardContent className={`space-y-4 ${isFullscreen ? 'h-full overflow-y-auto' : ''}`}>
          {/* K線圖 */}
          {activeCharts.has('candlestick') && (
            <CandlestickChart
              data={candleData}
              symbol={symbol}
              loading={loading}
              onRefresh={onRefresh}
              height={isFullscreen ? 400 : 300}
              showVolume={false}
              theme={theme}
            />
          )}

          {/* 成交量圖 */}
          {activeCharts.has('volume') && volumeData.length > 0 && (
            <LineChart
              data={volumeData}
              title="成交量"
              color="#26a69a"
              loading={loading}
              onRefresh={onRefresh}
              height={isFullscreen ? 200 : 150}
              theme={theme}
              format="volume"
            />
          )}

          {/* RSI 指標 */}
          {activeCharts.has('rsi') && rsiSeries.length > 0 && (
            <TechnicalIndicatorChart
              series={rsiSeries}
              title="RSI (相對強弱指標)"
              loading={loading}
              onRefresh={onRefresh}
              height={isFullscreen ? 200 : 150}
              theme={theme}
              precision={2}
            />
          )}

          {/* MACD 指標 */}
          {activeCharts.has('macd') && macdSeries.length > 0 && (
            <TechnicalIndicatorChart
              series={macdSeries}
              title="MACD (指數平滑移動平均匯聚分離)"
              loading={loading}
              onRefresh={onRefresh}
              height={isFullscreen ? 200 : 150}
              theme={theme}
              precision={4}
            />
          )}

          {/* 移動平均 */}
          {activeCharts.has('ma') && maSeries.length > 0 && (
            <TechnicalIndicatorChart
              series={maSeries}
              title="移動平均線"
              loading={loading}
              onRefresh={onRefresh}
              height={isFullscreen ? 200 : 150}
              theme={theme}
              precision={2}
            />
          )}

          {/* 布林通道 */}
          {activeCharts.has('bollinger') && bollingerSeries.length > 0 && (
            <TechnicalIndicatorChart
              series={bollingerSeries}
              title="布林通道"
              loading={loading}
              onRefresh={onRefresh}
              height={isFullscreen ? 200 : 150}
              theme={theme}
              precision={2}
            />
          )}

          {/* 無數據提示 */}
          {Array.from(activeCharts).every(chartId => {
            if (chartId === 'candlestick') return candleData.length === 0;
            if (chartId === 'volume') return volumeData.length === 0;
            if (chartId === 'rsi') return !indicators.rsi;
            if (chartId === 'macd') return !indicators.macd;
            if (chartId === 'ma') return !indicators.ma;
            if (chartId === 'bollinger') return !indicators.bollinger;
            return true;
          }) && (
            <div className="flex items-center justify-center py-12">
              <div className="text-center text-gray-500">
                <BarChart3 className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">暫無圖表數據</h3>
                <p className="text-gray-500 mb-4">請選擇要顯示的圖表類型或刷新數據</p>
                <Button onClick={onRefresh} disabled={loading}>
                  <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                  刷新數據
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default MultiChart;