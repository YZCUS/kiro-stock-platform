'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAppSelector, useAppDispatch } from '@/store';
import { setWatchlistItems, setWatchlistLoading, setWatchlistError, removeWatchlistItem } from '@/store/slices/watchlistSlice';
import { getWatchlistDetailed, removeFromWatchlist } from '@/services/watchlistApi';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import Link from 'next/link';

export default function WatchlistPage() {
  const router = useRouter();
  const dispatch = useAppDispatch();
  const { isAuthenticated, token } = useAppSelector((state) => state.auth);
  const { items, loading, error } = useAppSelector((state) => state.watchlist);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }

    loadWatchlist();
  }, [isAuthenticated]);

  const loadWatchlist = async () => {
    if (!token) return;

    dispatch(setWatchlistLoading(true));
    try {
      const data = await getWatchlistDetailed(token);
      dispatch(setWatchlistItems(data));
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || '載入自選股失敗';
      dispatch(setWatchlistError(errorMsg));
    }
  };

  const handleRemove = async (stockId: number, watchlistId: number) => {
    if (!token) return;

    try {
      await removeFromWatchlist(stockId, token);
      dispatch(removeWatchlistItem(watchlistId));
    } catch (err: any) {
      alert('移除失敗：' + (err.response?.data?.detail || '未知錯誤'));
    }
  };

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">我的自選股</h1>
          <p className="text-muted-foreground">
            管理您的自選股票清單，追蹤市場動態
          </p>
        </div>

        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {loading ? (
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
        ) : items.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <p className="text-muted-foreground mb-4">您還沒有加入任何自選股</p>
              <Button asChild>
                <Link href="/stocks">瀏覽股票</Link>
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {items.map((item) => (
              <Card key={item.watchlist_id} className="hover:shadow-md transition-shadow">
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <CardTitle className="flex items-center gap-2">
                        {item.stock.symbol}
                        <Badge variant={item.stock.market === 'TW' ? 'default' : 'secondary'}>
                          {item.stock.market}
                        </Badge>
                      </CardTitle>
                      <CardDescription>{item.stock.name}</CardDescription>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRemove(item.stock.id, item.watchlist_id)}
                    >
                      移除
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    {item.latest_price && (
                      <>
                        <div>
                          <div className="text-muted-foreground">最新價格</div>
                          <div className="font-semibold">${item.latest_price.close}</div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">成交量</div>
                          <div className="font-semibold">{item.latest_price.volume?.toLocaleString()}</div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">最高價</div>
                          <div className="font-semibold">${item.latest_price.high}</div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">最低價</div>
                          <div className="font-semibold">${item.latest_price.low}</div>
                        </div>
                      </>
                    )}
                  </div>
                  <div className="mt-4 text-xs text-muted-foreground">
                    加入時間：{new Date(item.added_at).toLocaleString('zh-TW')}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
