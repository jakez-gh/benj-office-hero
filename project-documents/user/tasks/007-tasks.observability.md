---
slice: observability
project: office-hero
lld: user/slices/007-slice.observability.md
dependencies: [1, 1a, 2, 3]
projectState: Slices 1-3 complete (Python scaffold, database foundation, auth & RBAC). FastAPI app skeleton ready with CORS and lifespan hooks. Ready to add structured logging, health checks, security headers, and rate limiting.
dateCreated: 20260308
dateUpdated: 20260308
status: not_started
---

## Context Summary

- Working on **Slice 4: Observability & Security Middleware** — implementing structured JSON logging, health checks, security headers, audit events, rate limiting, and exception handling
- Current state: FastAPI app (Slice 3) is running with auth middleware; ready to wrap with observability layer
- Deliverable: Complete observability stack with request/response logging, health diagnostics, security headers, audit trail, and configurable rate limiting
- Next: Slice 5 (Frontend Scaffold) will consume health checks and auth endpoints; Slice 4 serves all remaining slices

---

## Task Breakdown

### Phase 1: Dependencies & Core Configuration

- [ ] **Add observability dependencies to pyproject.toml**
  - [ ] Add: `structlog`, `slowapi`, `python-multipart` (for rate limit form parsing)
  - [ ] Run `poetry lock` to update lock file
  - [ ] Success: `poetry install` completes without errors; packages importable in Python REPL

- [ ] **Create core/logging.py — structlog configuration**
  - [ ] Configure structlog for JSON output in production, pretty-print in development (env var: `ENV=prod|dev`)
  - [ ] Bind context keys automatically: `request_id`, `tenant_id`, `method`, `path`
  - [ ] Provide `get_logger()` factory function
  - [ ] Success: `from office_hero.core.logging import get_logger; log = get_logger(); log.info("test")` outputs JSON in prod mode

---

### Phase 2: Database Layer (Audit & Rate Limiting Tables)

- [ ] **Create migration alembic/versions/0003_rate_limits_audit_events.py**
  - [ ] Create `rate_limits` table:
    - `id` (UUID, primary key)
    - `name` (String, unique)
    - `limit` (Integer)
    - `per_seconds` (Integer)
    - `scope` (String) — e.g., "auth", "write", "read", "global"
    - `filters` (JSON, nullable) — for scoping by tenant/IP/user
    - `created_at`, `updated_at` (DateTime, auto-managed)
  - [ ] Create `ban_list` table (same schema): records with `limit=0` or explicit deny flags
  - [ ] Create `audit_events` table (append-only):
    - `id` (UUID, primary key)
    - `timestamp` (DateTime, auto-managed)
    - `tenant_id` (UUID, FK to tenants.id)
    - `user_id` (UUID, FK to users.id, nullable for non-authenticated events)
    - `event_type` (String) — e.g., "auth.login", "auth.logout", "rbac.denial", "data.access"
    - `details` (JSON) — arbitrary event data
    - `request_id` (UUID) — for correlating with HTTP request logs
  - [ ] Add DB trigger on `audit_events` to prevent UPDATE/DELETE (INSERT only)
  - [ ] Add index on `audit_events(tenant_id, event_type, timestamp)` for efficient querying
  - [ ] Success: `alembic upgrade head` creates tables; `\d rate_limits` shows all columns in psql; trigger exists

- [ ] **Test migrations**
  - [ ] Write test `tests/test_observability_migrations.py`: run migration, verify tables exist with correct columns, trigger prevents UPDATE/DELETE
  - [ ] Success: `pytest tests/test_observability_migrations.py -v` passes

---

### Phase 3: Service Layer (Audit & Rate Limiting)

- [ ] **Create services/audit_service.py — AuditService class**
  - [ ] Async method `log_event(event_type: str, details: dict, user_id: UUID | None, tenant_id: UUID, request_id: UUID, session)`
  - [ ] Inserts row into `audit_events` table
  - [ ] Runs as background task (non-blocking)
  - [ ] Success: Method executes without import/type errors; audit event appears in DB

