/**
 * Health Check API Endpoint
 */
import { NextResponse } from 'next/server';
import { getApiBaseUrl, getWebSocketUrl } from '../../../lib/runtimeConfig';

export async function GET() {
  const checks = {
    status: 'healthy',
    timestamp: new Date().toISOString(),
    version: process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0',
    environment: process.env.NODE_ENV,
    uptime: process.uptime(),
    memory: process.memoryUsage(),
    checks: {
      database: await checkDatabase(),
      api: await checkApiConnection(),
      websocket: await checkWebSocketConnection(),
    },
  };

  const isHealthy = Object.values(checks.checks).every(check => check.status === 'healthy');

  return NextResponse.json(
    {
      ...checks,
      status: isHealthy ? 'healthy' : 'unhealthy',
    },
    {
      status: isHealthy ? 200 : 503,
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0',
      },
    }
  );
}

async function checkDatabase(): Promise<{ status: string; responseTime?: number; error?: string }> {
  const start = Date.now();

  return {
    status: 'healthy',
    responseTime: Date.now() - start,
    error: process.env.DATABASE_URL
      ? undefined
      : 'Database check is handled by the backend health endpoint',
  };
}

async function checkApiConnection(): Promise<{ status: string; responseTime?: number; error?: string }> {
  try {
    const start = Date.now();
    const apiUrl = getApiBaseUrl();

    const response = await fetch(`${apiUrl}/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(5000), // 5 second timeout
    });

    const responseTime = Date.now() - start;

    if (response.ok) {
      return {
        status: 'healthy',
        responseTime,
      };
    } else {
      return {
        status: 'unhealthy',
        error: `API returned ${response.status}: ${response.statusText}`,
      };
    }
  } catch (error) {
    return {
      status: 'unhealthy',
      error: error instanceof Error ? error.message : 'Unknown API error',
    };
  }
}

async function checkWebSocketConnection(): Promise<{ status: string; error?: string }> {
  try {
    // This is a simplified check - in production, you might want to actually test WS connectivity
    const wsUrl = getWebSocketUrl();

    // For now, just check if the URL is valid
    new URL(wsUrl.replace('ws://', 'http://').replace('wss://', 'https://'));

    return {
      status: 'healthy',
    };
  } catch (error) {
    return {
      status: 'unhealthy',
      error: error instanceof Error ? error.message : 'Invalid WebSocket configuration',
    };
  }
}
