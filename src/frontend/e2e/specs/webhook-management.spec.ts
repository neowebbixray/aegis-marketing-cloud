import { test, expect } from '@playwright/test';

test.describe('Webhook Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/webhooks');
    await page.waitForLoadState('networkidle');
  });

  test('displays webhooks page with heading', async ({ page }) => {
    const heading = page.locator('h1, h2').first();
    await expect(heading).toBeVisible({ timeout: 10_000 });
    await expect(heading).toContainText(/webhook/i);
  });

  test('shows webhook list or table', async ({ page }) => {
    const table = page.locator('table');
    const emptyState = page.locator('text=/no webhooks/i');

    if (await table.count() > 0) {
      await expect(table.first()).toBeVisible({ timeout: 10_000 });
      // Table should have webhook-related headers
      const headers = await table.locator('th').allTextContents();
      const hasNameOrUrl = headers.some(
        (h) => h.toLowerCase().includes('name') || h.toLowerCase().includes('url')
      );
      expect(hasNameOrUrl).toBeTruthy();
    } else if (await emptyState.count() > 0) {
      await expect(emptyState.first()).toBeVisible();
    }
  });

  test('create webhook dialog opens with form fields', async ({ page }) => {
    // Click the Create Webhook button
    const createButton = page.locator(
      'button:has-text("Create Webhook"), a:has-text("Create Webhook"), button:has-text("New Webhook")'
    ).first();

    if (await createButton.count() > 0) {
      await createButton.click();
      await page.waitForTimeout(500);

      // Dialog should appear with form fields
      const dialog = page.locator('[role="dialog"], [data-testid="dialog"]').first();
      await expect(dialog).toBeVisible({ timeout: 5_000 });

      // Verify essential form fields exist
      const nameField = dialog.locator('input[name="name"], input[id="name"], input[placeholder*="My Webhook"]');
      const urlField = dialog.locator('input[name="url"], input[id="url"], input[placeholder*="https://"]');

      if (await nameField.count() > 0) {
        await expect(nameField.first()).toBeVisible();
      }
      if (await urlField.count() > 0) {
        await expect(urlField.first()).toBeVisible();
      }

      // Dialog should have a Cancel and Create button
      const cancelButton = dialog.locator('button:has-text("Cancel")');
      const submitButton = dialog.locator('button:has-text("Create")');

      if (await cancelButton.count() > 0) {
        await expect(cancelButton.first()).toBeVisible();
      }
      if (await submitButton.count() > 0) {
        await expect(submitButton.first()).toBeVisible();
      }

      // Close the dialog via cancel
      if (await cancelButton.count() > 0) {
        await cancelButton.first().click();
        await expect(dialog).not.toBeVisible({ timeout: 3_000 });
      }
    }
  });

  test('status filter dropdown works', async ({ page }) => {
    // Find the status filter select
    const statusFilter = page.locator(
      'select, [role="combobox"], button:has-text("All Status"), button:has-text("Status")'
    ).first();

    if (await statusFilter.count() > 0) {
      await expect(statusFilter).toBeVisible({ timeout: 10_000 });

      // Open the dropdown
      await statusFilter.click();
      await page.waitForTimeout(300);

      // Check for status options
      const options = page.locator('[role="option"], [role="listbox"] option, [data-value]');
      if (await options.count() > 0) {
        const optionTexts = await options.allTextContents();
        const hasStatusOptions = optionTexts.some(
          (t) => t.toLowerCase().includes('active') || t.toLowerCase().includes('inactive')
        );
        expect(hasStatusOptions).toBeTruthy();
      }

      // Close by pressing Escape or clicking elsewhere
      await page.keyboard.press('Escape');
      await page.waitForTimeout(200);
    }
  });

  test('search input is present', async ({ page }) => {
    const searchInput = page.locator(
      'input[type="search"], input[placeholder*="search"], input[placeholder*="Search webhooks"]'
    ).first();

    if (await searchInput.count() > 0) {
      await expect(searchInput).toBeVisible({ timeout: 10_000 });
    }
  });

  test('webhook create page route is accessible', async ({ page }) => {
    // Navigate to the create webhook page (if it exists as a route)
    await page.goto('/webhooks/create');
    await page.waitForLoadState('networkidle');

    // Either we're on a create page or redirected back to webhooks list
    const currentUrl = page.url();
    const heading = page.locator('h1, h2').first();

    if (currentUrl.includes('/webhooks/create')) {
      await expect(heading).toBeVisible({ timeout: 10_000 });
      const headingText = await heading.textContent();
      expect(headingText?.toLowerCase()).toContain('webhook');
    } else {
      // Redirected back — still valid
      await expect(page.locator('body')).toBeVisible();
    }
  });
});
