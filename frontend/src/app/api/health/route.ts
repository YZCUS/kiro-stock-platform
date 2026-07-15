/**
 * Health Check API Endpoint
 */
import { NextResponse } from "next/server";
import { getApiBaseUrl } from "../../../lib/runtimeConfig";

interface BackendComponentHealth {
  status?: string;
  error?: string;
  response_time_ms?: number;
}

interface BackendHealthPayload {
  status?: string;
  timestamp?: string;
  components?: {
    database?: BackendComponentHealth;
    websocket?: BackendComponentHealth;
  };
}

interface ServiceCheck {
  status: string;
  responseTime?: number;
  error?: string;
}

const normalizeComponent = (
  component: BackendComponentHealth | undefined,
  missingMessage: string,
): ServiceCheck => {
  if (!component?.status) {
    return { status: "unavailable", error: missingMessage };
  }

  return {
    status: component.status,
    responseTime: component.response_time_ms,
    error: component.error,
  };
};

async function fetchBackendHealth(): Promise<{
  payload: BackendHealthPayload | null;
  responseTime: number;
  error?: string;
}> {
  const startedAt = Date.now();

  try {
    const response = await fetch(`${getApiBaseUrl()}/health`, {
      method: "GET",
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
    const payload = (await response
      .json()
      .catch(() => null)) as BackendHealthPayload | null;

    if (!payload?.components) {
      return {
        payload: null,
        responseTime: Date.now() - startedAt,
        error: `Backend health returned ${response.status} without component data`,
      };
    }

    return { payload, responseTime: Date.now() - startedAt };
  } catch (error) {
    return {
      payload: null,
      responseTime: Date.now() - startedAt,
      error: error instanceof Error ? error.message : "Backend unavailable",
    };
  }
}

export async function GET() {
  const backend = await fetchBackendHealth();
  const checks = {
    database: normalizeComponent(
      backend.payload?.components?.database,
      "Backend did not report database health",
    ),
    api: {
      status: backend.payload ? "healthy" : "unhealthy",
      responseTime: backend.responseTime,
      error: backend.error,
    },
    websocket: normalizeComponent(
      backend.payload?.components?.websocket,
      "Backend did not report WebSocket health",
    ),
  };
  const statuses = Object.values(checks).map((check) => check.status);
  const status =
    statuses.includes("unhealthy") || statuses.includes("unavailable")
      ? "unhealthy"
      : statuses.every((value) => value === "healthy")
        ? "healthy"
        : "degraded";

  return NextResponse.json(
    {
      status,
      timestamp: backend.payload?.timestamp ?? new Date().toISOString(),
      version: process.env.NEXT_PUBLIC_APP_VERSION || "1.0.0",
      environment: process.env.NODE_ENV,
      uptime: process.uptime(),
      memory: process.memoryUsage(),
      checks,
    },
    {
      status: status === "unhealthy" ? 503 : 200,
      headers: {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        Pragma: "no-cache",
        Expires: "0",
      },
    },
  );
}
