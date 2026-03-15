import fetch from 'cross-fetch';
import axios from 'axios';
import type {
  LoginResponse as MobileLoginResponse,
  Route,
  AcknowledgeResponse,
  AuditEventsPage,
  RateLimitErrorBody,
} from '@office-hero/types';

// --- Base URLs ---

const envBaseUrl =
  typeof process !== 'undefined' && process.env
    ? process.env.OFFICE_HERO_API_URL
    : undefined;

/** Mobile SDK base — always hits the origin directly. */
const BASE_URL = envBaseUrl ?? 'http://localhost:8000';

/**
 * Admin-web base — in the browser the Vite dev-server proxies /api → backend,
 * so we use '/api'; in Node (tests / SSR) we fall back to the env var or localhost.
 */
const AUTH_BASE_URL =
  (typeof window !== 'undefined' ? '/api' : undefined) ??
  envBaseUrl ??
  'http://localhost:8000';

// --- Axios client (used by admin-web auth + admin list endpoints) ---

export const client = axios.create({
  baseURL: AUTH_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

// --- Re-export admin-web auth module (login, refresh, logout, types) ---

export { login, refresh, logout } from './auth';
export type {
  LoginRequest,
  AuthUser,
  LoginResponse as AuthLoginResponse,
  RefreshRequest,
  RefreshResponse,
} from './auth';

// --- Admin entity types ---

export interface AdminJob {
  id: string;
  customer_name?: string;
  customer?: string;
  address?: string;
  status?: string;
  scheduled_at?: string;
}

export interface AdminRoute {
  id: string;
  vehicle_id?: string;
  technician_id?: string;
  status?: string;
  date?: string;
}

export interface AdminUser {
  id: string;
  email?: string;
  full_name?: string;
  role?: string;
  status?: string;
}

export interface AdminVehicle {
  id: string;
  name?: string;
  license_plate?: string;
  status?: string;
  make?: string;
  model?: string;
}

// --- Normaliser (handles both `T[]` and `{ items: T[] }` envelopes) ---

/**
 * API may return a bare array **or** an object with one array-valued key
 * (e.g. `{ items: [...] }`, `{ data: [...] }`).  This helper extracts the
 * array safely using `unknown` narrowing — the `as T[]` is justified
 * because the backend contract guarantees item shape.
 */
export function normalizeList<T>(data: unknown): T[] {
  if (Array.isArray(data)) {
    // Backend returned a bare array — cast is safe per API contract.
    return data as T[];
  }

  if (typeof data === 'object' && data !== null) {
    for (const value of Object.values(data as Record<string, unknown>)) {
      if (Array.isArray(value)) {
        return value as T[];
      }
    }
  }

  return [];
}

// --- Admin list endpoints (use axios `client` — auth header set by AuthProvider) ---

export async function listJobs(): Promise<AdminJob[]> {
  const { data } = await client.get<unknown>('/jobs');
  return normalizeList<AdminJob>(data);
}

export async function listRoutes(): Promise<AdminRoute[]> {
  const { data } = await client.get<unknown>('/routes');
  return normalizeList<AdminRoute>(data);
}

export async function listUsers(): Promise<AdminUser[]> {
  const { data } = await client.get<unknown>('/users');
  return normalizeList<AdminUser>(data);
}

export async function listVehicles(): Promise<AdminVehicle[]> {
  const { data } = await client.get<unknown>('/vehicles');
  return normalizeList<AdminVehicle>(data);
}

// --- Mobile SDK (cross-fetch based — username auth, direct URL) ---

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

export async function mobileLogin(creds: Credentials): Promise<MobileLoginResponse> {
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
