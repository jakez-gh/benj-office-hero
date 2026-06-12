/**
 * API client singleton for Office Hero admin web.
 *
 * Reads VITE_API_BASE_URL from environment.
 * Handles JSON serialization, auth headers, and error responses.
 */

/**
 * Resolve the API base URL.
 *
 * Vite injects ``import.meta.env`` at build time; jest (with ts-jest using
 * CommonJS) doesn't support ``import.meta`` so we look up the env via the
 * Vite-injected ``__VITE_ENV__`` only when it exists, then fall back to a
 * ``process.env`` lookup (Node test env) and finally to localhost.
 */
function resolveBaseUrl(): string {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const meta = (Function('return import.meta') as any)();
    if (meta?.env?.VITE_API_BASE_URL) {
      return meta.env.VITE_API_BASE_URL as string;
    }
  } catch {
    // import.meta is not available in this runtime (e.g. jest/CommonJS).
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const proc = (globalThis as any).process;
  if (proc?.env?.VITE_API_BASE_URL) {
    return proc.env.VITE_API_BASE_URL as string;
  }

  return 'http://localhost:8000';
}

const BASE_URL = resolveBaseUrl();

export interface ApiError {
  status: number;
  detail: string;
}

/**
 * FastAPI returns `detail` as a string for domain errors but as an ARRAY OF
 * OBJECTS ({type, loc, msg, input}) for Pydantic body-validation failures.
 * Pages render `detail` as a React child, so anything non-string must be
 * flattened here or the whole SPA crashes ("Objects are not valid as a
 * React child" — and there is no error boundary).
 */
function normalizeDetail(detail: unknown, fallback: string): string {
  if (typeof detail === 'string' && detail) return detail;
  if (Array.isArray(detail)) {
    const msgs = detail
      .map((d) => {
        if (typeof d === 'string') return d;
        const item = d as { msg?: string; loc?: unknown[] };
        if (item?.msg) {
          const field = Array.isArray(item.loc) ? item.loc.slice(1).join('.') : '';
          return field ? `${field}: ${item.msg}` : item.msg;
        }
        return JSON.stringify(d);
      })
      .filter(Boolean);
    if (msgs.length) return msgs.join('; ');
  }
  if (detail != null) return JSON.stringify(detail);
  return fallback;
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
      detail: normalizeDetail(body.detail, response.statusText),
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

// --- Job types (Slice 10) ---

export type JobStatus = 'pending' | 'scheduled' | 'in_progress' | 'completed' | 'cancelled';

export interface JobSummary {
  id: string;
  title: string;
  status: JobStatus;
  priority: number;
  scheduled_for: string | null;
  customer_id: string;
  location_id: string;
  industry: string;
  service_type: string | null;
}

export interface JobListResponse {
  items: JobSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface JobCreate {
  customer_id: string;
  location_id: string;
  title: string;
  description?: string | null;
  priority?: number;
  service_type?: string | null;
  estimated_duration_min?: number;
}

// --- Job API functions ---

export interface JobListParams {
  status?: JobStatus;
  search?: string;
  limit?: number;
  offset?: number;
}

export function listJobsApi(params: JobListParams = {}): Promise<JobListResponse> {
  const qs = new URLSearchParams();
  if (params.status) qs.set('status', params.status);
  if (params.search) qs.set('search', params.search);
  if (params.limit != null) qs.set('limit', String(params.limit));
  if (params.offset != null) qs.set('offset', String(params.offset));
  const query = qs.toString() ? `?${qs.toString()}` : '';
  return request<JobListResponse>(`/jobs${query}`);
}

export function createJobApi(body: JobCreate): Promise<JobSummary> {
  return request<JobSummary>('/jobs', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

// --- Schedule options types (Slice 13) ---

export interface ScheduleOptionItem {
  vehicle_id: string;
  vehicle_display: string;
  suggested_start: string;
  travel_seconds: number;
  rank: number;
}

export interface ScheduleOptionsResponse {
  job_id: string;
  options: ScheduleOptionItem[];
}

export interface ScheduleOptionsRequest {
  window_start: string;
  window_end: string;
  max_results?: number;
}

export function getScheduleOptionsApi(
  jobId: string,
  body: ScheduleOptionsRequest,
): Promise<ScheduleOptionsResponse> {
  return request<ScheduleOptionsResponse>(`/jobs/${jobId}/schedule-options`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

// --- Dispatch types (Slice 14) ---

export interface DispatchRequest {
  vehicle_id: string;
  scheduled_for: string;
}

export interface DispatchResponse {
  id: string;
  status: JobStatus;
  assigned_vehicle_id: string;
  scheduled_for: string;
  title: string;
  customer_id: string;
  location_id: string;
}

export function dispatchJobApi(
  jobId: string,
  body: DispatchRequest,
): Promise<DispatchResponse> {
  return request<DispatchResponse>(`/jobs/${jobId}/dispatch`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

// --- Contract types (Slice 11) ---

export type ContractStatus = 'active' | 'paused' | 'ended';

export type ContractFrequency =
  | 'weekly'
  | 'biweekly'
  | 'monthly'
  | 'quarterly'
  | 'semiannual'
  | 'annual';

export interface ContractSummary {
  id: string;
  title: string;
  status: ContractStatus;
  frequency: ContractFrequency;
  next_due: string;
  end_date: string | null;
  customer_id: string;
  location_id: string;
  industry: string;
  service_type: string | null;
  priority: number;
}

export interface ContractRead extends ContractSummary {
  tenant_id: string;
  description: string | null;
  estimated_duration_min: number;
  start_date: string;
  paused_at: string | null;
  ended_at: string | null;
  end_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface ContractListResponse {
  items: ContractSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface ContractCreate {
  customer_id: string;
  location_id: string;
  title: string;
  description?: string | null;
  service_type?: string | null;
  priority?: number;
  estimated_duration_min?: number;
  frequency: ContractFrequency;
  start_date: string;
  end_date?: string | null;
}

export interface GenerateJobsResponse {
  generated: JobSummary[];
  count: number;
}

// --- Contract API functions ---

export interface ContractListParams {
  status?: ContractStatus;
  search?: string;
  limit?: number;
  offset?: number;
}

export function listContractsApi(
  params: ContractListParams = {},
): Promise<ContractListResponse> {
  const qs = new URLSearchParams();
  if (params.status) qs.set('status', params.status);
  if (params.search) qs.set('search', params.search);
  if (params.limit != null) qs.set('limit', String(params.limit));
  if (params.offset != null) qs.set('offset', String(params.offset));
  const query = qs.toString() ? `?${qs.toString()}` : '';
  return request<ContractListResponse>(`/contracts${query}`);
}

export function createContractApi(body: ContractCreate): Promise<ContractRead> {
  return request<ContractRead>('/contracts', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function pauseContractApi(contractId: string): Promise<ContractRead> {
  return request<ContractRead>(`/contracts/${contractId}/pause`, { method: 'POST' });
}

export function resumeContractApi(contractId: string): Promise<ContractRead> {
  return request<ContractRead>(`/contracts/${contractId}/resume`, { method: 'POST' });
}

export function endContractApi(
  contractId: string,
  reason?: string,
): Promise<ContractRead> {
  return request<ContractRead>(`/contracts/${contractId}/end`, {
    method: 'POST',
    body: JSON.stringify(reason ? { reason } : {}),
  });
}

export function generateContractJobsApi(asOf?: string): Promise<GenerateJobsResponse> {
  return request<GenerateJobsResponse>('/contracts/generate-jobs', {
    method: 'POST',
    body: JSON.stringify(asOf ? { as_of: asOf } : {}),
  });
}
