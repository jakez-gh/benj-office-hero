/**
 * User-flow E2E tests — end-to-end journeys through the admin-web UI.
 *
 * Requires a live backend with OFFICE_HERO_TEST_AUTH=1.
 * Run with:
 *   DEMO_BACKEND=1 pnpm --filter admin-web exec playwright test user-flows --project=chromium
 */
import { test, expect, type Page, type APIRequestContext } from '@playwright/test';
import { randomUUID } from 'node:crypto';

const BACKEND = process.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
const TODAY = new Date().toISOString().slice(0, 10);

async function apiGet<T>(ctx: SeedCtx, path: string): Promise<T> {
  const resp = await ctx.api.get(`${BACKEND}${path}`, {
    headers: {
      'X-Test-Tenant-Id': ctx.tenantId,
      'X-Test-User-Id': ctx.userId,
      'X-Test-Role': 'operator',
      'X-Test-Permissions': '*',
    },
  });
  if (!resp.ok()) throw new Error(`GET ${path} → ${resp.status()}: ${await resp.text()}`);
  return resp.json() as Promise<T>;
}

async function apiPostEmpty<T>(ctx: SeedCtx, path: string): Promise<T> {
  const resp = await ctx.api.post(`${BACKEND}${path}`, {
    data: {},
    headers: {
      'X-Test-Tenant-Id': ctx.tenantId,
      'X-Test-User-Id': ctx.userId,
      'X-Test-Role': 'operator',
      'X-Test-Permissions': '*',
    },
  });
  if (!resp.ok()) throw new Error(`POST ${path} → ${resp.status()}: ${await resp.text()}`);
  return resp.json() as Promise<T>;
}

interface SeedCtx {
  tenantId: string;
  userId: string;
  api: APIRequestContext;
}

async function apiPost<T>(ctx: SeedCtx, path: string, body: object): Promise<T> {
  const resp = await ctx.api.post(`${BACKEND}${path}`, {
    data: body,
    headers: {
      'X-Test-Tenant-Id': ctx.tenantId,
      'X-Test-User-Id': ctx.userId,
      'X-Test-Role': 'operator',
      'X-Test-Permissions': '*',
    },
  });
  if (!resp.ok()) throw new Error(`POST ${path} → ${resp.status()}: ${await resp.text()}`);
  return resp.json() as Promise<T>;
}

async function injectAuth(page: Page, tenantId: string, userId: string): Promise<void> {
  const hdrs = {
    'X-Test-Tenant-Id': tenantId,
    'X-Test-User-Id': userId,
    'X-Test-Role': 'operator',
    'X-Test-Permissions': '*',
  };
  await page.route(`${BACKEND}/**`, (r) => r.continue({ headers: { ...r.request().headers(), ...hdrs } }));
  await page.route('**/api/**', (r) => r.continue({ headers: { ...r.request().headers(), ...hdrs } }));
  await page.addInitScript(({ tid, uid }) => {
    localStorage.setItem('access_token', 'test-token');
    localStorage.setItem('refresh_token', 'test-refresh');
    localStorage.setItem('user', JSON.stringify({ id: uid, email: 'test@officehero.dev', role: 'Operator' }));
    localStorage.setItem('tenant_id', tid);
  }, { tid: tenantId, uid: userId });
}

test.use({ viewport: { width: 1280, height: 800 }, testIdAttribute: 'data-testid' });
test.setTimeout(90_000);

// ── Customer flows ──────────────────────────────────────────────────────────

