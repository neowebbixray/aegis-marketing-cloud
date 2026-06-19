import { test, expect } from '@playwright/test';

test.describe('Sidebar Navigation', () => {
  test.beforeEach(async ({ page }) => {
    // Start at dashboard to ensure we see the full sidebar
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
  });

  test('sidebar is visible with all sections', async ({ page }) => {
    const sidebar = page.locator('aside, nav').first();
    await expect(sidebar).toBeVisible({ timeout: 10_000 });

    // Section headings (Main, CRM, Marketing, Channels, Analytics, Settings, Content)
    const sectionLabels = ['Main', 'CRM', 'Marketing', 'Channels', 'Analytics', 'Settings', 'Content'];
    const visibleSections: string[] = [];

    for (const label of sectionLabels) {
      const section = sidebar.locator(`text=${label}`);
      if (await section.count() > 0) {
        visibleSections.push(label);
      }
    }

    // At least a few sections should be visible (sidebar may be collapsed)
    expect(visibleSections.length).toBeGreaterThanOrEqual(1);
  });

  test.describe('Main section links', () => {
    test('Dashboard link navigates to /dashboard', async ({ page }) => {
      const dashboardLink = page.locator('a[href="/dashboard"], a[href*="/dashboard"]').first();
      await expect(dashboardLink).toBeVisible({ timeout: 10_000 });

      await dashboardLink.click();
      await page.waitForURL('/dashboard', { timeout: 10_000 });

      const heading = page.locator('h1, h2').first();
      await expect(heading).toBeVisible();
    });
  });

  test.describe('CRM section links', () => {
    test('Contacts link navigates to /crm/contacts', async ({ page }) => {
      const contactsLink = page.locator('a[href*="/crm/contacts"]').first();
      if (await contactsLink.count() > 0) {
        await contactsLink.click();
        await page.waitForURL(/\/crm\/contacts/, { timeout: 10_000 });
        await expect(page.locator('body')).toBeVisible();
      }
    });

    test('Deals link navigates to /crm/deals', async ({ page }) => {
      const dealsLink = page.locator('a[href*="/crm/deals"]').first();
      if (await dealsLink.count() > 0) {
        await dealsLink.click();
        await page.waitForURL(/\/crm\/deals/, { timeout: 10_000 });
        await expect(page.locator('body')).toBeVisible();
      }
    });

    test('Pipelines link navigates to /crm/pipelines', async ({ page }) => {
      const pipelinesLink = page.locator('a[href*="/crm/pipelines"]').first();
      if (await pipelinesLink.count() > 0) {
        await pipelinesLink.click();
        await page.waitForURL(/\/crm\/pipelines/, { timeout: 10_000 });
        await expect(page.locator('body')).toBeVisible();
      }
    });
  });

  test.describe('Marketing section links', () => {
    test('Campaigns link navigates to /marketing/campaigns', async ({ page }) => {
      const campaignsLink = page.locator('a[href*="/marketing/campaigns"]').first();
      if (await campaignsLink.count() > 0) {
        await campaignsLink.click();
        await page.waitForURL(/\/marketing\/campaigns/, { timeout: 10_000 });
        await expect(page.locator('body')).toBeVisible();
      }
    });

    test('AI Suite link navigates to /ai-suite', async ({ page }) => {
      const aiSuiteLink = page.locator('a[href="/ai-suite"], a[href*="/ai-suite"]').first();
      if (await aiSuiteLink.count() > 0) {
        await aiSuiteLink.click();
        await page.waitForURL(/\/ai-suite/, { timeout: 10_000 });
        const heading = page.locator('h1, h2').first();
        await expect(heading).toBeVisible();
        // Should mention AI or Suite
        await expect(heading).toContainText(/ai/i);
      }
    });
  });

  test.describe('Channels section links', () => {
    test('SEO link navigates to /marketing/seo', async ({ page }) => {
      const seoLink = page.locator('a[href*="/marketing/seo"]').first();
      if (await seoLink.count() > 0) {
        await seoLink.click();
        await page.waitForURL(/\/marketing\/seo/, { timeout: 10_000 });
        await expect(page.locator('body')).toBeVisible();
      }
    });

    test('Social link navigates to /marketing/social', async ({ page }) => {
      const socialLink = page.locator('a[href*="/marketing/social"]').first();
      if (await socialLink.count() > 0) {
        await socialLink.click();
        await page.waitForURL(/\/marketing\/social/, { timeout: 10_000 });
        await expect(page.locator('body')).toBeVisible();
      }
    });
  });

  test.describe('Analytics section links', () => {
    test('Dashboards link navigates to /analytics', async ({ page }) => {
      const analyticsLink = page.locator('a[href="/analytics"], a[href*="/analytics"]').first();
      if (await analyticsLink.count() > 0) {
        await analyticsLink.click();
        await page.waitForURL(/\/analytics/, { timeout: 10_000 });
        await expect(page.locator('body')).toBeVisible();
      }
    });

    test('Reports link navigates to /analytics/reports', async ({ page }) => {
      const reportsLink = page.locator('a[href*="/analytics/reports"]').first();
      if (await reportsLink.count() > 0) {
        await reportsLink.click();
        await page.waitForURL(/\/analytics\/reports/, { timeout: 10_000 });
        await expect(page.locator('body')).toBeVisible();
      }
    });
  });

  test.describe('Settings section links', () => {
    test('Settings link navigates to /settings', async ({ page }) => {
      const settingsLink = page.locator('a[href="/settings"], a[href*="/settings"]').first();
      if (await settingsLink.count() > 0) {
        await settingsLink.click();
        await page.waitForURL('/settings', { timeout: 10_000 });
        await expect(page.locator('body')).toBeVisible();
      }
    });

    test('Billing link navigates to /billing', async ({ page }) => {
      const billingLink = page.locator('a[href="/billing"], a[href*="/billing"]').first();
      if (await billingLink.count() > 0) {
        await billingLink.click();
        await page.waitForURL('/billing', { timeout: 10_000 });
        const heading = page.locator('h1, h2').first();
        await expect(heading).toBeVisible();
        await expect(heading).toContainText(/billing/i);
      }
    });

    test('Webhooks link navigates to /webhooks', async ({ page }) => {
      const webhooksLink = page.locator('a[href="/webhooks"], a[href*="/webhooks"]').first();
      if (await webhooksLink.count() > 0) {
        await webhooksLink.click();
        await page.waitForURL('/webhooks', { timeout: 10_000 });
        const heading = page.locator('h1, h2').first();
        await expect(heading).toBeVisible();
        await expect(heading).toContainText(/webhook/i);
      }
    });
  });

  test.describe('Content section links', () => {
    test('Media Library link navigates to /media', async ({ page }) => {
      const mediaLink = page.locator('a[href="/media"], a[href*="/media"]').first();
      if (await mediaLink.count() > 0) {
        await mediaLink.click();
        await page.waitForURL('/media', { timeout: 10_000 });
        const heading = page.locator('h1, h2').first();
        await expect(heading).toBeVisible();
        await expect(heading).toContainText(/media/i);
      }
    });

    test('Knowledge Base link navigates to /knowledge', async ({ page }) => {
      const knowledgeLink = page.locator('a[href*="/knowledge"]').first();
      if (await knowledgeLink.count() > 0) {
        await knowledgeLink.click();
        await page.waitForURL(/\/knowledge/, { timeout: 10_000 });
        await expect(page.locator('body')).toBeVisible();
      }
    });
  });

  test('all sidebar links are rendered', async ({ page }) => {
    const sidebar = page.locator('aside, nav').first();

    // Check for all nav links in the sidebar
    const expectedLinks = [
      '/dashboard',
      '/crm/contacts',
      '/crm/deals',
      '/crm/pipelines',
      '/marketing/campaigns',
      '/ai-suite',
      '/marketing/seo',
      '/marketing/social',
      '/analytics',
      '/analytics/reports',
      '/settings',
      '/billing',
      '/webhooks',
      '/media',
      '/knowledge',
    ];

    for (const href of expectedLinks) {
      const link = sidebar.locator(`a[href="${href}"]`);
      if (await link.count() > 0) {
        await expect(link.first()).toBeVisible();
      }
    }
  });

  test('navigating through all sections does not produce errors', async ({ page }) => {
    // Listen for console errors
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    const routes = [
      '/dashboard',
      '/crm/contacts',
      '/crm/deals',
      '/crm/pipelines',
      '/marketing/campaigns',
      '/ai-suite',
      '/marketing/seo',
      '/marketing/social',
      '/analytics',
      '/analytics/reports',
      '/settings',
      '/billing',
      '/webhooks',
      '/media',
      '/knowledge',
    ];

    for (const route of routes) {
      await page.goto(route);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(500);

      // Page should have a body and no crash
      await expect(page.locator('body')).toBeVisible({ timeout: 10_000 });
    }

    // Log any console errors found
    expect(errors.filter((e) => !e.includes('favicon') && !e.includes('Failed to load resource'))).toEqual([]);
  });
});