- [ ] **Create services/rate_limit_manager.py — RateLimitManager class**
  - [ ] Class with 1-second TTL cache (using `functools.lru_cache` or simple dict + timestamp)
  - [ ] Methods:
    - `is_banned(scope_key: str) -> bool` — check `ban_list` table for matches
    - `get_limit(scope_key: str) -> int` — fetch limit from `rate_limits` or return default
  - [ ] Scope keys: `"auth"`, `"write"`, `"read"`, `"global"` (case-insensitive)
  - [ ] Hard-coded fallback defaults (if DB query fails):
    - auth: 10 req/min
    - write: 60 req/min
    - read: 300 req/min
    - global: 1000 req/min
  - [ ] Success: Methods execute without errors; queries cached correctly

- [ ] **Test audit & rate limiting services (unit tests)**
  - [ ] Create `tests/test_audit_service.py`:
    - Test `log_event` inserts row into `audit_events`
    - Test event details are stored correctly as JSON
    - Test request_id correlation
  - [ ] Create `tests/test_rate_limit_manager.py`:
    - Test `get_limit` returns value from DB
    - Test `get_limit` returns default if DB query fails
    - Test `is_banned` returns True for entries in ban_list
    - Test cache TTL (1-second expiry)
  - [ ] Success: `pytest tests/test_audit_service.py tests/test_rate_limit_manager.py -v` passes all tests

---

### Phase 4: Middleware & Exception Handlers

- [ ] **Create api/middleware/logging.py — per-request logging middleware**
  - [ ] Generates UUID `request_id` for each request (or reads from `X-Request-ID` header)
  - [ ] Binds `request_id`, `tenant_id` (from request.state), `method`, `path` to structlog context
  - [ ] Logs `event: "request.received"` with timestamp at start
  - [ ] Logs `event: "request.completed"` with `status_code`, `duration_ms` after response
  - [ ] Logs `event: "request.failed"` if unhandled exception occurs
  - [ ] Success: Middleware executes without errors; logs appear in stdout/logs

- [ ] **Create api/middleware/security_headers.py — security headers middleware**
  - [ ] Adds headers to all responses:
    - `X-Frame-Options: DENY`
    - `X-Content-Type-Options: nosniff`
    - `Content-Security-Policy: default-src 'self'`
    - `Strict-Transport-Security: max-age=31536000; includeSubDomains` (1 year HSTS)
    - `X-XSS-Protection: 1; mode=block`
  - [ ] Success: Middleware executes; headers present in response

- [ ] **Create api/exception_handlers.py — global exception handlers**
  - [ ] Handle `AuthError` → 401 Unauthorized with request_id in response
  - [ ] Handle `PermissionError` → 403 Forbidden with request_id in response
  - [ ] Handle `TenantError` → 400 Bad Request with request_id in response
  - [ ] Handle all other unhandled exceptions → 500 Internal Server Error with generic message (no stack trace to client; log full trace internally)
  - [ ] Success: Handlers catch exceptions; correct status codes returned

- [ ] **Test middleware & exception handlers (integration tests)**
  - [ ] Create `tests/test_logging_middleware.py`:
    - Test logging middleware binds request_id to context
    - Test request.received event is logged
    - Test request.completed event includes status_code + duration_ms
  - [ ] Create `tests/test_security_headers.py`:
    - Test all 5 security headers present in response
  - [ ] Create `tests/test_exception_handlers.py`:
    - Test AuthError → 401
    - Test PermissionError → 403
    - Test TenantError → 400
    - Test unhandled exception → 500 (no traceback leaked)
  - [ ] Success: `pytest tests/test_*_middleware.py tests/test_exception_handlers.py -v` passes

- [ ] **Wire middleware into app (update api/app.py from Slice 3)**
  - [ ] Import and add logging middleware (after auth middleware so tenant_id is available)
  - [ ] Import and add security headers middleware
  - [ ] Register exception handlers (using `@app.exception_handler()`)
  - [ ] Middleware order: auth → logging → security headers → response
  - [ ] Success: App starts without error; middleware chain executes in correct order

---

### Phase 5: Health Checks & Rate Limiting

