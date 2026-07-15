"use client";

import { useEffect, useId, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, RefreshCw, Search, X } from "lucide-react";
import {
  searchMarketSymbols,
  MarketSearchResult,
} from "@/services/marketInfoApi";
import { Button } from "@/components/ui/button";
import { useDialogA11y } from "@/hooks/useDialogA11y";

export default function MarketSearchCommand() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<MarketSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryRevision, setRetryRevision] = useState(0);
  const dialogTitleId = useId();
  const dialogRef = useDialogA11y(open, () => setOpen(false));

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen(true);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    if (!open) return;
    const trimmed = query.trim();
    if (!trimmed) {
      setResults([]);
      setError(null);
      setLoading(false);
      return;
    }

    let cancelled = false;
    const timer = window.setTimeout(async () => {
      setLoading(true);
      setError(null);
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
          setError("搜尋服務暫時無法使用，請稍後再試。");
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
  }, [open, query, retryRevision]);

  const groupedResults = useMemo(() => {
    return results.slice(0, 8);
  }, [results]);

  const selectResult = (result: MarketSearchResult) => {
    setOpen(false);
    setQuery("");
    if (result.stock_id) {
      const params = new URLSearchParams({
        stock: String(result.stock_id),
        symbol: result.symbol,
        market: result.market,
      });
      if (result.name) {
        params.set("name", result.name);
      }
      router.push(`/dashboard?${params.toString()}`);
      return;
    }
    const params = new URLSearchParams({
      symbol: result.symbol,
      market: result.market,
    });
    if (result.name) {
      params.set("name", result.name);
    }
    router.push(`/dashboard?${params.toString()}`);
  };

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setOpen(true)}
        aria-label="搜尋股票"
        aria-haspopup="dialog"
        aria-expanded={open}
        className="inline-flex h-9 w-9 justify-center px-0 text-muted-foreground sm:w-auto sm:min-w-44 sm:justify-between sm:px-3"
      >
        <span className="flex items-center gap-2">
          <Search className="h-4 w-4" />
          <span className="hidden sm:inline">搜尋股票</span>
        </span>
        <span className="hidden rounded border border-border px-1.5 text-xs xl:inline">
          ⌘K
        </span>
      </Button>

      {open && (
        <div
          className="fixed inset-0 z-[80] bg-slate-950/45 p-4 backdrop-blur-[1px]"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setOpen(false);
          }}
        >
          <div
            ref={dialogRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby={dialogTitleId}
            tabIndex={-1}
            className="mx-auto mt-20 w-full max-w-xl overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl outline-none"
          >
            <h2 id={dialogTitleId} className="sr-only">
              搜尋股票
            </h2>
            <div className="flex items-center border-b border-gray-200 px-4">
              <Search className="h-4 w-4 text-gray-400" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="輸入股票代號或公司名稱"
                aria-label="股票代號或公司名稱"
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

            <div className="max-h-96 overflow-y-auto p-2" aria-live="polite">
              {loading && (
                <div className="px-3 py-6 text-center text-sm text-gray-500">
                  搜尋中...
                </div>
              )}

              {!loading && error && (
                <div
                  className="m-1 rounded-lg border border-destructive/20 bg-destructive/5 px-4 py-5 text-center"
                  role="alert"
                >
                  <AlertCircle className="mx-auto h-5 w-5 text-destructive" />
                  <p className="mt-2 text-sm text-destructive">{error}</p>
                  <Button
                    size="sm"
                    variant="outline"
                    className="mt-3"
                    onClick={() => setRetryRevision((revision) => revision + 1)}
                  >
                    <RefreshCw className="h-4 w-4" />
                    重新搜尋
                  </Button>
                </div>
              )}

              {!loading &&
                !error &&
                groupedResults.map((result) => (
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
                        {result.name ||
                          result.tradingview_symbol ||
                          result.market}
                      </span>
                    </span>
                    <span className="ml-3 rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-600">
                      {result.is_local ? result.market : result.provider}
                    </span>
                  </button>
                ))}

              {!loading &&
                !error &&
                query.trim() &&
                groupedResults.length === 0 && (
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
