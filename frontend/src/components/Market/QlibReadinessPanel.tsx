'use client';

import { useEffect, useState } from 'react';
import { Activity, BrainCircuit, CheckCircle2 } from 'lucide-react';
import { getQlibReadiness, QlibReadiness } from '@/services/qlibApi';

interface QlibReadinessPanelProps {
  market: 'US' | 'TW';
}

export default function QlibReadinessPanel({ market }: QlibReadinessPanelProps) {
  const [readiness, setReadiness] = useState<QlibReadiness | null>(null);

  useEffect(() => {
    let cancelled = false;
    getQlibReadiness({
      market,
      min_stocks: market === 'US' ? 200 : 100,
      min_bars: 504,
    })
      .then((data) => {
        if (!cancelled) setReadiness(data);
      })
      .catch(() => {
        if (!cancelled) setReadiness(null);
      });
    return () => {
      cancelled = true;
    };
  }, [market]);

  if (!readiness) {
    return null;
  }

  const coverage = readiness.coverage;
  const requiredStocks = market === 'US' ? 200 : 100;
  const collectedStocks = coverage.stocks_with_daily_bars;
  const coveragePercent = Math.min(100, Math.round((collectedStocks / requiredStocks) * 100));

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BrainCircuit className="h-4 w-4 text-gray-500" />
          <h3 className="text-sm font-semibold text-gray-900">AI 預測狀態</h3>
        </div>
        <span
          className={`rounded-full px-2 py-1 text-xs font-medium ${
            readiness.ready
              ? 'bg-green-50 text-green-700'
              : 'bg-amber-50 text-amber-700'
          }`}
        >
          {readiness.ready ? '可用' : '準備中'}
        </span>
      </div>

      {readiness.ready ? (
        <div className="flex gap-2 rounded-md bg-green-50 px-3 py-2 text-xs text-green-800">
          <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
          <span>此市場已有足夠歷史資料，可顯示 Qlib AI 預測信號。</span>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-sm leading-6 text-gray-600">
            暫不顯示 AI 預測。系統需要累積更多同市場股票資料，才會啟用模型排名結果。
          </p>
          <div>
            <div className="mb-1 flex items-center justify-between text-xs text-gray-500">
              <span>股票池資料</span>
              <span>{collectedStocks}/{requiredStocks} 檔</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-gray-100">
              <div
                className="h-full rounded-full bg-amber-400"
                style={{ width: `${coveragePercent}%` }}
              />
            </div>
          </div>
          {readiness.issues.length > 0 && (
            <div className="flex gap-2 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-800">
              <Activity className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
              <span>每日資料預載完成後會自動更新，不需要使用者手動處理。</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
