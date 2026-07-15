import { apiClient, ApiService } from "../../lib/api";
import { changePassword, getCurrentUser, login, register } from "../authApi";
import {
  calculateProfitLossPercent,
  createTransaction,
  formatCurrency,
  formatPercent,
  getPortfolioList,
  getPortfolioSummary,
  getTransactionList,
  getTransactionSummary,
  isProfitable,
} from "../portfolioApi";
import * as stockListApi from "../stockListApi";
import {
  detectMarket,
  ensureStockExists,
  ensureStockExistsAuto,
  formatStockSymbol,
  validateStockSymbol,
  validateStockSymbolAuto,
} from "../stockValidationApi";
import StocksApiService from "../stocksApi";
import * as strategyApi from "../strategyApi";

jest.mock("../../lib/api", () => {
  const actual = jest.requireActual("../../lib/api");
  return {
    ...actual,
    apiClient: {
      post: jest.fn(),
      get: jest.fn(),
    },
    ApiService: {
      get: jest.fn(),
      post: jest.fn(),
      put: jest.fn(),
      patch: jest.fn(),
      delete: jest.fn(),
    },
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    del: jest.fn(),
  };
});

const mockApiClient = apiClient as jest.Mocked<typeof apiClient>;
const mockApiService = ApiService as jest.Mocked<typeof ApiService>;

const libApi = jest.requireMock("../../lib/api") as {
  get: jest.Mock;
  post: jest.Mock;
  put: jest.Mock;
  del: jest.Mock;
};

describe("authApi", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("register and login post credentials to auth endpoints", async () => {
    const tokenResponse = {
      access_token: "token",
      token_type: "bearer",
      user: {
        id: "user-1",
        email: "user@example.com",
        username: "user",
        is_active: true,
        created_at: "2026-01-01T00:00:00Z",
      },
    };
    mockApiClient.post.mockResolvedValue({ data: tokenResponse });

    const registerResult = await register({
      email: "user@example.com",
      username: "user",
      password: "secret",
    });
    const loginResult = await login({ username: "user", password: "secret" });

    expect(registerResult).toEqual(tokenResponse);
    expect(loginResult).toEqual(tokenResponse);
    expect(mockApiClient.post).toHaveBeenNthCalledWith(
      1,
      "/api/v1/auth/register",
      { email: "user@example.com", username: "user", password: "secret" },
    );
    expect(mockApiClient.post).toHaveBeenNthCalledWith(
      2,
      "/api/v1/auth/login",
      { username: "user", password: "secret" },
    );
  });

  it("sends bearer token for current user and password changes", async () => {
    mockApiClient.get.mockResolvedValue({ data: { id: "user-1" } });
    mockApiClient.post.mockResolvedValue({ data: { message: "changed" } });

    await getCurrentUser("token");
    const result = await changePassword(
      { old_password: "old", new_password: "new" },
      "token",
    );

    expect(result).toEqual({ message: "changed" });
    expect(mockApiClient.get).toHaveBeenCalledWith("/api/v1/auth/me", {
      headers: { Authorization: "Bearer token" },
    });
    expect(mockApiClient.post).toHaveBeenCalledWith(
      "/api/v1/auth/change-password",
      { old_password: "old", new_password: "new" },
      { headers: { Authorization: "Bearer token" } },
    );
  });
});

describe("StocksApiService", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("builds stock list query params from pagination, filters, and search", async () => {
    mockApiService.get.mockResolvedValue({ items: [], total: 0 });

    await StocksApiService.getStocks({
      page: 2,
      pageSize: 25,
      search: "AAPL",
      filters: { market: "US", active_only: true },
    });

    expect(mockApiService.get).toHaveBeenCalledWith(
      "/api/v1/stocks/?page=2&per_page=25&market=US&is_active=true&search=AAPL",
    );
  });

  it("maps stock CRUD and price endpoints", async () => {
    mockApiService.get.mockResolvedValue({});
    mockApiService.post.mockResolvedValue({});
    mockApiService.patch.mockResolvedValue({});
    mockApiService.delete.mockResolvedValue({});

    await StocksApiService.getStock(3);
    await StocksApiService.createStock({
      symbol: "AAPL",
      name: "Apple",
      market: "US",
    });
    await StocksApiService.updateStock(3, { name: "Apple Inc." });
    await StocksApiService.deleteStock(3);
    await StocksApiService.getStockPriceHistory(3, {
      start_date: "2026-01-01",
      end_date: "2026-01-31",
      interval: "1d",
    });
    await StocksApiService.backfillStockData(3, { force: true });

    expect(mockApiService.get).toHaveBeenNthCalledWith(1, "/api/v1/stocks/3");
    expect(mockApiService.post).toHaveBeenNthCalledWith(1, "/api/v1/stocks/", {
      symbol: "AAPL",
      name: "Apple",
      market: "US",
    });
    expect(mockApiService.patch).toHaveBeenCalledWith("/api/v1/stocks/3", {
      name: "Apple Inc.",
    });
    expect(mockApiService.delete).toHaveBeenCalledWith("/api/v1/stocks/3");
    expect(mockApiService.get).toHaveBeenNthCalledWith(
      2,
      "/api/v1/stocks/3/price-history/?start_date=2026-01-01&end_date=2026-01-31&interval=1d",
    );
    expect(mockApiService.post).toHaveBeenNthCalledWith(
      2,
      "/api/v1/stocks/3/price/backfill",
      { force: true },
    );
  });
});

