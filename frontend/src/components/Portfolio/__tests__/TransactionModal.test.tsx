import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Provider } from "react-redux";

import TransactionModal from "@/components/Portfolio/TransactionModal";
import portfolioApi from "@/services/portfolioApi";
import { makeStore } from "@/store";
import type { Stock } from "@/types";

jest.mock("@/services/portfolioApi", () => ({
  __esModule: true,
  default: {
    getPortfolioList: jest.fn(),
    createTransaction: jest.fn(),
  },
}));

const mockGetPortfolioList = jest.mocked(portfolioApi.getPortfolioList);
const mockCreateTransaction = jest.mocked(portfolioApi.createTransaction);

const stock: Stock = {
  id: 1,
  symbol: "AAPL",
  name: "Apple",
  market: "US",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  latest_price: {
    close: 200,
    change: null,
    change_percent: null,
    date: "2026-01-01T00:00:00Z",
    volume: null,
  },
};

const emptyPortfolioResponse = {
  items: [],
  total: 0,
  total_cost: 0,
  total_current_value: 0,
  total_profit_loss: 0,
  total_profit_loss_percent: 0,
};

describe("TransactionModal", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("checks current holdings before claiming a sell is unavailable", async () => {
    let resolvePortfolio!: (value: typeof emptyPortfolioResponse) => void;
    mockGetPortfolioList.mockReturnValue(
      new Promise((resolve) => {
        resolvePortfolio = resolve;
      }),
    );

    render(
      <Provider store={makeStore()}>
        <TransactionModal
          isOpen
          onClose={jest.fn()}
          stock={stock}
          transactionType="SELL"
        />
      </Provider>,
    );

    expect(
      await screen.findByText("正在確認可賣出數量..."),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("您尚未持有 AAPL，請先買入後才能賣出。"),
    ).not.toBeInTheDocument();

    resolvePortfolio(emptyPortfolioResponse);
    expect(
      await screen.findByText("您尚未持有 AAPL，請先買入後才能賣出。"),
    ).toBeInTheDocument();
  });

  it("submits a fractional quantity without truncating it", async () => {
    mockCreateTransaction.mockResolvedValue({
      id: 10,
      user_id: "user-1",
      portfolio_id: 1,
      stock_id: 1,
      stock_symbol: "AAPL",
      transaction_type: "BUY",
      quantity: 1.5,
      price: 200,
      fee: 0,
      tax: 0,
      total: 300,
      transaction_date: "2026-07-15",
      created_at: "2026-07-15T00:00:00Z",
    });
    mockGetPortfolioList.mockResolvedValue(emptyPortfolioResponse);

    render(
      <Provider store={makeStore()}>
        <TransactionModal
          isOpen
          onClose={jest.fn()}
          stock={stock}
          transactionType="BUY"
        />
      </Provider>,
    );

    fireEvent.change(screen.getByLabelText(/數量/), {
      target: { value: "1.5" },
    });
    expect(screen.getByText("US$300.00")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "確認買入" }));

    await waitFor(() => {
      expect(mockCreateTransaction).toHaveBeenCalledWith(
        expect.objectContaining({ quantity: 1.5 }),
      );
    });
  });
});