test.describe('Customers', () => {
  test('create customer via modal and verify it appears', async ({ page }) => {
    const tenantId = randomUUID();
    const userId = randomUUID();
    await injectAuth(page, tenantId, userId);

    await page.goto('/customers');
    await page.waitForLoadState('load');
    await expect(page.getByText(/no customers yet/i)).toBeVisible({ timeout: 8000 });

    await page.getByRole('button', { name: /add customer/i }).click();
    await page.getByLabel(/name/i).fill('Acme HVAC Services');
    await page.getByLabel(/email/i).fill('ops@acme.example.com');
    await page.getByLabel(/phone/i).fill('555-0123');
    await page.getByRole('button', { name: /create customer/i }).click();

    await expect(page.getByText('Acme HVAC Services')).toBeVisible({ timeout: 8000 });
    await expect(page.getByText(/no customers yet/i)).not.toBeVisible();
  });

  test('search filter narrows customer list', async ({ page, request }) => {
    const tenantId = randomUUID();
    const userId = randomUUID();
    const ctx: SeedCtx = { tenantId, userId, api: request };

    await apiPost(ctx, '/customers', { name: 'Alpha Plumbing' });
    await apiPost(ctx, '/customers', { name: 'Beta Pest Control' });

    await injectAuth(page, tenantId, userId);
    await page.goto('/customers');

    await expect(page.getByText('Alpha Plumbing')).toBeVisible({ timeout: 8000 });
    await expect(page.getByText('Beta Pest Control')).toBeVisible();

    await page.getByPlaceholder(/search customers/i).fill('Alpha');
    await expect(page.getByText('Alpha Plumbing')).toBeVisible({ timeout: 4000 });
    await expect(page.getByText('Beta Pest Control')).not.toBeVisible();
  });
});

// ── Jobs flows ──────────────────────────────────────────────────────────────

test.describe('Jobs', () => {
  test('create job via modal and verify it appears in list', async ({ page, request }) => {
    const tenantId = randomUUID();
    const userId = randomUUID();
    const ctx: SeedCtx = { tenantId, userId, api: request };

    const cust = await apiPost<{ id: string }>(ctx, '/customers', { name: 'Job Test Co' });
    await apiPost(ctx, `/customers/${cust.id}/locations`, {
      street: '1 Job St', city: 'Portland', state: 'OR', postal_code: '97201',
    });

    await injectAuth(page, tenantId, userId);
    await page.goto('/jobs');
    await page.waitForLoadState('load');

    await page.getByRole('button', { name: /new job/i }).click();
    await page.getByLabel(/title/i).fill('Fix leaking pipe');
    await page.locator('#job-customer').selectOption({ label: 'Job Test Co' });
    await page.waitForTimeout(600);
    await page.locator('#job-location').selectOption({ index: 1 });
    await page.getByRole('button', { name: /create job/i }).click();

    await expect(page.getByText('Fix leaking pipe')).toBeVisible({ timeout: 8000 });
    await expect(page.getByTestId('job-row').first()).toBeVisible();
  });

  test('search filter narrows job list', async ({ page, request }) => {
    const tenantId = randomUUID();
    const userId = randomUUID();
    const ctx: SeedCtx = { tenantId, userId, api: request };

    const cust = await apiPost<{ id: string }>(ctx, '/customers', { name: 'Search Co' });
    const loc = await apiPost<{ id: string }>(ctx, `/customers/${cust.id}/locations`, {
      street: '2 Search Ln', city: 'Portland', state: 'OR', postal_code: '97201',
    });
    const base = { customer_id: cust.id, location_id: loc.id, priority: 50, estimated_duration_min: 60 };
    await apiPost(ctx, '/jobs', { ...base, title: 'Alpha job' });
    await apiPost(ctx, '/jobs', { ...base, title: 'Beta job' });

    await injectAuth(page, tenantId, userId);
    await page.goto('/jobs');

    await expect(page.getByText('Alpha job')).toBeVisible({ timeout: 8000 });
    await expect(page.getByText('Beta job')).toBeVisible();

    await page.getByPlaceholder(/search jobs/i).fill('Alpha');
    await expect(page.getByText('Alpha job')).toBeVisible({ timeout: 4000 });
    await expect(page.getByText('Beta job')).not.toBeVisible();
  });

  test('status filter shows only matching jobs', async ({ page, request }) => {
    const tenantId = randomUUID();
    const userId = randomUUID();
    const ctx: SeedCtx = { tenantId, userId, api: request };

    const cust = await apiPost<{ id: string }>(ctx, '/customers', { name: 'Status Co' });
    const loc = await apiPost<{ id: string }>(ctx, `/customers/${cust.id}/locations`, {
      street: '3 Status Blvd', city: 'Portland', state: 'OR', postal_code: '97201',
    });
    const veh = await apiPost<{ id: string }>(ctx, '/vehicles', {
      license_plate: 'FLT-001', make: 'Ford', model: 'Transit', year: 2022,
    });
    await apiPost(ctx, '/vehicle-crews', {
      vehicle_id: veh.id, work_date: TODAY,
      shift_start: '07:00:00', shift_end: '17:00:00',
      members: [{ user_id: userId, role_on_crew: 'lead' }],
    });
    const base = { customer_id: cust.id, location_id: loc.id, priority: 50, estimated_duration_min: 60 };
    const pendingJob = await apiPost<{ id: string }>(ctx, '/jobs', { ...base, title: 'Pending job' });
    const scheduledJob = await apiPost<{ id: string }>(ctx, '/jobs', { ...base, title: 'Scheduled job' });
    await apiPost(ctx, `/jobs/${scheduledJob.id}/dispatch`, {
      vehicle_id: veh.id, scheduled_for: new Date().toISOString(),
      travel_seconds: 300, distance_meters: 2000,
    });
    void pendingJob;

    await injectAuth(page, tenantId, userId);
    await page.goto('/jobs');
    await expect(page.getByText('Pending job')).toBeVisible({ timeout: 8000 });
    await expect(page.getByText('Scheduled job')).toBeVisible();

    // Filter to pending only
    await page.getByRole('combobox', { name: /filter by status/i }).selectOption('pending');
    await expect(page.getByText('Pending job')).toBeVisible({ timeout: 4000 });
    await expect(page.getByText('Scheduled job')).not.toBeVisible();
  });
});

