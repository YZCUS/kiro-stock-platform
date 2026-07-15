import {
  aggregatePortfolioByMarket,
  currencyForMarket,
  formatLocalDateInput,
  inferMarketFromSymbol,
} from "@/lib/finance";

describe("finance helpers", () => {
  it("infers the market and currency from a symbol", () => {
    expect(inferMarketFromSymbol("2330.TW")).toBe("TW");
    expect(inferMarketFromSymbol("8069.TWO")).toBe("TW");
    expect(inferMarketFromSymbol("0050")).toBe("TW");
    expect(inferMarketFromSymbol("AAPL")).toBe("US");
    expect(currencyForMarket("TW")).toBe("TWD");
    expect(currencyForMarket("US")).toBe("USD");
  });

  it("uses the local calendar date instead of the UTC date", () => {
    expect(formatLocalDateInput(new Date(2026, 0, 2, 23, 30))).toBe(
      "2026-01-02",
    );
  });

  it("keeps Taiwan and US portfolio totals separate", () => {
    expect(
      aggregatePortfolioByMarket([
        {
          stock_symbol: "2330.TW",
          total_cost: 100_000,
          current_value: 110_000,
          profit_loss: 10_000,
        },
        {
          stock_symbol: "AAPL",
          total_cost: 1_000,
          current_value: 900,
          profit_loss: -100,
        },
      ]),
    ).toEqual([
      {
        market: "TW",
        cost: 100_000,
        value: 110_000,
        profitLoss: 10_000,
        profitLossPercent: 10,
        hasCompleteValuation: true,
      },
      {
        market: "US",
        cost: 1_000,
        value: 900,
        profitLoss: -100,
        profitLossPercent: -10,
        hasCompleteValuation: true,
      },
    ]);
  });

  it("marks market totals incomplete when a holding has no current valuation", () => {
    expect(
      aggregatePortfolioByMarket([
        { stock_symbol: "AAPL", total_cost: 1_000, current_value: null },
      ]),
    ).toEqual([
      {
        market: "US",
        cost: 1_000,
        value: 0,
        profitLoss: 0,
        profitLossPercent: 0,
        hasCompleteValuation: false,
      },
    ]);
  });
});
