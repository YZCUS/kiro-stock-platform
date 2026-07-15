export type SupportedMarket = "TW" | "US";

export interface PortfolioValue {
  stock_symbol?: string;
  total_cost: number;
  current_value?: number | null;
  profit_loss?: number | null;
}

export interface MarketPortfolioTotal {
  market: SupportedMarket;
  cost: number;
  value: number;
  profitLoss: number;
  profitLossPercent: number;
  hasCompleteValuation: boolean;
}

export function inferMarketFromSymbol(symbol?: string): SupportedMarket {
  if (!symbol) return "US";
  const normalized = symbol.trim().toUpperCase();
  return normalized.endsWith(".TW") ||
    normalized.endsWith(".TWO") ||
    /^\d+$/.test(normalized)
    ? "TW"
    : "US";
}

export function currencyForMarket(market: SupportedMarket): "TWD" | "USD" {
  return market === "TW" ? "TWD" : "USD";
}

export function formatMarketCurrency(
  amount: number,
  market: SupportedMarket,
): string {
  return new Intl.NumberFormat("zh-TW", {
    style: "currency",
    currency: currencyForMarket(market),
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

export function formatLocalDateInput(date = new Date()): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function aggregatePortfolioByMarket(
  portfolios: PortfolioValue[],
): MarketPortfolioTotal[] {
  const totals = new Map<
    SupportedMarket,
    Omit<MarketPortfolioTotal, "market" | "profitLossPercent">
  >();

  portfolios.forEach((portfolio) => {
    const market = inferMarketFromSymbol(portfolio.stock_symbol);
    const current = totals.get(market) ?? {
      cost: 0,
      value: 0,
      profitLoss: 0,
      hasCompleteValuation: true,
    };
    const hasValuation = portfolio.current_value != null;
    const value = portfolio.current_value ?? 0;
    const profitLoss =
      portfolio.profit_loss ??
      (hasValuation ? value - portfolio.total_cost : 0);

    totals.set(market, {
      cost: current.cost + portfolio.total_cost,
      value: current.value + value,
      profitLoss: current.profitLoss + profitLoss,
      hasCompleteValuation: current.hasCompleteValuation && hasValuation,
    });
  });

  return (["TW", "US"] as const)
    .filter((market) => totals.has(market))
    .map((market) => {
      const total = totals.get(market)!;
      return {
        market,
        ...total,
        profitLossPercent:
          total.cost === 0 ? 0 : (total.profitLoss / total.cost) * 100,
      };
    });
}
