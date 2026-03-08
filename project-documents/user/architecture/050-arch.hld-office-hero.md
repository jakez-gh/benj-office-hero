---
docType: reference
layer: project
phase: 2
phaseName: architecture
audience: [human, ai]
description: High-Level Design (HLD) for Office Hero — single-initiative project architecture
dependsOn: [../project-guides/001-concept.office-hero.md, ../project-guides/002-spec.office-hero.md]
dateCreated: 20260308
dateUpdated: 20260308
status: in_progress
---

# High-Level Design: Office Hero

Phase 2 architecture document. This is the primary input to Phase 3 (Slice Planning).
See spec and concept docs for terminology, constraints, and decision rationale.

---

## System Context

```text
┌─────────────────────────────────────────────────────────────────┐
│                        Internet                                 │
│                                                                 │
│  ┌──────────────────┐   ┌──────────────────┐                   │
│  │  Tenant Admin    │   │  Operator        │                   │
│  │  Web Browser     │   │  Web Browser     │                   │
│  └────────┬─────────┘   └────────┬─────────┘                   │
│           │                      │                             │
│  ┌────────▼──────────────────────▼─────────┐                   │
│  │           Office Hero API               │                   │
│  │           (FastAPI on Fly.io)           │                   │
│  └──┬──────────────┬────────────┬──────────┘                   │
│     │              │            │                              │
│  ┌──▼───┐  ┌───────▼──┐  ┌─────▼──────────────────┐           │
│  │ Neon │  │   ORS    │  │  Technician Android App │           │
│  │  DB  │  │ Routing  │  │  (React Native Expo)    │           │
│  └──────┘  └──────────┘  └─────────────────────────┘           │
│                                                                 │
│  ┌──────────────────────────┐                                   │
│  │  MCP Server (AI access)  │                                   │
│  └──────────────────────────┘                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Major Subsystems

### 1. Office Hero API (FastAPI)

The single API consumed by all clients. Structured in layers:

```text
src/office_hero/
├── api/                  # FastAPI routers only — no business logic
│   ├── routes/           # One module per resource group
│   ├── middleware/        # Auth, RBAC, tenant context, logging
│   └── schemas/          # Pydantic request/response models
├── services/             # Business logic — no HTTP, no direct DB
├── repositories/         # All DB access — one class per aggregate root
│   └── protocols/        # ABCs defining Repository interfaces
├── adapters/
│   ├── routing/          # RoutingAdapter protocol + ORS implementation
│   └── back_office/      # BackOfficeAdapter protocol + implementations
├── models/               # SQLAlchemy ORM models
├── db/                   # Engine, session, RLS helpers
└── core/                 # Config, logging, exceptions, constants
```

**Swap strategy:** The `api/` layer only imports from `services/`. The `services/`
layer only imports from `protocols/`. Swapping FastAPI = replace `api/` only.
Swapping ORM = replace `repositories/` implementations only.

### 2. Tenant Isolation (PostgreSQL RLS)

Every Tenant-scoped table has a `tenant_id` column. PostgreSQL Row-Level Security
policies enforce that queries automatically filter to the session's Tenant.

```sql
-- Applied to every tenant-scoped table:
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON jobs
    USING (tenant_id = current_setting('app.tenant_id')::uuid);
```

The API middleware sets `app.tenant_id` from the JWT before every query.
Service layer also validates `tenant_id` as defense-in-depth (never trust client input).

### 3. RBAC

JWT payload: `{ sub, tenant_id, role, permissions[] }`

Role hierarchy enforced by a `@require_role` / `@require_permission` decorator on
every FastAPI endpoint. Roles: Operator, OperatorStaff, TenantAdmin, Dispatcher,
Technician, TechnicianHelper.

### 4. Repository Pattern

```text
Service → RepositoryProtocol (ABC) → ConcreteRepository → SQLAlchemy → PostgreSQL
```

Unit tests inject mock repositories — no DB, no network, instant execution.
Integration tests use real repositories against a dedicated Neon branch.

### 5. Back-Office Adapter

```python
class BackOfficeAdapter(Protocol):
    async def get_customer(self, id: UUID) -> Customer: ...
    async def create_job(self, job: Job) -> Job: ...
    # ... full CRUD surface
