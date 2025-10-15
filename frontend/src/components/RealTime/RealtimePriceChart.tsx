/**
 * 即時價格圖表組件
 */
'use client';

import React, { useEffect, useRef, useState } from 'react';
import { createChart, IChartApi, ISeriesApi, UTCTimestamp } from 'lightweight-charts';
import { usePriceUpdates, useIndicatorUpdates } from '../../hooks/useWebSocket';
import { RealtimePriceData, Stock } from '../../types';

export interface RealtimePriceChartProps {
  stock: Pick<Stock, 'id' | 'symbol'> & { name?: string };
  height?: number;
}

const RealtimePriceChart: React.FC<RealtimePriceChartProps> = ({
  stock,
  height = 400
}) => {
  const { id: stockId, symbol, name: stockName } = stock;
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const smaSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const [historicalData, setHistoricalData] = useState<any[]>([]);

  // 使用 WebSocket hooks
  const { priceData, lastUpdate, isSubscribed } = usePriceUpdates(stockId);
  const { indicators } = useIndicatorUpdates(stockId);

  // 載入歷史價格數據
  useEffect(() => {
    const loadHistoricalData = async () => {
      try {
        const response = await fetch(`http://localhost:8000/api/v1/stocks/${stockId}/prices?limit=100`);

        if (!response.ok) {
          console.error(`Failed to load historical data: ${response.status} ${response.statusText}`);
          setHistoricalData([]);
          return;
        }

        const data = await response.json();

        // 驗證返回的數據是陣列
        if (Array.isArray(data)) {
          setHistoricalData(data);
        } else {
          console.error('Historical data is not an array:', data);
          setHistoricalData([]);
        }
      } catch (error) {
        console.error('Failed to load historical data:', error);
        setHistoricalData([]);
      }
    };

    loadHistoricalData();
  }, [stockId]);

  // 初始化圖表
  useEffect(() => {
    if (!chartContainerRef.current || isInitialized) return;

    // 創建圖表
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height,
      layout: {
        background: { color: '#ffffff' },
        textColor: '#333',
      },
      grid: {
        vertLines: { color: '#f0f0f0' },
        horzLines: { color: '#f0f0f0' },
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: true,
        borderColor: '#ddd',
      },
      rightPriceScale: {
        borderColor: '#ddd',
      },
      crosshair: {
        mode: 0,
      },
    });

    // 創建 K 線系列
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderDownColor: '#ef5350',
      borderUpColor: '#26a69a',
      wickDownColor: '#ef5350',
      wickUpColor: '#26a69a',
    });

    // 創建 SMA 系列
    const smaSeries = chart.addLineSeries({
      color: '#2196F3',
      lineWidth: 2,
      title: 'SMA(20)',
    });

    chartRef.current = chart;
    seriesRef.current = candlestickSeries;
    smaSeriesRef.current = smaSeries;

    setIsInitialized(true);

    // 處理視窗大小變化
    const handleResize = () => {
      if (chartContainerRef.current && chart) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    // 清理函數
    return () => {
      window.removeEventListener('resize', handleResize);
      if (chart) {
        chart.remove();
      }
    };
  }, [height, isInitialized]);

  // 載入歷史數據到圖表
  useEffect(() => {
    if (!isInitialized || !seriesRef.current || !smaSeriesRef.current) return;

    // 嚴格檢查 historicalData 是否為有效陣列
    if (!Array.isArray(historicalData) || historicalData.length === 0) return;

    try {
      // 轉換歷史數據為圖表格式
      const chartData = historicalData
        .map(item => {
          const date = new Date(item.date);
          return {
            time: Math.floor(date.getTime() / 1000) as UTCTimestamp,
            open: item.open,
            high: item.high,
            low: item.low,
            close: item.close,
          };
        })
        .sort((a, b) => a.time - b.time);

      // 計算 SMA
      const smaData = chartData.map((item, index) => {
        if (index < 19) return null;
        const sum = chartData
          .slice(index - 19, index + 1)
          .reduce((acc, curr) => acc + curr.close, 0);
        return {
          time: item.time,
          value: sum / 20,
        };
      }).filter(Boolean) as { time: UTCTimestamp; value: number }[];

      seriesRef.current.setData(chartData);
      smaSeriesRef.current.setData(smaData);
    } catch (error) {
      console.error('Failed to set chart data:', error);
    }
  }, [isInitialized, historicalData]);

  // 處理即時價格更新
  useEffect(() => {
    if (!priceData || !seriesRef.current) return;

    try {
      const time = Math.floor(new Date(priceData.timestamp).getTime() / 1000) as UTCTimestamp;

      // 處理真實的 OHLC 數據
      let candlestickData;

      if (priceData.ohlc) {
        // 如果 WebSocket 提供完整的 OHLC 數據
        candlestickData = {
          time,
          open: priceData.ohlc.open,
          high: priceData.ohlc.high,
          low: priceData.ohlc.low,
          close: priceData.ohlc.close,
        };
      } else {
        // 如果只有當前價格，則構建簡化的蠟燭圖數據
        // 在實際應用中，建議後端提供完整的 OHLC 數據
        const currentPrice = priceData.price;

        // 獲取前一個數據點作為參考
        const chartData = seriesRef.current.data();
        const lastCandle = chartData.length > 0 ? chartData[chartData.length - 1] : null;

        // 檢查 lastCandle 是否為有效的 CandlestickData 並包含必要屬性
        const isValidCandle = lastCandle &&
          typeof lastCandle === 'object' &&
          'close' in lastCandle &&
          'high' in lastCandle &&
          'low' in lastCandle &&
          'open' in lastCandle &&
          typeof (lastCandle as any).close === 'number' &&
          typeof (lastCandle as any).high === 'number' &&
          typeof (lastCandle as any).low === 'number' &&
          typeof (lastCandle as any).open === 'number';

        const previousClose = isValidCandle ? (lastCandle as any).close : currentPrice;
        const previousHigh = isValidCandle ? (lastCandle as any).high : currentPrice;
        const previousLow = isValidCandle ? (lastCandle as any).low : currentPrice;

        candlestickData = {
          time,
          open: previousClose,
          high: Math.max(previousHigh, currentPrice),
          low: Math.min(previousLow, currentPrice),
          close: currentPrice,
        };
      }

      // 更新 K 線數據
      seriesRef.current.update(candlestickData);

      if (process.env.NODE_ENV === 'development') {
        console.log('更新即時價格數據:', {
          symbol: symbol,
          time: new Date(time * 1000).toISOString(),
          data: candlestickData,
          volume: priceData.volume,
        });
      }
    } catch (error) {
      console.error('更新圖表數據時發生錯誤:', error);

      // 報告錯誤到錯誤追蹤系統
      if (typeof window !== 'undefined') {
        import('../../lib/errorReporting').then(({ reportError }) => {
          reportError('Chart update error', {
            component: 'RealtimePriceChart',
            symbol,
            stockId,
            error: error instanceof Error ? error.message : String(error),
            priceData,
          });
        });
      }
    }
  }, [priceData, symbol, stockId]);

  // 處理技術指標更新
  useEffect(() => {
    if (!indicators.SMA || !smaSeriesRef.current) return;

    try {
      const smaData = indicators.SMA;
      if (smaData.data && smaData.data.length > 0) {
        const latestSMA = smaData.data[smaData.data.length - 1];
        const time = Math.floor(new Date(latestSMA.date).getTime() / 1000) as UTCTimestamp;

        smaSeriesRef.current.update({
          time,
          value: latestSMA.value,
        });

        console.log('更新 SMA 指標:', { time, value: latestSMA.value });
      }
    } catch (error) {
      console.error('更新指標數據時發生錯誤:', error);
    }
  }, [indicators]);

  return (
    <div className="bg-white shadow rounded-lg">
      <div className="px-4 py-3 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-medium text-gray-900">
              {symbol} {stockName && `(${stockName})`} 即時價格圖表
            </h3>
            {lastUpdate && (
              <p className="text-sm text-gray-500">
                最後更新: {lastUpdate.toLocaleTimeString('zh-TW')}
              </p>
            )}
          </div>
          <div className="flex items-center space-x-4">
            {/* 訂閱狀態 */}
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${
                isSubscribed ? 'bg-green-500 animate-pulse' : 'bg-gray-400'
              }`}></div>
              <span className={`text-sm ${
                isSubscribed ? 'text-green-600' : 'text-gray-500'
              }`}>
                {isSubscribed ? '已訂閱' : '未訂閱'}
              </span>
            </div>

            {/* 股票ID */}
            <span className="text-sm text-gray-500">
              ID: {stockId}
            </span>
          </div>
        </div>
      </div>

      <div className="p-4">
        {/* 當前價格信息 */}
        {priceData && (
          <div className="mb-4 p-3 bg-gray-50 rounded-lg">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <div className="text-sm text-gray-600">當前價格</div>
                <div className="text-lg font-bold text-gray-900">
                  ${priceData.price?.toFixed(2) || 'N/A'}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600">漲跌</div>
                <div className={`text-lg font-bold ${
                  (priceData.change || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {priceData.change >= 0 ? '+' : ''}{priceData.change?.toFixed(2) || 'N/A'}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600">漲跌幅</div>
                <div className={`text-lg font-bold ${
                  (priceData.change_percent || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {priceData.change_percent >= 0 ? '+' : ''}{priceData.change_percent?.toFixed(2) || 'N/A'}%
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600">成交量</div>
                <div className="text-lg font-bold text-gray-900">
                  {priceData.volume?.toLocaleString() || 'N/A'}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 圖表容器 */}
        <div
          ref={chartContainerRef}
          style={{ height: `${height}px` }}
          className="w-full border border-gray-200 rounded"
        />

        {/* 圖例 */}
        <div className="mt-3 flex items-center justify-center space-x-6">
          <div className="flex items-center space-x-2">
            <div className="w-4 h-2 bg-green-500"></div>
            <span className="text-sm text-gray-600">上漲</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-2 bg-red-500"></div>
            <span className="text-sm text-gray-600">下跌</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-0.5 bg-blue-500"></div>
            <span className="text-sm text-gray-600">SMA(20)</span>
          </div>
        </div>

        {/* 技術指標信息 */}
        {indicators && Object.keys(indicators).length > 0 && (
          <div className="mt-4 p-3 bg-gray-50 rounded-lg">
            <div className="text-sm font-medium text-gray-700 mb-2">技術指標</div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {Object.entries(indicators).map(([key, data]) => (
                <div key={key} className="text-center">
                  <div className="text-xs text-gray-600">{key}</div>
                  <div className="text-sm font-medium text-gray-900">
                    {data.data && data.data.length > 0
                      ? data.data[data.data.length - 1].value.toFixed(2)
                      : 'N/A'
                    }
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default RealtimePriceChart;