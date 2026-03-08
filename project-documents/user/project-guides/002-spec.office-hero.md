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

> Phase 2 artifact. Fills in tech stack, architecture, and data model decisions
> after the concept is stable. Open questions are marked **TBD**.

See [001-concept.office-hero.md](001-concept.office-hero.md) for full terminology
and vision. All terms (Job, Customer, Tenant, Route, etc.) are defined there.

---

## Technology Stack

| Layer | Choice | Rationale |
| ----- | ------ | --------- |
| Language | Python 3.11+ | Team expertise; strong FSM/data ecosystem |
| Web framework | **TBD** (FastAPI vs Flask) | FastAPI preferred — async, auto OpenAPI docs |
| Database | PostgreSQL | Relational; row-level security for Tenant isolation |
| ORM | SQLAlchemy + Alembic | Established Python ORM with migration support |
| Auth | JWT + bcrypt | Stateless; works across web and mobile browser |
| Routing engine | **TBD** (OpenRouteService or Google Maps) | ORS preferred — fully free and open-source |
| Location tracking | Mobile browser Geolocation API | No native app required at launch |
| Hosting | **TBD** (Railway / Render / Fly.io) | Free-tier; revisit at first revenue |
| DB hosting | **TBD** (Supabase / Neon / Railway Postgres) | Free-tier PostgreSQL |
| CI/CD | GitHub Actions | Already configured |

---

## Architecture

### High-level components

```text
[Operator Admin UI]
        |
[Office Hero API] ─── [PostgreSQL (multi-tenant, RLS)]
        |                      |
[Tenant Web UI]        [Routing Engine API]
        |
[Technician Mobile Web]
        |
[Geolocation → API → DB (Vehicle positions)]
```

### Multi-tenancy model

- Every Tenant-scoped table carries a `tenant_id` foreign key.
- PostgreSQL Row-Level Security (RLS) enforces isolation at the DB layer —
  a query that leaks a `tenant_id` is rejected by the DB, not just caught in app code.
- Operator-level endpoints are protected by a separate `operator` role claim in the JWT.
- Tenants cannot see other Tenants' data or any Operator-level views.

---

## Data Model (draft)

Key entities — detail expanded in slice designs.

| Entity | Key Fields | Notes |
| ------ | ---------- | ----- |
| Tenant | id, name, industry, plan, active | Top-level isolation unit |
| User | id, tenant_id, email, password_hash, role | Roles: operator / tenant_admin / technician |
| Customer | id, tenant_id, name, contact_info | Tenant's end customers |
| Location | id, customer_id, tenant_id, address, lat, lng | Service address; Customer may have many |
| Job | id, tenant_id, customer_id, location_id, service_type, status, scheduled_window, custom_fields | Core operational record; JSONB for industry-specific fields |
| Contract | id, tenant_id, customer_id, service_type, frequency, next_due | Recurring service plan that generates Jobs |
| Vehicle | id, tenant_id, name, active | Truck / van |
| VehicleLocation | id, vehicle_id, lat, lng, recorded_at | Time-series position log |
| Route | id, tenant_id, vehicle_id, date, status | A day's dispatch plan for one Vehicle |
| RouteStop | id, route_id, job_id, sequence, eta | Ordered stops within a Route |

Industry-specific Job fields (permit numbers for plumbing, chemical usage records
for pest control, equipment model for HVAC) are stored in `custom_fields` (JSONB)
with per-industry field templates configurable by Tenant Admin.

---

## API Outline

To be detailed in slice designs. Top-level groups:

- `POST /auth/login`, `POST /auth/logout`
- `GET/POST /customers`, `GET/PUT /customers/{id}`
- `GET/POST /locations`, `GET/PUT /locations/{id}`
- `GET/POST /jobs`, `GET/PUT /jobs/{id}`
- `POST /jobs/{id}/routing-options` — returns 3 ranked Route options
- `POST /jobs/{id}/dispatch` — commits the chosen Route option
- `GET/POST /contracts`, `GET/PUT /contracts/{id}`
- `GET/POST /vehicles`, `PUT /vehicles/{id}/location`
- `GET /routes`, `GET /routes/{id}`
- `GET /operator/tenants` (Operator only)

---

## Non-functional Requirements

| Requirement | Target |
| ----------- | ------ |
| Tenant data isolation | Hard — enforced at DB layer (PostgreSQL RLS) |
| Authentication | JWT, 24 h expiry, revocable |
| Test coverage | 0% floor at launch; gate raised each sprint |
| Code quality | TDD, SOLID, DRY; pre-commit + CI enforced |
| Security scanning | bandit (static) + pip-audit (CVE) on every push |
| Uptime SLO | TBD — 99% reasonable for small-scale launch |
| Routing response time | TBD — sub-2 s for routing option generation |

---

## Constraints & Dependencies

- **Budget:** Free-tier hosting only until first revenue
- **Team:** Solo developer (Operator) + AI co-pilot
- **External:** Routing engine API availability and rate limits (TBD on choice)
- **Integration:** Tenant back-office system integration deferred to Phase 2+

---

## Open Architecture Decisions (ADRs pending)

Decisions to be recorded in `project-documents/user/architecture/` once made:

1. FastAPI vs Flask
2. OpenRouteService vs Google Maps Directions API
3. Row-level security (DB) vs application-layer Tenant filtering
4. Hosting platform selection (Railway / Render / Fly.io)
5. Frontend approach — server-rendered vs SPA
