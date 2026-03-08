---
layer: project
phase: 2
phaseName: spec
guideRole: primary
audience: [human, ai]
description: Specification for Office Hero
dependsOn: [001-concept.office-hero.md]
dateCreated: 20260308
dateUpdated: 20260308
status: review
---

# Office Hero — Specification

See [001-concept.office-hero.md](001-concept.office-hero.md) for full terminology and vision.
See [docs/glossary.md](../../../docs/glossary.md) for all term definitions.
Architecture detail lives in [050-arch.hld-office-hero.md](../architecture/050-arch.hld-office-hero.md).

---

## Functional Requirements

### User Roles & RBAC

Every request carries a JWT containing `user_id`, `tenant_id`, `role`, and
`permissions[]`. PostgreSQL RLS enforces tenant isolation at the DB layer as a
hard gate. The service layer also validates `tenant_id` as defense-in-depth.

**Role hierarchy (highest to lowest):**

| Role | Scope | Capabilities |
| ---- | ----- | ------------ |
| **Owner** | Platform | God mode — Jake + 1 other. Manages Operators. Cannot be modified by Operators. Full billing, platform config, Operator user management. Immutable audit log access. |
| **Operator** | Platform | All Tenant data, platform configuration (except Owner management) |
| **OperatorStaff** | Platform | Same as Operator minus billing and Operator/Owner user management |
| **TenantAdmin** | Own Tenant only | Full CRUD within their Tenant |
| **Dispatcher** | Own Tenant only | Jobs, Routes, Dispatch — no user/account management |
| **Technician** | Own Tenant only | View own Route, enter Jobs in field, location updates |
| **TechnicianHelper** | Own Tenant only | View own Route, location updates — read-only Jobs |

**Fine-grained permissions:**
The `permissions[]` array in the JWT enables per-user permission overrides without
creating new roles. Roles provide a default permission set; `permissions[]` can
add (grant) or remove (deny, prefixed `!`) individual capabilities.

**Customizable roles per Tenant:**
TenantAdmins may define their own role names and associated permission sets
within the scope of their Tenant. The platform ships with the standard hierarchy
above, but a TenantAdmin can use the **role builder** UI to create, modify, or
delete tenant‑scoped roles (e.g. "Senior Technician", "Weekend Dispatcher").
These custom roles are stored in a `roles` table keyed by `tenant_id`; when a
user logs in the JWT’s `role` claim reflects the chosen role and the service
layer fetches the corresponding default permissions. This mechanism keeps the
model simple while giving each Tenant fine‑grained control over their internal
organizational structure. Tenant-level role defaults are also editable by the
Operator for all Tenants if desired.

```text
permissions: ["jobs:write", "routes:read", "!dispatch:write"]
```

This allows, for example, a Dispatcher who is temporarily restricted from
dispatching (e.g., trainee mode) without creating a new role. Permissions are
managed by TenantAdmin for their users, and by Operator for Tenant-level defaults.
Owner permission grants/revocations override all.

Every endpoint declares: (a) the minimum role required, and (b) any specific
permission required. Both must be satisfied. `@require_role` + `@require_permission`
decorators enforce this at the router layer.

### Core Workflows

**Job Intake:**
A TenantAdmin or Technician enters a Job (Customer, Location, service type, scheduling
window, industry-specific fields). Industry-specific fields are stored in a `custom_fields`
JSONB column, populated from per-industry field templates.

**Dispatch (3-option routing):**
On Job entry or manual dispatch, the system generates three ranked routing options:

1. Nearest available Vehicle to the Job Location
2. Earliest completion (minimizes remaining route time)
3. Balanced workload (most even distribution across Vehicles)

The recommended option is pre-selected. TenantAdmin selects one of the three, or
enters a custom fourth option. Dispatch commits the Job to a Route.

