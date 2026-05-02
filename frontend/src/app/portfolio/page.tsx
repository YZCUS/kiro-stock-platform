'use client';

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { useRouter } from 'next/navigation';
import { useAppSelector, useAppDispatch } from '@/store';
import { fetchPortfolioList, fetchPortfolioSummary, removePortfolio } from '@/store/slices/portfolioSlice';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { MetricCard, PageHeader, PageShell } from '@/components/ui/page';
import Link from 'next/link';
import { TrendingUp, TrendingDown, Trash2, ShoppingCart } from 'lucide-react';
import type { Portfolio, Stock } from '@/types';

// 動態載入 TransactionModal（僅在需要時載入）
const TransactionModal = dynamic(
  () => import('@/components/Portfolio/TransactionModal'),
  {
    ssr: false,
    loading: () => null, // 模態框不需要loading state
  }
);

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
  const [transactionModal, setTransactionModal] = useState<{
    isOpen: boolean;
    stock: any | null;
    type: 'BUY' | 'SELL';
  }>({
    isOpen: false,
    stock: null,
    type: 'BUY'
  });

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

  const inferMarket = (symbol?: string): 'TW' | 'US' => {
    if (!symbol) {
      return 'US';
    }

    return symbol.endsWith('.TW') || /^\d+$/.test(symbol) ? 'TW' : 'US';
  };

  const toTransactionStock = (portfolio: Portfolio): Stock => ({
    id: portfolio.stock_id,
    symbol: portfolio.stock_symbol || '',
    name: portfolio.stock_name || portfolio.stock_symbol || null,
    market: inferMarket(portfolio.stock_symbol),
    is_active: true,
    created_at: portfolio.created_at,
    updated_at: portfolio.updated_at,
    latest_price: portfolio.current_price
      ? {
          close: portfolio.current_price,
          change: 0,
          change_percent: 0,
          date: new Date().toISOString().split('T')[0],
          volume: 0,
        }
      : null,
  });

  // 在客戶端渲染前顯示 loading 狀態，避免 hydration 錯誤
  if (!isMounted) {
    return (
      <PageShell className="max-w-6xl">
          <PageHeader title="持倉管理" />
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
      </PageShell>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <PageShell className="max-w-6xl">
        <PageHeader
          title="持倉管理"
          description="查看您的投資組合，追蹤盈虧表現。"
        />

        {/* Summary Cards */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
          <MetricCard label="總成本" value={formatCurrency(totalCost)} />
          <MetricCard label="當前市值" value={formatCurrency(totalCurrentValue)} />
          <MetricCard
            label="總盈虧"
            value={formatCurrency(totalProfitLoss)}
            tone={totalProfitLoss >= 0 ? 'green' : 'red'}
          />
          <MetricCard
            label="報酬率"
            value={formatPercent(totalProfitLossPercent)}
            icon={totalProfitLossPercent >= 0 ? TrendingUp : TrendingDown}
            tone={totalProfitLossPercent >= 0 ? 'green' : 'red'}
          />
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
                <Link href="/stocks">前往股票列表選擇標的</Link>
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
                    <div className="mt-4 flex flex-wrap gap-2">
                      <Button
                        variant="success"
                        size="sm"
                        onClick={() => setTransactionModal({
                          isOpen: true,
                          stock: toTransactionStock(portfolio),
                          type: 'BUY'
                        })}
                      >
                        <ShoppingCart className="w-4 h-4 mr-2" />
                        加倉
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => setTransactionModal({
                          isOpen: true,
                          stock: toTransactionStock(portfolio),
                          type: 'SELL'
                        })}
                      >
                        <TrendingDown className="w-4 h-4 mr-2" />
                        減倉
                      </Button>
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
          }}
        />
    </PageShell>
  );
}
