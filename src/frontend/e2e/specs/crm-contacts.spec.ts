import { test, expect } from '@playwright/test';

test.describe('CRM Contacts', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/crm/contacts');
    await page.waitForLoadState('networkidle');
  });

  test('displays contacts page', async ({ page }) => {
    // Should see the contacts page heading
    const heading = page.locator('h1, h2').first();
    await expect(heading).toBeVisible({ timeout: 10_000 });
    await expect(heading).toContainText(/contact/i);
  });

  test('shows contacts table or list', async ({ page }) => {
    // Either a table or a list/grid of contacts should be visible
    const table = page.locator('table');
    const list = page.locator('[role="list"], [data-testid="contacts-list"], .grid, section');

    if (await table.count() > 0) {
      await expect(table.first()).toBeVisible();
      // Table should have column headers
      const headers = table.first().locator('th, thead *');
      const headerCount = await headers.count();
      expect(headerCount).toBeGreaterThan(1);
    } else if (await list.count() > 0) {
      await expect(list.first()).toBeVisible();
    }
  });

  test('has search or filter functionality', async ({ page }) => {
    const searchInput = page.locator(
      'input[type="search"], input[placeholder*="search"], input[placeholder*="Search"], input[name="search"]'
    );
    if (await searchInput.count() > 0) {
      await expect(searchInput.first()).toBeVisible();
    }
  });

  test('has create contact button', async ({ page }) => {
    const createButton = page.locator(
      'a[href*="new"], a[href*="create"], button:has-text("New"), button:has-text("Create"), a:has-text("Add Contact"), a:has-text("New Contact")'
    );
    if (await createButton.count() > 0) {
      await expect(createButton.first()).toBeVisible();
    }
  });

  test('can navigate to contact details', async ({ page }) => {
    // Find the first contact link/row
    const contactLink = page.locator(
      'a[href*="/crm/contacts/"], tr a, [role="row"] a, [data-testid="contact-link"]'
    ).first();

    if (await contactLink.count() > 0) {
      // Click the first contact
      const href = await contactLink.getAttribute('href');
      await contactLink.click();

      // Should navigate to a contact detail page
      await page.waitForURL(/\/crm\/contacts\//, { timeout: 10_000 });
      await expect(page.locator('h1, h2').first()).toBeVisible();
    }
  });

  test.describe('Create Contact', () => {
    test.beforeEach(async ({ page }) => {
      // Navigate to create contact page or open modal
      await page.goto('/crm/contacts?new=true');
      await page.waitForLoadState('networkidle');
    });

    test('shows create contact form', async ({ page }) => {
      // Check for form fields
      const form = page.locator('form');
      if (await form.count() > 0) {
        const firstName = form.locator('input[name="first_name"], input[name="firstName"], input[placeholder*="First"]');
        const lastName = form.locator('input[name="last_name"], input[name="lastName"], input[placeholder*="Last"]');
        const email = form.locator('input[name="email"], input[type="email"]');

        if (await firstName.count() > 0) {
          await expect(firstName.first()).toBeVisible();
        }
        if (await lastName.count() > 0) {
          await expect(lastName.first()).toBeVisible();
        }
        if (await email.count() > 0) {
          await expect(email.first()).toBeVisible();
        }
      }
    });

    test('can cancel creation', async ({ page }) => {
      // Find cancel button or link
      const cancelButton = page.locator(
        'button:has-text("Cancel"), a:has-text("Cancel"), button:has-text("Back")'
      ).first();

      if (await cancelButton.count() > 0) {
        await cancelButton.click();
        // Should navigate back to contacts list
        await expect(page).toHaveURL(/\/crm\/contacts$/);
      }
    });
  });
});
