import { test, type Page, type APIRequestContext } from '@playwright/test';
import { randomUUID } from 'node:crypto';
import path from 'node:path';

/**
 * Screenshots of admin-web with REAL seeded data.
 *
 * Requires a live backend: DEMO_BACKEND=1 OFFICE_HERO_TEST_AUTH=1
 * Run:
 *   DEMO_BACKEND=1 pnpm --filter admin-web exec playwright test screenshots-seeded --project=chromium
 *
 * Images are written to apps/admin-web/screenshots-seeded/{desktop,mobile}/.
 * These are NOT committed (they vary by data) — useful for documentation
 * and manual review only.
 */

if (!process.env.DEMO_BACKEND) {
  test('screenshots-seeded requires DEMO_BACKEND=1', () => {
    test.skip(true, 'Set DEMO_BACKEND=1 to run seeded screenshots');
  });
}

const BACKEND = process.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
const SCREENSHOT_DIR = process.env.SCREENSHOT_DIR ?? 'screenshots-seeded';
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

// ── Seed helpers ─────────────────────────────────────────────────────────────

interface SeedCtx { tenantId: string; userId: string; api: APIRequestContext }

async function apiPost<T>(ctx: SeedCtx, p: string, body: object): Promise<T> {
  const r = await ctx.api.post(`${BACKEND}${p}`, {
    data: body,
    headers: {
      'X-Test-Tenant-Id': ctx.tenantId, 'X-Test-User-Id': ctx.userId,
      'X-Test-Role': 'operator', 'X-Test-Permissions': '*',
    },
  });
  if (!r.ok()) throw new Error(`POST ${p} → ${r.status()}: ${await r.text()}`);
  return r.json() as Promise<T>;
}

interface ScenarioResult {
  tenantId: string; userId: string;
  pendingJobId: string;
}

async function seedScenario(ctx: SeedCtx): Promise<ScenarioResult> {
  const cust = await apiPost<{ id: string }>(ctx, '/customers', {
    name: 'Riverside Cleaning Co',
    email: 'ops@riverside.example.com',
    phone: '+1-555-0100',
  });
  const loc = await apiPost<{ id: string }>(ctx, `/customers/${cust.id}/locations`, {
    street: '123 Main St', city: 'Portland', state: 'OR', postal_code: '97201',
  });
  // Two dispatched jobs (will appear on Routes and Jobs pages)
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
  // One pending job so Dispatch page shows a real job in its dropdown
  const job3 = await apiPost<{ id: string }>(ctx, '/jobs', {
    customer_id: cust.id, location_id: loc.id,
    title: 'End-of-day sanitize', service_type: 'Sanitizing',
    priority: 30, estimated_duration_min: 45,
  });
  const veh = await apiPost<{ id: string }>(ctx, '/vehicles', {
    license_plate: 'DEMO-001', make: 'Toyota', model: 'Sienna', year: 2023,
  });
  await apiPost(ctx, '/vehicle-crews', {
    vehicle_id: veh.id, work_date: TODAY,
    shift_start: '07:00:00', shift_end: '17:00:00',
    members: [{ user_id: ctx.userId, role_on_crew: 'lead' }],
  });
  await apiPost(ctx, `/jobs/${job1.id}/dispatch`, {
    vehicle_id: veh.id, scheduled_for: nowAt(9),
    travel_seconds: 900, distance_meters: 8000,
  });
  await apiPost(ctx, `/jobs/${job2.id}/dispatch`, {
    vehicle_id: veh.id, scheduled_for: nowAt(13),
    travel_seconds: 600, distance_meters: 5000,
  });
  await apiPost(ctx, '/contracts', {
    customer_id: cust.id, location_id: loc.id,
    title: 'Monthly cleaning plan', frequency: 'monthly',
    start_date: TWO_MONTHS_AGO, service_type: 'Deep cleaning',
    estimated_duration_min: 90,
  });
  // Seed tenants so the Tenants admin page shows real rows
  await apiPost(ctx, '/admin/tenants', { name: 'Acme Pest Control', industry: 'pest_control' });
  await apiPost(ctx, '/admin/tenants', { name: 'Green Thumb HVAC', industry: 'hvac' });
  return { tenantId: ctx.tenantId, userId: ctx.userId, pendingJobId: job3.id };
}

