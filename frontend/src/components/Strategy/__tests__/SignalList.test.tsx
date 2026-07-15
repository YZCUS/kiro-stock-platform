import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { makeStore } from "@/store";
import * as strategyApi from "@/services/strategyApi";
import StocksApiService from "@/services/stocksApi";
import type { TradingSignal } from "@/types/strategy";
import SignalList from "../SignalList";

jest.mock("@/services/strategyApi");

const signal: TradingSignal = {
  id: 1,
  stock_id: 10,
  stock_symbol: "AAPL",
  stock_name: "Apple Inc.",
  strategy_type: "momentum",
  strategy_name: "動能策略",
  signal_horizon: "1d",
  direction: "LONG",
  confidence: 82,
  entry_min: 190,
  entry_max: 195,
  stop_loss: 180,
  take_profit: [205],
  status: "active",
  signal_date: "2026-07-15T12:00:00Z",
  valid_until: "2099-07-20T12:00:00Z",
  reason: "動能轉強",
  created_at: "2026-07-15T12:00:00Z",
};

const renderSignalList = () => {
  const store = makeStore();
  return render(
    <Provider store={store}>
      <SignalList />
    </Provider>,
  );
};

describe("SignalList", () => {
  const getSignals = jest.mocked(strategyApi.getSignals);

  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(StocksApiService, "getStockPrices").mockResolvedValue([]);
  });

  it("shows an API error instead of a misleading empty state", async () => {
    getSignals.mockRejectedValue({
      response: { data: { detail: "信號服務暫時不可用" } },
    });

    renderSignalList();

    expect(await screen.findByText("信號服務暫時不可用")).toBeInTheDocument();
    expect(screen.queryByText("目前沒有交易信號")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "重試" })).toBeInTheDocument();
  });

  it("shows a true empty state when the API succeeds with no signals", async () => {
    getSignals.mockResolvedValue({
      signals: [],
      total: 0,
      limit: 100,
      offset: 0,
    });

    renderSignalList();

    expect(await screen.findByText("目前沒有交易信號")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("expands a signal group from the keyboard and exposes its state", async () => {
    const user = userEvent.setup();
    getSignals.mockResolvedValue({
      signals: [signal],
      total: 1,
      limit: 100,
      offset: 0,
    });

    renderSignalList();

    const expansionButton = await screen.findByRole("button", {
      name: "展開 AAPL 信號明細",
    });
    expect(expansionButton).toHaveAttribute("aria-expanded", "false");

    expansionButton.focus();
    await user.keyboard("{Enter}");

    expect(expansionButton).toHaveAttribute("aria-expanded", "true");
    expect(
      screen.getByRole("heading", { name: "信號明細" }),
    ).toBeInTheDocument();
  });

  it("requests the next API page instead of using the capped load-more control", async () => {
    const user = userEvent.setup();
    getSignals.mockResolvedValue({
      signals: [signal],
      total: 101,
      limit: 100,
      offset: 0,
    });

    renderSignalList();

    const nextButton = await screen.findByRole("button", { name: "下一頁" });
    await user.click(nextButton);

    await waitFor(() => {
      expect(getSignals).toHaveBeenLastCalledWith(
        expect.objectContaining({ limit: 100, offset: 100 }),
      );
    });
    expect(
      screen.queryByRole("button", { name: "載入更多" }),
    ).not.toBeInTheDocument();
  });
});