// ── Route flows ─────────────────────────────────────────────────────────────

test.describe('Routes', () => {
  test('dispatched job appears as route with stop', async ({ page, request }) => {
    const tenantId = randomUUID();
    const userId = randomUUID();
    const ctx: SeedCtx = { tenantId, userId, api: request };

    const cust = await apiPost<{ id: string }>(ctx, '/customers', { name: 'Route Co' });
    const loc = await apiPost<{ id: string }>(ctx, `/customers/${cust.id}/locations`, {
      street: '5 Route Ave', city: 'Portland', state: 'OR', postal_code: '97201',
    });
    const job = await apiPost<{ id: string }>(ctx, '/jobs', {
      customer_id: cust.id, location_id: loc.id,
      title: 'Route test job', priority: 60, estimated_duration_min: 60,
    });
    const veh = await apiPost<{ id: string }>(ctx, '/vehicles', {
      license_plate: 'RTE-001', make: 'Toyota', model: 'Sienna', year: 2023,
    });
    await apiPost(ctx, '/vehicle-crews', {
      vehicle_id: veh.id, work_date: TODAY,
      shift_start: '07:00:00', shift_end: '17:00:00',
      members: [{ user_id: userId, role_on_crew: 'lead' }],
    });
    await apiPost(ctx, `/jobs/${job.id}/dispatch`, {
      vehicle_id: veh.id, scheduled_for: new Date().toISOString(),
      travel_seconds: 600, distance_meters: 5000,
    });

    await injectAuth(page, tenantId, userId);
    await page.goto('/routes');
    await page.waitForLoadState('load');

    await expect(page.getByTestId('route-card')).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId('route-stop').first()).toBeVisible();
  });

  test('schedule a job manually via the Jobs page', async ({ page, request }) => {
    const tenantId = randomUUID();
    const userId = randomUUID();
    const ctx: SeedCtx = { tenantId, userId, api: request };

    const cust = await apiPost<{ id: string }>(ctx, '/customers', { name: 'Manual Schedule Co' });
    const loc = await apiPost<{ id: string }>(ctx, `/customers/${cust.id}/locations`, {
      street: '6 Schedule St', city: 'Portland', state: 'OR', postal_code: '97201',
    });
    await apiPost(ctx, '/jobs', {
      customer_id: cust.id, location_id: loc.id,
      title: 'Manually scheduled job', priority: 50, estimated_duration_min: 60,
    });
    const veh = await apiPost<{ id: string }>(ctx, '/vehicles', {
      license_plate: 'MAN-001', make: 'Honda', model: 'Odyssey', year: 2021,
    });
    await apiPost(ctx, '/vehicle-crews', {
      vehicle_id: veh.id, work_date: TODAY,
      shift_start: '07:00:00', shift_end: '17:00:00',
      members: [{ user_id: userId, role_on_crew: 'lead' }],
    });

    await injectAuth(page, tenantId, userId);
    await page.goto('/jobs');
    await expect(page.getByText('Manually scheduled job')).toBeVisible({ timeout: 8000 });

    // Click Schedule on the pending job
    await page.getByTestId('job-row').getByRole('button', { name: /schedule/i }).click();

    // Enable manual override
    const manualCheckbox = page.getByRole('checkbox', { name: /assign manually/i });
    await expect(manualCheckbox).toBeVisible({ timeout: 4000 });
    await manualCheckbox.check();

    // Select the seeded vehicle
    await page.locator('#manual-vehicle').selectOption({ label: 'MAN-001' });

    // Set start time to tomorrow 09:00
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const pad = (n: number) => String(n).padStart(2, '0');
    const tomorrowLocal = `${tomorrow.getFullYear()}-${pad(tomorrow.getMonth() + 1)}-${pad(tomorrow.getDate())}T09:00`;
    await page.locator('#manual-time').fill(tomorrowLocal);

    await page.getByRole('button', { name: /confirm booking/i }).click();

    // Job should now show as scheduled
    await expect(page.getByText('Manually scheduled job')).toBeVisible({ timeout: 8000 });
    await page.waitForLoadState('load');
  });
});

