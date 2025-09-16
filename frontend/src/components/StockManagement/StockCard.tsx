'use client';

import React from 'react';
import Card, { CardHeader, CardTitle, CardContent } from '../ui/Card';
import Button from '../ui/Button';
import { 
  TrendingUp, 
  TrendingDown, 
  Minus, 
  MoreVertical, 
  Eye, 
  Edit, 
  Trash2, 
  RefreshCw,
  Activity,
  Calendar,
  DollarSign
} from 'lucide-react';
import type { Stock } from '../../types';

export interface StockCardProps {
  stock: Stock;
  onView?: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
  onRefresh?: () => void;
  isRefreshing?: boolean;
  showActions?: boolean;
  priceData?: {
    current_price?: number;
    price_change?: number;
    price_change_percent?: number;
    volume?: number;
    last_updated?: string;
  };
}

const StockCard: React.FC<StockCardProps> = ({
  stock,
  onView,
  onEdit,
  onDelete,
  onRefresh,
  isRefreshing = false,
  showActions = true,
  priceData
}) => {
  const getTrendIcon = () => {
    if (!priceData?.price_change) {
      return <Minus className="w-4 h-4 text-gray-400" />;
    }
    
    if (priceData.price_change > 0) {
      return <TrendingUp className="w-4 h-4 text-green-600" />;
    } else if (priceData.price_change < 0) {
      return <TrendingDown className="w-4 h-4 text-red-600" />;
    } else {
      return <Minus className="w-4 h-4 text-gray-400" />;
    }
  };

  const getTrendColor = () => {
    if (!priceData?.price_change) return 'text-gray-600';
    
    if (priceData.price_change > 0) {
      return 'text-green-600';
    } else if (priceData.price_change < 0) {
      return 'text-red-600';
    } else {
      return 'text-gray-600';
    }
  };

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('zh-TW', {
      style: 'currency',
      currency: stock.market === 'TW' ? 'TWD' : 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(price);
  };

  const formatVolume = (volume: number) => {
    if (volume >= 1000000) {
      return `${(volume / 1000000).toFixed(1)}M`;
    } else if (volume >= 1000) {
      return `${(volume / 1000).toFixed(1)}K`;
    }
    return volume.toString();
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('zh-TW', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <Card className="hover:shadow-md transition-shadow cursor-pointer group">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div 
            className="flex items-center gap-3 flex-1"
            onClick={onView}
          >
            <div className="flex items-center gap-2">
              {getTrendIcon()}
              <div>
                <CardTitle className="text-lg font-bold">
                  {stock.symbol}
                </CardTitle>
                <div className="text-sm text-gray-600">
                  {stock.name || '無名稱'}
                </div>
              </div>
            </div>
            
            <div className="ml-auto">
              <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                {stock.market}
              </span>
            </div>
          </div>

          {/* 動作按鈕 */}
          {showActions && (
            <div className="opacity-0 group-hover:opacity-100 transition-opacity">
              <div className="flex items-center gap-1">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    onRefresh?.();
                  }}
                  disabled={isRefreshing}
                  title="刷新數據"
                >
                  <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                </Button>
                
                <Button
                  variant="outline"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    onEdit?.();
                  }}
                  title="編輯"
                >
                  <Edit className="w-4 h-4" />
                </Button>
                
                <Button
                  variant="outline"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete?.();
                  }}
                  title="刪除"
                  className="text-red-600 hover:text-red-700"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent className="pt-0" onClick={onView}>
        <div className="space-y-3">
          {/* 價格資訊 */}
          {priceData ? (
            <div className="space-y-2">
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-bold">
                  {formatPrice(priceData.current_price || 0)}
                </span>
                <div className={`text-sm font-medium ${getTrendColor()}`}>
                  {priceData.price_change !== undefined && (
                    <>
                      {priceData.price_change > 0 && '+'}
                      {formatPrice(priceData.price_change)}
                      {priceData.price_change_percent !== undefined && (
                        <span className="ml-1">
                          ({priceData.price_change_percent > 0 && '+'}
                          {priceData.price_change_percent.toFixed(2)}%)
                        </span>
                      )}
                    </>
                  )}
                </div>
              </div>

              {/* 成交量 */}
              {priceData.volume !== undefined && (
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <Activity className="w-4 h-4" />
                  <span>成交量: {formatVolume(priceData.volume)}</span>
                </div>
              )}

              {/* 最後更新時間 */}
              {priceData.last_updated && (
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  <Calendar className="w-3 h-3" />
                  <span>更新: {formatDate(priceData.last_updated)}</span>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-4 text-gray-500">
              <DollarSign className="w-8 h-8 mx-auto mb-2 text-gray-300" />
              <div className="text-sm">尚無價格數據</div>
            </div>
          )}

          {/* 股票狀態 */}
          <div className="flex items-center justify-between text-xs text-gray-500 pt-2 border-t">
            <span>
              建立: {formatDate(stock.created_at)}
            </span>
            {stock.is_active ? (
              <span className="text-green-600 font-medium">啟用</span>
            ) : (
              <span className="text-red-600 font-medium">停用</span>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default StockCard;