describe("stockListApi", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("maps list and list item endpoints", async () => {
    mockApiService.get.mockResolvedValue({});
    mockApiService.post.mockResolvedValue({});
    mockApiService.put.mockResolvedValue({});
    mockApiService.delete.mockResolvedValue({});

    await stockListApi.getStockLists();
    await stockListApi.createStockList({ name: "Watch", description: "Tech" });
    await stockListApi.updateStockList(4, { name: "Core" });
    await stockListApi.getListStocks(4);
    await stockListApi.addStockToList(4, { stock_id: 10 });
    await stockListApi.removeStockFromList(4, 10);
    await stockListApi.reorderListStocks(4, {
      stock_orders: [{ stock_id: 10, sort_order: 1 }],
    });

    expect(mockApiService.get).toHaveBeenNthCalledWith(
      1,
      "/api/v1/stock-lists/",
    );
    expect(mockApiService.post).toHaveBeenNthCalledWith(
      1,
      "/api/v1/stock-lists/",
      {
        name: "Watch",
        description: "Tech",
      },
    );
    expect(mockApiService.put).toHaveBeenCalledWith("/api/v1/stock-lists/4", {
      name: "Core",
    });
    expect(mockApiService.get).toHaveBeenNthCalledWith(
      2,
      "/api/v1/stock-lists/4/stocks",
    );
    expect(mockApiService.post).toHaveBeenNthCalledWith(
      2,
      "/api/v1/stock-lists/4/stocks",
      { stock_id: 10 },
    );
    expect(mockApiService.delete).toHaveBeenCalledWith(
      "/api/v1/stock-lists/4/stocks/10",
    );
    expect(mockApiService.post).toHaveBeenNthCalledWith(
      3,
      "/api/v1/stock-lists/4/stocks/reorder",
      { stock_orders: [{ stock_id: 10, sort_order: 1 }] },
    );
  });
});

describe("stockValidationApi", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("detects markets and formats Taiwan symbols", () => {
    expect(detectMarket("2330")).toBe("TW");
    expect(detectMarket("2330.TW")).toBe("TW");
    expect(detectMarket("8069.TWO")).toBe("TW");
    expect(detectMarket("aapl")).toBe("US");
    expect(formatStockSymbol("2330", "TW")).toBe("2330.TW");
    expect(formatStockSymbol("8069.TWO", "TW")).toBe("8069.TWO");
    expect(formatStockSymbol("AAPL", "US")).toBe("AAPL");
  });

  it("uses auto market detection for validation and ensure calls", async () => {
    mockApiService.post.mockResolvedValue({ valid: true });

    await validateStockSymbol("AAPL", "US");
    await validateStockSymbolAuto("2330");
    await ensureStockExists("AAPL", "US");
    await ensureStockExistsAuto("2330");

    expect(mockApiService.post).toHaveBeenNthCalledWith(
      1,
      "/api/v1/stocks/validate?symbol=AAPL&market=US",
      {},
    );
    expect(mockApiService.post).toHaveBeenNthCalledWith(
      2,
      "/api/v1/stocks/validate?symbol=2330&market=TW",
      {},
    );
    expect(mockApiService.post).toHaveBeenNthCalledWith(
      3,
      "/api/v1/stocks/ensure?symbol=AAPL&market=US",
      {},
    );
    expect(mockApiService.post).toHaveBeenNthCalledWith(
      4,
      "/api/v1/stocks/ensure?symbol=2330&market=TW",
      {},
    );
  });

  it("surfaces backend validation errors as user-facing errors", async () => {
    mockApiService.post.mockRejectedValueOnce({
      response: { data: { detail: "invalid symbol" } },
    });

    await expect(ensureStockExists("BAD", "US")).rejects.toThrow(
      "invalid symbol",
    );
  });
});

