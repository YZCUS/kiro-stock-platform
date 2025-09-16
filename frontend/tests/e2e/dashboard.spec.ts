/**
 * Dashboard E2E Tests
 */
import { test, expect } from '@playwright/test';

test.describe('Dashboard Page', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to dashboard
    await page.goto('/dashboard');
  });

  test('should display dashboard title and description', async ({ page }) => {
    // Check main heading
    await expect(page.locator('h1')).toContainText('即時交易儀表板');

    // Check description
    await expect(page.locator('text=股票價格、技術指標和交易信號的即時監控')).toBeVisible();
  });

  test('should display connection status', async ({ page }) => {
    // Check for connection status indicator
    await expect(page.locator('[data-testid="connection-status"]')).toBeVisible();
  });

  test('should display statistics cards', async ({ page }) => {
    // Wait for statistics cards to load
    await page.waitForSelector('[data-testid="stats-cards"]');

    // Check that all 4 stats cards are present
    const statsCards = page.locator('[data-testid="stats-card"]');
    await expect(statsCards).toHaveCount(4);

    // Check specific stats
    await expect(page.locator('text=連線狀態')).toBeVisible();
    await expect(page.locator('text=訂閱股票')).toBeVisible();
    await expect(page.locator('text=最新信號')).toBeVisible();
    await expect(page.locator('text=市場狀態')).toBeVisible();
  });

  test('should display stock subscription management', async ({ page }) => {
    // Check stock subscription section
    await expect(page.locator('text=股票訂閱管理')).toBeVisible();

    // Should show stock cards
    await page.waitForSelector('[data-testid="stock-card"]');
    const stockCards = page.locator('[data-testid="stock-card"]');

    // Should have at least one stock card
    await expect(stockCards.first()).toBeVisible();
  });

  test('should allow stock subscription toggle', async ({ page }) => {
    // Wait for stock cards to load
    await page.waitForSelector('[data-testid="stock-card"]');

    // Find first subscription button
    const subscriptionButton = page.locator('[data-testid="subscription-button"]').first();
    await expect(subscriptionButton).toBeVisible();

    // Click to toggle subscription
    await subscriptionButton.click();

    // Verify the button state changed (this might need adjustment based on implementation)
    // The exact assertion will depend on how the UI indicates subscription state
  });

  test('should display real-time chart', async ({ page }) => {
    // Wait for chart container
    await page.waitForSelector('[data-testid="realtime-chart"]', { timeout: 10000 });

    // Check that chart is rendered
    await expect(page.locator('[data-testid="realtime-chart"]')).toBeVisible();
  });

  test('should display real-time signals panel', async ({ page }) => {
    // Check signals panel
    await expect(page.locator('[data-testid="realtime-signals"]')).toBeVisible();
  });

  test('should be responsive on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    // Check that main elements are still visible
    await expect(page.locator('h1')).toContainText('即時交易儀表板');
    await expect(page.locator('[data-testid="stats-cards"]')).toBeVisible();

    // Check mobile-specific layout adjustments
    // This will depend on your responsive design implementation
  });

  test('should handle loading states', async ({ page }) => {
    // Intercept API calls to test loading states
    await page.route('**/api/v1/stocks*', route => {
      // Delay the response to test loading state
      setTimeout(() => route.continue(), 2000);
    });

    await page.goto('/dashboard');

    // Should show loading indicators
    await expect(page.locator('[data-testid="loading-skeleton"]')).toBeVisible();
  });

  test('should handle error states', async ({ page }) => {
    // Intercept API calls to simulate errors
    await page.route('**/api/v1/stocks*', route => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ message: 'Internal Server Error' }),
      });
    });

    await page.goto('/dashboard');

    // Should show error message or retry option
    await expect(page.locator('text=載入失敗')).toBeVisible();
    await expect(page.locator('button:has-text("重試")')).toBeVisible();
  });

  test('should allow switching between different stocks', async ({ page }) => {
    // Wait for stock cards
    await page.waitForSelector('[data-testid="stock-card"]');

    // Click on different stock cards to switch active stock
    const stockCards = page.locator('[data-testid="stock-card"]');
    const count = await stockCards.count();

    if (count > 1) {
      // Click on second stock card
      await stockCards.nth(1).click();

      // Verify that the chart updates (this might need adjustment based on implementation)
      // You might check for chart re-rendering or active state changes
    }
  });
});

test.describe('Dashboard Navigation', () => {
  test('should navigate to dashboard from other pages', async ({ page }) => {
    // Start from home page
    await page.goto('/');

    // Click dashboard link in navigation
    await page.click('a[href="/dashboard"]');

    // Should be on dashboard page
    await expect(page).toHaveURL('/dashboard');
    await expect(page.locator('h1')).toContainText('即時交易儀表板');
  });

  test('should maintain WebSocket connection across navigation', async ({ page }) => {
    // Go to dashboard
    await page.goto('/dashboard');

    // Wait for WebSocket connection
    await page.waitForSelector('[data-testid="connection-status"]');

    // Navigate away and back
    await page.goto('/stocks');
    await page.goto('/dashboard');

    // Connection should still be maintained
    await expect(page.locator('[data-testid="connection-status"]')).toBeVisible();
  });
});