/**
 * API client singleton for Office Hero admin web.
 *
 * Reads VITE_API_BASE_URL from environment.
 * Handles JSON serialization, auth headers, and error responses.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export interface ApiError {
  status: number;
  detail: string;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  const response = await fetch(url, { ...options, headers });

  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    const error: ApiError = {
      status: response.status,
      detail: body.detail || response.statusText,
    };
    throw error;
  }

  return response.json();
}

// --- Saga types ---

export interface SagaState {
  saga_id: string;
  saga_type: string;
  status: 'running' | 'done' | 'compensating' | 'failed';
  current_step: number;
  context: Record<string, unknown>;
  last_error: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface CreateSagaRequest {
  saga_type: string;
  context: Record<string, unknown>;
}

// --- Dead-letter types ---

export interface DeadLetterItem {
  id: string;
  tenant_id: string;
  event_type: string;
  payload: Record<string, unknown>;
  status: string;
  attempt_count: number;
  created_at: string | null;
  processed_at: string | null;
  dead_letter_reason: string | null;
}

export interface DeadLetterListResponse {
  items: DeadLetterItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface DeadLetterRetryResponse {
  id: string;
  status: string;
  message: string;
}

// --- API functions ---

/** POST /sagas — dispatch a new saga */
export function createSaga(body: CreateSagaRequest): Promise<SagaState> {
  return request<SagaState>('/sagas', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

/** GET /sagas/{sagaId}/state — get saga status */
export function getSagaState(sagaId: string): Promise<SagaState> {
  return request<SagaState>(`/sagas/${sagaId}/state`);
}

/** GET /admin/dead-letters — list dead-letter events */
export function listDeadLetters(
  limit = 50,
  offset = 0,
): Promise<DeadLetterListResponse> {
  return request<DeadLetterListResponse>(
    `/admin/dead-letters?limit=${limit}&offset=${offset}`,
  );
}

/** POST /admin/dead-letters/{eventId}/retry — retry a dead-letter */
export function retryDeadLetter(eventId: string): Promise<DeadLetterRetryResponse> {
  return request<DeadLetterRetryResponse>(
    `/admin/dead-letters/${eventId}/retry`,
    { method: 'POST' },
  );
}

/** GET /admin/sagas/{sagaId}/logs — get saga execution log */
export function getSagaLogs(sagaId: string): Promise<SagaState> {
  return request<SagaState>(`/admin/sagas/${sagaId}/logs`);
}

/** GET /health — health check */
export function healthCheck(): Promise<{ status: string }> {
  return request<{ status: string }>('/health');
}
