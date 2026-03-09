---
docType: slice-design
parent: ../project-guides/003-slices.office-hero.md
project: office-hero
dateCreated: 20260308
status: not_started
---

# Slice Design 007: Observability & security middleware

This is the fourth foundation slice. It implements structured logging (JSON via `structlog`),
security headers, health checks, a global exception handler, rate limit configuration management,
and audit event logging. It wires everything together into the FastAPI app.

It corresponds to slice 4 in the slice plan.

## Goals

* Add `structlog` to `pyproject.toml`.
* Create `src/office_hero/core/logging.py` — configure structlog for JSON output:
  * Production: JSON renderer to stdout (for log aggregation)
  * Development: pretty-printed, readable
  * Automatically bind `request_id`, `tenant_id`, `method`, `path` to context on each request
  * Provide a logger factory function
* Create `src/office_hero/api/middleware/logging.py` — per-request middleware that:
  * Generates a UUID `request_id` for each request (or reads from `X-Request-ID` header if provided)
  * Binds `request_id`, `tenant_id` (from request.state), `method`, `path` to structlog context
  * Logs `event: "request.received"` with `timestamp`, `request_id`, `tenant_id`
  * Logs `event: "request.completed"` with `status_code`, `duration_ms` after response
  * Logs `event: "request.failed"` if an unhandled exception bubbles up
* Create `src/office_hero/api/middleware/security_headers.py` — adds security headers to all responses:
  * `X-Frame-Options: DENY` (prevent clickjacking)
  * `X-Content-Type-Options: nosniff` (prevent MIME sniffing)
  * `Content-Security-Policy: default-src 'self'` (basic CSP)
  * `Strict-Transport-Security: max-age=31536000; includeSubDomains` (HSTS, 1 year)
  * `X-XSS-Protection: 1; mode=block` (legacy XSS protection)
* Create `src/office_hero/api/routes/health.py` — `GET /health` endpoint:
  * Checks database reachability: `SELECT 1` against configured connection
  * Checks ORS reachability: HTTP GET to ORS `/health` or equivalent (configurable)
  * Returns `{"status": "ok", "db": "ok|error", "ors": "ok|degraded|error"}` with HTTP 200 if all ok, 503 if any error
  * Does not require JWT; logs as internal diagnostic
* Create `src/office_hero/api/exception_handlers.py` — global exception handlers:
  * Catch `AuthError` → 401 Unauthorized
  * Catch `PermissionError` → 403 Forbidden
  * Catch `TenantError` → 400 Bad Request
  * Catch all other unhandled exceptions → 500 Internal Server Error with generic message
    (never leak stack traces to client; log full stack internally)
  * All error responses include `request_id` for tracing
* Create `src/office_hero/db/audit.py` — `AuditService` class:
  * Async method `log_event(event_type: str, details: dict, user_id: UUID, tenant_id: UUID, session)`
  * Inserts row into `audit_events` table
  * Runs as background task (does not block request path)
  * Events logged: auth (login/logout), RBAC denials, tenant data access anomalies
* Create `src/office_hero/services/rate_limit_manager.py` — `RateLimitManager` class:
  * Queries `rate_limits` + `ban_list` tables on each request (with 1s TTL cache)
  * Methods:
    * `is_banned(scope_key: str) -> bool` — check ban_list for matches
    * `get_limit(scope_key: str) -> int` — fetch limit from rate_limits or return global default
  * Scope keys: `"auth"`, `"write"`, `"read"`, `"global"` (can be further scoped by tenant/IP/user)
  * Default limits (hard-coded fallback):
    * auth: 10 req/min
    * write: 60 req/min
    * read: 300 req/min
    * global: 1000 req/min
* Wire `slowapi` limiter into FastAPI app:
  * Create limiter instance with `RateLimitManager` hook
  * Apply to `/auth/*` endpoints: 10 req/min
  * All other endpoints: appropriate tier based on HTTP method