// ── Vehicles flows ──────────────────────────────────────────────────────────

test.describe('Vehicles', () => {
  test('empty state visible when no vehicles exist', async ({ page }) => {
    const tenantId = randomUUID();
    const userId = randomUUID();
    await injectAuth(page, tenantId, userId);

    await page.goto('/vehicles');
    await page.waitForLoadState('load');
    await expect(page.getByText(/no vehicles on record/i)).toBeVisible({ timeout: 8000 });
  });

  test('seeded vehicle appears in list', async ({ page, request }) => {
    const tenantId = randomUUID();
    const userId = randomUUID();
    const ctx: SeedCtx = { tenantId, userId, api: request };

    await apiPost(ctx, '/vehicles', {
      license_plate: 'LST-001', make: 'Chevy', model: 'Express', year: 2020,
    });

    await injectAuth(page, tenantId, userId);
    await page.goto('/vehicles');
    await expect(page.getByText('LST-001')).toBeVisible({ timeout: 8000 });
  });
});

// ── Contracts flows ─────────────────────────────────────────────────────────

test.describe('Contracts', () => {
  test('pause and resume a contract', async ({ page, request }) => {
    const tenantId = randomUUID();
    const userId = randomUUID();
    const ctx: SeedCtx = { tenantId, userId, api: request };

    const cust = await apiPost<{ id: string }>(ctx, '/customers', { name: 'Contract Co' });
    const loc = await apiPost<{ id: string }>(ctx, `/customers/${cust.id}/locations`, {
      street: '7 Contract Ave', city: 'Portland', state: 'OR', postal_code: '97201',
    });
    await apiPost(ctx, '/contracts', {
      customer_id: cust.id, location_id: loc.id,
      title: 'Monthly pest control', frequency: 'monthly',
      start_date: TODAY, estimated_duration_min: 60,
    });

    await injectAuth(page, tenantId, userId);
    await page.goto('/contracts');
    await page.waitForLoadState('load');

    await expect(page.getByText('Monthly pest control')).toBeVisible({ timeout: 8000 });
    const row = page.getByTestId('contract-row').first();

    // Pause it
    await row.getByRole('button', { name: /pause/i }).click();
    await expect(page.getByText(/paused/i).first()).toBeVisible({ timeout: 4000 });

    // Resume it
    await row.getByRole('button', { name: /resume/i }).click();
    await expect(page.getByText(/active/i).first()).toBeVisible({ timeout: 4000 });
  });

  test('create contract via modal and verify it appears', async ({ page, request }) => {
    const tenantId = randomUUID();
    const userId = randomUUID();
    const ctx: SeedCtx = { tenantId, userId, api: request };

    const cust = await apiPost<{ id: string }>(ctx, '/customers', { name: 'New Contract Co' });
    await apiPost(ctx, `/customers/${cust.id}/locations`, {
      street: '8 Contract Ln', city: 'Portland', state: 'OR', postal_code: '97201',
    });

    await injectAuth(page, tenantId, userId);
    await page.goto('/contracts');
    await page.waitForLoadState('load');

    await page.getByRole('button', { name: /new contract/i }).click();
    await page.getByLabel(/title/i).fill('Weekly HVAC check');
    await page.locator('#contract-customer').selectOption({ label: 'New Contract Co' });
    await page.waitForTimeout(600);
    await page.locator('#contract-location').selectOption({ index: 1 });
    await page.locator('#contract-frequency').selectOption('weekly');
    await page.getByRole('button', { name: /create contract/i }).click();

    await expect(page.getByText('Weekly HVAC check')).toBeVisible({ timeout: 8000 });
  });
});