**Vehicle/Technician model:**
Routes belong to Vehicles. Technicians are assigned to a Vehicle per day via
`VehicleCrew` (one driver, zero or more helpers). Location is tracked via the
lead Technician's Android phone app. A Technician may be on different Vehicles
on different days. A Vehicle may carry multiple Technicians simultaneously.

**Dynamic re-routing:**
Day-of events (Technician sick, Customer cancellation, emergency Job added) trigger
re-routing. The system presents updated options; Dispatcher/TenantAdmin confirms.

**Back-office integration:**
A `BackOfficeAdapter` protocol defines the interface. All data access goes through
an adapter. The default adapter uses Office Hero as the system of record. Future
adapters (ServiceTitan, PestPac, Jobber) implement the same protocol. Each
integration is its own slice. The data model mirrors common FSM back-office fields
to minimize translation cost.

---

## Non-Functional Requirements

| Requirement | Target | Notes |
| ----------- | ------ | ----- |
| Uptime SLO | 99.5% monthly | ~3.6 hrs/month allowed downtime |
| API response (p95) | < 500 ms | Standard CRUD endpoints |
| Routing option generation | < 8 s | ORS community server; self-host ORS if too slow |
| Tenant data isolation | Hard gate | PostgreSQL RLS + service-layer tenant check |
| Authentication | JWT RS256, 15 min access / 7 day refresh | See ADR 060 |
| RBAC | Role + fine-grained permissions[] | Every endpoint declares role + permission |
| Rate limiting | All endpoints — tiered by endpoint type; dynamically configurable by Operator at runtime | `slowapi` plus `RateLimitManager` (see ADR 062); auth tighter; global fallback |
| Audit logging | Every auth event, RBAC check, data access | Immutable, queryable, forensic-grade |
| Test coverage | Increases each sprint | 0% floor at launch; no sprint regresses coverage |
| TDD | Strict | Failing test written before every production code change; pytest runs on every push |
| E2E tests | When no better option | Android, iOS, web (Playwright), API, MCP |
| CVE scanning | 4× daily | `pip-audit` via GitHub Actions scheduled scan |
| Code quality | Automated, blocking | black, ruff, bandit, markdownlint on every commit/push |

---

## Technology Stack

All choices are wrapped for swapability — see ADRs in `user/architecture/` (including 057–063). Design patterns used by these ADRs are documented in `user/architecture/patterns.md`.

| Layer | Choice | ADR |
| ----- | ------ | --- |
| Language | Python 3.11+ | [057-adr.language.md](../architecture/057-adr.language.md) |
| Web framework | FastAPI | [051-adr.web-framework.md](../architecture/051-adr.web-framework.md) |
| ORM | SQLAlchemy 2.x + Alembic | [058-adr.orm.md](../architecture/058-adr.orm.md) |
| Database | PostgreSQL 15+ | [059-adr.database.md](../architecture/059-adr.database.md) |
| DB hosting | Neon (serverless PG, free tier) | [054-adr.hosting.md](../architecture/054-adr.hosting.md) |
| App hosting | Fly.io (free tier) | [054-adr.hosting.md](../architecture/054-adr.hosting.md) |
| Routing engine | OpenRouteService (ORS) | [052-adr.routing-engine.md](../architecture/052-adr.routing-engine.md) |
| Tenant isolation | PostgreSQL RLS | [053-adr.tenant-isolation.md](../architecture/053-adr.tenant-isolation.md) |
| Web frontend | React (TypeScript) | [055-adr.frontend.md](../architecture/055-adr.frontend.md) |
| Mobile app | React Native (Expo) | [055-adr.frontend.md](../architecture/055-adr.frontend.md) |
| Auth | JWT RS256 + bcrypt + refresh tokens | [060-adr.auth.md](../architecture/060-adr.auth.md) |
| MCP server | Python MCP SDK + OpenAPI codegen | [061-adr.mcp-server.md](../architecture/061-adr.mcp-server.md) |
| Rate limiting | slowapi (starlette-compatible) | [062-adr.rate-limiting.md](../architecture/062-adr.rate-limiting.md) |
| Logging | structlog (JSON) + audit log | [063-adr.logging-observability.md](../architecture/063-adr.logging-observability.md) |
| Observability | Grafana + Loki (free) or Better Stack | [063-adr.logging-observability.md](../architecture/063-adr.logging-observability.md) |

