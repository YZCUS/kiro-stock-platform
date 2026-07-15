import React from "react";
import { render, screen } from "@testing-library/react";

import RealtimeDashboard from "../RealtimeDashboard";

const mockDispatch = jest.fn();

interface MockState {
  auth: {
    isAuthenticated: boolean;
  };
  stockList: {
    lists: never[];
    currentListStocks: never[];
    loading: boolean;
    error: string | null;
  };
}

let mockState: MockState;

jest.mock("@/store", () => ({
  useAppDispatch: () => mockDispatch,
  useAppSelector: <T,>(selector: (state: MockState) => T) =>
    selector(mockState),
}));

jest.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
}));

jest.mock("next/dynamic", () => () => () => null);

jest.mock("@/services/marketInfoApi", () => ({
  getStockQuote: jest.fn(),
  searchMarketSymbols: jest.fn(),
}));

jest.mock("@/services/portfolioApi", () => ({
  getPortfolioList: jest.fn(),
}));

jest.mock("@/components/Market/MarketNewsPanel", () => () => null);
jest.mock("../../Portfolio/TransactionModal", () => () => null);

const createState = (
  overrides: Partial<MockState["stockList"]> = {},
): MockState => ({
  auth: {
    isAuthenticated: false,
  },
  stockList: {
    lists: [],
    currentListStocks: [],
    loading: false,
    error: null,
    ...overrides,
  },
});

describe("RealtimeDashboard workspace layout", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockState = createState();
  });

  it("keeps search and the watchlist before the chart workspace in source order", () => {
    render(<RealtimeDashboard />);

    const search = screen.getByRole("search");
    const watchlist = screen.getByRole("complementary", {
      name: "研究標的清單",
    });
    const chartWorkspace = screen
      .getByRole("heading", { name: "選擇一檔標的開始研究" })
      .closest("section");

    expect(screen.getByLabelText("股票代號")).toBeVisible();
    expect(search).not.toHaveClass("xl:hidden");
    expect(
      search.compareDocumentPosition(watchlist) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(chartWorkspace).not.toBeNull();
    expect(
      watchlist.compareDocumentPosition(chartWorkspace as HTMLElement) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it("shows a list failure without also presenting it as an empty watchlist", () => {
    mockState = createState({ error: "無法載入觀察清單" });

    render(<RealtimeDashboard />);

    expect(screen.getByRole("alert")).toHaveTextContent("無法載入觀察清單");
    expect(screen.queryByText("尚無可研究標的")).not.toBeInTheDocument();
  });
});
