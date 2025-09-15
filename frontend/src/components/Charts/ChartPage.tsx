'use client';

import React, { useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Layout } from '../Layout';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import { 
  ArrowLeft,
  BarChart3,
  TrendingUp,
  Activity,
  Download,
  Settings,
  Calendar,
  RefreshCw
} from 'lucide-react';
import { AppDispatch, RootState } from '../../store';
import { fetchStock } from '../../store/slices/stocksSlice';
import MultiChart from './MultiChart';
import type { Stock } from '../../types';
import type { CandleData } from './CandlestickChart';
import type { LineDataPoint } from './LineChart';

export interface ChartPageProps {
  stockId: number;
  onBack?: () => void;
}

const ChartPage: React.FC<ChartPageProps> = ({
  stockId,
  onBack
}) => {
  const dispatch = useDispatch<AppDispatch>();
  const { selectedStock, loading } = useSelector((state: RootState) => state.stocks);
  
  const [chartData, setChartData] = useState<{
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
  }>({
    candleData: [],
    indicators: {}
  });
  
  const [dataLoading, setDataLoading] = useState(false);
  const [timeRange, setTimeRange] = useState<'1D' | '1W' | '1M' | '3M' | '6M' | '1Y'>('1M');

  useEffect(() => {
    dispatch(fetchStock(stockId));
  }, [dispatch, stockId]);

  useEffect(() => {
    if (selectedStock) {
      loadChartData();
    }
  }, [selectedStock, timeRange]);

  const loadChartData = async () => {
    if (!selectedStock) return;

    setDataLoading(true);
    try {
      // 模擬數據 - 實際應該調用 API
      const mockCandleData: CandleData[] = generateMockCandleData(timeRange);
      const mockIndicators = generateMockIndicators(mockCandleData);

      setChartData({
        candleData: mockCandleData,
        indicators: mockIndicators
      });
    } catch (error) {
      console.error('載入圖表數據失敗:', error);
    } finally {
      setDataLoading(false);
    }
  };

  const generateMockCandleData = (range: string): CandleData[] => {
    const days = {
      '1D': 1,
      '1W': 7,
      '1M': 30,
      '3M': 90,
      '6M': 180,
      '1Y': 365
    }[range] || 30;

    const data: CandleData[] = [];
    let basePrice = 100;
    
    for (let i = 0; i < days; i++) {
      const date = new Date();
      date.setDate(date.getDate() - (days - i - 1));
      
      const open = basePrice + (Math.random() - 0.5) * 2;
      const close = open + (Math.random() - 0.5) * 4;
      const high = Math.max(open, close) + Math.random() * 2;
      const low = Math.min(open, close) - Math.random() * 2;
      const volume = Math.floor(Math.random() * 1000000) + 100000;
      
      data.push({
        time: date.toISOString().split('T')[0],
        open,
        high,
        low,
        close,
        volume
      });
      
      basePrice = close;
    }
    
    return data;
  };

  const generateMockIndicators = (candleData: CandleData[]) => {
    if (candleData.length === 0) return {};

    // 生成 RSI 數據
    const rsi: LineDataPoint[] = candleData.map((item, index) => ({
      time: item.time,
      value: 30 + Math.random() * 40 // RSI 通常在 0-100 之間
    }));

    // 生成 MACD 數據
    const macd = {
      macd: candleData.map(item => ({
        time: item.time,
        value: (Math.random() - 0.5) * 2
      })),
      signal: candleData.map(item => ({
        time: item.time,
        value: (Math.random() - 0.5) * 1.5
      })),
      histogram: candleData.map(item => ({
        time: item.time,
        value: (Math.random() - 0.5) * 1
      }))
    };

    // 生成移動平均數據
    const ma = {
      ma5: candleData.map(item => ({
        time: item.time,
        value: item.close + (Math.random() - 0.5) * 0.5
      })),
      ma10: candleData.map(item => ({
        time: item.time,
        value: item.close + (Math.random() - 0.5) * 1
      })),
      ma20: candleData.map(item => ({
        time: item.time,
        value: item.close + (Math.random() - 0.5) * 2
      }))
    };

    // 生成布林通道數據
    const bollinger = {
      upper: candleData.map(item => ({
        time: item.time,
        value: item.close + 2 + Math.random()
      })),
      middle: candleData.map(item => ({
        time: item.time,
        value: item.close
      })),
      lower: candleData.map(item => ({
        time: item.time,
        value: item.close - 2 - Math.random()
      }))
    };

    return { rsi, macd, ma, bollinger };
  };

  const handleExport = () => {
    // TODO: 實作圖表匯出功能
    console.log('匯出圖表');
  };

  const handleRefresh = () => {
    loadChartData();
  };

  if (!selectedStock) {
    return (
      <Layout>
        <div className="flex items-center justify-center py-8">
          <RefreshCw className="w-6 h-6 animate-spin mr-2" />
          載入股票資訊中...
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6">
        {/* 標題列 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button 
              variant="outline" 
              size="sm"
              onClick={onBack}
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              返回
            </Button>
            
            <div className="flex items-center gap-3">
              <BarChart3 className="w-8 h-8 text-blue-600" />
              <div>
                <h1 className="text-3xl font-bold text-gray-900">
                  {selectedStock.symbol} 圖表分析
                </h1>
                <p className="text-gray-600">
                  {selectedStock.name || '無名稱'}
                  <span className="ml-2 text-sm bg-gray-100 text-gray-600 px-2 py-1 rounded">
                    {selectedStock.market}
                  </span>
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              onClick={handleExport}
            >
              <Download className="w-4 h-4 mr-2" />
              匯出圖表
            </Button>
            
            <Button
              variant="outline"
            >
              <Settings className="w-4 h-4 mr-2" />
              設定
            </Button>
          </div>
        </div>

        {/* 時間範圍選擇 */}
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-gray-500" />
                <span className="text-sm text-gray-600">時間範圍:</span>
                <div className="flex gap-1">
                  {(['1D', '1W', '1M', '3M', '6M', '1Y'] as const).map((range) => (
                    <Button
                      key={range}
                      variant={timeRange === range ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setTimeRange(range)}
                    >
                      {range}
                    </Button>
                  ))}
                </div>
              </div>

              <div className="flex items-center gap-4 text-sm text-gray-600">
                <div className="flex items-center gap-2">
                  <Activity className="w-4 h-4" />
                  <span>數據點: {chartData.candleData.length}</span>
                </div>
                {chartData.candleData.length > 0 && (
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-4 h-4" />
                    <span>
                      最新價格: {chartData.candleData[chartData.candleData.length - 1]?.close.toFixed(2)}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 多重圖表 */}
        <MultiChart
          symbol={selectedStock.symbol}
          candleData={chartData.candleData}
          indicators={chartData.indicators}
          loading={dataLoading}
          onRefresh={handleRefresh}
          theme="light"
        />

        {/* 圖表統計資訊 */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">K線數據點</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {chartData.candleData.length}
                  </p>
                </div>
                <BarChart3 className="w-8 h-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">技術指標</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {Object.keys(chartData.indicators).length}
                  </p>
                </div>
                <TrendingUp className="w-8 h-8 text-green-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">時間範圍</p>
                  <p className="text-2xl font-bold text-gray-900">{timeRange}</p>
                </div>
                <Calendar className="w-8 h-8 text-purple-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">數據狀態</p>
                  <p className="text-2xl font-bold text-green-600">
                    {dataLoading ? '載入中' : '已載入'}
                  </p>
                </div>
                <Activity className="w-8 h-8 text-orange-600" />
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </Layout>
  );
};

export default ChartPage;