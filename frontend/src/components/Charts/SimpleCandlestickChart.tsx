'use client';

import React, { useEffect, useRef } from 'react';
import { createChart, ColorType } from 'lightweight-charts';
import Card, { CardHeader, CardTitle, CardContent } from '../ui/Card';

export interface ChartData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

export interface SimpleCandlestickChartProps {
  data: ChartData[];
  symbol: string;
  height?: number;
}

const SimpleCandlestickChart: React.FC<SimpleCandlestickChartProps> = ({
  data,
  symbol,
  height = 400,
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'white' },
        textColor: '#333',
      },
      width: chartContainerRef.current.clientWidth,
      height: height,
      grid: {
        vertLines: { color: '#f0f0f0' },
        horzLines: { color: '#f0f0f0' },
      },
      rightPriceScale: {
        borderColor: '#cccccc',
      },
      timeScale: {
        borderColor: '#cccccc',
      },
    });

    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#10b981',
      downColor: '#ef4444',
      borderUpColor: '#10b981',
      borderDownColor: '#ef4444',
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    });

    // 轉換數據格式
    const chartData = data.map(item => ({
      time: item.time,
      open: item.open,
      high: item.high,
      low: item.low,
      close: item.close,
    }));

    candlestickSeries.setData(chartData);

    chartRef.current = chart;

    // 處理視窗大小調整
    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data, height]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {symbol} 股價走勢圖
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div ref={chartContainerRef} style={{ height }} />
      </CardContent>
    </Card>
  );
};

export default SimpleCandlestickChart;