```

`NativeAdapter` is the default (Office Hero as SoR). Each external system
(ServiceTitan, PestPac, Jobber, etc.) is a separate adapter implementation and
a separate slice. Tenant's adapter is configured per Tenant and injected at runtime.

### 6. Routing Subsystem

```python
class RoutingAdapter(Protocol):
    async def routing_options(
        self, job: Job, vehicles: list[VehicleState]
    ) -> list[RouteOption]: ...
```

`ORSAdapter` implements this against the OpenRouteService API.
Returns exactly three ranked options. Dispatcher selects one or enters a custom fourth.
Swap ORS for Google Maps / Mapbox by providing a new adapter implementation.

### 7. Location Tracking

Technician Android app (React Native Expo) posts `{ vehicle_id, lat, lng }` to
`PUT /vehicles/{id}/location` on a configurable interval (default 60 s while on route).
Stored in `VehicleLocation` (time-series). Routing engine reads latest position when
generating options.

### 8. Web Frontend (React)

Two distinct React applications sharing a common API client library:

- **Tenant Admin SPA** — full dispatch dashboard, Job management, Route management
- **Technician Web View** — lighter view: own Route, Job entry

Both are served as static assets (Fly.io or CDN). Communicate exclusively with the
REST API. No business logic in the frontend.

### 9. Mobile App (React Native Expo)

Technician-facing. Android first, iOS-ready. Capabilities:

- Receive and acknowledge daily Route
- View Job details at each stop
- Post location updates (background or foreground)
- Enter new Jobs in the field

Shares API client code with the React web apps via a shared TypeScript package.

### 10. MCP Server

Wraps the REST API as an MCP tool set. Allows AI assistants (Claude, etc.) to query
and update Office Hero data programmatically. Uses the same auth/RBAC as the API.
Deployed as a separate process on Fly.io.

---

## Data Flow: Job Dispatch

```text
1. TenantAdmin enters Job → POST /jobs
2. Service validates, stores Job (status: pending), triggers routing
3. RoutingAdapter.routing_options() called with Job + current VehicleLocations
4. ORS returns routes; service ranks into 3 options
5. API returns 3 RouteOptions to client
6. TenantAdmin selects option → POST /jobs/{id}/dispatch
7. Service creates/updates Route and RouteStops; Job status → dispatched
8. Technician app polls/receives updated Route
```

---

## Infrastructure

| Concern | Solution |
| ------- | -------- |
| App hosting | Fly.io (free tier, no cold starts) |
| DB hosting | Neon serverless PostgreSQL (free tier, no pause) |
| DB branching | Neon branches for dev/test environments |
| Static assets | Fly.io or Cloudflare Pages (free) |
| CI/CD | GitHub Actions (2,000 min/month free on private) + git hooks |
| Secrets | Fly.io secrets store (env vars); never in code |
| Monitoring | TBD — Fly.io metrics + Sentry free tier |

---

## Cross-Cutting Concerns

These are addressed as **Foundation Work** slices (the first slices implemented):

| Concern | Approach |
| ------- | -------- |
| Structured logging | `structlog` — JSON output, request-id correlation |
| Error handling | Global FastAPI exception handler; maps domain exceptions to HTTP status codes |
| Health checks | `GET /health` — DB connectivity, routing engine reachability |
| Request tracing | Middleware injects `X-Request-ID`; propagated to all log lines |
| Observability | Fly.io metrics + structured logs; Sentry for error tracking |
| Config management | `pydantic-settings`; all config from env vars; `.env` for local dev |

---

## Security at Depth (layers)

1. HTTPS enforced at edge; HTTP redirected
2. JWT validation middleware on every request
3. RBAC decorator on every endpoint
4. Service layer validates `tenant_id` from JWT (never from client)
5. PostgreSQL RLS enforces tenant isolation at DB
6. Pydantic validates all inputs; rejects unknown fields
7. SQLAlchemy ORM prevents raw SQL injection
8. bandit static analysis on every push
9. pip-audit CVE scan daily
10. Secrets in env vars only; detect-private-key pre-commit hook

---

## Key Design Constraints

- **Swap-ability:** every integration point (web framework, routing engine, DB,
  back-office systems) is hidden behind a protocol/interface. Changing any component
  requires implementing a new class, not changing existing business logic.
- **TDD:** Repository protocols make all business logic unit-testable without
  a database. Foundation slices set this up before any feature work.
- **SOLID / DRY:** services are the single source of business logic;
  routers handle HTTP concerns only; repositories handle DB concerns only.
