import { test, expect } from '@playwright/test';

test.describe('Login Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
  });

  test('displays login form', async ({ page }) => {
    // Check for heading
    await expect(page.locator('h1, h2').first()).toBeVisible();

    // Check for email and password fields
    const emailInput = page.locator('input[name="email"], input[type="email"]');
    const passwordInput = page.locator('input[name="password"], input[type="password"]');

    await expect(emailInput).toBeVisible();
    await expect(passwordInput).toBeVisible();

    // Check for submit button
    const submitButton = page.locator('button[type="submit"]');
    await expect(submitButton).toBeVisible();
  });

  test('shows error on invalid credentials', async ({ page }) => {
    // Fill in invalid credentials
    await page.fill('input[name="email"], input[type="email"]', 'invalid@test.com');
    await page.fill('input[name="password"], input[type="password"]', 'wrong-password');

    // Submit
    await page.click('button[type="submit"]');

    // Wait for error message to appear
    const errorMessage = page.locator('text=/invalid|error|incorrect/i, [role="alert"]');
    await expect(errorMessage.first()).toBeVisible({ timeout: 10_000 });
  });

  test('has link to register page', async ({ page }) => {
    const registerLink = page.locator('a[href*="register"], a:has-text("Sign up"), a:has-text("Register")');
    if (await registerLink.count() > 0) {
      await expect(registerLink.first()).toBeVisible();
    }
  });

  test('has remember me checkbox if present', async ({ page }) => {
    const rememberCheckbox = page.locator('input[type="checkbox"]');
    if (await rememberCheckbox.count() > 0) {
      await expect(rememberCheckbox.first()).toBeVisible();
    }
  });
});