---

## Architecture Patterns

### Layered Architecture

```text
HTTP Request
    → FastAPI Router   (HTTP only — no business logic)
    → Service Layer    (all business logic — no HTTP, no DB)
    → Repository Layer (all DB access — no business logic)
    → PostgreSQL       (RLS enforces tenant isolation)
```

All inter-layer dependencies flow inward via protocols (ABCs).
This enables mocking at every boundary for fast, isolated unit tests.

### Back-Office Adapter Pattern

```text
Service Layer
    → BackOfficeAdapter (protocol / ABC)
        → NativeAdapter          (Office Hero as SoR — default)
        → ServiceTitanAdapter    (future slice)
        → PestPacAdapter         (future slice)
        → JobberAdapter          (future slice)
```

Adapters translate between Office Hero's internal model and external systems.
A Tenant's adapter is configured at Tenant creation time.

### Quality & Security Patterns

**Security at depth (OWASP Top 10 — see HLD for full table):**

- Transport: HTTPS enforced; HTTP redirected; HSTS header
- Auth: JWT RS256 validated on every request by middleware; 15 min access token
- RBAC: role + fine-grained permission check on every endpoint (`@require_role`, `@require_permission`)
- Rate limiting: `slowapi` middleware on **all** endpoints, tiered by sensitivity:
  - Auth endpoints (`/auth/*`): 10 req/min per IP
  - Write endpoints (`POST`, `PUT`, `DELETE`): 60 req/min per user
  - Read endpoints (`GET`): 300 req/min per user
  - Global fallback: 1000 req/min per IP (DDoS basic mitigation)
- Tenant isolation: PostgreSQL RLS (hard gate) + service-layer `tenant_id` assertion
- Input validation: Pydantic `model_config = ConfigDict(extra='forbid')` on all schemas
- SQL injection: SQLAlchemy ORM only; no raw SQL in services or routers
- SSRF: ORS + back-office adapter URLs validated against allowlist; no user-supplied URLs
- CSP + security headers: middleware on all responses
- Static analysis: bandit on every push (pre-commit push stage)
- CVE scanning: pip-audit 4× daily (06:00, 12:00, 18:00, 00:00 UTC)
- Secrets: env vars only; `detect-private-key` pre-commit hook; never in code or commits

**Audit logging (forensic tracing):**

Every significant event is written to a separate immutable audit log (append-only,
never mutated after write) in addition to the structured application log:

- Auth events: login (success/fail), logout, token refresh, account lockout
- RBAC events: every permission denial with `user_id`, `endpoint`, `required` vs `actual` role
- Tenant data access: every cross-tenant access attempt (should be zero — indicates RLS bypass)
- Admin actions: any Operator/Owner action on Tenant data
- Back-office Saga events: each step, compensation, dead-letter
- Security anomalies: rate limit exceeded, SSRF attempt blocked, JWT decode failure

Audit log is stored in `audit_events` table (append-only, no UPDATE/DELETE ever issued
by application code; DB trigger prevents modification). Operator log viewer surfaces this.

**Quality automation:**

- Pre-commit hooks auto-fix what they can (black, ruff --fix, trailing whitespace,
  line endings) before blocking on what they cannot
- Git push hook runs `bandit` (security) + `pytest` (TDD gate) — no broken tests
  can be pushed
- Hooks and configuration live in `.githooks/` + `.pre-commit-config.yaml`;
  rehydrated via `bash scripts/setup-dev.sh` on any new machine
- CI runs on every push: lint, bandit, pip-audit, pytest
- GitHub Actions: free up to 2,000 min/month on private repos

