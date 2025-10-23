'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAppSelector, useAppDispatch } from '@/store';
import { fetchPortfolioList, fetchPortfolioSummary, removePortfolio } from '@/store/slices/portfolioSlice';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import TransactionModal from '@/components/Portfolio/TransactionModal';
import { useStocks } from '@/hooks/useStocks';
import Link from 'next/link';
import { TrendingUp, TrendingDown, Plus, Trash2, ShoppingCart } from 'lucide-react';

export default function PortfolioPage() {
  const router = useRouter();
  const dispatch = useAppDispatch();
  const { isAuthenticated } = useAppSelector((state) => state.auth);
  const {
    portfolios,
    totalCost,
    totalCurrentValue,
    totalProfitLoss,
    totalProfitLossPercent,
    portfolioLoading,
    error
  } = useAppSelector((state) => state.portfolio);
  const [isMounted, setIsMounted] = useState(false);
  const [selectedStock, setSelectedStock] = useState<any>(null);
  const [transactionModal, setTransactionModal] = useState<{
    isOpen: boolean;
    stock: any | null;
    type: 'BUY' | 'SELL';
  }>({
    isOpen: false,
    stock: null,
    type: 'BUY'
  });

  // 獲取所有股票列表（用於選擇器）
  const { data: stocksResponse } = useStocks({ page: 1, pageSize: 100 });

  // 確保只在客戶端渲染，避免 hydration 錯誤
  useEffect(() => {
    setIsMounted(true);
  }, []);

  useEffect(() => {
    if (!isMounted) return;

    if (!isAuthenticated) {
      router.push('/login');
      return;
    }

    loadPortfolio();
  }, [isAuthenticated, isMounted]);

  const loadPortfolio = async () => {
    dispatch(fetchPortfolioList());
    dispatch(fetchPortfolioSummary());
  };

  const handleRemove = async (portfolioId: number, stockSymbol: string) => {
    if (!confirm(`確定要刪除 ${stockSymbol} 的持倉嗎？`)) {
      return;
    }

    try {
      await dispatch(removePortfolio(portfolioId)).unwrap();
      // 重新載入持倉列表
      loadPortfolio();
    } catch (err: any) {
      alert('刪除失敗：' + err);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('zh-TW', {
      style: 'currency',
      currency: 'TWD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  const formatPercent = (percent: number) => {
    return `${percent >= 0 ? '+' : ''}${percent.toFixed(2)}%`;
  };

  // 在客戶端渲染前顯示 loading 狀態，避免 hydration 錯誤
  if (!isMounted) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-6xl mx-auto">
          <div className="mb-8">
            <h1 className="text-3xl font-bold mb-2">持倉管理</h1>
          </div>
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <Card key={i}>
                <CardContent className="p-6">
                  <Skeleton className="h-6 w-32 mb-2" />
                  <Skeleton className="h-4 w-48" />
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-start mb-8">
          <div>
            <h1 className="text-3xl font-bold mb-2">持倉管理</h1>
            <p className="text-muted-foreground">
              查看您的投資組合，追蹤盈虧表現
            </p>
          </div>

          {/* 新增交易區域 */}
          <div className="flex gap-2">
            <select
              value={selectedStock?.id || ''}
              onChange={(e) => {
                const stock = stocksResponse?.items.find(s => s.id === parseInt(e.target.value));
                setSelectedStock(stock || null);
              }}
              className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">選擇股票...</option>
              {stocksResponse?.items.map((stock) => (
                <option key={stock.id} value={stock.id}>
                  {stock.symbol} - {stock.name}
                </option>
              ))}
            </select>
            <Button
              onClick={() => {
                if (!selectedStock) {
                  alert('請先選擇股票');
                  return;
                }
                setTransactionModal({ isOpen: true, stock: selectedStock, type: 'BUY' });
              }}
              disabled={!selectedStock}
              className="bg-green-600 hover:bg-green-700"
            >
              <ShoppingCart className="w-4 h-4 mr-2" />
              買入
            </Button>
            <Button
              onClick={() => {
                if (!selectedStock) {
                  alert('請先選擇股票');
                  return;
                }
                setTransactionModal({ isOpen: true, stock: selectedStock, type: 'SELL' });
              }}
              disabled={!selectedStock}
              variant="destructive"
            >
              <TrendingDown className="w-4 h-4 mr-2" />
              賣出
            </Button>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>總成本</CardDescription>
              <CardTitle className="text-2xl">{formatCurrency(totalCost)}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>當前市值</CardDescription>
              <CardTitle className="text-2xl">{formatCurrency(totalCurrentValue)}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>總盈虧</CardDescription>
              <CardTitle className={`text-2xl ${totalProfitLoss >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {formatCurrency(totalProfitLoss)}
              </CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>報酬率</CardDescription>
              <CardTitle className={`text-2xl flex items-center gap-2 ${totalProfitLossPercent >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {totalProfitLossPercent >= 0 ? (
                  <TrendingUp className="w-5 h-5" />
                ) : (
                  <TrendingDown className="w-5 h-5" />
                )}
                {formatPercent(totalProfitLossPercent)}
              </CardTitle>
            </CardHeader>
          </Card>
        </div>

        {/* Error Alert */}
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Portfolio List */}
        {portfolioLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <Card key={i}>
                <CardContent className="p-6">
                  <Skeleton className="h-6 w-32 mb-2" />
                  <Skeleton className="h-4 w-48" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : portfolios.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <p className="text-muted-foreground mb-4">您還沒有任何持倉</p>
              <Button asChild>
                <Link href="/stocks">開始投資</Link>
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {portfolios.map((portfolio) => {
              const profitLoss = portfolio.profit_loss || 0;
              const profitLossPercent = portfolio.profit_loss_percent || 0;
              const isProfitable = profitLoss >= 0;

              return (
                <Card key={portfolio.id} className="hover:shadow-md transition-shadow">
                  <CardHeader>
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <CardTitle className="flex items-center gap-2">
                          {portfolio.stock_symbol}
                          <Badge variant="outline">
                            {portfolio.stock_name}
                          </Badge>
                        </CardTitle>
                        <CardDescription className="mt-1">
                          持有 {portfolio.quantity} 股 · 平均成本 {formatCurrency(portfolio.avg_cost)}
                        </CardDescription>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRemove(portfolio.id, portfolio.stock_symbol || '')}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
                      <div>
                        <div className="text-muted-foreground">總成本</div>
                        <div className="font-semibold">{formatCurrency(portfolio.total_cost)}</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">當前價格</div>
                        <div className="font-semibold">
                          {portfolio.current_price ? formatCurrency(portfolio.current_price) : '-'}
                        </div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">當前市值</div>
                        <div className="font-semibold">
                          {portfolio.current_value ? formatCurrency(portfolio.current_value) : '-'}
                        </div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">未實現盈虧</div>
                        <div className={`font-semibold ${isProfitable ? 'text-green-600' : 'text-red-600'}`}>
                          {formatCurrency(profitLoss)}
                        </div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">報酬率</div>
                        <div className={`font-semibold flex items-center gap-1 ${isProfitable ? 'text-green-600' : 'text-red-600'}`}>
                          {isProfitable ? (
                            <TrendingUp className="w-3 h-3" />
                          ) : (
                            <TrendingDown className="w-3 h-3" />
                          )}
                          {formatPercent(profitLossPercent)}
                        </div>
                      </div>
                    </div>
                    <div className="mt-4 flex gap-2">
                      <Button variant="outline" size="sm" asChild>
                        <Link href={`/dashboard?stock=${portfolio.stock_id}&source=portfolio`}>
                          查看圖表
                        </Link>
                      </Button>
                      <Button variant="outline" size="sm">
                        交易記錄
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}

        {/* 交易 Modal */}
        <TransactionModal
          isOpen={transactionModal.isOpen}
          onClose={() => setTransactionModal({ isOpen: false, stock: null, type: 'BUY' })}
          stock={transactionModal.stock}
          transactionType={transactionModal.type}
          onSuccess={() => {
            // 交易成功後重新載入持倉列表
            loadPortfolio();
            setSelectedStock(null);
          }}
        />
      </div>
    </div>
  );
}