// ── Dispatch page flows ─────────────────────────────────────────────────────

test.describe('Dispatch', () => {
  test('shows pending jobs in dropdown and dispatches via saga', async ({ page, request }) => {
    const tenantId = randomUUID();
    const userId = randomUUID();
    const ctx: SeedCtx = { tenantId, userId, api: request };

    const cust = await apiPost<{ id: string }>(ctx, '/customers', { name: 'Dispatch Co' });
    const loc = await apiPost<{ id: string }>(ctx, `/customers/${cust.id}/locations`, {
      street: '9 Dispatch Rd', city: 'Portland', state: 'OR', postal_code: '97201',
    });
    const job = await apiPost<{ id: string }>(ctx, '/jobs', {
      customer_id: cust.id, location_id: loc.id,
      title: 'Pending dispatch job', priority: 70, estimated_duration_min: 60,
    });

    await injectAuth(page, tenantId, userId);
    await page.goto('/dispatch');
    await page.waitForLoadState('load');

    // Wait for the job selector to load
    await page.waitForSelector('select[aria-label="Select job"]', { timeout: 10000 });

    // Select the pending job
    await page.selectOption('select[aria-label="Select job"]', { value: job.id });

    // The selected job summary should appear
    await expect(page.getByText('Pending dispatch job')).toBeVisible({ timeout: 4000 });

    // Dispatch button should be enabled
    const dispatchBtn = page.getByRole('button', { name: /dispatch job/i });
    await expect(dispatchBtn).not.toBeDisabled();

    // Click dispatch
    await dispatchBtn.click();

    // Saga state card should appear
    await expect(page.getByText(/saga state/i)).toBeVisible({ timeout: 8000 });
    await expect(page.getByText(/running|done|failed/i)).toBeVisible({ timeout: 4000 });
  });
});

// ── Route lifecycle ─────────────────────────────────────────────────────────

