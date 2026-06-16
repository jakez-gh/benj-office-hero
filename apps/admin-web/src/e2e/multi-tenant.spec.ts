/**
 * Multi-tenant isolation tests.
 *
 * Verifies that one tenant cannot read or enumerate another tenant's data
 * through the API (backend enforcement).
 *
 * These are API-only tests — no browser required, but a running backend with
 * OFFICE_HERO_TEST_AUTH=1 is needed.
 *
 * Run with:
 *   DEMO_BACKEND=1 pnpm --filter admin-web exec playwright test multi-tenant --project=chromium
 */
import { test, expect, type APIRequestContext } from '@playwright/test';
import { randomUUID } from 'node:crypto';

const BACKEND = process.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

interface SeedCtx {
  tenantId: string;
  userId: string;
  api: APIRequestContext;
}

function testHeaders(tenantId: string, userId: string) {
  return {
    'X-Test-Tenant-Id': tenantId,
    'X-Test-User-Id': userId,
    'X-Test-Role': 'operator',
    'X-Test-Permissions': '*',
  };
}

async function apiPost<T>(ctx: SeedCtx, path: string, body: object): Promise<T> {
  const resp = await ctx.api.post(`${BACKEND}${path}`, {
    data: body,
    headers: testHeaders(ctx.tenantId, ctx.userId),
  });
  if (!resp.ok()) throw new Error(`POST ${path} → ${resp.status()}: ${await resp.text()}`);
  return resp.json() as Promise<T>;
}

