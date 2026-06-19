import { test as setup, expect } from '@playwright/test';

const authFile = 'e2e/.auth/user.json';

setup('authenticate', async ({ page }) => {
  // Start at login page
  await page.goto('/login');

  // Wait for the login form to be visible
  await page.waitForSelector('form', { timeout: 10_000 });

  // Fill in credentials
  await page.fill('input[name="email"]', 'test@aegis-mc.io');
  await page.fill('input[name="password"]', process.env.E2E_PASSWORD || 'test-password');

  // Submit the form
  await page.click('button[type="submit"]');

  // Wait for successful login — expect redirect to dashboard
  await page.waitForURL('/dashboard', { timeout: 15_000 });

  // Verify we're on the dashboard
  await expect(page.locator('h1')).toContainText(/dashboard/i);
  await expect(page.locator('body')).toContainText(/Aegis/i);

  // Save authentication state
  await page.context().storageState({ path: authFile });
});