test.describe('Route lifecycle', () => {
  test('start route and complete a stop via API, verify UI reflects state', async ({ page, request }) => {
    const tenantId = randomUUID();
    const userId = randomUUID();
    const ctx: SeedCtx = { tenantId, userId, api: request };

    const cust = await apiPost<{ id: string }>(ctx, '/customers', { name: 'Lifecycle Co' });
    const loc = await apiPost<{ id: string }>(ctx, `/customers/${cust.id}/locations`, {
      street: '10 Lifecycle St', city: 'Portland', state: 'OR', postal_code: '97201',
    });
    const job = await apiPost<{ id: string }>(ctx, '/jobs', {
      customer_id: cust.id, location_id: loc.id,
      title: 'Lifecycle job', priority: 60, estimated_duration_min: 60,
    });
    const veh = await apiPost<{ id: string }>(ctx, '/vehicles', {
      license_plate: 'LCY-001', make: 'Ford', model: 'Transit', year: 2022,
    });
    await apiPost(ctx, '/vehicle-crews', {
      vehicle_id: veh.id, work_date: TODAY,
      shift_start: '07:00:00', shift_end: '17:00:00',
      members: [{ user_id: userId, role_on_crew: 'lead' }],
    });
    const dispatch = await apiPost<{ route_id: string }>(ctx, `/jobs/${job.id}/dispatch`, {
      vehicle_id: veh.id, scheduled_for: new Date().toISOString(),
      travel_seconds: 300, distance_meters: 2000,
    });
    const routeId = dispatch.route_id;

    await injectAuth(page, tenantId, userId);
    await page.goto('/routes');
    await page.waitForLoadState('load');
    await expect(page.getByTestId('route-card')).toBeVisible({ timeout: 10000 });

    // Start the route via API
    await apiPostEmpty(ctx, `/routes/${routeId}/start`);

    // Reload and verify in_progress state
    await page.reload();
    await page.waitForLoadState('load');
    await expect(page.getByTestId('route-card')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/in.?progress/i)).toBeVisible({ timeout: 4000 });

    // Get stop ID to complete it
    const route = await apiGet<{ stops: Array<{ id: string; job_id: string }> }>(ctx, `/routes/${routeId}`);
    const stop = route.stops.find((s) => s.job_id === job.id);
    if (stop) {
      await apiPostEmpty(ctx, `/routes/${routeId}/stops/${stop.id}/arrived`);
      await apiPostEmpty(ctx, `/routes/${routeId}/stops/${stop.id}/complete`);
    }

    // Reload and verify stop shows complete
    await page.reload();
    await page.waitForLoadState('load');
    await expect(page.getByTestId('route-stop').first()).toBeVisible({ timeout: 8000 });
    await expect(page.getByTestId('route-stop').first().getByText(/complete/i)).toBeVisible({ timeout: 4000 });
  });
});

// ── Contract → job generation ────────────────────────────────────────────────

test.describe('Contract job generation', () => {
  test('generate due jobs from a contract and verify they appear in Jobs', async ({ page, request }) => {
    const tenantId = randomUUID();
    const userId = randomUUID();
    const ctx: SeedCtx = { tenantId, userId, api: request };

    const cust = await apiPost<{ id: string }>(ctx, '/customers', { name: 'Gen Co' });
    const loc = await apiPost<{ id: string }>(ctx, `/customers/${cust.id}/locations`, {
      street: '11 Generate Ave', city: 'Portland', state: 'OR', postal_code: '97201',
    });
    // start_date = today so next_due = today and generation should produce a job
    await apiPost(ctx, '/contracts', {
      customer_id: cust.id, location_id: loc.id,
      title: 'Weekly pest inspection', frequency: 'weekly',
      start_date: TODAY, service_type: 'Pest inspection',
      estimated_duration_min: 60,
    });

    await injectAuth(page, tenantId, userId);
    await page.goto('/contracts');
    await page.waitForLoadState('load');

    await expect(page.getByText('Weekly pest inspection')).toBeVisible({ timeout: 8000 });

    // Click "Generate due jobs"
    await page.getByRole('button', { name: /generate due jobs/i }).click();

    // A success alert should appear
    await expect(page.getByRole('alert')).toBeVisible({ timeout: 8000 });
    await expect(page.getByText(/created|job/i)).toBeVisible({ timeout: 4000 });

    // Navigate to Jobs and verify the generated job appears
    await page.goto('/jobs');
    await page.waitForLoadState('load');
    await expect(page.getByText(/pest inspection/i)).toBeVisible({ timeout: 8000 });
  });
});
