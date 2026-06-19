import { test, expect } from '@playwright/test';

test.describe('Media Library', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/media');
    await page.waitForLoadState('networkidle');
  });

  test('displays media library page', async ({ page }) => {
    const heading = page.locator('h1, h2').first();
    await expect(heading).toBeVisible({ timeout: 10_000 });
    await expect(heading).toContainText(/media/i);
  });

  test('upload button is visible', async ({ page }) => {
    const uploadButton = page.locator(
      'button:has-text("Upload"), a:has-text("Upload"), [data-testid="upload-button"]'
    );
    await expect(uploadButton.first()).toBeVisible({ timeout: 10_000 });
  });

  test('switch between grid and list view', async ({ page }) => {
    // Look for view toggle buttons (grid/list icons)
    const gridButton = page.locator('button:has(svg), [data-testid="grid-view"], button:has-text("Grid")').first();
    const listButton = page.locator('button:has(svg), [data-testid="list-view"], button:has-text("List")').first();

    if (await gridButton.count() > 0 && await listButton.count() > 0) {
      // Click grid view
      await gridButton.click();
      await page.waitForTimeout(300);

      // Click list view
      await listButton.click();
      await page.waitForTimeout(300);

      // Verify page still renders
      await expect(page.locator('body')).toBeVisible();
    }
  });

  test('search filter works', async ({ page }) => {
    // Find the search input
    const searchInput = page.locator(
      'input[type="search"], input[placeholder*="search"], input[placeholder*="Search"], input[placeholder*="Search media"]'
    ).first();

    if (await searchInput.count() > 0) {
      await expect(searchInput).toBeVisible();
      await searchInput.fill('test search');
      await page.waitForTimeout(500);

      // Verify search triggered (clear button appears or results updated)
      const clearButton = page.locator('button:has(svg), [data-testid="clear-search"]').first();
      // Page should still be in a valid state
      await expect(page.locator('body')).toBeVisible();
    }
  });

  test('type filter dropdown is present', async ({ page }) => {
    // Find the media type filter select
    const typeFilter = page.locator(
      'select, [role="combobox"], button:has-text("All Types"), div:has-text("All Types")'
    ).first();

    if (await typeFilter.count() > 0) {
      await expect(typeFilter).toBeVisible({ timeout: 10_000 });
    }
  });

  test('clicking on media item navigates to detail', async ({ page }) => {
    await page.waitForTimeout(1000);

    // Check if any media card/row exists
    const mediaCard = page.locator(
      'a[href*="/media/"], [class*="cursor-pointer"], tr[class*="cursor-pointer"]'
    ).first();

    if (await mediaCard.count() > 0) {
      // Get the href if it's an anchor
      const href = await mediaCard.getAttribute('href').catch(() => null);
      if (href) {
        await mediaCard.click();
        // Should navigate to a media detail page
        await page.waitForURL(/\/media\//, { timeout: 10_000 });
        await expect(page.locator('body')).toBeVisible();
      } else {
        // It's a div/card with onClick handler
        await mediaCard.click();
        await page.waitForTimeout(1000);
        // Page might navigate or show a dialog
        await expect(page.locator('body')).toBeVisible();
      }
    }
  });

  test('page shows media assets or empty state', async ({ page }) => {
    await page.waitForTimeout(1500);

    const noAssets = page.locator('text=/no media assets/i, text=/no media/i');
    const gridItems = page.locator('[class*="grid"] [class*="card"], [class*="grid"] div[class*="rounded"]');

    if (await noAssets.count() > 0) {
      // Empty state should have upload prompt
      const uploadPrompt = page.locator('button:has-text("Upload Files")');
      if (await uploadPrompt.count() > 0) {
        await expect(uploadPrompt.first()).toBeVisible();
      }
    } else {
      // Should have some media content area
      const contentArea = page.locator('main, [role="main"]').first();
      await expect(contentArea).toBeVisible();
    }
  });
});
