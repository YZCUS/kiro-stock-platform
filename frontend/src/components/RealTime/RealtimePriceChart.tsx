/**
 * 即時價格圖表組件
 */
'use client';

import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import {
  createChart,
  IChartApi,
  ISeriesApi,
  SeriesMarker,
  UTCTimestamp,
} from 'lightweight-charts';
import { useIndicatorUpdates } from '../../hooks/useWebSocket';
import { useMarketStream } from '../../hooks/useMarketStream';
import StocksApiService from '../../services/stocksApi';
import {
  getStockValuationMetrics,
  type StockValuationMetrics,
} from '../../services/marketInfoApi';
import { PriceData, Stock } from '../../types';

type ChartTimeframe = '1d' | '5m';

export interface RealtimePriceChartProps {
  stock: Pick<Stock, 'id' | 'symbol'> & { name?: string; market?: string };
  height?: number;
  timeframe?: ChartTimeframe;
}

interface ChartCandle {
  open: number;
  high: number;
  low: number;
  close: number;
}

interface ChartCandleData extends ChartCandle {
  time: UTCTimestamp;
}

interface ChartVolumeData {
  time: UTCTimestamp;
  value: number;
  color: string;
}

type MovingAveragePeriod = 5 | 20 | 60 | 120;

interface MovingAverageSummary {
  period: MovingAveragePeriod;
  label: string;
  color: string;
  latestValue: number | null;
  deductionPrice: number | null;
  deductionTime: UTCTimestamp | null;
  barsAvailable: number;
}

const MOVING_AVERAGE_CONFIGS: Array<{
  period: MovingAveragePeriod;
  label: string;
  color: string;
}> = [
  { period: 5, label: '5K', color: '#0891b2' },
  { period: 20, label: '20K', color: '#2563eb' },
  { period: 60, label: '60K', color: '#7c3aed' },
  { period: 120, label: '120K', color: '#ea580c' },
];

const CHART_TIMEFRAME_OPTIONS: Array<{
  value: ChartTimeframe;
  label: string;
}> = [
  { value: '1d', label: '日線' },
  { value: '5m', label: '5分K' },
];

const TRADING_DAYS_PER_YEAR = 252;
const DEFAULT_HISTORICAL_K_BARS = TRADING_DAYS_PER_YEAR * 3;
const DEFAULT_INTRADAY_K_BARS = 390;
const PRICE_HISTORY_LOOKBACK_YEARS = 3;
const INTRADAY_LOOKBACK_DAYS = 7;
const VOLUME_UP_COLOR = 'rgba(38, 166, 154, 0.35)';
const VOLUME_DOWN_COLOR = 'rgba(239, 83, 80, 0.35)';

const formatDateInput = (date: Date): string => date.toISOString().slice(0, 10);

const getHistoricalPriceRange = (timeframe: ChartTimeframe) => {
  const endDate = new Date();
  const startDate = new Date(endDate);

  if (timeframe === '5m') {
    startDate.setDate(startDate.getDate() - INTRADAY_LOOKBACK_DAYS);
  } else {
    startDate.setFullYear(startDate.getFullYear() - PRICE_HISTORY_LOOKBACK_YEARS);
  }

  return {
    start_date: formatDateInput(startDate),
    end_date: formatDateInput(endDate),
  };
};

const isChartCandle = (value: unknown): value is ChartCandle => {
  if (!value || typeof value !== 'object') {
    return false;
  }

  const candle = value as Record<string, unknown>;
  return (
    typeof candle.open === 'number' &&
    typeof candle.high === 'number' &&
    typeof candle.low === 'number' &&
    typeof candle.close === 'number'
  );
};

const isChartCandleData = (value: unknown): value is ChartCandleData => {
  if (!isChartCandle(value)) {
    return false;
  }

  return typeof (value as { time?: unknown }).time === 'number';
};

