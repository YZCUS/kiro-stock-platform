'use client';

import React, { useEffect, useRef, useState } from 'react';
import {
  createChart,
  IChartApi,
  ISeriesApi,
  CandlestickData,
  Time,
  ColorType,
  CrosshairMode,
  LineStyle,
  PriceScaleMode
} from 'lightweight-charts';
import Card, { CardHeader, CardTitle, CardContent } from '../ui/Card';
import Button from '../ui/Button';
import { 
  TrendingUp, 
  Settings, 
  Maximize2, 
  RefreshCw,
  ZoomIn,
  ZoomOut
} from 'lucide-react';

export interface CandleData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

export interface CandlestickChartProps {
  data: CandleData[];
  symbol: string;
  loading?: boolean;
  onRefresh?: () => void;
  height?: number;
  showVolume?: boolean;
  showGrid?: boolean;
  theme?: 'light' | 'dark';
}

const CandlestickChart: React.FC<CandlestickChartProps> = ({
  data,
  symbol,
  loading = false,
  onRefresh,
  height = 400,
  showVolume = true,
  showGrid = true,
  theme = 'light'
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

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
        visible: showGrid,
      },
      horzLines: {
        color: theme === 'dark' ? '#2a2a2a' : '#f0f0f0',
        style: LineStyle.Dotted,
        visible: showGrid,
      },
    },
    crosshair: {
      mode: CrosshairMode.Normal,
    },
    rightPriceScale: {
      borderColor: theme === 'dark' ? '#485158' : '#cccccc',
      mode: PriceScaleMode.Normal,
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
      text: symbol,
    },
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

    // 創建成交量系列
    if (showVolume) {
      const volumeSeries = chart.addHistogramSeries({
        color: '#26a69a',
        priceFormat: {
          type: 'volume',
        },
        priceScaleId: 'volume',
      });

      volumeSeriesRef.current = volumeSeries;

      // 設置成交量價格軸
      chart.priceScale('volume').applyOptions({
        scaleMargins: {
          top: 0.7,
          bottom: 0,
        },
      });
    }

    return () => {
      chart.remove();
    };
  }, [height, showVolume, showGrid, theme, symbol]);

  // 更新數據
  useEffect(() => {
    if (!candlestickSeriesRef.current || !data.length) return;

    // 轉換數據格式
    const candleData: CandlestickData[] = data.map(item => ({
      time: item.time as Time,
      open: item.open,
      high: item.high,
      low: item.low,
      close: item.close,
    }));

    candlestickSeriesRef.current.setData(candleData);

    // 更新成交量數據
    if (volumeSeriesRef.current && showVolume) {
      const volumeData = data
        .filter(item => item.volume !== undefined)
        .map(item => ({
          time: item.time as Time,
          value: item.volume!,
          color: item.close >= item.open ? '#26a69a' : '#ef5350',
        }));

      volumeSeriesRef.current.setData(volumeData);
    }

    // 自動縮放到數據範圍
    chartRef.current?.timeScale().fitContent();
  }, [data, showVolume]);

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

  const handleZoomIn = () => {
    if (chartRef.current) {
      const timeScale = chartRef.current.timeScale();
      const visibleRange = timeScale.getVisibleRange();
      if (visibleRange) {
        const range = Number(visibleRange.to) - Number(visibleRange.from);
        const newRange = range * 0.8; // 縮小 20%
        const center = (Number(visibleRange.from) + Number(visibleRange.to)) / 2;
        timeScale.setVisibleRange({
          from: (center - newRange / 2) as Time,
          to: (center + newRange / 2) as Time,
        });
      }
    }
  };

  const handleZoomOut = () => {
    if (chartRef.current) {
      const timeScale = chartRef.current.timeScale();
      const visibleRange = timeScale.getVisibleRange();
      if (visibleRange) {
        const range = Number(visibleRange.to) - Number(visibleRange.from);
        const newRange = range * 1.2; // 放大 20%
        const center = (Number(visibleRange.from) + Number(visibleRange.to)) / 2;
        timeScale.setVisibleRange({
          from: (center - newRange / 2) as Time,
          to: (center + newRange / 2) as Time,
        });
      }
    }
  };

  const handleFitContent = () => {
    chartRef.current?.timeScale().fitContent();
  };

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  return (
    <Card className={isFullscreen ? 'fixed inset-4 z-50' : ''}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5" />
            {symbol} K線圖
          </CardTitle>
          
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleZoomIn}
              title="放大"
            >
              <ZoomIn className="w-4 h-4" />
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              onClick={handleZoomOut}
              title="縮小"
            >
              <ZoomOut className="w-4 h-4" />
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              onClick={handleFitContent}
              title="適應內容"
            >
              <Settings className="w-4 h-4" />
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
      </CardHeader>
      
      <CardContent className="p-0">
        {loading && data.length === 0 ? (
          <div className="flex items-center justify-center" style={{ height }}>
            <RefreshCw className="w-6 h-6 animate-spin mr-2" />
            載入圖表數據中...
          </div>
        ) : data.length === 0 ? (
          <div className="flex items-center justify-center" style={{ height }}>
            <div className="text-center text-gray-500">
              <TrendingUp className="w-12 h-12 mx-auto mb-2 text-gray-300" />
              <p>暫無圖表數據</p>
            </div>
          </div>
        ) : (
          <div 
            ref={chartContainerRef} 
            style={{ 
              height: isFullscreen ? 'calc(100vh - 120px)' : height,
              width: '100%' 
            }}
          />
        )}
      </CardContent>
    </Card>
  );
};

export default CandlestickChart;