/**
 * Error Reporting Service
 */

// Configuration
const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN;
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Error types
export interface ErrorContext {
  component?: string;
  action?: string;
  userId?: string;
  sessionId?: string;
  url?: string;
  userAgent?: string;
  timestamp?: string;
  [key: string]: any;
}

export interface ErrorReport {
  message: string;
  stack?: string;
  context?: ErrorContext;
  level?: 'error' | 'warning' | 'info';
}

// In-memory error storage for development
let errorStorage: ErrorReport[] = [];

/**
 * Report error to external service (Sentry, API endpoint, etc.)
 */
export async function reportError(
  error: string | Error,
  context: ErrorContext = {},
  level: 'error' | 'warning' | 'info' = 'error'
): Promise<void> {
  const errorReport: ErrorReport = {
    message: typeof error === 'string' ? error : error.message,
    stack: error instanceof Error ? error.stack : undefined,
    context: {
      ...context,
      url: typeof window !== 'undefined' ? window.location.href : undefined,
      userAgent: typeof window !== 'undefined' ? navigator.userAgent : undefined,
      timestamp: new Date().toISOString(),
    },
    level,
  };

  // Store in memory for development
  errorStorage.push(errorReport);

  // Keep only last 100 errors
  if (errorStorage.length > 100) {
    errorStorage = errorStorage.slice(-100);
  }

  // Console logging for development
  if (process.env.NODE_ENV === 'development') {
    console.group(`🔴 Error Report (${level})`);
    console.error('Message:', errorReport.message);
    if (errorReport.stack) {
      console.error('Stack:', errorReport.stack);
    }
    console.log('Context:', errorReport.context);
    console.groupEnd();
  }

  try {
    // Send to Sentry if configured
    if (SENTRY_DSN && typeof window !== 'undefined') {
      // This would integrate with Sentry in a real implementation
      // For now, we'll just log
      console.log('Would send to Sentry:', errorReport);
    }

    // Send to API endpoint
    if (typeof window !== 'undefined') {
      await fetch(`${API_BASE_URL}/api/v1/errors`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(errorReport),
      }).catch(err => {
        // Silently fail if error reporting endpoint is not available
        console.warn('Failed to send error to API:', err.message);
      });
    }
  } catch (err) {
    // Silently fail if error reporting fails
    console.warn('Error reporting failed:', err);
  }
}

/**
 * Report performance issue
 */
export async function reportPerformanceIssue(
  metric: string,
  value: number,
  context: ErrorContext = {}
): Promise<void> {
  await reportError(
    `Performance issue: ${metric} = ${value}`,
    {
      ...context,
      metric,
      value,
      type: 'performance',
    },
    'warning'
  );
}

/**
 * Report user action for analytics
 */
export async function reportUserAction(
  action: string,
  context: ErrorContext = {}
): Promise<void> {
  await reportError(
    `User action: ${action}`,
    {
      ...context,
      action,
      type: 'user_action',
    },
    'info'
  );
}

/**
 * Get recent errors (for development/debugging)
 */
export function getRecentErrors(): ErrorReport[] {
  return [...errorStorage];
}

/**
 * Clear error storage
 */
export function clearErrorStorage(): void {
  errorStorage = [];
}

/**
 * Global error handler
 */
export function setupGlobalErrorHandling(): void {
  if (typeof window === 'undefined') return;

  // Handle unhandled promise rejections
  window.addEventListener('unhandledrejection', (event) => {
    reportError(
      event.reason instanceof Error ? event.reason : new Error(String(event.reason)),
      {
        component: 'global',
        type: 'unhandled_promise_rejection',
      }
    );
  });

  // Handle uncaught errors
  window.addEventListener('error', (event) => {
    reportError(
      event.error || new Error(event.message),
      {
        component: 'global',
        type: 'uncaught_error',
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
      }
    );
  });

  // Handle React error boundaries (if using error boundary)
  const originalConsoleError = console.error;
  console.error = (...args) => {
    const message = args.join(' ');

    // Check if this looks like a React error
    if (message.includes('React') || message.includes('Component')) {
      reportError(
        new Error(message),
        {
          component: 'react',
          type: 'react_error',
        }
      );
    }

    originalConsoleError.apply(console, args);
  };
}

// Auto-setup in browser environment
if (typeof window !== 'undefined' && process.env.NODE_ENV !== 'test') {
  setupGlobalErrorHandling();
}

export default {
  reportError,
  reportPerformanceIssue,
  reportUserAction,
  getRecentErrors,
  clearErrorStorage,
  setupGlobalErrorHandling,
};