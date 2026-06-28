import { test, expect, type Page, type APIRequestContext } from '@playwright/test';
import { randomUUID } from 'node:crypto';

/**
 * Video demo flows for Office Hero admin-web.
 *
 * Each test walks through a real end-to-end scenario against a live backend.
 * Data is seeded via the API before the browser navigates so every page shows
 * real data rather than empty/error states.
 *
 * Run with video recording:
 *   RECORD_VIDEO=1 pnpm --filter admin-web exec playwright test demo-flows --project=chromium
 *
 * Videos are saved to apps/admin-web/test-results/.
 */

const BACKEND = process.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

const TODAY = new Date().toISOString().slice(0, 10);
const TWO_MONTHS_AGO = (() => {
  const d = new Date();
  d.setMonth(d.getMonth() - 2);
  return d.toISOString().slice(0, 10);
})();

function nowAt(hour: number): string {
  const d = new Date();
  d.setUTCHours(hour, 0, 0, 0);
  return d.toISOString();
}

// ── Seed helpers ────────────────────────────────────────────────────────────

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
  if (!resp.ok()) {
    const text = await resp.text();
    throw new Error(`POST ${path} → ${resp.status()}: ${text}`);
  }
  return resp.json() as Promise<T>;
}

async function apiPostEmpty<T>(ctx: SeedCtx, path: string): Promise<T> {
  return apiPost<T>(ctx, path, {});
}

async function seedScenario(ctx: SeedCtx) {
  const cust = await apiPost<{ id: string }>(ctx, '/customers', {
    name: 'Riverside Cleaning Co',
    email: 'ops@riverside.example.com',
    phone: '+1-555-0100',
  });
  const loc = await apiPost<{ id: string }>(ctx, `/customers/${cust.id}/locations`, {
    street: '123 Main St', city: 'Portland', state: 'OR', postal_code: '97201',
  });
  const job1 = await apiPost<{ id: string }>(ctx, '/jobs', {
    customer_id: cust.id, location_id: loc.id,
    title: 'Morning deep clean', service_type: 'Deep cleaning',
    priority: 60, estimated_duration_min: 90,
  });
  const job2 = await apiPost<{ id: string }>(ctx, '/jobs', {
    customer_id: cust.id, location_id: loc.id,
    title: 'Afternoon touch-up', service_type: 'Touch-up',
    priority: 40, estimated_duration_min: 60,
  });
  const veh = await apiPost<{ id: string }>(ctx, '/vehicles', {
    license_plate: 'DEMO-001', make: 'Toyota', model: 'Sienna', year: 2023,
  });
  await apiPost(ctx, '/vehicle-crews', {
    vehicle_id: veh.id, work_date: TODAY,
    shift_start: '07:00:00', shift_end: '17:00:00',
    members: [{ user_id: ctx.userId, role_on_crew: 'lead' }],
  });
  const disp = await apiPost<{ route_id: string }>(ctx, `/jobs/${job1.id}/dispatch`, {
    vehicle_id: veh.id, scheduled_for: nowAt(9),
    travel_seconds: 900, distance_meters: 8000,
  });
  await apiPost(ctx, `/jobs/${job2.id}/dispatch`, {
    vehicle_id: veh.id, scheduled_for: nowAt(13),
    travel_seconds: 600, distance_meters: 5000,
  });
  const contract = await apiPost<{ id: string }>(ctx, '/contracts', {
    customer_id: cust.id, location_id: loc.id,
    title: 'Monthly cleaning plan', frequency: 'monthly',
    start_date: TWO_MONTHS_AGO, service_type: 'Deep cleaning',
    estimated_duration_min: 90,
  });
  return { cust, loc, job1, job2, veh, routeId: disp.route_id, contract };
}

// ── Auth injection ──────────────────────────────────────────────────────────

const TEST_HEADERS = (tenantId: string, userId: string) => ({
  'X-Test-Tenant-Id': tenantId,
  'X-Test-User-Id': userId,
  'X-Test-Role': 'operator',
  'X-Test-Permissions': '*',
});

