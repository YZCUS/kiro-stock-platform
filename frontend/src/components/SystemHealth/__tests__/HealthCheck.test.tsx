import { render, screen, waitFor } from "@testing-library/react";

import { HealthCheck } from "@/components/SystemHealth/HealthCheck";

describe("HealthCheck", () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("renders a partial structured health response without crashing", async () => {
    jest.spyOn(global, "fetch").mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({
        status: "unhealthy",
        checks: {
          api: { status: "unhealthy", error: "Backend unavailable" },
        },
      }),
    } as Response);

    render(<HealthCheck autoRefresh={false} />);

    await waitFor(() => {
      expect(screen.getByText("系統異常")).toBeInTheDocument();
    });
    expect(screen.getAllByText("未提供")).toHaveLength(4);
    expect(screen.getByText("Backend unavailable")).toBeInTheDocument();
    expect(screen.queryByText("健康檢查失敗")).not.toBeInTheDocument();
  });

  it("labels degraded services as degraded rather than offline", async () => {
    jest.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        status: "degraded",
        checks: {
          websocket: { status: "degraded", error: "stream reconnecting" },
        },
      }),
    } as Response);

    render(<HealthCheck autoRefresh={false} />);

    await waitFor(() => {
      expect(screen.getAllByText("服務降級")).toHaveLength(2);
    });
    expect(screen.queryByText("系統異常")).not.toBeInTheDocument();
  });
});