**TDD philosophy:**

- Write the failing test first — always
- When fixing tests: understand the intent of the test before modifying;
  only change a test if the requirement it tests has changed
- Unit tests mock the Repository layer (no DB, no network, instant)
- Integration tests use real repositories against an isolated Neon branch
- E2E tests cover: Android app (emulator), iOS app (emulator), web (Playwright),
  API (pytest/httpx), MCP (tool invocation tests)
- No production code is written without a failing test justifying it

**Additional engineering principles:**

- **SOLID** — Single responsibility, Open/closed, Liskov substitution, Interface
  segregation, Dependency inversion — enforced by architecture (routers/services/repos)
- **DRY** — business logic in one place (service layer); schemas defined once (Pydantic)
- **YAGNI** — implement for current requirements, not hypothetical future ones
- **KISS** — simplest solution that satisfies the requirement and tests
- **Fail Fast** — validate inputs at the boundary; raise domain exceptions early
- **Prefer existing libraries** — use battle-tested open-source libraries (slowapi,
  structlog, python-jose, bcrypt, SQLAlchemy, Alembic) over custom implementations.
  Evaluate: free, safe, legal, actively maintained, well-documented.

---

## Operator Dashboard & Observability

Operators and Owners get a dedicated observability dashboard — not a feature
for Tenants. Use **existing free services** rather than building custom:

**Platform:** Grafana Cloud free tier (10,000 series, 14-day retention) or
Better Stack (formerly Logtail) free tier. Both ingest from Fly.io logs and
provide dashboards + log search out of the box.

**Metrics dashboard (real-time + historical):**

- API uptime (SLO 99.5% — shown as % + downtime budget remaining)
- API response time: p50, p95, p99 (live and 24h/7d/30d sparklines)
- Error rate (5xx/4xx ratio) with anomaly highlighting
- Active users per Tenant (session count)
- Routing engine response time (ORS calls)
- Back-office Saga dead-letter queue depth (alerts if > 0)
- Request rate per endpoint (top 10 by volume)

**Log viewer (Operator + Owner only):**

Structured log search with:

- Live control panel: Operators can adjust rate limits and add/remove ban filters (account, tenant, IP, geography) dynamically from the dashboard; changes propagate immediately without a restart.

- Filter by: `tenant_id`, `user_id`, `request_id`, `level`, `endpoint`, time range
- Search by: arbitrary JSON field value (structlog produces JSON)
- Audit log tab: auth events, RBAC denials, admin actions — separate from debug logs
- Export: filtered log lines as JSON or CSV for incident investigation

**Implementation:** `structlog` logs ship to Fly.io stdout → forwarded to
Grafana Loki (or Better Stack Logs) via the Fly.io log shipper. No custom
log infrastructure code required; just configure the shipper and Grafana dashboards.

**Alerting:**

- Fly.io uptime alert if `/health` fails (email/Slack webhook)
- Sentry for exception tracking (free tier: 5,000 errors/month)
- Dead-letter growth alert (Grafana alert rule: `dead_letter_count > 0`)
- Rate limit breach alert (unusual spike indicates probing/attack)

---

## GUI Architecture

```text
┌─────────────────────┐  ┌─────────────────────────┐
│  Tenant Admin Web   │  │   Technician Web View   │
│  (React SPA)        │  │   (React, lightweight)  │
└────────┬────────────┘  └──────────┬──────────────┘
         │                          │
┌────────▼──────────────────────────▼──────────────┐
│               Office Hero REST API               │
│               (FastAPI, OpenAPI spec)            │
└───────┬──────────────────────────────────────────┘
        │
┌───────▼───────┐  ┌──────────────────────────────┐
│  MCP Server   │  │  React Native App (Expo)      │
│  (AI access)  │  │  Technician Android/iOS       │
└───────────────┘  └──────────────────────────────┘
```