async function injectAuth(page: Page, tenantId: string, userId: string): Promise<void> {
  // Two route patterns are needed because the app uses two different clients:
  //   src/api.ts          → direct http://localhost:8000/**  (CORS-enabled backend)
  //   @office-hero/api-client → /api/** via Vite proxy        (same-origin)
  // Both must receive X-Test-* headers so the backend can identify the tenant.
  //
  // Strip the Authorization header: auth.tsx sets "Bearer demo-video-token" from
  // localStorage, which the JWT middleware sees as an invalid token and clears
  // request.state — overriding what TestAuthMiddleware already set. Removing it
  // lets TestAuth's X-Test-* headers be the sole identity signal.
  const hdrs = TEST_HEADERS(tenantId, userId);
  function mergeHeaders(existing: Record<string, string>) {
    const merged = { ...existing, ...hdrs };
    delete merged['authorization'];
    delete merged['Authorization'];
    return merged;
  }

  // Match direct backend calls regardless of whether the app uses 127.0.0.1 or localhost
  for (const pattern of [`${BACKEND}/**`, 'http://localhost:8000/**', '**/api/**']) {
    await page.route(pattern, async (route) => {
      await route.continue({ headers: mergeHeaders(route.request().headers()) });
    });
  }

  // Seed localStorage so the app treats the session as authenticated.
  await page.addInitScript(({ tid, uid }) => {
    localStorage.setItem('access_token', 'demo-video-token');
    localStorage.setItem('refresh_token', 'demo-video-refresh');
    localStorage.setItem(
      'user',
      JSON.stringify({ id: uid, email: 'demo@officehero.dev', role: 'operator' })
    );
    // Expose tenant for any component that reads it
    localStorage.setItem('tenant_id', tid);
  }, { tid: tenantId, uid: userId });
}

async function pause(ms = 800): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

// ── Demo flow ───────────────────────────────────────────────────────────────

// viewport and video are set via playwright.config.ts projects or RECORD_VIDEO env var
test.use({ viewport: { width: 1280, height: 800 }, testIdAttribute: 'data-testid' });
// Each demo navigates multiple pages with deliberate pauses for video capture
test.setTimeout(120_000);

