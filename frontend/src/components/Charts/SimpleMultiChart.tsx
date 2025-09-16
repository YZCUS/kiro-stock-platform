'use client';

import React from 'react';
import Card, { CardHeader, CardTitle, CardContent } from '../ui/Card';
import Button from '../ui/Button';
import { RefreshCw } from 'lucide-react';
import SimpleCandlestickChart from './SimpleCandlestickChart';

export interface ChartData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

export interface LineDataPoint {
  time: string;
  value: number;
}

export interface SimpleMultiChartProps {
  symbol: string;
  candleData: ChartData[];
  indicators?: {
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

const SimpleMultiChart: React.FC<SimpleMultiChartProps> = ({
  symbol,
  candleData,
  indicators = {},
  loading = false,
  onRefresh,
  theme = 'light',
}) => {
  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <RefreshCw className="w-6 h-6 animate-spin mr-2" />
          載入圖表數據中...
        </CardContent>
      </Card>
    );
  }

  if (candleData.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            {symbol} 圖表分析
            {onRefresh && (
              <Button variant="outline" size="sm" onClick={onRefresh}>
                <RefreshCw className="w-4 h-4 mr-2" />
                重新載入
              </Button>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center py-12 text-gray-500">
          暫無圖表數據
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* 主要 K線圖 */}
      <SimpleCandlestickChart
        data={candleData}
        symbol={symbol}
        height={400}
      />

      {/* 技術指標摘要 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {indicators.rsi && (
          <Card>
            <CardContent className="p-4">
              <div className="text-center">
                <p className="text-sm text-gray-600 mb-1">RSI 指標</p>
                <p className="text-lg font-bold text-blue-600">
                  {indicators.rsi[indicators.rsi.length - 1]?.value.toFixed(1) || 'N/A'}
                </p>
              </div>
            </CardContent>
          </Card>
        )}

        {indicators.macd && (
          <Card>
            <CardContent className="p-4">
              <div className="text-center">
                <p className="text-sm text-gray-600 mb-1">MACD</p>
                <p className="text-lg font-bold text-green-600">
                  {indicators.macd.macd[indicators.macd.macd.length - 1]?.value.toFixed(3) || 'N/A'}
                </p>
              </div>
            </CardContent>
          </Card>
        )}

        {indicators.ma && (
          <Card>
            <CardContent className="p-4">
              <div className="text-center">
                <p className="text-sm text-gray-600 mb-1">MA20</p>
                <p className="text-lg font-bold text-purple-600">
                  {indicators.ma.ma20[indicators.ma.ma20.length - 1]?.value.toFixed(2) || 'N/A'}
                </p>
              </div>
            </CardContent>
          </Card>
        )}

        {indicators.bollinger && (
          <Card>
            <CardContent className="p-4">
              <div className="text-center">
                <p className="text-sm text-gray-600 mb-1">布林通道</p>
                <div className="space-y-1">
                  <p className="text-xs text-red-600">
                    上軌: {indicators.bollinger.upper[indicators.bollinger.upper.length - 1]?.value.toFixed(2) || 'N/A'}
                  </p>
                  <p className="text-xs text-blue-600">
                    中軌: {indicators.bollinger.middle[indicators.bollinger.middle.length - 1]?.value.toFixed(2) || 'N/A'}
                  </p>
                  <p className="text-xs text-green-600">
                    下軌: {indicators.bollinger.lower[indicators.bollinger.lower.length - 1]?.value.toFixed(2) || 'N/A'}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* 圖表說明 */}
      <Card>
        <CardHeader>
          <CardTitle>圖表說明</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-600">
            <div>
              <h4 className="font-medium text-gray-900 mb-2">K線圖顏色</h4>
              <ul className="space-y-1">
                <li className="flex items-center">
                  <div className="w-3 h-3 bg-green-500 rounded mr-2"></div>
                  綠色：上漲 (收盤 &gt; 開盤)
                </li>
                <li className="flex items-center">
                  <div className="w-3 h-3 bg-red-500 rounded mr-2"></div>
                  紅色：下跌 (收盤 &lt; 開盤)
                </li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium text-gray-900 mb-2">功能操作</h4>
              <ul className="space-y-1">
                <li>• 滑鼠滾輪：縮放圖表</li>
                <li>• 點擊拖拽：移動圖表</li>
                <li>• 十字線：查看詳細數據</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default SimpleMultiChart;