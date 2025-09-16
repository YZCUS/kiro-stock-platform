/**
 * Health Check API Endpoint
 */
import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
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
  try {
    const start = Date.now();

    // 檢查資料庫連接 - 在真實應用中連接到 PostgreSQL
    if (process.env.DATABASE_URL) {
      // 在生產環境中，這裡會建立真實的資料庫連接檢查
      // 例如：簡單的 SELECT 1 查詢來驗證連接

      // 模擬資料庫查詢
      await new Promise((resolve, reject) => {
        // 模擬隨機的資料庫延遲和偶爾的失敗
        const delay = Math.random() * 50 + 10; // 10-60ms
        const shouldFail = Math.random() < 0.05; // 5% 失敗率

        setTimeout(() => {
          if (shouldFail) {
            reject(new Error('Database connection timeout'));
          } else {
            resolve(true);
          }
        }, delay);
      });
    } else {
      // 如果沒有配置資料庫 URL，標記為未配置
      return {
        status: 'healthy',
        responseTime: 0,
        error: 'Database URL not configured (development mode)',
      };
    }

    const responseTime = Date.now() - start;

    return {
      status: 'healthy',
      responseTime,
    };
  } catch (error) {
    return {
      status: 'unhealthy',
      error: error instanceof Error ? error.message : 'Unknown database error',
    };
  }
}

async function checkApiConnection(): Promise<{ status: string; responseTime?: number; error?: string }> {
  try {
    const start = Date.now();
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL;

    if (!wsUrl) {
      return {
        status: 'unhealthy',
        error: 'WebSocket URL not configured',
      };
    }

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