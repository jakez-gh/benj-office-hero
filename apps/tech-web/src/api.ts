/**
 * API client for tech-web. Reads VITE_API_BASE_URL from env, falls back to localhost.
 */

function resolveBaseUrl(): string {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const meta = (Function('return import.meta') as any)();
    if (meta?.env?.VITE_API_BASE_URL) return meta.env.VITE_API_BASE_URL as string;
  } catch { /* jest/CommonJS */ }
  return 'http://localhost:8000';
}

const BASE = resolveBaseUrl();

let _token: string | null = localStorage.getItem('tech_token');

export function setToken(t: string | null) {
  _token = t;
  if (t) localStorage.setItem('tech_token', t);
  else localStorage.removeItem('tech_token');
}

export function getToken(): string | null { return _token; }

async function req<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (_token) headers['Authorization'] = `Bearer ${_token}`;
  const resp = await fetch(`${BASE}${path}`, { ...opts, headers });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw { status: resp.status, detail: body.detail ?? resp.statusText };
  }
  return resp.json() as Promise<T>;
}

// --- Auth ---

export interface LoginResponse { access_token: string; token_type: string; }

export function loginApi(email: string, password: string): Promise<LoginResponse> {
  return req('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) });
}

// --- Crew ---

export interface MyCrewToday { crew_id: string; vehicle_id: string; work_date: string; }

export function myCrewTodayApi(): Promise<MyCrewToday> {
  return req('/vehicles/my-crew-today');
}

// --- Jobs ---

export type JobStatus = 'pending' | 'scheduled' | 'in_progress' | 'completed' | 'cancelled';

export interface JobSummary {
  id: string;
  title: string;
  status: JobStatus;
  service_type: string | null;
  scheduled_for: string | null;
  priority: number;
  customer_id: string;
  location_id: string;
  estimated_duration_min: number;
}

export interface JobList { items: JobSummary[]; total: number; }

export function listJobsApi(params: {
  assigned_vehicle_id?: string;
  scheduled_for_date?: string;
  status?: string;
}): Promise<JobList> {
  const q = new URLSearchParams();
  if (params.assigned_vehicle_id) q.set('assigned_vehicle_id', params.assigned_vehicle_id);
  if (params.scheduled_for_date) q.set('scheduled_for_date', params.scheduled_for_date);
  if (params.status) q.set('status', params.status);
  return req(`/jobs?${q}`);
}

export function getJobApi(jobId: string): Promise<JobSummary> {
  return req(`/jobs/${jobId}`);
}

export function startJobApi(jobId: string): Promise<JobSummary> {
  return req(`/jobs/${jobId}/start`, { method: 'POST' });
}

export function completeJobApi(jobId: string, notes?: string): Promise<JobSummary> {
  return req(`/jobs/${jobId}/complete`, {
    method: 'POST',
    body: JSON.stringify({ completion_notes: notes ?? null }),
  });
}

export interface JobCreatePayload {
  customer_id: string;
  location_id: string;
  title: string;
  service_type?: string | null;
  estimated_duration_min?: number;
}

export function createJobApi(payload: JobCreatePayload): Promise<JobSummary> {
  return req('/jobs', { method: 'POST', body: JSON.stringify(payload) });
}
