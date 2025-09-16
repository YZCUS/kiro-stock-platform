/**
 * Error Reporting API Endpoint
 */
import { NextRequest, NextResponse } from 'next/server';

export interface ErrorReportRequest {
  id: string;
  timestamp: string;
  message: string;
  stack?: string;
  componentStack?: string;
  url: string;
  userAgent: string;
  userId?: string;
  sessionId: string;
  level: 'error' | 'warning' | 'info';
  category: 'javascript' | 'network' | 'component' | 'api' | 'websocket';
  metadata?: Record<string, any>;
}

export async function POST(request: NextRequest) {
  try {
    const errorReport: ErrorReportRequest = await request.json();

    // 驗證必要欄位
    if (!errorReport.message || !errorReport.timestamp) {
      return NextResponse.json(
        { error: 'Missing required fields: message, timestamp' },
        { status: 400 }
      );
    }

    // 記錄錯誤到控制台（開發環境）
    if (process.env.NODE_ENV === 'development') {
      console.error('Frontend Error Report:', {
        id: errorReport.id,
        message: errorReport.message,
        level: errorReport.level,
        category: errorReport.category,
        url: errorReport.url,
        timestamp: errorReport.timestamp,
      });

      if (errorReport.stack) {
        console.error('Stack trace:', errorReport.stack);
      }

      if (errorReport.metadata) {
        console.error('Metadata:', errorReport.metadata);
      }
    }

    // 在生產環境中，可以發送到外部錯誤追蹤服務
    if (process.env.NODE_ENV === 'production') {
      await sendToExternalService(errorReport);
    }

    // 儲存到資料庫（如果需要）
    await saveErrorReport(errorReport);

    // 檢查是否需要發送警報
    await checkForAlerts(errorReport);

    return NextResponse.json(
      {
        success: true,
        id: errorReport.id,
        message: 'Error report received'
      },
      { status: 200 }
    );
  } catch (error) {
    console.error('Failed to process error report:', error);

    return NextResponse.json(
      { error: 'Failed to process error report' },
      { status: 500 }
    );
  }
}

async function sendToExternalService(errorReport: ErrorReportRequest): Promise<void> {
  try {
    // 集成外部錯誤追蹤服務（Sentry、DataDog、LogRocket等）

    // Sentry 示例
    if (process.env.SENTRY_DSN) {
      // 這裡可以整合 Sentry SDK
      console.log('Would send to Sentry:', errorReport.id);
    }

    // DataDog 示例
    if (process.env.DATADOG_API_KEY) {
      // 這裡可以整合 DataDog logging
      console.log('Would send to DataDog:', errorReport.id);
    }

    // 自訂錯誤追蹤服務
    if (process.env.CUSTOM_ERROR_TRACKING_URL) {
      await fetch(process.env.CUSTOM_ERROR_TRACKING_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${process.env.CUSTOM_ERROR_TRACKING_TOKEN}`,
        },
        body: JSON.stringify(errorReport),
      });
    }
  } catch (error) {
    console.error('Failed to send error to external service:', error);
  }
}

async function saveErrorReport(errorReport: ErrorReportRequest): Promise<void> {
  try {
    // 這裡可以將錯誤保存到資料庫
    // 例如：PostgreSQL、MongoDB等

    // 示例：保存到本地日誌文件（開發環境）
    if (process.env.NODE_ENV === 'development') {
      const fs = await import('fs/promises');
      const path = await import('path');

      const logDir = path.join(process.cwd(), 'logs');
      const logFile = path.join(logDir, 'frontend-errors.log');

      try {
        await fs.mkdir(logDir, { recursive: true });

        const logEntry = {
          ...errorReport,
          timestamp: new Date().toISOString(),
        };

        await fs.appendFile(
          logFile,
          JSON.stringify(logEntry) + '\n'
        );
      } catch (fileError) {
        console.warn('Failed to write error log to file:', fileError);
      }
    }

    // 示例：保存到資料庫
    // const db = await getDatabase();
    // await db.errorReports.create(errorReport);

  } catch (error) {
    console.error('Failed to save error report:', error);
  }
}

async function checkForAlerts(errorReport: ErrorReportRequest): Promise<void> {
  try {
    // 檢查是否需要發送警報
    const criticalConditions = [
      errorReport.level === 'error' && errorReport.category === 'api',
      errorReport.message.includes('WebSocket'),
      errorReport.message.includes('Authentication'),
    ];

    const shouldAlert = criticalConditions.some(condition => condition);

    if (shouldAlert) {
      await sendAlert(errorReport);
    }
  } catch (error) {
    console.error('Failed to check for alerts:', error);
  }
}

async function sendAlert(errorReport: ErrorReportRequest): Promise<void> {
  try {
    // 發送警報通知（Slack、Email、SMS等）

    // Slack 示例
    if (process.env.SLACK_WEBHOOK_URL) {
      await fetch(process.env.SLACK_WEBHOOK_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: `🚨 Critical Frontend Error: ${errorReport.message}`,
          attachments: [{
            color: 'danger',
            fields: [
              { title: 'Error ID', value: errorReport.id, short: true },
              { title: 'Category', value: errorReport.category, short: true },
              { title: 'URL', value: errorReport.url, short: false },
              { title: 'Timestamp', value: errorReport.timestamp, short: true },
            ],
          }],
        }),
      });
    }

    // Email 示例
    if (process.env.ALERT_EMAIL_URL) {
      await fetch(process.env.ALERT_EMAIL_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          to: process.env.ALERT_EMAIL_RECIPIENTS,
          subject: `Critical Frontend Error: ${errorReport.message}`,
          body: `
            Error Report Details:

            ID: ${errorReport.id}
            Message: ${errorReport.message}
            Category: ${errorReport.category}
            Level: ${errorReport.level}
            URL: ${errorReport.url}
            Timestamp: ${errorReport.timestamp}

            ${errorReport.stack ? `Stack Trace:\n${errorReport.stack}` : ''}
          `,
        }),
      });
    }
  } catch (error) {
    console.error('Failed to send alert:', error);
  }
}

// GET 方法用於獲取錯誤報告統計
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const timeframe = searchParams.get('timeframe') || '24h';
    const category = searchParams.get('category');

    // 這裡可以從資料庫獲取錯誤統計
    const stats = {
      totalErrors: 0,
      errorsByCategory: {},
      errorsByLevel: {},
      recentErrors: [],
      timeframe,
    };

    return NextResponse.json(stats);
  } catch (error) {
    console.error('Failed to get error statistics:', error);
    return NextResponse.json(
      { error: 'Failed to get error statistics' },
      { status: 500 }
    );
  }
}