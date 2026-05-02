'use client';

import { useEffect, useState } from 'react';
import { ExternalLink } from 'lucide-react';
import { getMarketNews, getStockNews, NewsArticle } from '@/services/marketInfoApi';

interface MarketNewsPanelProps {
  market?: string;
  symbol?: string;
}

export default function MarketNewsPanel({ market, symbol }: MarketNewsPanelProps) {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const request = market && symbol
      ? getStockNews(market, symbol, 6)
      : getMarketNews(6);

    request
      .then((items) => {
        if (!cancelled) setArticles(items);
      })
      .catch(() => {
        if (!cancelled) setArticles([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [market, symbol]);

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">市場新聞</h3>
        {symbol && <span className="text-xs text-gray-500">{symbol}</span>}
      </div>

      {loading ? (
        <div className="py-6 text-center text-sm text-gray-500">載入中...</div>
      ) : articles.length === 0 ? (
        <div className="rounded-md bg-gray-50 px-3 py-4 text-sm text-gray-500">
          暫無新聞
        </div>
      ) : (
        <div className="space-y-3">
          {articles.slice(0, 5).map((article, index) => (
            <a
              key={article.id || `${article.url}-${index}`}
              href={article.url || '#'}
              target="_blank"
              rel="noreferrer"
              className="block rounded-md border border-gray-100 p-3 hover:bg-gray-50"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="line-clamp-2 text-sm font-medium text-gray-900">
                    {article.headline}
                  </div>
                  <div className="mt-1 text-xs text-gray-500">
                    {article.source || article.provider}
                  </div>
                </div>
                <ExternalLink className="mt-0.5 h-4 w-4 flex-shrink-0 text-gray-400" />
              </div>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
