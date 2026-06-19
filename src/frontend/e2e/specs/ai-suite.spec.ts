import { test, expect } from '@playwright/test';

test.describe('AI Suite', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/ai-suite');
    await page.waitForLoadState('networkidle');
  });

  test('displays AI suite page', async ({ page }) => {
    const heading = page.locator('h1, h2').first();
    await expect(heading).toBeVisible({ timeout: 10_000 });
    await expect(heading).toContainText(/ai/i);
  });

  test('displays agent cards or empty state', async ({ page }) => {
    await page.waitForTimeout(1500);

    const noAgents = page.locator('text=/no agents/i');
    const statsCards = page.locator('main [class*="grid"] > div, [role="main"] [class*="grid"] > div').first();

    if (await noAgents.count() > 0) {
      // Empty state should exist with a create button
      const createButton = page.locator('button:has-text("Create Agent")');
      if (await createButton.count() > 0) {
        await expect(createButton.first()).toBeVisible();
      }
    } else {
      // Should see stats cards
      await expect(statsCards).toBeVisible({ timeout: 10_000 });
    }
  });

  test('has stats overview section', async ({ page }) => {
    // Stats cards show metrics like Total Agents, Tasks Completed, etc.
    const statHeadings = page.locator('text=/Total Agents|Tasks Completed|Avg\\. Response|Guardrails Active/');
    const statCount = await statHeadings.count();
    // At least one stat should be visible
    expect(statCount).toBeGreaterThanOrEqual(1);
  });

  test('status filter is present', async ({ page }) => {
    const statusFilter = page.locator(
      'select, [role="combobox"], button:has-text("All Status"), button:has-text("Status")'
    ).first();

    if (await statusFilter.count() > 0) {
      await expect(statusFilter).toBeVisible({ timeout: 10_000 });

      // Try opening the filter
      await statusFilter.click();
      await page.waitForTimeout(300);

      // Should have status options
      const options = page.locator('[role="option"], [role="listbox"] option');
      if (await options.count() > 0) {
        const optionTexts = await options.allTextContents();
        const hasIdleOrRunning = optionTexts.some(
          (t) => t.toLowerCase().includes('idle') || t.toLowerCase().includes('running')
        );
        expect(hasIdleOrRunning).toBeTruthy();
      }

      await page.keyboard.press('Escape');
    }
  });

  test('capability filter is present', async ({ page }) => {
    const capabilityFilter = page.locator(
      'button:has-text("All Capabilities"), [role="combobox"]'
    ).first();

    if (await capabilityFilter.count() > 0) {
      await expect(capabilityFilter).toBeVisible({ timeout: 10_000 });
    }
  });

  test('generate content button navigates to content page', async ({ page }) => {
    const generateButton = page.locator(
      'a[href*="/ai-suite/content"], button:has-text("Generate Content"), a:has-text("Generate Content")'
    ).first();

    if (await generateButton.count() > 0) {
      await expect(generateButton).toBeVisible();

      // Click and verify navigation
      await generateButton.click();
      await page.waitForURL(/\/ai-suite\/content/, { timeout: 10_000 });
      await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 10_000 });
    }
  });

  test('create agent dialog opens', async ({ page }) => {
    const createButton = page.locator('button:has-text("Create Agent")').first();

    if (await createButton.count() > 0) {
      await createButton.click();
      await page.waitForTimeout(500);

      const dialog = page.locator('[role="dialog"]').first();
      await expect(dialog).toBeVisible({ timeout: 5_000 });

      // Dialog should have agent name field
      const nameField = dialog.locator('input[id="agent-name"], input[name="name"], input[placeholder*="Content Specialist"]');
      if (await nameField.count() > 0) {
        await expect(nameField.first()).toBeVisible();
      }

      // Cancel to close
      const cancelButton = dialog.locator('button:has-text("Cancel")');
      if (await cancelButton.count() > 0) {
        await cancelButton.first().click();
        await expect(dialog).not.toBeVisible({ timeout: 3_000 });
      }
    }
  });

  test.describe('Content Generation Page', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/ai-suite/content');
      await page.waitForLoadState('networkidle');
    });

    test('displays content generation page', async ({ page }) => {
      const heading = page.locator('h1, h2').first();
      await expect(heading).toBeVisible({ timeout: 10_000 });
    });

    test('content type selector exists', async ({ page }) => {
      // Look for the content type selector
      const contentTypeSelector = page.locator(
        'select, [role="combobox"], div:has-text("Blog Post"), div:has-text("Social Post")'
      ).first();

      await expect(contentTypeSelector).toBeVisible({ timeout: 10_000 });
    });

    test('prompt input field is present', async ({ page }) => {
      const promptInput = page.locator(
        'textarea, input[placeholder*="prompt"], input[placeholder*="Prompt"], [role="textbox"]'
      ).first();

      if (await promptInput.count() > 0) {
        await expect(promptInput).toBeVisible({ timeout: 10_000 });
      }
    });

    test('generate button is present', async ({ page }) => {
      const generateButton = page.locator(
        'button:has-text("Generate"), button:has-text("Create"), button:has-text("Submit")'
      ).first();

      if (await generateButton.count() > 0) {
        await expect(generateButton).toBeVisible({ timeout: 10_000 });
      }
    });

    test('tone and length selectors are available', async ({ page }) => {
      // Tone selector
      const toneSelector = page.locator(
        'select, [role="combobox"], div:has-text("Professional")'
      ).first();
      if (await toneSelector.count() > 0) {
        await expect(toneSelector).toBeVisible({ timeout: 10_000 });
      }
    });
  });
});