// ── Auth injection ────────────────────────────────────────────────────────────

async function injectAuth(page: Page, tenantId: string, userId: string): Promise<void> {
  await page.addInitScript(({ tid, uid }) => {
    localStorage.setItem('access_token', 'seeded-screenshot-token');
    localStorage.setItem('refresh_token', 'seeded-refresh-token');
    localStorage.setItem('tenant_id', tid);
    localStorage.setItem('user', JSON.stringify({ id: uid, tenant_id: tid, role: 'operator' }));
  }, { tid: tenantId, uid: userId });
  // Forward test headers on every API request so the backend knows which tenant
  await page.route('**/*', async (route) => {
    const type = route.request().resourceType();
    if (type === 'fetch' || type === 'xhr') {
      await route.continue({
        headers: {
          ...route.request().headers(),
          'X-Test-Tenant-Id': tenantId,
          'X-Test-User-Id': userId,
          'X-Test-Role': 'operator',
          'X-Test-Permissions': '*',
        },
      });
    } else {
      await route.continue();
    }
  });
}

async function freezeAnimations(page: Page): Promise<void> {
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        animation: none !important;
        transition: none !important;
        caret-color: transparent !important;
      }
      [data-testid="app-version"] { visibility: hidden !important; }
    `,
  });
}

// ── Shared scenario (seeded once, reused by all screenshot tests) ─────────────

const VIEWPORTS = {
  desktop: { width: 1280, height: 800 },
  mobile: { width: 375, height: 812 },
} as const;

interface RouteConfig {
  name: string;
  path: string;
  // CSS selector to wait for before screenshotting, confirming data loaded.
  waitForSelector: string;
}

const ROUTES: RouteConfig[] = [
  { name: '01-login',     path: '/',          waitForSelector: 'input[type="email"]' },
  { name: '02-jobs',      path: '/jobs',       waitForSelector: 'text=Morning deep clean' },
  { name: '03-dispatch',  path: '/dispatch',   waitForSelector: 'select[aria-label="Select job"]' },
  { name: '04-vehicles',  path: '/vehicles',   waitForSelector: 'text=DEMO-001' },
  { name: '05-users',     path: '/users',      waitForSelector: 'h1' },
  { name: '06-customers', path: '/customers',  waitForSelector: 'text=Riverside' },
  { name: '07-contracts', path: '/contracts',  waitForSelector: 'text=Monthly cleaning plan' },
  { name: '08-routes',    path: '/routes',     waitForSelector: '[data-testid="route-card"]' },
  { name: '09-tenants',   path: '/tenants',    waitForSelector: 'text=Acme Pest Control' },
  { name: '10-operator',  path: '/operator',   waitForSelector: 'text=Rate Limits' },
];

// Capture screenshots for one viewport using the pre-seeded scenario IDs.
async function captureViewport(
  viewport: string,
  size: { width: number; height: number },
  scenario: ScenarioResult,
  page: Page,
): Promise<void> {
  await page.setViewportSize(size);

  for (const route of ROUTES) {
    const isAuth = route.path !== '/';
    if (isAuth) await injectAuth(page, scenario.tenantId, scenario.userId);

    await page.goto(route.path, { waitUntil: 'load' });

    // Wait for the data indicator or a generous fallback timeout
    await page.waitForSelector(route.waitForSelector, { timeout: 8000 }).catch(() => {});
    await freezeAnimations(page);
    await page.waitForTimeout(300);

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, viewport, `${route.name}.png`),
      fullPage: true,
      animations: 'disabled',
    });
  }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

for (const [viewport, size] of Object.entries(VIEWPORTS) as [string, typeof VIEWPORTS[keyof typeof VIEWPORTS]][]) {
  test.describe(`Seeded screenshots — ${viewport}`, () => {
    let scenario: ScenarioResult;

    test.use({ viewport: size });

    test.beforeAll(async ({ request }) => {
      const tenantId = randomUUID();
      const userId = randomUUID();
      scenario = await seedScenario({ tenantId, userId, api: request });
    });

    test(`capture all ${viewport} screenshots`, async ({ page }) => {
      await captureViewport(viewport, size, scenario, page);
    });
  });
}
