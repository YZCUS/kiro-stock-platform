/**
 * Dashboard E2E Tests
 */
import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';

const stockFixture = {
  exists: true,
  created: false,
  stock: {
    id: 42,
    symbol: 'AAPL',
    name: 'Apple Inc.',
    market: 'US',
    latest_price: {
      close: 188.45,
      change: 2.33,
      change_percent: 1.25,
      date: '2026-04-29',
      volume: 58920000,
    },
  },
};

const priceHistoryFixture = [
  {
    date: '2026-04-28T14:30:00Z',
    open: 185,
    high: 190,
    low: 184,
    close: 188.45,
  },
];

async function mockSuccessfulStockSearch(page: Page) {
  await page.route('**/api/v1/stocks/ensure**', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(stockFixture),
    });
  });

  await page.route('**/api/v1/stocks/42/prices**', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(priceHistoryFixture),
    });
  });
}

test.describe('Dashboard Page', () => {
  test('should display the current dashboard shell for anonymous users', async ({ page }) => {
    await page.goto('/dashboard');

    await expect(page.getByRole('heading', { name: '即時圖表分析' })).toBeVisible();
    await expect(page.getByText('選擇清單和股票，查看即時價格走勢和技術指標')).toBeVisible();
    await expect(page.getByPlaceholder('輸入股號 (如: AAPL, 2330)')).toBeVisible();

    const listSelector = page.getByRole('button', { name: /請先登入/ });
    await expect(listSelector).toBeDisabled();
    await expect(page.getByText('請選擇清單和股票')).toBeVisible();
  });

  test('should keep search disabled until a symbol is entered and normalize input to uppercase', async ({ page }) => {
    await page.goto('/dashboard');

    const input = page.getByPlaceholder('輸入股號 (如: AAPL, 2330)');
    const searchButton = input.locator('..').getByRole('button').first();

    await expect(searchButton).toBeDisabled();

    await input.fill('aapl');

    await expect(input).toHaveValue('AAPL');
    await expect(searchButton).toBeEnabled();
  });

  test('should query a stock by symbol and render the selected stock summary', async ({ page }) => {
    await mockSuccessfulStockSearch(page);
    await page.goto('/dashboard');

    const input = page.getByPlaceholder('輸入股號 (如: AAPL, 2330)');
    const searchButton = input.locator('..').getByRole('button').first();
    const ensureRequestPromise = page.waitForRequest('**/api/v1/stocks/ensure**');

    await input.fill('aapl');
    await searchButton.click();

    const ensureRequest = await ensureRequestPromise;
    const ensureUrl = new URL(ensureRequest.url());
    expect(ensureUrl.searchParams.get('symbol')).toBe('AAPL');
    expect(ensureUrl.searchParams.get('market')).toBe('US');

    await expect(page.getByRole('heading', { name: 'AAPL - Apple Inc.' })).toBeVisible();
    await expect(page.getByText('$188.45').first()).toBeVisible();
    await expect(page.getByText('+2.33').first()).toBeVisible();
    await expect(page.getByText('+1.25%').first()).toBeVisible();
    await expect(page.getByText('AAPL (Apple Inc.) 即時價格圖表')).toBeVisible();
  });

  test('should show the backend error message when direct search fails', async ({ page }) => {
    await page.route('**/api/v1/stocks/ensure**', async route => {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: '找不到股票 AAPL' }),
      });
    });
    await page.goto('/dashboard');

    const input = page.getByPlaceholder('輸入股號 (如: AAPL, 2330)');
    const searchButton = input.locator('..').getByRole('button').first();

    await input.fill('aapl');
    await searchButton.click();

    await expect(page.getByText('找不到股票 AAPL')).toBeVisible();
  });

  test('should keep the main workflow usable on mobile width', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/dashboard');

    await expect(page.getByRole('heading', { name: '即時圖表分析' })).toBeVisible();
    await expect(page.getByPlaceholder('輸入股號 (如: AAPL, 2330)')).toBeVisible();
    await expect(page.getByText('請選擇清單和股票')).toBeVisible();
  });
});

test.describe('Dashboard Navigation', () => {
  test('should navigate to dashboard from other pages', async ({ page }) => {
    await page.goto('/');

    await page.getByRole('link', { name: '即時分析' }).click();

    await expect(page).toHaveURL('/dashboard');
    await expect(page.getByRole('heading', { name: '即時圖表分析' })).toBeVisible();
  });
});
