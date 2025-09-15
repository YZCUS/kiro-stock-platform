'use client';

import React, { useEffect, useRef } from 'react';
import { 
  createChart, 
  IChartApi, 
  ISeriesApi,
  LineData,
  Time,
  ColorType,
  CrosshairMode,
  LineStyle
} from 'lightweight-charts';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import { 
  TrendingUp, 
  Settings, 
  RefreshCw
} from 'lucide-react';

export interface LineDataPoint {
  time: string;
  value: number;
}

export interface LineChartProps {
  data: LineDataPoint[];
  title: string;
  color?: string;
  loading?: boolean;
  onRefresh?: () => void;
  height?: number;
  showGrid?: boolean;
  theme?: 'light' | 'dark';
  precision?: number;
  format?: 'price' | 'percentage' | 'volume';
}

const LineChart: React.FC<LineChartProps> = ({
  data,
  title,
  color = '#2196F3',
  loading = false,
  onRefresh,
  height = 300,
  showGrid = true,
  theme = 'light',
  precision = 2,
  format = 'price'
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const lineSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);

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
    },
    timeScale: {
      borderColor: theme === 'dark' ? '#485158' : '#cccccc',
      timeVisible: true,
      secondsVisible: false,
    },
  };

  // 獲取價格格式配置
  const getPriceFormat = () => {
    switch (format) {
      case 'percentage':
        return {
          type: 'custom' as const,
          formatter: (price: number) => `${price.toFixed(precision)}%`,
        };
      case 'volume':
        return {
          type: 'volume' as const,
        };
      default:
        return {
          type: 'price' as const,
          precision,
          minMove: Math.pow(10, -precision),
        };
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

    // 創建線條系列
    const lineSeries = chart.addLineSeries({
      color: color,
      lineWidth: 2,
      priceFormat: getPriceFormat(),
    });

    lineSeriesRef.current = lineSeries;

    return () => {
      chart.remove();
    };
  }, [height, showGrid, theme, color, precision, format]);

  // 更新數據
  useEffect(() => {
    if (!lineSeriesRef.current || !data.length) return;

    // 轉換數據格式
    const lineData: LineData[] = data.map(item => ({
      time: item.time as Time,
      value: item.value,
    }));

    lineSeriesRef.current.setData(lineData);

    // 自動縮放到數據範圍
    chartRef.current?.timeScale().fitContent();
  }, [data]);

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

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5" />
            {title}
          </CardTitle>
          
          <div className="flex items-center gap-2">
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
            style={{ height, width: '100%' }}
          />
        )}
      </CardContent>
    </Card>
  );
};

export default LineChart;