// Shared TypeScript types used by both web and mobile clients

export interface Stop {
  id: string;
  address: string;
  latitude: number;
  longitude: number;
  acknowledged: boolean;
}

export interface Route {
  id: string;
  date: string; // ISO date string yyyy-mm-dd
  vehicleId?: string;
  stops: Stop[];
}

export interface LoginResponse {
  token: string;
}

export interface AcknowledgeResponse {
  success: boolean;
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

// ---------------------------------------------------------------------------
// Slice 4 — Observability & Rate Limiting
// ---------------------------------------------------------------------------

/** Audit event record returned by GET /admin/audit-events */
export interface AuditEvent {
  id: string;
  timestamp: string; // ISO 8601
  tenant_id: string;
  user_id: string | null;
  event_type: string;
  details: Record<string, unknown>;
  request_id: string | null;
}

/** Paginated response from GET /admin/audit-events */
export interface AuditEventsPage {
  items: AuditEvent[];
  total: number;
  limit: number;
  offset: number;
}

/** Error body returned by 429 Too Many Requests */
export interface RateLimitErrorBody {
  detail: string;
  retry_after: number; // seconds
  request_id: string | null;
}
