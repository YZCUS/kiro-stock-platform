'use client';

import React, { useState } from 'react';
import Card, { CardHeader, CardTitle, CardContent } from '../ui/Card';
import Button from '../ui/Button';
import Input from '../ui/Input';
import { 
  Bell,
  TrendingUp,
  TrendingDown,
  Search,
  Filter,
  Calendar,
  MoreVertical,
  Eye,
  Trash2,
  AlertCircle,
  Activity
} from 'lucide-react';
import type { TradingSignal } from '../../types';

export interface SignalListProps {
  signals: TradingSignal[];
  loading?: boolean;
  onSignalView?: (signal: TradingSignal) => void;
  onSignalDelete?: (signal: TradingSignal) => void;
  onRefresh?: () => void;
}

const SignalList: React.FC<SignalListProps> = ({
  signals,
  loading = false,
  onSignalView,
  onSignalDelete,
  onRefresh
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState<'ALL' | 'BUY' | 'SELL' | 'GOLDEN_CROSS' | 'DEATH_CROSS'>('ALL');
  const [marketFilter, setMarketFilter] = useState<'ALL' | 'TW' | 'US'>('ALL');
  const [sortBy, setSortBy] = useState<'created_at' | 'confidence' | 'symbol'>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  // 信號類型配置
  const signalConfig = {
    BUY: {
      color: 'text-green-600 bg-green-100',
      icon: TrendingUp,
      label: '買入信號',
      description: '建議買入'
    },
    SELL: {
      color: 'text-red-600 bg-red-100',
      icon: TrendingDown,
      label: '賣出信號',
      description: '建議賣出'
    },
    GOLDEN_CROSS: {
      color: 'text-yellow-600 bg-yellow-100',
      icon: TrendingUp,
      label: '黃金交叉',
      description: '短期均線突破長期均線'
    },
    DEATH_CROSS: {
      color: 'text-purple-600 bg-purple-100',
      icon: TrendingDown,
      label: '死亡交叉',
      description: '短期均線跌破長期均線'
    },
    HOLD: {
      color: 'text-gray-600 bg-gray-100',
      icon: Activity,
      label: '觀望',
      description: '維持現狀'
    }
  };

  // 過濾和排序信號
  const filteredAndSortedSignals = React.useMemo(() => {
    let filtered = signals.filter(signal => {
      const matchesSearch = !searchTerm || 
        signal.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
        signal.signal_type.toLowerCase().includes(searchTerm.toLowerCase());
      
      const matchesType = typeFilter === 'ALL' || signal.signal_type === typeFilter;
      const matchesMarket = marketFilter === 'ALL' || signal.market === marketFilter;
      
      return matchesSearch && matchesType && matchesMarket;
    });

    filtered.sort((a, b) => {
      let aValue: string | number;
      let bValue: string | number;

      switch (sortBy) {
        case 'created_at':
          aValue = new Date(a.created_at).getTime();
          bValue = new Date(b.created_at).getTime();
          break;
        case 'confidence':
          aValue = a.confidence || 0;
          bValue = b.confidence || 0;
          break;
        case 'symbol':
          aValue = a.symbol;
          bValue = b.symbol;
          break;
        default:
          aValue = new Date(a.created_at).getTime();
          bValue = new Date(b.created_at).getTime();
      }

      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortOrder === 'asc' 
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }

      return sortOrder === 'asc' 
        ? (aValue as number) - (bValue as number)
        : (bValue as number) - (aValue as number);
    });

    return filtered;
  }, [signals, searchTerm, typeFilter, marketFilter, sortBy, sortOrder]);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('zh-TW', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatConfidence = (confidence?: number) => {
    if (confidence === undefined) return '-';
    return `${(confidence * 100).toFixed(1)}%`;
  };

  const getSignalConfig = (signalType: string) => {
    return signalConfig[signalType as keyof typeof signalConfig] || signalConfig.HOLD;
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Bell className="w-5 h-5" />
            交易信號清單 ({filteredAndSortedSignals.length})
          </CardTitle>
          
          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            disabled={loading}
          >
            <Activity className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* 搜尋和篩選 */}
        <div className="flex flex-col lg:flex-row gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <Input
              placeholder="搜尋股票代號或信號類型..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9"
            />
          </div>
          
          <div className="flex gap-2">
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value as any)}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
            >
              <option value="ALL">全部類型</option>
              <option value="BUY">買入信號</option>
              <option value="SELL">賣出信號</option>
              <option value="GOLDEN_CROSS">黃金交叉</option>
              <option value="DEATH_CROSS">死亡交叉</option>
            </select>
            
            <select
              value={marketFilter}
              onChange={(e) => setMarketFilter(e.target.value as any)}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
            >
              <option value="ALL">全部市場</option>
              <option value="TW">台股</option>
              <option value="US">美股</option>
            </select>
            
            <select
              value={`${sortBy}_${sortOrder}`}
              onChange={(e) => {
                const [sort, order] = e.target.value.split('_');
                setSortBy(sort as any);
                setSortOrder(order as any);
              }}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
            >
              <option value="created_at_desc">時間 ↓</option>
              <option value="created_at_asc">時間 ↑</option>
              <option value="confidence_desc">信心度 ↓</option>
              <option value="confidence_asc">信心度 ↑</option>
              <option value="symbol_asc">代號 ↑</option>
              <option value="symbol_desc">代號 ↓</option>
            </select>
          </div>
        </div>

        {/* 信號清單 */}
        {filteredAndSortedSignals.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            {loading ? (
              <div className="flex items-center justify-center">
                <Activity className="w-6 h-6 animate-spin mr-2" />
                載入交易信號中...
              </div>
            ) : (
              <div>
                <Bell className="w-12 h-12 mx-auto mb-2 text-gray-300" />
                <p>{searchTerm || typeFilter !== 'ALL' || marketFilter !== 'ALL' ? '沒有符合條件的信號' : '尚未產生任何交易信號'}</p>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {filteredAndSortedSignals.map((signal) => {
              const config = getSignalConfig(signal.signal_type);
              const Icon = config.icon;
              
              return (
                <div
                  key={signal.id}
                  className="flex items-center gap-4 p-4 border rounded-lg hover:bg-gray-50 transition-colors"
                >
                  {/* 信號圖標和類型 */}
                  <div className={`flex items-center justify-center w-10 h-10 rounded-full ${config.color}`}>
                    <Icon className="w-5 h-5" />
                  </div>

                  {/* 主要資訊 */}
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-1">
                      <h3 className="font-medium text-gray-900">
                        {signal.symbol}
                        <span className="ml-2 text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                          {signal.market}
                        </span>
                      </h3>
                      <span className={`text-sm font-medium px-2 py-1 rounded ${config.color}`}>
                        {config.label}
                      </span>
                    </div>
                    
                    <p className="text-sm text-gray-600">
                      {signal.description || config.description}
                    </p>
                    
                    <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                      <div className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        <span>{formatDate(signal.created_at)}</span>
                      </div>
                      
                      {signal.confidence !== undefined && (
                        <div className="flex items-center gap-1">
                          <Activity className="w-3 h-3" />
                          <span>信心度: {formatConfidence(signal.confidence)}</span>
                        </div>
                      )}
                      
                      {signal.price && (
                        <div className="flex items-center gap-1">
                          <span>價格: ${signal.price.toFixed(2)}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* 操作按鈕 */}
                  <div className="flex items-center gap-1">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onSignalView?.(signal)}
                      title="查看詳情"
                    >
                      <Eye className="w-4 h-4" />
                    </Button>
                    
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onSignalDelete?.(signal)}
                      title="刪除信號"
                      className="text-red-600 hover:text-red-700"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* 載入更多 */}
        {loading && signals.length > 0 && (
          <div className="flex justify-center py-4">
            <Activity className="w-5 h-5 animate-spin" />
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default SignalList;