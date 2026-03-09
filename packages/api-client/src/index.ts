import fetch from 'cross-fetch';
import type { LoginResponse, Route, AcknowledgeResponse } from '@office-hero/types';

// Support both Expo (EXPO_PUBLIC_*) and standard Node env vars
const BASE_URL = (globalThis as any).__EXPO_PUBLIC_OFFICE_HERO_API_URL ||
                 process.env.EXPO_PUBLIC_OFFICE_HERO_API_URL ||
                 process.env.OFFICE_HERO_API_URL ||
                 'http://localhost:8000';

export interface Credentials {
  username: string;
  password: string;
}

export async function login(creds: Credentials): Promise<LoginResponse> {
  const resp = await fetch(BASE_URL + '/auth/login', {
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