- [ ] **Create api/routes/health.py — health check endpoint**
  - [ ] Endpoint `GET /health`:
    - Does NOT require JWT (public endpoint)
    - Checks DB reachability: `SELECT 1` against session connection
    - Checks ORS reachability: HTTP GET to configured ORS_HEALTH_URL (env var, default `http://localhost:5000/health`)
    - Returns 200 if all healthy: `{status: "ok", db: "ok", ors: "ok"}`
    - Returns 503 if any unhealthy: `{status: "unhealthy", db: "ok|error", ors: "ok|degraded|error"}`
  - [ ] Logs as internal diagnostic (no audit event)
  - [ ] Success: Endpoint responds with correct status codes; both checks work

- [ ] **Create api/limiter.py — slowapi rate limiter setup**
  - [ ] Instantiate slowapi limiter with custom key function (uses RateLimitManager)
  - [ ] Default key: global scope (can be overridden per endpoint)
  - [ ] Success: Limiter initializes without errors

- [ ] **Wire rate limiting into app (update api/app.py)**
  - [ ] Import limiter from `api/limiter.py`
  - [ ] Apply to `/auth/*` endpoints: `@limiter.limit("10/minute")` (auth scope from RateLimitManager)
  - [ ] Apply to other endpoints based on HTTP method:
    - POST/PATCH/DELETE: write scope (60/minute)
    - GET: read scope (300/minute)
    - All: global scope fallback (1000/minute)
  - [ ] Success: App starts; rate limiter is active

- [ ] **Test health & rate limiting (E2E tests)**
  - [ ] Create `tests/test_health.py`:
    - Test `GET /health` with healthy DB → 200, `{status: "ok", db: "ok", ors: "ok"}`
    - Test `GET /health` with DB down → 503, `{status: "unhealthy", db: "error", ...}`
  - [ ] Create `tests/test_rate_limiting.py`:
    - Test auth endpoint: send 11 requests in 60s, 11th returns 429 (Too Many Requests)
    - Test write endpoint: allows 60 requests in 60s, 61st returns 429
    - Test read endpoint: allows 300 requests in 60s, 301st returns 429
    - Test ban_list: insert IP into ban_list, request from that IP returns 403
  - [ ] Success: `pytest tests/test_health.py tests/test_rate_limiting.py -v` passes all scenarios

---

### Phase 6: Validation & Commit

- [ ] **Run full test suite**
  - [ ] Command: `pytest tests/ -v --cov=src/office_hero`
  - [ ] Success: All tests pass (observability + previous slices)
  - [ ] Coverage: ≥85% for observability module

- [ ] **Verify app starts with all middleware**
  - [ ] Command: `python -m uvicorn office_hero.api.app:app --reload` from repo root
  - [ ] Verify: `GET http://localhost:8000/health` returns 200 with status fields
  - [ ] Verify: `GET http://localhost:8000/docs` shows all endpoints (including /health)
  - [ ] Verify: Response headers include security headers (use browser DevTools or `curl -i`)

- [ ] **Verify logging output**
  - [ ] Make a request to any endpoint
  - [ ] Check stdout for structured logs with request_id, tenant_id, method, path
  - [ ] Success: Logs are present and properly formatted

- [ ] **Final commit & push**
  - [ ] Commit: "Implement Slice 4 (Observability): structlog, health checks, security headers, audit events, rate limiting"
  - [ ] Push to feature branch (e.g., `phase-6/slice-4-implementation`)
  - [ ] Create PR with summary
  - [ ] Success: GitHub CI passes (lint, tests, security checks)

---

## Success Criteria (Phase 5 Complete)

- ✅ All 12 test files created and passing
- ✅ All 11 implementation files created and imported without errors
- ✅ structlog configured for JSON output (prod) and pretty-print (dev)
- ✅ Health check endpoint functional and tests passing
- ✅ Rate limiting enforces correct limits per scope
- ✅ Audit events logged immutably (INSERT only)
- ✅ Security headers present on all responses
- ✅ Exception handlers convert exceptions to correct HTTP status codes
- ✅ Middleware chain executes in correct order
- ✅ App starts without errors
- ✅ All changes committed and pushed
- ✅ Ready for Phase 6 (Implementation) of Slice 5 (Frontend Scaffold)