test.describe('Demo flows', () => {

  test('Demo 1 — Jobs & Dispatch overview', async ({ page, request }) => {
    const tenantId = randomUUID();
    const userId = randomUUID();
    const ctx: SeedCtx = { tenantId, userId, api: request };

    // Seed data before browser opens
    const { cust, loc, job2, routeId, contract: _c } = await seedScenario(ctx);
    void [job2, _c]; // referenced for completeness

    await injectAuth(page, tenantId, userId);

    // — Jobs page —
    await page.goto('/jobs');
    await page.waitForLoadState('load');
    await pause(800);

    // Show both jobs in the list
    await expect(page.getByText('Morning deep clean')).toBeVisible({ timeout: 8000 });
    await expect(page.getByText('Afternoon touch-up')).toBeVisible({ timeout: 4000 });
    await pause(1500);

    // Filter to scheduled jobs
    await page.getByRole('combobox').selectOption('scheduled');
    await page.waitForLoadState('load');
    await pause(1200);

    // — Routes page —
    await page.goto('/routes');
    await page.waitForLoadState('load');
    await pause(800);
    // At least one route should appear
    await page.waitForSelector('[data-testid="route-row"], tr', { timeout: 8000 }).catch(() => null);
    await pause(1500);
    void routeId; // seeded above

    // — Vehicles page —
    await page.goto('/vehicles');
    await page.waitForLoadState('load');
    await pause(800);
    await expect(page.getByText('DEMO-001')).toBeVisible({ timeout: 8000 });
    await pause(1500);

    // — Dispatch page (new dropdown UI) —
    // Create an extra pending job — the two seeded jobs are already scheduled above.
    const pendingJob = await apiPost<{ id: string }>(ctx, '/jobs', {
      customer_id: cust.id, location_id: loc.id,
      title: 'Emergency repair call', service_type: 'Emergency',
      priority: 90, estimated_duration_min: 45,
    });

    await page.goto('/dispatch');
    await page.waitForLoadState('load');
    await pause(800);
    // Wait for the job dropdown to populate
    await page.waitForSelector('select[aria-label="Select job"]', { timeout: 10000 });
    await pause(500);
    // Filter by title to isolate the emergency job, then select it
    await page.getByLabel('Search jobs').fill('Emergency');
    await pause(400);
    await page.selectOption('select[aria-label="Select job"]', { value: pendingJob.id });
    await pause(800);
    // Submit dispatch
    await page.getByRole('button', { name: /dispatch job/i }).click();
    await page.waitForLoadState('load');
    await pause(2000);

    await pause(1000);
  });

  test('Demo 2 — Contracts lifecycle', async ({ page, request }) => {
    const tenantId = randomUUID();
    const userId = randomUUID();
    const ctx: SeedCtx = { tenantId, userId, api: request };

    await seedScenario(ctx);
    await injectAuth(page, tenantId, userId);

    // — Customers page —
    await page.goto('/customers');
    await page.waitForLoadState('load');
    await pause(800);
    await expect(page.getByText('Riverside Cleaning Co')).toBeVisible({ timeout: 8000 });
    await pause(1500);

    // — Contracts page —
    await page.goto('/contracts');
    await page.waitForLoadState('load');
    await pause(800);
    await expect(page.getByText('Monthly cleaning plan')).toBeVisible({ timeout: 8000 });
    await pause(1500);

    // — Jobs generated from contract —
    await page.goto('/jobs');
    await page.waitForLoadState('load');
    await pause(800);
    await expect(page.getByText('Morning deep clean')).toBeVisible({ timeout: 8000 });
    await pause(2000);
  });

  test('Demo 3 — Route management (resequence & complete)', async ({ page, request }) => {
    const tenantId = randomUUID();
    const userId = randomUUID();
    const ctx: SeedCtx = { tenantId, userId, api: request };

    const { routeId, job1, job2 } = await seedScenario(ctx);
    await injectAuth(page, tenantId, userId);

    // — Routes page —
    await page.goto('/routes');
    await page.waitForLoadState('load');
    await pause(800);
    await page.waitForSelector('tr', { timeout: 8000 }).catch(() => null);
    await pause(1500);

    // Via API: start the route so stop controls appear
    await apiPostEmpty(ctx, `/routes/${routeId}/start`);

    // Reload to pick up in_progress state
    await page.reload();
    await page.waitForLoadState('load');
    await pause(1500);

    // Complete stop 1 via API and reload to show progress
    const startedRoute = await (async () => {
      const resp = await ctx.api.get(`${BACKEND}/routes/${routeId}`, {
        headers: {
          'X-Test-Tenant-Id': tenantId,
          'X-Test-User-Id': userId,
          'X-Test-Role': 'operator',
          'X-Test-Permissions': '*',
        },
      });
      return resp.json() as Promise<{ stops: Array<{ id: string; job_id: string }> }>;
    })();

    const stop1 = startedRoute.stops.find((s) => s.job_id === job1.id);
    if (stop1) {
      await apiPostEmpty(ctx, `/routes/${routeId}/stops/${stop1.id}/arrived`);
      await apiPostEmpty(ctx, `/routes/${routeId}/stops/${stop1.id}/complete`);
    }
    void job2;

    await page.reload();
    await page.waitForLoadState('load');
    await pause(2000);
  });

  test('Demo 4 — Tenants admin + Operator Dashboard', async ({ page, request }) => {
    const tenantId = randomUUID();
    const userId = randomUUID();
    const ctx: SeedCtx = { tenantId, userId, api: request };

    // Seed two additional tenants via the admin endpoint so the Tenants table
    // has real rows to display (the test tenant itself is always present).
    const adminHeaders = {
      'X-Test-Tenant-Id': tenantId,
      'X-Test-User-Id': userId,
      'X-Test-Role': 'operator',
      'X-Test-Permissions': '*',
    };
    await request.post(`${BACKEND}/admin/tenants`, {
      data: { name: 'Acme Pest Control', industry: 'pest_control' },
      headers: adminHeaders,
    });
    await request.post(`${BACKEND}/admin/tenants`, {
      data: { name: 'Cool Air HVAC', industry: 'hvac' },
      headers: adminHeaders,
    });

    await injectAuth(page, tenantId, userId);

    // — Tenants page —
    await page.goto('/tenants');
    await page.waitForLoadState('load');
    await pause(800);
    // Two seeded tenants should appear
    await page.waitForSelector('h1', { timeout: 8000 });
    await pause(1500);

    // — New tenant form —
    // Fill name and industry then submit
    await page.fill('input[id="tenant-name"]', 'GreenThumb Landscaping');
    await page.selectOption('select[aria-label="Industry"]', 'landscaping');
    await page.getByRole('button', { name: /^Create$/i }).click();
    await page.waitForLoadState('load');
    await pause(1500);

    // — Operator Dashboard —
    await page.goto('/operator');
    await page.waitForLoadState('load');
    await pause(800);
    await page.waitForSelector('h1', { timeout: 8000 });
    await pause(2000);

    void ctx; // seeded above for headers
  });
});