test.describe('Multi-tenant isolation', () => {

  test('Tenant B cannot list Tenant A jobs', async ({ request }) => {
    const tenantA = randomUUID();
    const tenantB = randomUUID();
    const userA = randomUUID();
    const userB = randomUUID();
    const ctxA: SeedCtx = { tenantId: tenantA, userId: userA, api: request };

    const cust = await apiPost<{ id: string }>(ctxA, '/customers', { name: 'Tenant A Customer' });
    const loc = await apiPost<{ id: string }>(ctxA, `/customers/${cust.id}/locations`, {
      street: '1 A St', city: 'Portland', state: 'OR', postal_code: '97201',
    });
    const job = await apiPost<{ id: string }>(ctxA, '/jobs', {
      customer_id: cust.id, location_id: loc.id,
      title: 'Tenant A Job', priority: 50, estimated_duration_min: 60,
    });

    const listResp = await request.get(`${BACKEND}/jobs`, {
      headers: testHeaders(tenantB, userB),
    });
    expect(listResp.ok()).toBe(true);
    const body = await listResp.json() as { items: Array<{ id: string }> };
    expect(body.items.map((j) => j.id)).not.toContain(job.id);
  });

  test('Tenant B gets 404 fetching Tenant A job by ID', async ({ request }) => {
    const tenantA = randomUUID();
    const tenantB = randomUUID();
    const userA = randomUUID();
    const userB = randomUUID();
    const ctxA: SeedCtx = { tenantId: tenantA, userId: userA, api: request };

    const cust = await apiPost<{ id: string }>(ctxA, '/customers', { name: 'Isolated Customer' });
    const loc = await apiPost<{ id: string }>(ctxA, `/customers/${cust.id}/locations`, {
      street: '2 Isolated Ln', city: 'Portland', state: 'OR', postal_code: '97201',
    });
    const job = await apiPost<{ id: string }>(ctxA, '/jobs', {
      customer_id: cust.id, location_id: loc.id,
      title: 'Isolated Job', priority: 50, estimated_duration_min: 60,
    });

    const resp = await request.get(`${BACKEND}/jobs/${job.id}`, {
      headers: testHeaders(tenantB, userB),
    });
    expect(resp.status()).toBe(404);
  });

  test('Tenant B cannot list Tenant A customers', async ({ request }) => {
    const tenantA = randomUUID();
    const tenantB = randomUUID();
    const userA = randomUUID();
    const userB = randomUUID();
    const ctxA: SeedCtx = { tenantId: tenantA, userId: userA, api: request };

    const cust = await apiPost<{ id: string }>(ctxA, '/customers', { name: 'Secret Customer' });

    const listResp = await request.get(`${BACKEND}/customers`, {
      headers: testHeaders(tenantB, userB),
    });
    expect(listResp.ok()).toBe(true);
    const body = await listResp.json() as { items: Array<{ id: string }> };
    expect(body.items.map((c) => c.id)).not.toContain(cust.id);
  });

  test('Tenant B cannot list Tenant A vehicles', async ({ request }) => {
    const tenantA = randomUUID();
    const tenantB = randomUUID();
    const userA = randomUUID();
    const userB = randomUUID();
    const ctxA: SeedCtx = { tenantId: tenantA, userId: userA, api: request };

    const veh = await apiPost<{ id: string }>(ctxA, '/vehicles', {
      license_plate: 'SEC-001', make: 'Ford', model: 'Transit', year: 2022,
    });

    const listResp = await request.get(`${BACKEND}/vehicles`, {
      headers: testHeaders(tenantB, userB),
    });
    expect(listResp.ok()).toBe(true);
    const body = await listResp.json() as Array<{ id: string }>;
    const ids = Array.isArray(body) ? body.map((v) => v.id) : [];
    expect(ids).not.toContain(veh.id);
  });

  test('Tenant B cannot list Tenant A contracts', async ({ request }) => {
    const tenantA = randomUUID();
    const tenantB = randomUUID();
    const userA = randomUUID();
    const userB = randomUUID();
    const ctxA: SeedCtx = { tenantId: tenantA, userId: userA, api: request };
    const today = new Date().toISOString().slice(0, 10);

    const cust = await apiPost<{ id: string }>(ctxA, '/customers', { name: 'Contract Owner' });
    const loc = await apiPost<{ id: string }>(ctxA, `/customers/${cust.id}/locations`, {
      street: '3 Contract St', city: 'Portland', state: 'OR', postal_code: '97201',
    });
    const contract = await apiPost<{ id: string }>(ctxA, '/contracts', {
      customer_id: cust.id, location_id: loc.id,
      title: 'Secret Contract', frequency: 'monthly',
      start_date: today, estimated_duration_min: 60,
    });

    const listResp = await request.get(`${BACKEND}/contracts`, {
      headers: testHeaders(tenantB, userB),
    });
    expect(listResp.ok()).toBe(true);
    const body = await listResp.json() as { items: Array<{ id: string }> };
    expect(body.items.map((c) => c.id)).not.toContain(contract.id);
  });

  test('Tenant B cannot list Tenant A routes', async ({ request }) => {
    const tenantA = randomUUID();
    const tenantB = randomUUID();
    const userA = randomUUID();
    const userB = randomUUID();
    const ctxA: SeedCtx = { tenantId: tenantA, userId: userA, api: request };
    const today = new Date().toISOString().slice(0, 10);

    const cust = await apiPost<{ id: string }>(ctxA, '/customers', { name: 'Route Owner' });
    const loc = await apiPost<{ id: string }>(ctxA, `/customers/${cust.id}/locations`, {
      street: '4 Route Blvd', city: 'Portland', state: 'OR', postal_code: '97201',
    });
    const job = await apiPost<{ id: string }>(ctxA, '/jobs', {
      customer_id: cust.id, location_id: loc.id,
      title: 'Route Job', priority: 50, estimated_duration_min: 60,
    });
    const veh = await apiPost<{ id: string }>(ctxA, '/vehicles', {
      license_plate: 'RT-SEC', make: 'Toyota', model: 'Sienna', year: 2022,
    });
    await apiPost(ctxA, '/vehicle-crews', {
      vehicle_id: veh.id, work_date: today,
      shift_start: '07:00:00', shift_end: '17:00:00',
      members: [{ user_id: userA, role_on_crew: 'lead' }],
    });
    const dispatch = await apiPost<{ route_id: string }>(ctxA, `/jobs/${job.id}/dispatch`, {
      vehicle_id: veh.id, scheduled_for: new Date().toISOString(),
      travel_seconds: 300, distance_meters: 2000,
    });

    const listResp = await request.get(`${BACKEND}/routes?work_date=${today}`, {
      headers: testHeaders(tenantB, userB),
    });
    expect(listResp.ok()).toBe(true);
    const body = await listResp.json() as { items: Array<{ id: string }> };
    expect(body.items.map((r) => r.id)).not.toContain(dispatch.route_id);
  });

});
