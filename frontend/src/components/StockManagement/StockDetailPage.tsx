'use client';

import React, { useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Layout } from '../Layout';
import Card, { CardHeader, CardTitle, CardContent } from '../ui/Card';
import Button from '../ui/Button';
import { 
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Minus,
  RefreshCw,
  Edit,
  Trash2,
  Activity,
  Calendar,
  DollarSign,
  BarChart3,
  Bell,
  AlertCircle,
  Eye
} from 'lucide-react';
import { AppDispatch, RootState } from '../../store';
import { fetchStock, refreshStockData } from '../../store/slices/stocksSlice';
import type { Stock } from '../../types';

export interface StockDetailPageProps {
  stockId: number;
  onBack?: () => void;
  onEdit?: (stock: Stock) => void;
  onDelete?: (stock: Stock) => void;
}

const StockDetailPage: React.FC<StockDetailPageProps> = ({
  stockId,
  onBack,
  onEdit,
  onDelete
}) => {
  const dispatch = useDispatch<AppDispatch>();
  const { selectedStock, loading, error } = useSelector((state: RootState) => state.stocks);
  
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'prices' | 'indicators' | 'signals'>('overview');

  useEffect(() => {
    dispatch(fetchStock(stockId));
  }, [dispatch, stockId]);

  const handleRefresh = async () => {
    if (!selectedStock) return;
    
    setIsRefreshing(true);
    try {
      await dispatch(refreshStockData({
        stockId: selectedStock.id,
        days: 30
      })).unwrap();
    } catch (error) {
      console.error('刷新失敗:', error);
    } finally {
      setIsRefreshing(false);
    }
  };

  const getTrendIcon = (change?: number) => {
    if (change === undefined) {
      return <Minus className="w-5 h-5 text-gray-400" />;
    }
    
    if (change > 0) {
      return <TrendingUp className="w-5 h-5 text-green-600" />;
    } else if (change < 0) {
      return <TrendingDown className="w-5 h-5 text-red-600" />;
    } else {
      return <Minus className="w-5 h-5 text-gray-400" />;
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('zh-TW', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading && !selectedStock) {
    return (
      <Layout>
        <div className="flex items-center justify-center py-8">
          <RefreshCw className="w-6 h-6 animate-spin mr-2" />
          載入股票資訊中...
        </div>
      </Layout>
    );
  }

  if (error || !selectedStock) {
    return (
      <Layout>
        <div className="flex flex-col items-center justify-center py-8">
          <AlertCircle className="w-12 h-12 text-red-500 mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">載入失敗</h2>
          <p className="text-gray-600 mb-4">{error || '找不到指定的股票'}</p>
          <Button onClick={onBack} variant="outline">
            <ArrowLeft className="w-4 h-4 mr-2" />
            返回
          </Button>
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
              {getTrendIcon()}
              <div>
                <h1 className="text-3xl font-bold text-gray-900">
                  {selectedStock.symbol}
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
              onClick={handleRefresh}
              disabled={isRefreshing}
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
              刷新數據
            </Button>
            
            <Button
              variant="outline"
              onClick={() => onEdit?.(selectedStock)}
            >
              <Edit className="w-4 h-4 mr-2" />
              編輯
            </Button>
            
            <Button
              variant="outline"
              onClick={() => onDelete?.(selectedStock)}
              className="text-red-600 hover:text-red-700"
            >
              <Trash2 className="w-4 h-4 mr-2" />
              刪除
            </Button>
          </div>
        </div>

        {/* 分頁標籤 */}
        <div className="border-b">
          <nav className="flex space-x-8">
            {[
              { id: 'overview', label: '概覽', icon: Eye },
              { id: 'prices', label: '價格數據', icon: DollarSign },
              { id: 'indicators', label: '技術指標', icon: BarChart3 },
              { id: 'signals', label: '交易信號', icon: Bell }
            ].map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id as any)}
                className={`flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </button>
            ))}
          </nav>
        </div>

        {/* 分頁內容 */}
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* 基本資訊 */}
            <Card>
              <CardHeader>
                <CardTitle>基本資訊</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-600">股票代號</span>
                    <span className="font-medium">{selectedStock.symbol}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">股票名稱</span>
                    <span className="font-medium">{selectedStock.name || '無名稱'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">市場</span>
                    <span className="font-medium">{selectedStock.market}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">狀態</span>
                    <span className={`font-medium ${
                      selectedStock.is_active ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {selectedStock.is_active ? '啟用' : '停用'}
                    </span>
                  </div>
                </div>
                
                <hr />
                
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-600">建立時間</span>
                    <span className="font-medium text-sm">
                      {formatDate(selectedStock.created_at)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">更新時間</span>
                    <span className="font-medium text-sm">
                      {formatDate(selectedStock.updated_at)}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* 最新價格 */}
            <Card>
              <CardHeader>
                <CardTitle>最新價格</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center py-8">
                  <DollarSign className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                  <p className="text-gray-500">尚無價格數據</p>
                  <p className="text-sm text-gray-400 mt-2">
                    請刷新數據以獲取最新價格
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* 統計資訊 */}
            <Card>
              <CardHeader>
                <CardTitle>統計資訊</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-600">數據點數</span>
                    <span className="font-medium">-</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-600">技術指標</span>
                    <span className="font-medium">-</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-600">交易信號</span>
                    <span className="font-medium">-</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-600">最後分析</span>
                    <span className="font-medium text-sm">-</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === 'prices' && (
          <div className="space-y-6">
            {/* 引入圖表組件 */}
            <Card>
              <CardHeader>
                <CardTitle>K線圖表</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center py-12">
                  <BarChart3 className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">價格圖表</h3>
                  <p className="text-gray-500 mb-4">查看股票的價格走勢和K線圖</p>
                  <Button variant="outline">查看詳細圖表</Button>
                </div>
              </CardContent>
            </Card>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>價格統計</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-gray-600">今日開盤</span>
                      <span className="font-medium">-</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">今日最高</span>
                      <span className="font-medium">-</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">今日最低</span>
                      <span className="font-medium">-</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">收盤價</span>
                      <span className="font-medium">-</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">成交量</span>
                      <span className="font-medium">-</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>歷史表現</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-gray-600">52週最高</span>
                      <span className="font-medium">-</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">52週最低</span>
                      <span className="font-medium">-</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">平均成交量</span>
                      <span className="font-medium">-</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">市值</span>
                      <span className="font-medium">-</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">本益比</span>
                      <span className="font-medium">-</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        )}

        {activeTab === 'indicators' && (
          <Card>
            <CardHeader>
              <CardTitle>技術指標</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-12">
                <Activity className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">技術指標分析</h3>
                <p className="text-gray-500 mb-4">RSI、MACD、布林通道等技術指標</p>
                <Button variant="outline">計算技術指標</Button>
              </div>
            </CardContent>
          </Card>
        )}

        {activeTab === 'signals' && (
          <Card>
            <CardHeader>
              <CardTitle>交易信號</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-12">
                <Bell className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">交易信號偵測</h3>
                <p className="text-gray-500 mb-4">黃金交叉、死亡交叉等交易信號</p>
                <Button variant="outline">偵測交易信號</Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </Layout>
  );
};

export default StockDetailPage;