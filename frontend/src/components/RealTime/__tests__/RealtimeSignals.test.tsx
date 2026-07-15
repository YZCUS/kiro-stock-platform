import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import RealtimeSignals from "../RealtimeSignals";
import { useSystemNotifications } from "@/hooks/useWebSocket";
import { useMarketStream } from "@/hooks/useMarketStream";
import { getSignals } from "@/services/strategyApi";
import type { TradingSignal } from "@/types/strategy";

jest.mock("@/hooks/useWebSocket", () => ({
  useSystemNotifications: jest.fn(),
}));

jest.mock("@/hooks/useMarketStream", () => ({
  useMarketStream: jest.fn(),
}));

jest.mock("@/services/strategyApi", () => ({
  getSignals: jest.fn(),
}));

const mockUseSystemNotifications =
  useSystemNotifications as jest.MockedFunction<typeof useSystemNotifications>;
const mockUseMarketStream = useMarketStream as jest.MockedFunction<
  typeof useMarketStream
>;
const mockGetSignals = getSignals as jest.MockedFunction<typeof getSignals>;

const signal: TradingSignal = {
  id: 11,
  stock_id: 1,
  strategy_type: "momentum",
  strategy_name: "Momentum Breakout",
  direction: "LONG",
  confidence: 0.82,
  stop_loss: 180,
  status: "active",
  signal_date: "2026-07-15T10:00:00Z",
  created_at: "2026-07-15T10:00:00Z",
};

describe("RealtimeSignals", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseSystemNotifications.mockReturnValue({
      notifications: [],
      clearNotification: jest.fn(),
      clearAllNotifications: jest.fn(),
    });
    mockUseMarketStream.mockReturnValue({
      quote: null,
      bar: null,
      signal: null,
      status: "connected",
      error: null,
    });
  });

  it("shows a strategy API failure separately from an empty result and retries", async () => {
    mockGetSignals
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce({ signals: [signal], total: 1 });

    render(<RealtimeSignals stockId={1} symbol="AAPL" market="US" />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "無法取得策略信號",
    );
    expect(screen.queryByText("目前沒有活躍策略信號")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "重新載入" }));

    expect(await screen.findByText("Momentum Breakout")).toBeVisible();
    expect(mockGetSignals).toHaveBeenCalledTimes(2);
  });

  it("shows the empty state after a successful request with no signals", async () => {
    mockGetSignals.mockResolvedValueOnce({ signals: [], total: 0 });

    render(<RealtimeSignals stockId={1} symbol="AAPL" market="US" />);

    expect(await screen.findByText("目前沒有活躍策略信號")).toBeVisible();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
