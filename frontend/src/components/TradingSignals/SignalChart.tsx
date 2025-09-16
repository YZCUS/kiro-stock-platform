'use client';

import React, { useEffect, useRef } from 'react';
import {
  createChart,
  IChartApi,
  ISeriesApi,
  CandlestickData,
  Time,
  ColorType,
  CrosshairMode,
  LineStyle
} from 'lightweight-charts';
import Card, { CardHeader, CardTitle, CardContent } from '../ui/Card';
import Button from '../ui/Button';
import { 
  Bell,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  Eye,
  EyeOff
} from 'lucide-react';
import type { TradingSignal } from '../../types';

export interface SignalPoint {
  time: string;
  price: number;
  type: 'BUY' | 'SELL' | 'GOLDEN_CROSS' | 'DEATH_CROSS';
  signal: TradingSignal;
}

export interface SignalChartProps {
  candleData: Array<{
    time: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume?: number;
  }>;
  signals: SignalPoint[];
  symbol: string;
  loading?: boolean;
  onRefresh?: () => void;
  height?: number;
  showSignalLabels?: boolean;
  theme?: 'light' | 'dark';
}

const SignalChart: React.FC<SignalChartProps> = ({
  candleData,
  signals,
  symbol,
  loading = false,
  onRefresh,
  height = 400,
  showSignalLabels = true,
  theme = 'light'
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const buySeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const sellSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);

  // 圖表配置
  const chartOptions = {
    layout: {
      background: { 
        type: ColorType.Solid, 
        color: theme === 'dark' ? '#1a1a1a' : '#ffffff' 
      },
      textColor: theme === 'dark' ? '#d1d4dc' : '#191919',
    },
    grid: {
      vertLines: {
        color: theme === 'dark' ? '#2a2a2a' : '#f0f0f0',
        style: LineStyle.Dotted,
        visible: true,
      },
      horzLines: {
        color: theme === 'dark' ? '#2a2a2a' : '#f0f0f0',
        style: LineStyle.Dotted,
        visible: true,
      },
    },
    crosshair: {
      mode: CrosshairMode.Normal,
    },
    rightPriceScale: {
      borderColor: theme === 'dark' ? '#485158' : '#cccccc',
    },
    timeScale: {
      borderColor: theme === 'dark' ? '#485158' : '#cccccc',
      timeVisible: true,
      secondsVisible: false,
    },
    watermark: {
      visible: true,
      fontSize: 24,
      horzAlign: 'left' as const,
      vertAlign: 'top' as const,
      color: theme === 'dark' ? '#2a2a2a' : '#f0f0f0',
      text: `${symbol} 交易信號`,
    },
  };

  // 信號類型配置
  const signalConfig = {
    BUY: {
      color: '#26a69a',
      shape: 'arrowUp' as const,
      icon: TrendingUp,
      label: '買入'
    },
    SELL: {
      color: '#ef5350',
      shape: 'arrowDown' as const,
      icon: TrendingDown,
      label: '賣出'
    },
    GOLDEN_CROSS: {
      color: '#ffc107',
      shape: 'arrowUp' as const,
      icon: TrendingUp,
      label: '黃金交叉'
    },
    DEATH_CROSS: {
      color: '#9c27b0',
      shape: 'arrowDown' as const,
      icon: TrendingDown,
      label: '死亡交叉'
    }
  };

  // 初始化圖表
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      ...chartOptions,
      width: chartContainerRef.current.clientWidth,
      height: height,
    });

    chartRef.current = chart;

    // 創建 K 線系列
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
      priceFormat: {
        type: 'price',
        precision: 2,
        minMove: 0.01,
      },
    });

    candlestickSeriesRef.current = candlestickSeries;

    return () => {
      chart.remove();
    };
  }, [height, theme, symbol]);

  // 更新 K 線數據
  useEffect(() => {
    if (!candlestickSeriesRef.current || !candleData.length) return;

    const formattedData: CandlestickData[] = candleData.map(item => ({
      time: item.time as Time,
      open: item.open,
      high: item.high,
      low: item.low,
      close: item.close,
    }));

    candlestickSeriesRef.current.setData(formattedData);
    chartRef.current?.timeScale().fitContent();
  }, [candleData]);

  // 更新交易信號
  useEffect(() => {
    if (!chartRef.current || !candlestickSeriesRef.current) return;

    // 清除現有的信號標記
    if (buySeriesRef.current) {
      chartRef.current.removeSeries(buySeriesRef.current);
      buySeriesRef.current = null;
    }
    if (sellSeriesRef.current) {
      chartRef.current.removeSeries(sellSeriesRef.current);
      sellSeriesRef.current = null;
    }

    if (signals.length === 0) return;

    // 分離買入和賣出信號
    const buySignals = signals.filter(s => s.type === 'BUY' || s.type === 'GOLDEN_CROSS');
    const sellSignals = signals.filter(s => s.type === 'SELL' || s.type === 'DEATH_CROSS');

    // 添加買入信號標記
    if (buySignals.length > 0) {
      const buyMarkers = buySignals.map(signal => ({
        time: signal.time as Time,
        position: 'belowBar' as const,
        color: signalConfig[signal.type].color,
        shape: 'arrowUp' as const,
        text: showSignalLabels ? signalConfig[signal.type].label : '',
        size: 1,
      }));

      candlestickSeriesRef.current.setMarkers(buyMarkers);
    }

    // 添加賣出信號標記
    if (sellSignals.length > 0) {
      const sellMarkers = sellSignals.map(signal => ({
        time: signal.time as Time,
        position: 'aboveBar' as const,
        color: signalConfig[signal.type].color,
        shape: 'arrowDown' as const,
        text: showSignalLabels ? signalConfig[signal.type].label : '',
        size: 1,
      }));

      // 合併買入和賣出標記
      const allMarkers = [
        ...buySignals.map(signal => ({
          time: signal.time as Time,
          position: 'belowBar' as const,
          color: signalConfig[signal.type].color,
          shape: 'arrowUp' as const,
          text: showSignalLabels ? signalConfig[signal.type].label : '',
          size: 1,
        })),
        ...sellMarkers
      ];

      candlestickSeriesRef.current.setMarkers(allMarkers);
    }
  }, [signals, showSignalLabels]);

  // 響應式調整
  useEffect(() => {
    const handleResize = () => {
      if (chartRef.current && chartContainerRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleFitContent = () => {
    chartRef.current?.timeScale().fitContent();
  };

  // 統計信號數量
  const signalStats = React.useMemo(() => {
    const stats = {
      BUY: 0,
      SELL: 0,
      GOLDEN_CROSS: 0,
      DEATH_CROSS: 0,
    };

    signals.forEach(signal => {
      stats[signal.type]++;
    });

    return stats;
  }, [signals]);

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Bell className="w-5 h-5" />
            {symbol} 交易信號分析
          </CardTitle>
          
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleFitContent}
              title="適應內容"
            >
              <Eye className="w-4 h-4" />
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              onClick={onRefresh}
              disabled={loading}
              title="刷新數據"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>

        {/* 信號統計 */}
        {signals.length > 0 && (
          <div className="flex flex-wrap gap-3 mt-3">
            {Object.entries(signalStats).map(([type, count]) => {
              if (count === 0) return null;
              const config = signalConfig[type as keyof typeof signalConfig];
              const Icon = config.icon;
              
              return (
                <div
                  key={type}
                  className="flex items-center gap-2 px-3 py-1 rounded-full text-sm border"
                  style={{ 
                    backgroundColor: config.color + '20',
                    borderColor: config.color + '40',
                    color: config.color 
                  }}
                >
                  <Icon className="w-3 h-3" />
                  <span>{config.label}: {count}</span>
                </div>
              );
            })}
          </div>
        )}
      </CardHeader>
      
      <CardContent className="p-0">
        {loading && candleData.length === 0 ? (
          <div className="flex items-center justify-center" style={{ height }}>
            <RefreshCw className="w-6 h-6 animate-spin mr-2" />
            載入交易信號數據中...
          </div>
        ) : candleData.length === 0 ? (
          <div className="flex items-center justify-center" style={{ height }}>
            <div className="text-center text-gray-500">
              <Bell className="w-12 h-12 mx-auto mb-2 text-gray-300" />
              <p>暫無交易信號數據</p>
            </div>
          </div>
        ) : (
          <div 
            ref={chartContainerRef} 
            style={{ height, width: '100%' }}
          />
        )}
      </CardContent>
    </Card>
  );
};

export default SignalChart;