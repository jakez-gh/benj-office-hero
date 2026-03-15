import fetch from 'cross-fetch';
import axios from 'axios';
import type { LoginResponse as MobileLoginResponse, Route, AcknowledgeResponse } from '@office-hero/types';

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
  if (!resp.ok) throw new Error(`login failed: ${resp.status}`);
  return resp.json();
}

export async function getDailyRoute(token: string): Promise<Route> {
  const resp = await fetch(BASE_URL + '/technician/route', {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) throw new Error(`getDailyRoute failed: ${resp.status}`);
  return resp.json();
}

export async function acknowledgeStop(token: string, stopId: string): Promise<AcknowledgeResponse> {
  const resp = await fetch(BASE_URL + `/stops/${stopId}/ack`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
  });
  if (!resp.ok) throw new Error(`acknowledgeStop failed: ${resp.status}`);
  return resp.json();
}

export async function postLocation(token: string, vehicleId: string, lat: number, lng: number): Promise<void> {
  const resp = await fetch(BASE_URL + `/vehicles/${vehicleId}/location`, {
    method: 'PUT',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ latitude: lat, longitude: lng }),
  });
  if (!resp.ok) throw new Error(`postLocation failed: ${resp.status}`);
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
  if (!resp.ok) throw new Error(`createJob failed: ${resp.status}`);
  return resp.json();
}