describe("portfolioApi", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("maps portfolio and transaction endpoints", async () => {
    mockApiService.get.mockResolvedValue({});
    mockApiService.post.mockResolvedValue({});

    await getPortfolioList();
    await getPortfolioSummary();
    await createTransaction({
      stock_id: 1,
      transaction_type: "BUY",
      quantity: 2,
      price: 100,
      transaction_date: "2026-01-01",
    });
    await getTransactionList({
      stock_id: 1,
      transaction_type: "BUY",
      start_date: "2026-01-01",
    });
    await getTransactionSummary("2026-01-01", "2026-01-31");

    expect(mockApiService.get).toHaveBeenNthCalledWith(1, "/api/v1/portfolio/");
    expect(mockApiService.get).toHaveBeenNthCalledWith(
      2,
      "/api/v1/portfolio/summary",
    );
    expect(mockApiService.post).toHaveBeenCalledWith(
      "/api/v1/portfolio/transactions",
      {
        stock_id: 1,
        transaction_type: "BUY",
        quantity: 2,
        price: 100,
        transaction_date: "2026-01-01",
      },
    );
    expect(mockApiService.get).toHaveBeenNthCalledWith(
      3,
      "/api/v1/portfolio/transactions?stock_id=1&transaction_type=BUY&start_date=2026-01-01",
    );
    expect(mockApiService.get).toHaveBeenNthCalledWith(
      4,
      "/api/v1/portfolio/transactions/summary?start_date=2026-01-01&end_date=2026-01-31",
    );
  });

  it("formats portfolio helper outputs", () => {
    expect(calculateProfitLossPercent(25, 100)).toBe(25);
    expect(calculateProfitLossPercent(25, 0)).toBe(0);
    expect(formatCurrency(1234)).toContain("1,234.00");
    expect(formatPercent(3.456)).toBe("+3.46%");
    expect(formatPercent(-3.456)).toBe("-3.46%");
    expect(isProfitable(1)).toBe(true);
    expect(isProfitable(0)).toBe(false);
  });
});

describe("strategyApi", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("maps strategy subscription endpoints with query params", async () => {
    await strategyApi.getAvailableStrategies();
    await strategyApi.getSubscriptions(true);
    await strategyApi.createSubscription({
      strategy_type: "golden_cross",
      parameters: {},
      monitor_all_lists: true,
      monitor_portfolio: false,
      selected_list_ids: [],
    });
    await strategyApi.updateSubscription(5, { monitor_portfolio: true });
    await strategyApi.deleteSubscription(5, true);
    await strategyApi.toggleSubscription(5, false);

    expect(libApi.get).toHaveBeenNthCalledWith(
      1,
      "/api/v1/strategies/available",
    );
    expect(libApi.get).toHaveBeenNthCalledWith(
      2,
      "/api/v1/strategies/subscriptions",
      { active_only: true },
    );
    expect(libApi.post).toHaveBeenNthCalledWith(
      1,
      "/api/v1/strategies/subscriptions",
      {
        strategy_type: "golden_cross",
        params: {},
        monitor_all_lists: true,
        monitor_portfolio: false,
        selected_list_ids: [],
      },
    );
    expect(libApi.put).toHaveBeenCalledWith(
      "/api/v1/strategies/subscriptions/5",
      {
        monitor_portfolio: true,
      },
    );
    expect(libApi.del).toHaveBeenCalledWith(
      "/api/v1/strategies/subscriptions/5?hard_delete=true",
    );
    expect(libApi.post).toHaveBeenNthCalledWith(
      2,
      "/api/v1/strategies/subscriptions/5/toggle?is_active=false",
    );
  });

  it("maps strategy signal endpoints", async () => {
    await strategyApi.getSignals({ status: "active", limit: 10 });
    await strategyApi.getSignalStatistics("2026-01-01", "2026-01-31");
    await strategyApi.updateSignalStatus(7, { status: "triggered" });
    await strategyApi.generateSignals("user-1");

    expect(libApi.get).toHaveBeenNthCalledWith(
      1,
      "/api/v1/strategies/signals",
      {
        status: "active",
        limit: 10,
      },
    );
    expect(libApi.get).toHaveBeenNthCalledWith(
      2,
      "/api/v1/strategies/signals/statistics",
      { date_from: "2026-01-01", date_to: "2026-01-31" },
    );
    expect(libApi.put).toHaveBeenCalledWith(
      "/api/v1/strategies/signals/7/status",
      {
        status: "triggered",
      },
    );
    expect(libApi.post).toHaveBeenCalledWith(
      "/api/v1/strategies/signals/generate?user_id=user-1",
    );
  });
});
