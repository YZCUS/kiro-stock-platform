jest.mock("next/server", () => ({
  NextResponse: {
    json: (body: unknown, init?: { status?: number }) => ({
      status: init?.status ?? 200,
      json: async () => body,
    }),
  },
}));

describe("frontend health route", () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("reports the backend database and websocket component states", async () => {
    Object.defineProperty(AbortSignal, "timeout", {
      configurable: true,
      value: () => new AbortController().signal,
    });
    const { GET } = await import("@/app/api/health/route");
    jest.spyOn(global, "fetch").mockResolvedValue({
      status: 503,
      json: async () => ({
        status: "unhealthy",
        timestamp: "2026-07-15T00:00:00Z",
        components: {
          database: { status: "unhealthy", error: "ConnectionError" },
          websocket: { status: "degraded", error: "stream unavailable" },
        },
      }),
    } as Response);

    const response = await GET();
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(body.checks.database).toEqual({
      status: "unhealthy",
      error: "ConnectionError",
    });
    expect(body.checks.websocket).toEqual({
      status: "degraded",
      error: "stream unavailable",
    });
    expect(body.checks.api.status).toBe("healthy");
  });
});
