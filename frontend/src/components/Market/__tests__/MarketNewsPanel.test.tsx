import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import MarketNewsPanel from "../MarketNewsPanel";
import { getMarketNews, getStockNews } from "@/services/marketInfoApi";

jest.mock("@/services/marketInfoApi", () => ({
  getMarketNews: jest.fn(),
  getStockNews: jest.fn(),
}));

const mockGetMarketNews = getMarketNews as jest.MockedFunction<
  typeof getMarketNews
>;
const mockGetStockNews = getStockNews as jest.MockedFunction<
  typeof getStockNews
>;

describe("MarketNewsPanel", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("shows a news API failure separately from an empty result and retries", async () => {
    mockGetStockNews
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce([
        {
          id: "article-1",
          headline: "Apple announces quarterly results",
          source: "Example News",
          provider: "example",
          url: "https://example.com/article-1",
        },
      ]);

    render(<MarketNewsPanel market="US" symbol="AAPL" />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "無法取得市場新聞",
    );
    expect(screen.queryByText("目前沒有相關新聞")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "重新載入" }));

    expect(
      await screen.findByText("Apple announces quarterly results"),
    ).toBeVisible();
    expect(mockGetStockNews).toHaveBeenCalledTimes(2);
  });

  it("shows an empty state after a successful market news request", async () => {
    mockGetMarketNews.mockResolvedValueOnce([]);

    render(<MarketNewsPanel />);

    expect(await screen.findByText("目前沒有相關新聞")).toBeVisible();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
