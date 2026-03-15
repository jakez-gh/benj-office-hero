import fetch from 'cross-fetch';
import type {
  LoginResponse,
  Route,
  AcknowledgeResponse,
  AuditEventsPage,
  RateLimitErrorBody,
} from '@office-hero/types';

const BASE_URL = process.env.OFFICE_HERO_API_URL || 'http://localhost:8000';

// ---------------------------------------------------------------------------
// Custom error for 429 responses so UI can show user-friendly feedback
// ---------------------------------------------------------------------------

export class RateLimitError extends Error {
  /** Seconds the client should wait before retrying. */
  retryAfter: number;

  constructor(retryAfter: number, message?: string) {
    super(message ?? `Rate limited. Retry after ${retryAfter}s.`);
    this.name = 'RateLimitError';
    this.retryAfter = retryAfter;
  }
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/** Throw RateLimitError for 429, generic Error for other failures. */
async function assertOk(resp: Response, label: string): Promise<void> {
  if (resp.ok) return;

  if (resp.status === 429) {
    let retryAfter = 60; // default
    const retryHeader = resp.headers.get('Retry-After');
    if (retryHeader) {
      const parsed = parseInt(retryHeader, 10);
      if (!isNaN(parsed)) retryAfter = parsed;
    }
    // Try to read body for detail
    try {
      const body: RateLimitErrorBody = await resp.json();
      if (body.retry_after) retryAfter = body.retry_after;
    } catch {
      // ignore parse errors
    }
    throw new RateLimitError(retryAfter);
  }

  throw new Error(`${label} failed: ${resp.status}`);
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export interface Credentials {
  username: string;
  password: string;
}

export async function login(creds: Credentials): Promise<LoginResponse> {
  const resp = await fetch(BASE_URL + '/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(creds),
  });
  await assertOk(resp, 'login');
  return resp.json();
}

export async function getDailyRoute(token: string): Promise<Route> {
  const resp = await fetch(BASE_URL + '/technician/route', {
    headers: { Authorization: `Bearer ${token}` },
  });
  await assertOk(resp, 'getDailyRoute');
  return resp.json();
}

export async function acknowledgeStop(token: string, stopId: string): Promise<AcknowledgeResponse> {
  const resp = await fetch(BASE_URL + `/stops/${stopId}/ack`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
  });
  await assertOk(resp, 'acknowledgeStop');
  return resp.json();
}

export async function postLocation(token: string, vehicleId: string, lat: number, lng: number): Promise<void> {
  const resp = await fetch(BASE_URL + `/vehicles/${vehicleId}/location`, {
    method: 'PUT',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ latitude: lat, longitude: lng }),
  });
  await assertOk(resp, 'postLocation');
}

export interface CreateJobRequest {
  customerName: string;
  address: string;
  latitude?: number;
  longitude?: number;
  description?: string;
}

export interface CreateJobResponse {
  jobId: string;
}

export async function createJob(token: string, job: CreateJobRequest): Promise<CreateJobResponse> {
  const resp = await fetch(BASE_URL + '/jobs', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(job),
  });
  await assertOk(resp, 'createJob');
  return resp.json();
}

// ---------------------------------------------------------------------------
// Audit Events — Admin panel (Slice 4)
// ---------------------------------------------------------------------------

export interface AuditEventsParams {
  limit?: number;
  offset?: number;
  event_type?: string;
  tenant_id?: string;
}

export async function getAuditEvents(
  token: string,
  params: AuditEventsParams = {},
): Promise<AuditEventsPage> {
  const qs = new URLSearchParams();
  if (params.limit != null) qs.set('limit', String(params.limit));
  if (params.offset != null) qs.set('offset', String(params.offset));
  if (params.event_type) qs.set('event_type', params.event_type);
  if (params.tenant_id) qs.set('tenant_id', params.tenant_id);

  const resp = await fetch(`${BASE_URL}/admin/audit-events?${qs.toString()}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  await assertOk(resp, 'getAuditEvents');
  return resp.json();
}
