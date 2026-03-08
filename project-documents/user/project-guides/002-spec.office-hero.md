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
status: in_progress
---

# Office Hero — Specification

See [001-concept.office-hero.md](001-concept.office-hero.md) for full terminology and vision.
See [docs/glossary.md](../../../docs/glossary.md) for all term definitions.
Architecture detail lives in [050-arch.hld-office-hero.md](../architecture/050-arch.hld-office-hero.md).

---

## Functional Requirements

### User Roles & RBAC

Every request carries a JWT containing `user_id`, `tenant_id`, and `role`.
PostgreSQL RLS enforces tenant isolation at the DB layer as a hard gate.
The service layer also validates `tenant_id` as defense-in-depth (never trust client input).

| Role | Scope | Capabilities |
| ---- | ----- | ------------ |
| **Operator** | Platform | All Tenant data, platform configuration, billing |
| **OperatorStaff** | Platform | Same as Operator minus billing and Operator user management |
| **TenantAdmin** | Own Tenant only | Full CRUD within their Tenant |
| **Dispatcher** | Own Tenant only | Jobs, Routes, Dispatch — no user/account management |
| **Technician** | Own Tenant only | View own Route, enter Jobs in field, location updates |
| **TechnicianHelper** | Own Tenant only | View own Route, location updates — read-only Jobs |

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
| Tenant data isolation | Hard gate | PostgreSQL RLS enforced at DB layer |
| Authentication | JWT, 24 h expiry | Revocable via token blocklist |
| RBAC | Role + permission | Every endpoint declares required role/permission |
| Test coverage | Increases each sprint | 0% floor at launch; no sprint regresses coverage |
| TDD | Strict | Failing test written before every production code change |
| E2E tests | When no better option | Used when unit/integration test cannot cover the behaviour |

---

## Technology Stack

All choices are wrapped for swapability — see ADRs in `user/architecture/`.

| Layer | Choice | ADR |
| ----- | ------ | --- |
| Language | Python 3.11+ | — |
| Web framework | FastAPI | [051-adr.web-framework.md](../architecture/051-adr.web-framework.md) |
| ORM | SQLAlchemy 2.x + Alembic | — |
| Database | PostgreSQL 15+ | — |
| DB hosting | Neon (serverless PG, free tier) | [054-adr.hosting.md](../architecture/054-adr.hosting.md) |
| App hosting | Fly.io (free tier) | [054-adr.hosting.md](../architecture/054-adr.hosting.md) |
| Routing engine | OpenRouteService (ORS) | [052-adr.routing-engine.md](../architecture/052-adr.routing-engine.md) |
| Tenant isolation | PostgreSQL RLS | [053-adr.tenant-isolation.md](../architecture/053-adr.tenant-isolation.md) |
| Web frontend | React (TypeScript) | [055-adr.frontend.md](../architecture/055-adr.frontend.md) |
| Mobile app | React Native (Expo) | [055-adr.frontend.md](../architecture/055-adr.frontend.md) |
| Auth | JWT + bcrypt | — |
| MCP server | Python MCP SDK | — |

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

**Security at depth:**

- Transport: HTTPS enforced; HTTP redirected
- Auth: JWT validated on every request by middleware
- RBAC: permission check on every endpoint (decorator pattern)
- Tenant isolation: PostgreSQL RLS (hard gate) + service-layer `tenant_id` check
- Input validation: Pydantic schemas on all inputs
- SQL injection: SQLAlchemy ORM + parameterized queries only
- Static analysis: bandit on every push
- CVE scanning: pip-audit daily via GitHub Actions
- Secrets: environment variables only; never in code or commits

**Quality automation:**

- Pre-commit hooks auto-fix what they can (black, ruff --fix, trailing whitespace,
  line endings) before blocking on what they cannot
- Hooks and their configuration live in `.githooks/` and `.pre-commit-config.yaml`;
  rehydrated via `bash scripts/setup-dev.sh` on any new machine
- CI runs on every push: lint, bandit, pip-audit, pytest
- GitHub Actions: free up to 2,000 min/month on private repos (GitHub Free plan)

**TDD philosophy:**

- Write the failing test first — always
- Unit tests mock the Repository layer (no DB, no network, fast)
- Integration tests use real repositories against an isolated test DB (Neon branch)
- E2E tests (Playwright or Appium) cover flows that cannot be verified at a lower level
- No production code is written without a failing test justifying it

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

## Constraints

- Budget: free-tier hosting until first revenue; revisit at profit
- Team: solo developer + AI co-pilot
- Routing: ORS community server has rate limits; self-host or upgrade if too slow
- Phones: Android first; iOS added when React Native Expo build is stable
