import { test, expect } from '@playwright/test';

const TEST_USER = { email: 'test@example.com', password: 'password123' };
const SCREENSHOT_DIR = 'demo-recordings';

/**
 * Log in and wait for the nav shell to appear.
 * After login the BrowserRouter mounts and "/" renders JobsPage,
 * so we check for navigation presence rather than a specific URL.
 */
async function login(page: import('@playwright/test').Page) {
  await page.goto('/');
  await page.getByLabel(/email/i).fill(TEST_USER.email);
  await page.getByLabel(/password/i).fill(TEST_USER.password);
  await page.getByRole('button', { name: /login/i }).click();
  await expect(page.getByRole('navigation')).toBeVisible({ timeout: 5000 });
}

test.describe('DoD Screenshot Capture', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('capture jobs page', async ({ page }) => {
    // After login "/" renders JobsPage
    await expect(page.getByRole('heading', { name: /jobs/i })).toBeVisible({ timeout: 3000 });
    await page.waitForTimeout(1500);
    await page.screenshot({
      path: `${SCREENSHOT_DIR}/jobs-page.png`,
      fullPage: true,
    });
  });

  test('capture dispatch page', async ({ page }) => {
    await page.goto('/dispatch');
    await expect(page.getByRole('heading', { name: /dispatch/i })).toBeVisible({ timeout: 3000 });
    await page.waitForTimeout(1500);
    await page.screenshot({
      path: `${SCREENSHOT_DIR}/dispatch-page.png`,
      fullPage: true,
    });
  });

  test('capture users page', async ({ page }) => {
    await page.goto('/users');
    await expect(page.getByRole('heading', { name: /users/i })).toBeVisible({ timeout: 3000 });
    await page.waitForTimeout(1500);
    await page.screenshot({
      path: `${SCREENSHOT_DIR}/users-page.png`,
      fullPage: true,
    });
  });

  test('capture vehicles page', async ({ page }) => {
    await page.goto('/vehicles');
    await expect(page.getByRole('heading', { name: /vehicles/i })).toBeVisible({ timeout: 3000 });
    await page.waitForTimeout(1500);
    await page.screenshot({
      path: `${SCREENSHOT_DIR}/vehicles-page.png`,
      fullPage: true,
    });
  });
});
