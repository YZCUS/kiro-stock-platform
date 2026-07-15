"use client";

import { useEffect, useState } from "react";
import { AlertCircle, ExternalLink, RefreshCw } from "lucide-react";
import {
  getMarketNews,
  getStockNews,
  type NewsArticle,
} from "@/services/marketInfoApi";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface MarketNewsPanelProps {
  market?: string;
  symbol?: string;
}

export default function MarketNewsPanel({
  market,
  symbol,
}: MarketNewsPanelProps) {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [requestVersion, setRequestVersion] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setArticles([]);
    setLoading(true);
    setError(null);
    const request =
      market && symbol ? getStockNews(market, symbol, 6) : getMarketNews(6);

    request
      .then((items) => {
        if (!cancelled) setArticles(items);
      })
      .catch(() => {
        if (!cancelled) {
          setArticles([]);
          setError("無法取得市場新聞，請稍後重試。");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [market, requestVersion, symbol]);

  return (
    <Card role="region" aria-labelledby="market-news-title">
      <CardHeader className="flex-row items-start justify-between space-y-0 border-b border-border p-4">
        <div>
          <CardTitle id="market-news-title" className="text-sm">
            市場新聞
          </CardTitle>
          <CardDescription className="mt-1 text-xs leading-5">
            {symbol ? `${symbol} 的最新市場動態` : "重要市場動態與公司消息"}
          </CardDescription>
        </div>
        {symbol && <Badge variant="outline">{symbol}</Badge>}
      </CardHeader>

      <CardContent className="p-0" aria-live="polite">
        {loading ? (
          <div className="space-y-3 px-4 py-5" role="status">
            <span className="sr-only">載入市場新聞中</span>
            {[0, 1, 2].map((item) => (
              <div key={item} className="animate-pulse" aria-hidden="true">
                <div className="h-3.5 w-full rounded bg-muted" />
                <div className="mt-2 h-3 w-2/5 rounded bg-muted" />
              </div>
            ))}
          </div>
        ) : error ? (
          <div
            className="flex flex-col items-start gap-3 px-4 py-5"
            role="alert"
          >
            <div className="flex items-start gap-2 text-sm text-destructive">
              <AlertCircle
                className="mt-0.5 h-4 w-4 shrink-0"
                aria-hidden="true"
              />
              <span>{error}</span>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setRequestVersion((version) => version + 1)}
            >
              <RefreshCw aria-hidden="true" />
              重新載入
            </Button>
          </div>
        ) : articles.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-muted-foreground">
            目前沒有相關新聞
          </div>
        ) : (
          <div className="divide-y divide-border">
            {articles.slice(0, 5).map((article, index) => (
              <NewsRow
                key={
                  article.id || article.url || `${article.headline}-${index}`
                }
                article={article}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface NewsRowProps {
  article: NewsArticle;
}

function NewsRow({ article }: NewsRowProps) {
  const publishedAt = formatPublishedAt(article.published_at);
  const rowClassName = cn(
    "block px-4 py-3.5 transition-colors",
    article.url &&
      "hover:bg-accent/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring",
  );

  const content = (
    <div className="flex items-start justify-between gap-3">
      <div className="min-w-0">
        <p className="line-clamp-2 text-sm font-medium leading-5 text-foreground">
          {article.headline}
        </p>
        <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
          <span>{article.source || article.provider}</span>
          {publishedAt && (
            <>
              <span aria-hidden="true">·</span>
              <time dateTime={article.published_at || undefined}>
                {publishedAt}
              </time>
            </>
          )}
        </div>
      </div>
      {article.url && (
        <ExternalLink
          className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground"
          aria-hidden="true"
        />
      )}
    </div>
  );

  if (!article.url) {
    return <div className={rowClassName}>{content}</div>;
  }

  return (
    <a
      href={article.url}
      target="_blank"
      rel="noopener noreferrer"
      className={rowClassName}
      aria-label={`${article.headline}（在新分頁開啟）`}
    >
      {content}
    </a>
  );
}

function formatPublishedAt(value?: string | null) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString("zh-TW", {
    month: "numeric",
    day: "numeric",
  });
}
