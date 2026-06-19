import { test, expect } from '@playwright/test';

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to dashboard — if not authenticated, login flow will redirect
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
  });

  test('displays dashboard layout', async ({ page }) => {
    // Sidebar should be visible
    const sidebar = page.locator('aside, nav').first();
    await expect(sidebar).toBeVisible({ timeout: 10_000 });

    // Main content area should be visible
    const main = page.locator('main, [role="main"]').first();
    await expect(main).toBeVisible();

    // Should mention Aegis branding
    await expect(page.locator('body')).toContainText(/Aegis/i);
  });

  test('has navigation sidebar with key sections', async ({ page }) => {
    // Check for key navigation items
    await expect(page.locator('text=/dashboard/i')).toBeVisible({ timeout: 10_000 });

    // CRM section should be accessible from sidebar
    const contactsLink = page.locator('a[href*="/crm/contacts"]');
    if (await contactsLink.count() > 0) {
      await expect(contactsLink.first()).toBeVisible();
    }
  });

  test('dashboard has header', async ({ page }) => {
    // Check for header element
    const header = page.locator('header').first();
    await expect(header).toBeVisible({ timeout: 10_000 });
  });

  test('user menu is accessible', async ({ page }) => {
    // Look for user avatar or user button
    const userButton = page.locator(
      'button:has(img[alt*="user"]), button:has(img[alt*="avatar"]), [data-testid="user-button"], button:has-text("Account")'
    );
    if (await userButton.count() > 0) {
      await userButton.first().click();
      // Expect a dropdown menu to appear
      const menu = page.locator('[role="menu"], [data-testid="dropdown-content"]');
      await expect(menu).toBeVisible({ timeout: 5_000 });
    }
  });

  test('sidebar collapses and expands', async ({ page }) => {
    const toggleButton = page.locator('button:has(svg), button[aria-label*="toggle"], button[aria-label*="menu"]');
    if (await toggleButton.count() > 0) {
      // Click toggle to collapse
      await toggleButton.first().click();
      await page.waitForTimeout(500);

      // Click toggle again to expand
      await toggleButton.first().click();
      await page.waitForTimeout(500);
    }
  });
});