* Create migration `alembic/versions/0003_rate_limits_audit_events.py`:
  * Creates `rate_limits` table: `id (UUID, PK)`, `name (str, unique)`, `limit (int)`,
    `per_seconds (int)`, `scope (str)`, `filters (JSON)`, `created_at`, `updated_at`
  * Creates `ban_list` table (same schema): special records with `limit=0` or explicit deny
  * Creates `audit_events` table (append-only): `id (UUID, PK)`, `timestamp`, `tenant_id (UUID)`,
    `user_id (UUID)`, `event_type (str)`, `details (JSON)`, `request_id (UUID)`
  * Adds DB trigger on `audit_events` to prevent `UPDATE` or `DELETE`; only `INSERT` allowed
  * Adds indexes on `audit_events(tenant_id, event_type, timestamp)` for fast filtering
* Update `src/office_hero/api/app.py` (from slice 3):
  * Add logging middleware (after auth middleware so tenant_id is available)
  * Add security headers middleware
  * Register exception handlers
  * Mount health route
  * Wire slowapi limiter
* Create `tests/test_health.py`:
  * `test_health_returns_200_when_healthy` — GET /health with healthy DB + ORS returns 200
  * `test_health_returns_503_when_db_down` — GET /health with DB down returns 503
* Create `tests/test_logging.py`:
  * `test_request_logging_includes_request_id` — middleware logs request_id in both received + completed
  * `test_audit_event_logged` — call audit service, assert row in audit_events
* Create `tests/test_rate_limiting.py`:
  * `test_auth_endpoint_rate_limit_10_per_min` — send 11 requests in 60s, 11th returns 429
  * `test_read_endpoint_limit_higher` — GET endpoint allows more requests than auth endpoint
  * `test_ban_list_blocks_ip` — insert IP into ban_list, request from that IP returns 403
* Create `tests/test_exception_handlers.py`:
  * `test_auth_error_returns_401` — raise AuthError in endpoint, returns 401
  * `test_permission_error_returns_403` — raise PermissionError, returns 403
  * `test_unhandled_exception_returns_500_without_traceback` — unhandled exception returns 500, no stack trace in response

## Structure

```text
src/office_hero/
├── core/
│   └── logging.py                  # structlog configuration
├── db/
│   └── audit.py                    # AuditService for append-only audit log
├── services/
│   └── rate_limit_manager.py        # RateLimitManager + DB-backed config
├── api/
│   ├── app.py                      # Updated: add middleware, handlers, routes
│   ├── exception_handlers.py        # Global exception handlers
│   ├── middleware/
│   │   ├── logging.py              # Request/response logging
│   │   └── security_headers.py      # Security headers
│   └── routes/
│       └── health.py               # GET /health

alembic/
└── versions/
    └── 0003_rate_limits_audit_events.py

tests/
├── test_health.py
├── test_logging.py
├── test_rate_limiting.py
└── test_exception_handlers.py
```

## Failing Test Outline

```python
import pytest
from fastapi.testclient import TestClient
from office_hero.api.app import app

client = TestClient(app)


def test_health_returns_200_when_healthy():
    """GET /health with healthy DB and ORS returns 200 ok."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_auth_rate_limit_10_per_min():
    """11th /auth/login request in 60s returns 429."""
    for i in range(10):
        resp = client.post("/auth/login", json={"email": f"user{i}@t.com", "password": "x"})
        # First 10 may fail (401) but should not be rate-limited
        assert resp.status_code != 429

    resp = client.post("/auth/login", json={"email": "user11@t.com", "password": "x"})
    assert resp.status_code == 429  # rate limited


def test_exception_handler_does_not_leak_traceback():
    """Unhandled exception returns 500 with generic message, no traceback."""
    # Endpoint that raises ValueError
    resp = client.get("/test-error")  # hypothetical endpoint
    assert resp.status_code == 500
    assert "ValueError" not in resp.text
    assert "traceback" not in resp.text.lower()
    assert "request_id" in resp.json()
```

## Dependencies

Depends on slices 1, 2, and 3 (Auth). Slice 3 provides the auth middleware so logging can
bind `tenant_id`; slices 1–2 provide infrastructure.

## Effort

Estimate: 1/5. Most of the code is integrating existing libraries (`structlog`, `slowapi`).
The RateLimitManager is straightforward caching over a DB query. The audit logging is simple
INSERT. The main design work is getting middleware ordering correct (logging after auth so
we have tenant_id) and comprehensive test coverage of rate limits and error handling.

---

Once this design is approved, implementation proceeds with failing tests in `test_health.py`,
then implementing the health route, logging middleware, security headers, exception handlers,
and finally the rate limiting layer with the DB-backed manager.
