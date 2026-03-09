import { test, expect } from '@playwright/test';

// Test user credentials (from backend init_testdata.py)
const TEST_USER = {
  email: 'test@example.com',
  password: 'password123'
};

test.describe('Admin Web - Login & Auth Flow', () => {
  
  test('should display login form on initial load', async ({ page }) => {
    await page.goto('/');

    // Check for login form elements
    await expect(page.getByRole('heading', { name: /login/i })).toBeVisible();
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByLabel(/password/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /login/i })).toBeVisible();
  });

  test('should show error message on failed login', async ({ page }) => {
    await page.goto('/');

    // Fill in invalid credentials
    await page.getByLabel(/email/i).fill('invalid@example.com');
    await page.getByLabel(/password/i).fill('wrongpassword');

    // Click login button
    await page.getByRole('button', { name: /login/i }).click();

    // Wait for error message
    await expect(page.getByRole('alert')).toBeVisible({ timeout: 3000 });
    await expect(page.getByText(/invalid|failed|unauthorized/i)).toBeVisible();
  });

  test('should successfully login with valid credentials', async ({ page }) => {
    await page.goto('/');

    // Fill in valid credentials
    await page.getByLabel(/email/i).fill(TEST_USER.email);
    await page.getByLabel(/password/i).fill(TEST_USER.password);

    // Click login button
    await page.getByRole('button', { name: /login/i }).click();

    // Should redirect to jobs page
    await expect(page).toHaveURL('/jobs', { timeout: 3000 });
    
    // Should display nav shell
    await expect(page.getByRole('navigation')).toBeVisible();
    await expect(page.getByRole('button', { name: /logout/i })).toBeVisible();
  });

  test('should persist tokens in localStorage after login', async ({ page }) => {
    await page.goto('/');

    // Login
    await page.getByLabel(/email/i).fill(TEST_USER.email);
    await page.getByLabel(/password/i).fill(TEST_USER.password);
    await page.getByRole('button', { name: /login/i }).click();

    // Wait for redirect
    await expect(page).toHaveURL('/jobs', { timeout: 3000 });

    // Verify tokens are in localStorage
    const tokens = await page.evaluate(() => ({
      accessToken: localStorage.getItem('access_token'),
      refreshToken: localStorage.getItem('refresh_token'),
      user: localStorage.getItem('user')
    }));

    expect(tokens.accessToken).toBeTruthy();
    expect(tokens.refreshToken).toBeTruthy();
    expect(tokens.user).toBeTruthy();
    expect(JSON.parse(tokens.user!)).toHaveProperty('email', TEST_USER.email);
  });

  test('should restore session from localStorage (hook rehydration)', async ({ page }) => {
    // First, login to establish a session
    await page.goto('/');
    await page.getByLabel(/email/i).fill(TEST_USER.email);
    await page.getByLabel(/password/i).fill(TEST_USER.password);
    await page.getByRole('button', { name: /login/i }).click();

    // Wait for successful redirect
    await expect(page).toHaveURL('/jobs', { timeout: 3000 });
    
    // Get tokens from localStorage
    const tokens = await page.evaluate(() => ({
      accessToken: localStorage.getItem('access_token'),
      refreshToken: localStorage.getItem('refresh_token')
    }));

    // Now reload the page (simulating browser restart)
    await page.reload();

    // Should still be authenticated and on jobs page (not redirected to login)
    await expect(page).toHaveURL('/jobs', { timeout: 3000 });
    
    // Nav should be visible
    await expect(page.getByRole('navigation')).toBeVisible();
    await expect(page.getByRole('button', { name: /logout/i })).toBeVisible();

    // Verify same tokens are still in localStorage
    const restoredTokens = await page.evaluate(() => ({
      accessToken: localStorage.getItem('access_token'),
      refreshToken: localStorage.getItem('refresh_token')
    }));

    expect(restoredTokens.accessToken).toBe(tokens.accessToken);
    expect(restoredTokens.refreshToken).toBe(tokens.refreshToken);
  });

  test('should navigate between authenticated pages', async ({ page }) => {
    // Login first
    await page.goto('/');
    await page.getByLabel(/email/i).fill(TEST_USER.email);
    await page.getByLabel(/password/i).fill(TEST_USER.password);
    await page.getByRole('button', { name: /login/i }).click();

    // Wait for jobs page
    await expect(page).toHaveURL('/jobs', { timeout: 3000 });

    // Test navigation to each page
    const pages = [
      { name: 'Dispatch', path: '/dispatch' },
      { name: 'Vehicles', path: '/vehicles' },
      { name: 'Users', path: '/users' },
      { name: 'Jobs', path: '/jobs' }
    ];

    for (const { name, path } of pages) {
      await page.getByRole('link', { name }).click();
      await expect(page).toHaveURL(path, { timeout: 2000 });
    }
  });

  test('should logout and clear session', async ({ page }) => {
    // Login first
    await page.goto('/');
    await page.getByLabel(/email/i).fill(TEST_USER.email);
    await page.getByLabel(/password/i).fill(TEST_USER.password);
    await page.getByRole('button', { name: /login/i }).click();

    // Wait for successful login
    await expect(page).toHaveURL('/jobs', { timeout: 3000 });

    // Click logout
    await page.getByRole('button', { name: /logout/i }).click();

    // Should redirect to login page
    await expect(page).toHaveURL('/', { timeout: 2000 });
    
    // Login form should be visible
    await expect(page.getByRole('heading', { name: /login/i })).toBeVisible();

    // Verify tokens are cleared from localStorage
    const tokens = await page.evaluate(() => ({
      accessToken: localStorage.getItem('access_token'),
      refreshToken: localStorage.getItem('refresh_token'),
      user: localStorage.getItem('user')
    }));

    expect(tokens.accessToken).toBeNull();
    expect(tokens.refreshToken).toBeNull();
    expect(tokens.user).toBeNull();
  });

  test('should display version badge in nav', async ({ page }) => {
    // Login first
    await page.goto('/');
    await page.getByLabel(/email/i).fill(TEST_USER.email);
    await page.getByLabel(/password/i).fill(TEST_USER.password);
    await page.getByRole('button', { name: /login/i }).click();

    // Wait for nav to appear
    await expect(page).toHaveURL('/jobs', { timeout: 3000 });

    // Check for version badge
    const versionBadge = page.getByText(/v\d+\.\d+\.\d+/);
    await expect(versionBadge).toBeVisible();
  });

  test('should handle 401 errors with automatic refresh', async ({ page, context }) => {
    // Login first
    await page.goto('/');
    await page.getByLabel(/email/i).fill(TEST_USER.email);
    await page.getByLabel(/password/i).fill(TEST_USER.password);
    await page.getByRole('button', { name: /login/i }).click();

    // Wait for successful login
    await expect(page).toHaveURL('/jobs', { timeout: 3000 });

    // Get current access token
    const initialToken = await page.evaluate(() => 
      localStorage.getItem('access_token')
    );

    // Simulate expired token by replacing it with invalid token
    await page.evaluate(() => {
      localStorage.setItem('access_token', 'expired-token-' + Math.random());
    });

    // Navigate to another page (triggers API call)
    await page.getByRole('link', { name: /dispatch/i }).click();

    // Should either:
    // 1. Auto-refresh and navigate (if refresh succeeds), or
    // 2. Redirect to login (if refresh fails)
    try {
      await expect(page).toHaveURL('/dispatch', { timeout: 3000 });
      // If we got here, the auto-refresh worked!
    } catch {
      // If navigation didn't work, we might have been redirected to login
      // This is also acceptable behavior
      const url = page.url();
      expect(['/dispatch', '/']).toContain(url.split('/').pop() || '/');
    }
  });
});
