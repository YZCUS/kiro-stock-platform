'use client';

import { useEffect, useMemo, useRef } from 'react';

interface TradingViewSymbolWidgetProps {
  symbol: string;
  height?: number;
}

function toTradingViewSymbol(symbol: string): string {
  const upper = symbol.toUpperCase();
  if (upper.endsWith('.TW')) {
    return `TWSE:${upper.replace('.TW', '')}`;
  }
  if (upper.endsWith('.TWO')) {
    return `TPEX:${upper.replace('.TWO', '')}`;
  }
  return upper;
}

export default function TradingViewSymbolWidget({
  symbol,
  height = 420,
}: TradingViewSymbolWidgetProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const tvSymbol = useMemo(() => toTradingViewSymbol(symbol), [symbol]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || !tvSymbol) return;

    container.innerHTML = '';
    const widgetHost = document.createElement('div');
    widgetHost.className = 'tradingview-widget-container__widget';
    container.appendChild(widgetHost);

    const script = document.createElement('script');
    script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
    script.async = true;
    script.innerHTML = JSON.stringify({
      autosize: true,
      symbol: tvSymbol,
      interval: 'D',
      timezone: 'Etc/UTC',
      theme: 'light',
      style: '1',
      locale: 'zh_TW',
      enable_publishing: false,
      hide_top_toolbar: false,
      hide_legend: false,
      save_image: false,
      calendar: false,
      support_host: 'https://www.tradingview.com',
    });
    container.appendChild(script);

    return () => {
      container.innerHTML = '';
    };
  }, [tvSymbol]);

  return (
    <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
      <div
        ref={containerRef}
        className="tradingview-widget-container"
        style={{ height }}
      />
    </div>
  );
}
