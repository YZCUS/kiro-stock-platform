'use client';

import React, { useEffect, useRef, useState } from 'react';
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
import Card, { CardHeader, CardTitle, CardContent } from '../ui/Card';
import Button from '../ui/Button';
import { 
  BarChart3, 
  Settings, 
  RefreshCw,
  Eye,
  EyeOff
} from 'lucide-react';

export interface IndicatorDataPoint {
  time: string;
  value: number;
}

export interface IndicatorSeries {
  name: string;
  data: IndicatorDataPoint[];
  color: string;
  visible?: boolean;
}

export interface TechnicalIndicatorChartProps {
  series: IndicatorSeries[];
  title: string;
  loading?: boolean;
  onRefresh?: () => void;
  height?: number;
  showGrid?: boolean;
  theme?: 'light' | 'dark';
  precision?: number;
  showLegend?: boolean;
}

const TechnicalIndicatorChart: React.FC<TechnicalIndicatorChartProps> = ({
  series,
  title,
  loading = false,
  onRefresh,
  height = 300,
  showGrid = true,
  theme = 'light',
  precision = 2,
  showLegend = true
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRefs = useRef<Map<string, ISeriesApi<'Line'>>>(new Map());
  const [visibleSeries, setVisibleSeries] = useState<Set<string>>(
    new Set(series.filter(s => s.visible !== false).map(s => s.name))
  );

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

  // 初始化圖表
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      ...chartOptions,
      width: chartContainerRef.current.clientWidth,
      height: height,
    });

    chartRef.current = chart;

    // 清空之前的系列引用
    seriesRefs.current.clear();

    // 為每個系列創建線條
    series.forEach((seriesData) => {
      const lineSeries = chart.addLineSeries({
        color: seriesData.color,
        lineWidth: 2,
        priceFormat: {
          type: 'price',
          precision,
          minMove: Math.pow(10, -precision),
        },
        visible: visibleSeries.has(seriesData.name),
      });

      seriesRefs.current.set(seriesData.name, lineSeries);
    });

    return () => {
      chart.remove();
    };
  }, [height, showGrid, theme, precision, series.length]);

  // 更新數據
  useEffect(() => {
    if (!chartRef.current || series.length === 0) return;

    series.forEach((seriesData) => {
      const lineSeries = seriesRefs.current.get(seriesData.name);
      if (!lineSeries) return;

      // 轉換數據格式
      const lineData: LineData[] = seriesData.data.map(item => ({
        time: item.time as Time,
        value: item.value,
      }));

      lineSeries.setData(lineData);
    });

    // 自動縮放到數據範圍
    chartRef.current.timeScale().fitContent();
  }, [series]);

  // 更新系列可見性
  useEffect(() => {
    seriesRefs.current.forEach((lineSeries, name) => {
      lineSeries.applyOptions({
        visible: visibleSeries.has(name),
      });
    });
  }, [visibleSeries]);

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

  const toggleSeries = (seriesName: string) => {
    setVisibleSeries(prev => {
      const newSet = new Set(prev);
      if (newSet.has(seriesName)) {
        newSet.delete(seriesName);
      } else {
        newSet.add(seriesName);
      }
      return newSet;
    });
  };

  const hasData = series.some(s => s.data.length > 0);

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5" />
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

        {/* 圖例 */}
        {showLegend && series.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-3">
            {series.map((seriesData) => (
              <button
                key={seriesData.name}
                onClick={() => toggleSeries(seriesData.name)}
                className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm border transition-colors ${
                  visibleSeries.has(seriesData.name)
                    ? 'bg-blue-50 border-blue-200 text-blue-700'
                    : 'bg-gray-50 border-gray-200 text-gray-500'
                }`}
              >
                {visibleSeries.has(seriesData.name) ? (
                  <Eye className="w-3 h-3" />
                ) : (
                  <EyeOff className="w-3 h-3" />
                )}
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: seriesData.color }}
                />
                {seriesData.name}
              </button>
            ))}
          </div>
        )}
      </CardHeader>
      
      <CardContent className="p-0">
        {loading && !hasData ? (
          <div className="flex items-center justify-center" style={{ height }}>
            <RefreshCw className="w-6 h-6 animate-spin mr-2" />
            載入技術指標數據中...
          </div>
        ) : !hasData ? (
          <div className="flex items-center justify-center" style={{ height }}>
            <div className="text-center text-gray-500">
              <BarChart3 className="w-12 h-12 mx-auto mb-2 text-gray-300" />
              <p>暫無技術指標數據</p>
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

export default TechnicalIndicatorChart;