- All GUIs consume the same REST API
- MCP server wraps the API for AI tool access
- Technician mobile app: Android first (React Native Expo); iOS extension ready
- Tenant Admin mobile: responsive web first; native app when web is insufficient

---

## Data Model (draft — see HLD for full schema)

| Entity | Key Fields | Notes |
| ------ | ---------- | ----- |
| Tenant | id, name, industry, plan, active, back\_office\_adapter | Top-level isolation unit |
| User | id, tenant\_id, email, password\_hash, role | All human users |
| Customer | id, tenant\_id, name, contact\_info | Tenant's end customers |
| Location | id, customer\_id, tenant\_id, address, lat, lng | Service address; Customer has many |
| Job | id, tenant\_id, customer\_id, location\_id, service\_type, status, scheduled\_window, custom\_fields | Core record; JSONB for industry fields |
| Contract | id, tenant\_id, customer\_id, service\_type, frequency, next\_due | Recurring plan → generates Jobs |
| Vehicle | id, tenant\_id, name, capacity\_notes, active | Truck / van |
| VehicleCrew | id, vehicle\_id, technician\_id, date, role | Driver or helper per day |
| VehicleLocation | id, vehicle\_id, lat, lng, recorded\_at | Time-series; posted by Technician app |
| Route | id, tenant\_id, vehicle\_id, date, status | Day's plan for one Vehicle |
| RouteStop | id, route\_id, job\_id, sequence, eta | Ordered stops within a Route |

---

## API Outline (detail in slice designs)

- `POST /auth/login`, `POST /auth/logout`, `POST /auth/refresh`
- `GET/POST /customers`, `GET/PUT/DELETE /customers/{id}`
- `GET/POST /locations`, `GET/PUT /locations/{id}`
- `GET/POST /jobs`, `GET/PUT /jobs/{id}`
- `POST /jobs/{id}/routing-options` — three ranked Route options from ORS
- `POST /jobs/{id}/dispatch` — commits chosen option, updates Route
- `GET/POST /contracts`, `GET/PUT /contracts/{id}`
- `GET/POST /vehicles`, `GET/PUT /vehicles/{id}`
- `POST /vehicles/{id}/location` — location update from Technician app
- `GET/POST /routes`, `GET /routes/{id}`
- `GET /operator/tenants` (Operator only)
- MCP endpoints mirror API capabilities via MCP protocol

---

## Branching Strategy

**GitHub Flow** — simple, low-overhead, suited for solo dev + AI parallel sessions.

```text
main  ←──── always deployable, protected branch
  │
  ├── feature/{slice-name}    short-lived, one AI or human session
  ├── stream/backend-core     longer-lived parallel work stream (see docs/worktrees.md)
  ├── stream/frontend         parallel frontend work stream
  └── stream/mobile           parallel mobile work stream
```

**Rules:**

- `main` is always deployable. No direct pushes (enforce branch protection).
- All work happens in a feature or stream branch; merged to `main` via PR.
- CI must pass before merge (lint + security + tests).
- One active branch per machine at a time for feature work; use worktrees for
  parallel AI sessions (see [docs/worktrees.md](../../docs/worktrees.md)).
- Feature branches: delete after merge. Stream branches: long-lived, rebased
  onto `main` regularly.
- Prefer small, frequent PRs over large batches. Each slice = at most one PR.
- **No force-push to `main`** — ever.

**Merge conflicts:** Resolve by rebasing feature branch onto `main` before PR,
not by merging `main` into the feature branch. Keep history linear.

---

## Constraints

- Budget: free-tier hosting until first revenue; revisit at profit
- Team: solo developer + AI co-pilot (multiple parallel AI sessions via worktrees)
- Routing: ORS community server has rate limits; self-host or upgrade if too slow
- Phones: Android first; iOS added when React Native Expo build is stable
- Libraries: prefer existing open-source over custom; evaluate: free, safe, legal,
  actively maintained