const calculateMovingAverageData = (
  chartData: ChartCandleData[],
  period: MovingAveragePeriod
) => {
  return chartData
    .map((item, index) => {
      if (index < period - 1) {
        return null;
      }

      const sum = chartData
        .slice(index - period + 1, index + 1)
        .reduce((acc, curr) => acc + curr.close, 0);

      return {
        time: item.time,
        value: sum / period,
      };
    })
    .filter(
      (item): item is { time: UTCTimestamp; value: number } => item !== null
    );
};

const createChartDataFromPrices = (prices: PriceData[]): ChartCandleData[] => {
  return prices
    .map((item) => {
      const date = new Date(item.date);
      return {
        time: Math.floor(date.getTime() / 1000) as UTCTimestamp,
        open: item.open,
        high: item.high,
        low: item.low,
        close: item.close,
      };
    })
    .filter((item) => Number.isFinite(item.time))
    .sort((a, b) => a.time - b.time);
};

const createVolumeDataFromPrices = (prices: PriceData[]): ChartVolumeData[] => {
  return prices
    .map((item) => {
      const date = new Date(item.date);
      return {
        time: Math.floor(date.getTime() / 1000) as UTCTimestamp,
        value: item.volume,
        color: item.close >= item.open ? VOLUME_UP_COLOR : VOLUME_DOWN_COLOR,
      };
    })
    .filter((item) => Number.isFinite(item.time))
    .sort((a, b) => a.time - b.time);
};

const shouldBackfillHistoricalData = (
  prices: PriceData[],
  startDate: string
): boolean => {
  if (prices.length === 0) {
    return true;
  }

  const oldestTimestamp = Math.min(
    ...prices.map((price) => new Date(price.date).getTime())
  );
  const requestedStartTimestamp = new Date(startDate).getTime();

  if (!Number.isFinite(oldestTimestamp) || !Number.isFinite(requestedStartTimestamp)) {
    return false;
  }

  return oldestTimestamp > requestedStartTimestamp;
};

const createDeductionMarkers = (
  chartData: ChartCandleData[]
): SeriesMarker<UTCTimestamp>[] => {
  return MOVING_AVERAGE_CONFIGS.flatMap<SeriesMarker<UTCTimestamp>>((config) => {
    const deductionIndex = chartData.length - config.period;
    if (deductionIndex < 0) {
      return [];
    }

    const candle = chartData[deductionIndex];
    return [
      {
        time: candle.time,
        position: 'aboveBar',
        shape: 'circle',
        color: config.color,
        text: `${config.label}扣 ${candle.close.toFixed(2)}`,
        size: 1.2,
      },
    ];
  }).sort((a, b) => a.time - b.time);
};

const createMovingAverageSummary = (
  chartData: ChartCandleData[]
): MovingAverageSummary[] => {
  return MOVING_AVERAGE_CONFIGS.map((config) => {
    const movingAverageData = calculateMovingAverageData(
      chartData,
      config.period
    );
    const latestValue =
      movingAverageData.length > 0
        ? movingAverageData[movingAverageData.length - 1].value
        : null;
    const deductionIndex = chartData.length - config.period;
    const deductionCandle =
      deductionIndex >= 0 ? chartData[deductionIndex] : null;

    return {
      period: config.period,
      label: config.label,
      color: config.color,
      latestValue,
      deductionPrice: deductionCandle?.close ?? null,
      deductionTime: deductionCandle?.time ?? null,
      barsAvailable: chartData.length,
    };
  });
};

const formatPriceValue = (value: number | null) => {
  return value === null ? '資料不足' : value.toFixed(2);
};

const formatMetricValue = (
  value: number | null | undefined,
  suffix = '',
  digits = 2
) => {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return '--';
  }
  return `${value.toFixed(digits)}${suffix}`;
};

