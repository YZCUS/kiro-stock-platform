'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Search, X } from 'lucide-react';
import { searchMarketSymbols, MarketSearchResult } from '@/services/marketInfoApi';
import { Button } from '@/components/ui/button';

export default function MarketSearchCommand() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<MarketSearchResult[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setOpen(true);
      }
      if (event.key === 'Escape') {
        setOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  useEffect(() => {
    if (!open) return;
    const trimmed = query.trim();
    if (!trimmed) {
      setResults([]);
      return;
    }

    let cancelled = false;
    const timer = window.setTimeout(async () => {
      setLoading(true);
      try {
        const data = await searchMarketSymbols({
          q: trimmed,
          include_external: true,
          limit: 8,
        });
        if (!cancelled) {
          setResults(data);
        }
      } catch {
        if (!cancelled) {
          setResults([]);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }, 250);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [open, query]);

  const groupedResults = useMemo(() => {
    return results.slice(0, 8);
  }, [results]);

  const selectResult = (result: MarketSearchResult) => {
    setOpen(false);
    setQuery('');
    if (result.stock_id) {
      const params = new URLSearchParams({
        stock: String(result.stock_id),
        symbol: result.symbol,
        market: result.market,
      });
      if (result.name) {
        params.set('name', result.name);
      }
      router.push(`/dashboard?${params.toString()}`);
      return;
    }
    const params = new URLSearchParams({
      symbol: result.symbol,
      market: result.market,
    });
    if (result.name) {
      params.set('name', result.name);
    }
    router.push(`/dashboard?${params.toString()}`);
  };

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setOpen(true)}
        className="hidden min-w-44 justify-between text-gray-500 xl:inline-flex"
      >
        <span className="flex items-center gap-2">
          <Search className="h-4 w-4" />
          搜尋股票
        </span>
        <span className="rounded border border-gray-200 px-1.5 text-xs">⌘K</span>
      </Button>

      {open && (
        <div className="fixed inset-0 z-[80] bg-black/40 p-4">
          <div className="mx-auto mt-20 w-full max-w-xl overflow-hidden rounded-lg bg-white shadow-xl">
            <div className="flex items-center border-b border-gray-200 px-4">
              <Search className="h-4 w-4 text-gray-400" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                autoFocus
                placeholder="輸入股票代號或公司名稱"
                className="h-12 min-w-0 flex-1 border-0 px-3 text-sm outline-none"
              />
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setOpen(false)}
                aria-label="關閉搜尋"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            <div className="max-h-96 overflow-y-auto p-2">
              {loading && (
                <div className="px-3 py-6 text-center text-sm text-gray-500">
                  搜尋中...
                </div>
              )}

              {!loading && groupedResults.map((result) => (
                <button
                  key={`${result.provider}-${result.market}-${result.symbol}`}
                  onClick={() => selectResult(result)}
                  className="flex w-full items-center justify-between rounded-md px-3 py-3 text-left hover:bg-gray-50"
                >
                  <span className="min-w-0">
                    <span className="block text-sm font-semibold text-gray-900">
                      {result.symbol}
                    </span>
                    <span className="block truncate text-xs text-gray-500">
                      {result.name || result.tradingview_symbol || result.market}
                    </span>
                  </span>
                  <span className="ml-3 rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-600">
                    {result.is_local ? result.market : result.provider}
                  </span>
                </button>
              ))}

              {!loading && query.trim() && groupedResults.length === 0 && (
                <div className="px-3 py-6 text-center text-sm text-gray-500">
                  找不到結果
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
