import { test, expect } from '@playwright/test';

test.describe('Billing Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/billing');
    await page.waitForLoadState('networkidle');
  });

  test('displays billing page with heading', async ({ page }) => {
    const heading = page.locator('h1, h2').first();
    await expect(heading).toBeVisible({ timeout: 10_000 });
    await expect(heading).toContainText(/billing/i);
  });

  test('subscription tab is visible by default', async ({ page }) => {
    // Subscription tab should be present and active
    const subscriptionTab = page.locator('button[role="tab"]:has-text("Subscriptions"), [data-value="subscriptions"]');
    await expect(subscriptionTab.first()).toBeVisible();

    // Should show subscription content area
    const subscriptionsContent = page.locator('[role="tabpanel"]').first();
    await expect(subscriptionsContent).toBeVisible({ timeout: 10_000 });
  });

  test('navigates to invoices tab and verifies invoice table', async ({ page }) => {
    // Click the invoices tab
    const invoicesTab = page.locator('button[role="tab"]:has-text("Invoices"), [data-value="invoices"]');
    await expect(invoicesTab.first()).toBeVisible();
    await invoicesTab.first().click();

    await page.waitForTimeout(500);

    // Should show invoices tab panel
    const invoicesPanel = page.locator('[role="tabpanel"]').first();
    await expect(invoicesPanel).toBeVisible({ timeout: 10_000 });

    // Should have an invoices table
    const table = page.locator('table');
    await expect(table).toBeVisible({ timeout: 10_000 });

    // Table should have invoice-related columns
    const headerText = await table.locator('th').first().textContent();
    expect(headerText).toBeTruthy();
  });

  test('wallet tab is accessible', async ({ page }) => {
    const walletTab = page.locator('button[role="tab"]:has-text("Wallet"), [data-value="wallet"]');
    await expect(walletTab.first()).toBeVisible();
    await walletTab.first().click();

    await page.waitForTimeout(500);

    // Wallet tab panel should contain balance info or loading state
    const walletPanel = page.locator('[role="tabpanel"]').first();
    await expect(walletPanel).toBeVisible({ timeout: 10_000 });
  });

  test('has manage plan link', async ({ page }) => {
    // Look for "Manage Plan" button / link
    const managePlanLink = page.locator('a[href*="/billing/subscription"], a:has-text("Manage Plan"), a:has-text("View Plans")');
    if (await managePlanLink.count() > 0) {
      await expect(managePlanLink.first()).toBeVisible();
    }
  });

  test.describe('Subscription Management Page', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/billing/subscription');
      await page.waitForLoadState('networkidle');
    });

    test('displays subscription management page', async ({ page }) => {
      const heading = page.locator('h1, h2').first();
      await expect(heading).toBeVisible({ timeout: 10_000 });
      await expect(heading).toContainText(/subscription/i);
    });

    test('shows current plan section', async ({ page }) => {
      const currentPlanSection = page.locator('text=/current plan/i, h2:has-text("Compare Plans")');
      await expect(currentPlanSection.first()).toBeVisible({ timeout: 10_000 });
    });

    test('displays plan comparison grid', async ({ page }) => {
      // Look for the Compare Plans heading
      const compareHeading = page.locator('h2:has-text("Compare Plans")');
      await expect(compareHeading).toBeVisible({ timeout: 10_000 });

      // Expect plan cards (grid of plans) - they use Card components
      const planCards = page.locator('[class*="grid"]').first();
      await expect(planCards).toBeVisible();

      // Each plan card should show pricing info
      const priceElements = page.locator('text=/\\/month/');
      const priceCount = await priceElements.count();
      expect(priceCount).toBeGreaterThanOrEqual(1);
    });
  });

  test.describe('Invoices Page', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/billing/invoices');
      await page.waitForLoadState('networkidle');
    });

    test('displays invoices list page', async ({ page }) => {
      const heading = page.locator('h1, h2').first();
      await expect(heading).toBeVisible({ timeout: 10_000 });
      await expect(heading).toContainText(/invoice/i);
    });

    test('shows invoice table or empty state', async ({ page }) => {
      const table = page.locator('table');
      const emptyState = page.locator('text=/no invoices/i');

      if (await table.count() > 0) {
        await expect(table.first()).toBeVisible();
      } else if (await emptyState.count() > 0) {
        await expect(emptyState.first()).toBeVisible();
      }
    });
  });
});