const formatMarketCap = (
  value: number | null | undefined,
  unit?: string | null
) => {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return '--';
  }

  const normalizedValue = unit === 'million' ? value * 1_000_000 : value;
  if (normalizedValue >= 1_000_000_000_000) {
    return `${(normalizedValue / 1_000_000_000_000).toFixed(2)}T`;
  }
  if (normalizedValue >= 1_000_000_000) {
    return `${(normalizedValue / 1_000_000_000).toFixed(2)}B`;
  }
  if (normalizedValue >= 1_000_000) {
    return `${(normalizedValue / 1_000_000).toFixed(2)}M`;
  }
  return normalizedValue.toLocaleString();
};

const formatChartDate = (time: UTCTimestamp | null) => {
  if (time === null) {
    return '';
  }

  return new Intl.DateTimeFormat('zh-TW', {
    month: '2-digit',
    day: '2-digit',
  }).format(new Date(time * 1000));
};

const RealtimePriceChart: React.FC<RealtimePriceChartProps> = ({
  stock,
  height = 400,
  timeframe = '1d',
}) => {
  const { id: stockId, symbol } = stock;
  const market =
    stock.market ?? (symbol.endsWith('.TW') || /^\d+$/.test(symbol) ? 'TW' : 'US');
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const movingAverageSeriesRefs = useRef<
    Partial<Record<MovingAveragePeriod, ISeriesApi<'Line'>>>
  >({});
  const backfillRequestedStockIdsRef = useRef<Set<number>>(new Set());
  const [historicalData, setHistoricalData] = useState<PriceData[]>([]);
  const [chartData, setChartData] = useState<ChartCandleData[]>([]);
  const [chartReadyRevision, setChartReadyRevision] = useState(0);
  const [selectedTimeframe, setSelectedTimeframe] =
    useState<ChartTimeframe>(timeframe);
  const [displayedTimeframe, setDisplayedTimeframe] =
    useState<ChartTimeframe>(timeframe);
  const [valuationMetrics, setValuationMetrics] =
    useState<StockValuationMetrics | null>(null);
  const [valuationLoading, setValuationLoading] = useState(false);

  // 驗證 stockId 有效性 - 必須是有效的數字
  const validStockId =
    stockId && typeof stockId === 'number' && stockId > 0 ? stockId : null;

  useEffect(() => {
    setSelectedTimeframe(timeframe);
    setDisplayedTimeframe(timeframe);
  }, [timeframe]);

  const { quote: streamQuote, bar: streamBar } = useMarketStream(
    market,
    symbol,
    Boolean(symbol && market)
  );
  const { indicators } = useIndicatorUpdates(validStockId);
  const movingAverageSummary = useMemo(
    () => createMovingAverageSummary(chartData),
    [chartData]
  );

  const valuationRows = useMemo(
    () => [
      {
        label: '市值',
        value: formatMarketCap(
          valuationMetrics?.market_cap,
          valuationMetrics?.market_cap_unit
        ),
      },
      { label: 'P/E', value: formatMetricValue(valuationMetrics?.pe_ttm) },
      { label: 'P/B', value: formatMetricValue(valuationMetrics?.pb) },
      { label: 'P/S', value: formatMetricValue(valuationMetrics?.ps_ttm) },
      {
        label: 'EV/EBITDA',
        value: formatMetricValue(valuationMetrics?.ev_to_ebitda),
      },
      {
        label: '殖利率',
        value: formatMetricValue(valuationMetrics?.dividend_yield, '%'),
      },
      { label: 'Beta', value: formatMetricValue(valuationMetrics?.beta) },
      { label: 'EPS TTM', value: formatMetricValue(valuationMetrics?.eps_ttm) },
    ],
    [valuationMetrics]
  );

  // 載入歷史價格數據
  useEffect(() => {
    // 只有在 stockId 有效時才載入數據
    if (!validStockId) {
      setHistoricalData([]);
      setChartData([]);
      setDisplayedTimeframe(selectedTimeframe);
      return;
    }

    let cancelled = false;
    setHistoricalData([]);
    setChartData([]);
    setDisplayedTimeframe(selectedTimeframe);

    const loadHistoricalData = async () => {
      const fetchPrices = async (requestedTimeframe: ChartTimeframe) => {
        const priceRange = getHistoricalPriceRange(requestedTimeframe);
        const limit =
          requestedTimeframe === '5m'
            ? DEFAULT_INTRADAY_K_BARS
            : DEFAULT_HISTORICAL_K_BARS;
        const data = await StocksApiService.getStockPrices(validStockId, {
          ...priceRange,
          timeframe: requestedTimeframe,
          limit,
        });

        return {
          data,
          limit,
          priceRange,
          timeframe: requestedTimeframe,
        };
      };

      try {
        let result = await fetchPrices(selectedTimeframe);

        if (
          selectedTimeframe === '5m' &&
          Array.isArray(result.data) &&
          result.data.length === 0
        ) {
          result = await fetchPrices('1d');
        }

        // 驗證返回的數據是陣列
        if (Array.isArray(result.data)) {
          if (cancelled) {
            return;
          }
          setDisplayedTimeframe(result.timeframe);
          setHistoricalData(result.data);

          if (
            result.timeframe === '1d' &&
            shouldBackfillHistoricalData(result.data, result.priceRange.start_date) &&
            !backfillRequestedStockIdsRef.current.has(validStockId)
          ) {
            backfillRequestedStockIdsRef.current.add(validStockId);

            void StocksApiService.backfillStockData(validStockId, result.priceRange)
              .then(async () => {
                const refreshedData = await StocksApiService.getStockPrices(
                  validStockId,
                  {
                    ...result.priceRange,
                    timeframe: result.timeframe,
                    limit: result.limit,
                  }
                );

                if (!cancelled && Array.isArray(refreshedData)) {
                  setHistoricalData(refreshedData);
                }
              })
              .catch((backfillError) => {
                console.warn('Failed to backfill chart history:', backfillError);
              });
          }
        } else {
          console.error('Historical data is not an array:', result.data);
          setHistoricalData([]);
        }
      } catch (error) {
        if (selectedTimeframe === '5m') {
          try {
            const fallback = await fetchPrices('1d');
            if (!cancelled && Array.isArray(fallback.data)) {
              setDisplayedTimeframe('1d');
              setHistoricalData(fallback.data);
              return;
            }
          } catch (fallbackError) {
            console.error('Failed to load daily fallback data:', fallbackError);
          }
        }
        console.error('Failed to load historical data:', error);
        setHistoricalData([]);
        setChartData([]);
      }
    };

    loadHistoricalData();

    return () => {
      cancelled = true;
    };
  }, [selectedTimeframe, validStockId]);

  useEffect(() => {
    if (!validStockId || !symbol || !market) {
      setValuationMetrics(null);
      return;
    }

    let cancelled = false;
    setValuationLoading(true);
    setValuationMetrics(null);

    getStockValuationMetrics(market, symbol)
      .then((metrics) => {
        if (!cancelled) {
          setValuationMetrics(metrics);
        }
      })
      .catch((error) => {
        console.warn('Failed to load valuation metrics:', error);
        if (!cancelled) {
          setValuationMetrics(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setValuationLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [market, symbol, validStockId]);

  // 初始化圖表
  useEffect(() => {
    if (!chartContainerRef.current) return;

    // 清理舊圖表
    if (chartRef.current) {
      try {
        chartRef.current.remove();
      } catch (e) {
        console.warn('Error removing old chart:', e);
      }
      chartRef.current = null;
      seriesRef.current = null;
      volumeSeriesRef.current = null;
      movingAverageSeriesRefs.current = {};
    }

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
        scaleMargins: {
          top: 0.06,
          bottom: 0.24,
        },
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

    const volumeSeries = chart.addHistogramSeries({
      color: VOLUME_UP_COLOR,
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: '',
    });

    chart.priceScale('').applyOptions({
      scaleMargins: {
        top: 0.78,
        bottom: 0,
      },
    });

    // 創建均線系列
    const movingAverageSeries = MOVING_AVERAGE_CONFIGS.reduce<
      Partial<Record<MovingAveragePeriod, ISeriesApi<'Line'>>>
    >((seriesMap, config) => {
      seriesMap[config.period] = chart.addLineSeries({
        color: config.color,
        lineWidth: 1,
        title: config.label,
        priceLineVisible: false,
      });
      return seriesMap;
    }, {});

    chartRef.current = chart;
    seriesRef.current = candlestickSeries;
    volumeSeriesRef.current = volumeSeries;
    movingAverageSeriesRefs.current = movingAverageSeries;
    setChartReadyRevision((revision) => revision + 1);

    // 處理視窗大小變化
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        try {
          chartRef.current.applyOptions({
            width: chartContainerRef.current.clientWidth,
          });
        } catch (e) {
          console.warn('Error resizing chart:', e);
        }
      }
    };

    window.addEventListener('resize', handleResize);

    // 清理函數
    return () => {
      window.removeEventListener('resize', handleResize);
      // 清理圖表實例
      if (chartRef.current) {
        try {
          chartRef.current.remove();
        } catch (e) {
          console.warn('Error removing chart:', e);
        }
        chartRef.current = null;
        seriesRef.current = null;
        volumeSeriesRef.current = null;
        movingAverageSeriesRefs.current = {};
      }
    };
  }, [stockId, height]); // 依賴 stockId，當股票變化時重新創建圖表

  const applyMovingAverageOverlays = useCallback((chartData: ChartCandleData[]) => {
    MOVING_AVERAGE_CONFIGS.forEach((config) => {
      const movingAverageSeries = movingAverageSeriesRefs.current[config.period];
      if (!movingAverageSeries) {
        return;
      }

      movingAverageSeries.setData(
        calculateMovingAverageData(chartData, config.period)
      );
    });

    seriesRef.current?.setMarkers(createDeductionMarkers(chartData));
  }, []);

  // 載入歷史數據到圖表
  useEffect(() => {
    // 等待圖表初始化完成並確保所有 ref 都存在
    if (!seriesRef.current || !chartRef.current) {
      return;
    }

    // 嚴格檢查 historicalData 是否為有效陣列
    if (!Array.isArray(historicalData) || historicalData.length === 0) {
      seriesRef.current.setData([]);
      volumeSeriesRef.current?.setData([]);
      applyMovingAverageOverlays([]);
      setChartData([]);
      return;
    }

    try {

      // 轉換歷史數據為圖表格式
      const chartData = createChartDataFromPrices(historicalData);
      const volumeData = createVolumeDataFromPrices(historicalData);

      if (seriesRef.current) {
        seriesRef.current.setData(chartData);
        volumeSeriesRef.current?.setData(volumeData);
        applyMovingAverageOverlays(chartData);
        setChartData(chartData);
      }
    } catch (error) {
      console.error('Failed to set chart data:', error);
    }
  }, [applyMovingAverageOverlays, chartReadyRevision, historicalData]);

  // 處理即時串流更新：優先使用 5m bar，quote 只補最後價格。
  useEffect(() => {
    if (displayedTimeframe !== '5m') {
      return;
    }

    const streamUpdate = streamBar
      ? {
        timestamp: streamBar.bucket_start,
        volume: streamBar.volume,
        ohlc: {
          open: streamBar.open,
          high: streamBar.high,
          low: streamBar.low,
          close: streamBar.close,
        },
      }
      : streamQuote
        ? {
          timestamp: streamQuote.timestamp,
          volume: streamQuote.volume ?? 0,
          price: streamQuote.price,
        }
        : null;

    if (!streamUpdate || !seriesRef.current || !chartRef.current) return;

    try {
      // 檢查圖表是否已被清理
      if (!chartRef.current || !seriesRef.current) return;
      const time = Math.floor(new Date(streamUpdate.timestamp).getTime() / 1000) as UTCTimestamp;

      // 處理真實的 OHLC 數據
      let candlestickData;

      if ('ohlc' in streamUpdate) {
        // 如果 WebSocket 提供完整的 OHLC 數據
        candlestickData = {
          time,
          open: streamUpdate.ohlc.open,
          high: streamUpdate.ohlc.high,
          low: streamUpdate.ohlc.low,
          close: streamUpdate.ohlc.close,
        };
      } else {
        // 如果只有當前價格，則構建簡化的蠟燭圖數據
        // 在實際應用中，建議後端提供完整的 OHLC 數據
        const currentPrice = streamUpdate.price;

        // 獲取前一個數據點作為參考
        const chartData = seriesRef.current.data();
        const lastCandle = chartData.length > 0 ? chartData[chartData.length - 1] : null;

        const previousClose = isChartCandle(lastCandle) ? lastCandle.close : currentPrice;
        const previousHigh = isChartCandle(lastCandle) ? lastCandle.high : currentPrice;
        const previousLow = isChartCandle(lastCandle) ? lastCandle.low : currentPrice;

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
      volumeSeriesRef.current?.update({
        time,
        value: streamUpdate.volume ?? 0,
        color: candlestickData.close >= candlestickData.open
          ? VOLUME_UP_COLOR
          : VOLUME_DOWN_COLOR,
      });
      const updatedChartData = seriesRef.current.data().filter(isChartCandleData);
      applyMovingAverageOverlays(updatedChartData);
      setChartData(updatedChartData);

      if (process.env.NODE_ENV === 'development') {
        console.log('更新即時價格數據:', {
          symbol: symbol,
          time: new Date(time * 1000).toISOString(),
          data: candlestickData,
          volume: streamUpdate.volume,
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
            streamUpdate,
          });
        });
      }
    }
  }, [
    applyMovingAverageOverlays,
    displayedTimeframe,
    streamBar,
    streamQuote,
    symbol,
    stockId,
  ]);

  return (
    <div className="w-full">
        <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="inline-flex w-fit rounded-md border border-gray-200 bg-gray-50 p-1">
            {CHART_TIMEFRAME_OPTIONS.map((option) => {
              const isActive = selectedTimeframe === option.value;

              return (
                <button
                  key={option.value}
                  type="button"
                  aria-pressed={isActive}
                  onClick={() => setSelectedTimeframe(option.value)}
                  className={[
                    'h-8 rounded px-3 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-white text-gray-950 shadow-sm'
                      : 'text-gray-600 hover:text-gray-950',
                  ].join(' ')}
                >
                  {option.label}
                </button>
              );
            })}
          </div>
          {selectedTimeframe === '5m' && displayedTimeframe === '1d' && (
            <div className="text-xs font-medium text-amber-700">
              5分K暫無資料，已顯示日線
            </div>
          )}
        </div>

        {/* 圖表容器 */}
        <div
          ref={chartContainerRef}
          style={{ height: `${height}px` }}
          className="w-full border border-gray-200 rounded"
        />

        {/* 圖例 */}
        <div className="mt-3 flex flex-wrap items-center justify-center gap-x-6 gap-y-2">
          <div className="flex items-center space-x-2">
            <div className="w-4 h-2 bg-green-500"></div>
            <span className="text-sm text-gray-600">上漲</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-2 bg-red-500"></div>
            <span className="text-sm text-gray-600">下跌</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="h-2 w-4 bg-gray-300"></div>
            <span className="text-sm text-gray-600">成交量</span>
          </div>
          {MOVING_AVERAGE_CONFIGS.map((config) => (
            <div key={config.period} className="flex items-center space-x-2">
              <div
                className="h-0.5 w-4"
                style={{ backgroundColor: config.color }}
              />
              <span className="text-sm text-gray-600">{config.label}均線</span>
            </div>
          ))}
          <div className="flex items-center space-x-2">
            <div className="h-2.5 w-2.5 rounded-full bg-gray-500"></div>
            <span className="text-sm text-gray-600">扣抵價標記</span>
          </div>
        </div>

        {/* 均線摘要 */}
        <div className="mt-3 rounded-md border border-gray-200 bg-white p-3">
          <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
            <div className="text-sm font-medium text-gray-700">均線與扣抵價</div>
          </div>
          <div className="mt-3 grid grid-cols-[repeat(auto-fit,minmax(160px,1fr))] gap-3">
            {movingAverageSummary.map((item) => {
              const hasEnoughData = item.barsAvailable >= item.period;
              const placeholderText = '--';
              const deductionPrice = hasEnoughData
                ? formatPriceValue(item.deductionPrice)
                : placeholderText;
              const deductionDate = hasEnoughData
                ? formatChartDate(item.deductionTime)
                : null;

              return (
                <div
                  key={item.period}
                  className="rounded border border-gray-200 p-3"
                >
                  <div className="mb-2 flex items-center gap-2">
                    <span
                      className="h-2.5 w-2.5 rounded-full"
                      style={{ backgroundColor: item.color }}
                    />
                    <span className="text-sm font-medium text-gray-900">
                      {item.label}
                    </span>
                  </div>
                  <dl className="space-y-2 text-xs">
                    <div className="flex items-baseline justify-between gap-3">
                      <dt className="text-gray-500">最新均線</dt>
                      <dd className="font-semibold tabular-nums text-gray-900">
                        {hasEnoughData
                          ? formatPriceValue(item.latestValue)
                          : placeholderText}
                      </dd>
                    </div>
                    <div className="flex items-start justify-between gap-3">
                      <dt className="text-gray-500">扣抵價</dt>
                      <dd className="text-right">
                        <div className="font-semibold tabular-nums text-gray-900">
                          {deductionPrice}
                        </div>
                        {deductionDate && (
                          <div className="mt-0.5 whitespace-nowrap text-[11px] text-gray-500">
                            基準日 {deductionDate}
                          </div>
                        )}
                      </dd>
                    </div>
                  </dl>
                </div>
              );
            })}
          </div>
        </div>

        {/* 估值摘要 */}
        <div className="mt-3 rounded-md border border-gray-200 bg-white p-3">
          <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
            <div className="text-sm font-medium text-gray-700">估值指標</div>
            <div className="text-xs text-gray-500">
              {valuationMetrics?.provider
                ? `來源 ${valuationMetrics.provider}`
                : '來源待取得'}
            </div>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-4">
            {valuationRows.map((row) => (
              <div
                key={row.label}
                className="rounded border border-gray-200 bg-gray-50 px-3 py-2"
              >
                <div className="text-xs text-gray-500">{row.label}</div>
                <div className="mt-1 truncate text-sm font-semibold tabular-nums text-gray-900">
                  {valuationLoading ? '--' : row.value}
                </div>
              </div>
            ))}
          </div>
          {(valuationMetrics?.week_52_high || valuationMetrics?.week_52_low) && (
            <div className="mt-3 rounded border border-gray-200 px-3 py-2">
              <div className="mb-1 text-xs text-gray-500">52 週區間</div>
              <div
                className="flex items-center justify-between gap-3 text-sm font-semibold tabular-nums text-gray-900"
              >
                <span>{formatMetricValue(valuationMetrics.week_52_low)}</span>
                <div className="h-1 flex-1 rounded-full bg-gray-200" />
                <span>{formatMetricValue(valuationMetrics.week_52_high)}</span>
              </div>
            </div>
          )}
        </div>

        {/* 技術指標信息 */}
        {indicators && Object.keys(indicators).length > 0 && (
          <div className="mt-4 p-3 bg-gray-50 rounded-lg">
            <div className="text-sm font-medium text-gray-700 mb-2">即時指標</div>
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
  );
};

export default RealtimePriceChart;
