/**
 * 即時交易信號組件
 */
"use client";

import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { AlertCircle, RefreshCw, X } from "lucide-react";
import { useSystemNotifications } from "../../hooks/useWebSocket";
import { useMarketStream } from "../../hooks/useMarketStream";
import { getSignals } from "@/services/strategyApi";
import type { TradingSignal } from "@/types/strategy";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface RealtimeSignalsProps {
  stockId?: number | null;
  symbol?: string;
  market?: string;
  enabled?: boolean;
}

function RealtimeSignals({
  stockId,
  symbol,
  market,
  enabled = true,
}: RealtimeSignalsProps) {
  const { notifications, clearNotification, clearAllNotifications } =
    useSystemNotifications();
  const {
    signal: intradaySignal,
    status: streamStatus,
    error: streamError,
  } = useMarketStream(market, symbol, enabled && Boolean(market && symbol));
  const [signals, setSignals] = useState<TradingSignal[]>([]);
  const [intradaySignals, setIntradaySignals] = useState<TradingSignal[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [requestVersion, setRequestVersion] = useState(0);

  const formatTime = (dateString: string | Date | null | undefined) => {
    if (!dateString) return "-";
    const date =
      typeof dateString === "string" ? new Date(dateString) : dateString;
    return date.toLocaleTimeString("zh-TW", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  const formatDate = (dateString?: string | null) => {
    if (!dateString) return "-";
    return new Date(dateString).toLocaleDateString("zh-TW");
  };

  const formatPrice = (value?: number | null) =>
    typeof value === "number" && Number.isFinite(value)
      ? `${market === "TW" ? "NT$" : "$"}${value.toFixed(2)}`
      : "-";

  const formatConfidence = (value: number) => {
    const percent = value <= 1 ? value * 100 : value;
    return `${percent.toFixed(1)}%`;
  };

  const getDirectionVariant = (direction: TradingSignal["direction"]) => {
    switch (direction) {
      case "LONG":
        return "success" as const;
      case "SHORT":
        return "destructive" as const;
      default:
        return "secondary" as const;
    }
  };

  const getDirectionText = (direction: TradingSignal["direction"]) => {
    switch (direction) {
      case "LONG":
        return "看多";
      case "SHORT":
        return "看空";
      default:
        return "中性";
    }
  };

  useEffect(() => {
    let cancelled = false;

    if (!enabled || !stockId) {
      setSignals([]);
      setLoading(false);
      setError(null);
      return;
    }

    setSignals([]);
    setLoading(true);
    setError(null);
    getSignals({
      status: "active",
      stock_id: stockId,
      sort_by: "signal_date",
      sort_order: "desc",
      limit: 5,
    })
      .then((response) => {
        if (!cancelled) setSignals(response.signals);
      })
      .catch(() => {
        if (!cancelled) {
          setSignals([]);
          setError("無法取得策略信號，請稍後重試。");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [enabled, requestVersion, stockId]);

  useEffect(() => {
    setIntradaySignals([]);
  }, [market, stockId, symbol]);

  useEffect(() => {
    if (!intradaySignal || !stockId || intradaySignal.stock_id !== stockId)
      return;
    setIntradaySignals((current) => {
      if (current.some((signal) => signal.id === intradaySignal.id)) {
        return current;
      }
      return [intradaySignal, ...current].slice(0, 5);
    });
  }, [intradaySignal, stockId]);

  const streamLabel =
    streamStatus === "connected"
      ? "串流中"
      : streamStatus === "connecting"
        ? "連線中"
        : streamStatus === "error" || streamStatus === "disconnected"
          ? "串流中斷"
          : "等待";

  const streamVariant =
    streamStatus === "connected"
      ? "success"
      : streamStatus === "error" || streamStatus === "disconnected"
        ? "destructive"
        : "secondary";

  return (
    <div className="space-y-5">
      {notifications.length > 0 && (
        <Card role="region" aria-labelledby="system-notifications-title">
          <CardHeader className="flex-row items-center justify-between space-y-0 border-b border-border p-4">
            <div>
              <CardTitle id="system-notifications-title" className="text-sm">
                系統通知
              </CardTitle>
              <CardDescription className="mt-1 text-xs">
                最新 {Math.min(notifications.length, 3)} 則平台事件
              </CardDescription>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="xs"
              onClick={clearAllNotifications}
            >
              清除全部
            </Button>
          </CardHeader>
          <CardContent
            className="divide-y divide-border p-0"
            aria-live="polite"
          >
            {notifications.slice(0, 3).map((notification) => (
              <div
                key={notification.id}
                className="flex items-start gap-3 px-4 py-3"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm leading-5 text-foreground">
                    {notification.message}
                  </p>
                  <p className="mt-1 text-xs tabular-nums text-muted-foreground">
                    {formatTime(notification.timestamp)}
                  </p>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="iconSm"
                  onClick={() => clearNotification(notification.id)}
                  aria-label={`清除通知：${notification.message}`}
                >
                  <X aria-hidden="true" />
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <Card role="region" aria-labelledby="intraday-signals-title">
        <CardHeader className="flex-row items-start justify-between space-y-0 border-b border-border p-4">
          <div>
            <CardTitle id="intraday-signals-title" className="text-sm">
              日內即時信號
            </CardTitle>
            <CardDescription className="mt-1 text-xs leading-5">
              由 5 分鐘 K 線串流產生，供短線觀察
            </CardDescription>
          </div>
          <Badge
            variant={streamVariant}
            role="status"
            aria-label={`即時串流狀態：${streamLabel}`}
          >
            {streamLabel}
          </Badge>
        </CardHeader>

        <CardContent className="p-0">
          {!enabled ? (
            <PanelState>登入後顯示日內信號</PanelState>
          ) : !stockId ? (
            <PanelState>選擇股票後顯示日內信號</PanelState>
          ) : streamError ? (
            <div
              className="flex items-start gap-2 px-4 py-5 text-sm text-destructive"
              role="alert"
            >
              <AlertCircle
                className="mt-0.5 h-4 w-4 shrink-0"
                aria-hidden="true"
              />
              <span>即時串流暫時中斷，系統會自動重新連線。</span>
            </div>
          ) : intradaySignals.length === 0 ? (
            <PanelState role="status">等待新的 5 分鐘信號</PanelState>
          ) : (
            <div className="divide-y divide-border">
              {intradaySignals.map((signal) => (
                <SignalRow
                  key={signal.id}
                  signal={signal}
                  getDirectionVariant={getDirectionVariant}
                  getDirectionText={getDirectionText}
                  formatConfidence={formatConfidence}
                  formatDate={formatDate}
                  formatPrice={formatPrice}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card role="region" aria-labelledby="strategy-signals-title">
        <CardHeader className="border-b border-border p-4">
          <CardTitle id="strategy-signals-title" className="text-sm">
            策略交易信號
          </CardTitle>
          <CardDescription className="text-xs leading-5">
            {symbol ? `${symbol} 的活躍策略信號` : "隨訂閱策略與排程更新"}
          </CardDescription>
        </CardHeader>

        <CardContent className="p-0" aria-live="polite">
          {!enabled ? (
            <PanelState>登入後顯示策略信號</PanelState>
          ) : !stockId ? (
            <PanelState>選擇股票後顯示策略信號</PanelState>
          ) : loading ? (
            <PanelState role="status">載入策略信號中</PanelState>
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
          ) : signals.length === 0 ? (
            <PanelState>目前沒有活躍策略信號</PanelState>
          ) : (
            <>
              <div className="divide-y divide-border">
                {signals.map((signal) => (
                  <SignalRow
                    key={signal.id}
                    signal={signal}
                    getDirectionVariant={getDirectionVariant}
                    getDirectionText={getDirectionText}
                    formatConfidence={formatConfidence}
                    formatDate={formatDate}
                    formatPrice={formatPrice}
                  />
                ))}
              </div>
              <p className="border-t border-border px-4 py-3 text-xs leading-5 text-muted-foreground">
                信號由策略訂閱、手動刷新或排程產生，不是每筆報價即時計算。
              </p>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

interface PanelStateProps {
  children: ReactNode;
  role?: "status";
}

function PanelState({ children, role }: PanelStateProps) {
  return (
    <div
      className="px-4 py-8 text-center text-sm text-muted-foreground"
      role={role}
    >
      {children}
    </div>
  );
}

interface SignalRowProps {
  signal: TradingSignal;
  getDirectionVariant: (
    direction: TradingSignal["direction"],
  ) => "success" | "destructive" | "secondary";
  getDirectionText: (direction: TradingSignal["direction"]) => string;
  formatConfidence: (value: number) => string;
  formatDate: (dateString?: string | null) => string;
  formatPrice: (value?: number | null) => string;
}

function SignalRow({
  signal,
  getDirectionVariant,
  getDirectionText,
  formatConfidence,
  formatDate,
  formatPrice,
}: SignalRowProps) {
  return (
    <article className="px-4 py-3.5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={getDirectionVariant(signal.direction)}>
              {getDirectionText(signal.direction)}
            </Badge>
            {signal.signal_horizon && (
              <Badge variant="outline">{signal.signal_horizon}</Badge>
            )}
          </div>
          <p className="mt-2 truncate text-sm font-semibold text-foreground">
            {signal.strategy_name || signal.strategy_type}
          </p>
          <p className="mt-1 text-xs tabular-nums text-muted-foreground">
            {formatDate(signal.signal_date)} 至 {formatDate(signal.valid_until)}
          </p>
        </div>
        <div className="shrink-0 text-right tabular-nums">
          <p className="text-xs text-muted-foreground">信心度</p>
          <p className="mt-0.5 text-sm font-semibold text-foreground">
            {formatConfidence(signal.confidence)}
          </p>
        </div>
      </div>

      <dl className="mt-3 grid grid-cols-2 gap-3 text-xs">
        <div>
          <dt className="text-muted-foreground">進場</dt>
          <dd className="mt-0.5 font-medium tabular-nums text-foreground">
            {formatPrice(signal.entry_zone?.min ?? signal.entry_min)}
          </dd>
        </div>
        <div>
          <dt className="text-muted-foreground">停損</dt>
          <dd className="mt-0.5 font-medium tabular-nums text-destructive">
            {formatPrice(signal.stop_loss)}
          </dd>
        </div>
      </dl>

      {signal.reason && (
        <p className="mt-3 text-xs leading-5 text-muted-foreground">
          {signal.reason}
        </p>
      )}
    </article>
  );
}

export default RealtimeSignals;
