---
docType: reference
layer: project
audience: [human, ai]
description: Epic-level grouping of all slices — the zoom-out view between the slice plan and individual slices
dateCreated: 20260617
dateUpdated: 20260617
---

# Office Hero — Initiatives (Epics)

The slice plan (`003-slices.office-hero.md`) is the authoritative source of truth
for slice status. This file adds the **epic layer** — grouping slices into cohesive
workstreams so any session can orient at the right altitude before zooming in.

**When to use this file:**

- Start of a new workstream to understand what precedes and follows it
- Cross-slice decisions that affect multiple epics
- Communicating project state to stakeholders (not just "X of Y slices done")

---

## Epic 1 — Foundation `[complete]`

Everything the system needs to be runnable, testable, and deployable.

| Slice | Name | Status |
| ----- | ---- | ------ |
| 1 | Python project scaffold | complete |
| 1a | CLI & tooling baseline (`hero` console script) | complete |
| 2 | Database foundation (Neon, Alembic, RLS, multi-tenant schema) | complete |
| 3 | Auth / RBAC (JWT RS256, role + permission model) | complete |
| 4 | Observability (structlog, audit log, health endpoint) | complete |
| 5 | Frontend scaffold (React + Vite + Tailwind v3) | complete |
| 5a | Admin web shell (login, nav, route guards) | complete |

ADRs: [057 language](../architecture/057-adr.language.md),
[059 database](../architecture/059-adr.database.md),
[060 auth](../architecture/060-adr.auth.md),
[063 logging](../architecture/063-adr.logging-observability.md)

---

## Epic 2 — Platform & Operator Tools `[complete]`

The administrative layer: tenant management, user management, operator observability.

| Slice | Name | Status |
| ----- | ---- | ------ |
| 7 | Tenant management (CRUD, plan limits) | complete |
| 7a | Operator observability dashboard (rate limits, ban filters, audit log) | complete |
| 8 | User management (invite, roles, deactivate) | complete |

ADRs: [062 rate-limiting](../architecture/062-adr.rate-limiting.md)

---

## Epic 3 — Core Field Service `[complete]`

The domain model: customers, jobs, vehicles, contracts.

| Slice | Name | Status |
| ----- | ---- | ------ |
| 9 | Customer + location management | complete |
| 10 | Job management (FSM: pending → dispatched → done) | complete |
| 11 / 023 | Contract management (recurring job generation) | complete |
| 12 | Vehicle + crew management | complete |

---

## Epic 4 — Dispatch & Routing `[complete]`

Route planning, real-time dispatch, and day-of exception handling.

| Slice | Name | Status |
| ----- | ---- | ------ |
| 13 | ORS routing engine integration | complete |
| 14 | Dispatch (Saga-based job dispatch, DispatchDashboard DnD UI) | complete |
| 15 | Vehicle location tracking (polling + GPS ping) | complete |
| 16 / 025 | Dynamic re-routing (reassign route, emergency insert) | complete |

ADRs: [052 routing engine](../architecture/052-adr.routing-engine.md)

---

## Epic 5 — Technician Experience `[code complete; Maestro tests blocked]`

All surfaces a field technician interacts with: mobile app and mobile-optimised web.

| Slice | Name | Status |
| ----- | ---- | ------ |
| 6 | Mobile scaffold (React Native Expo in `apps/tech-mobile`) | complete |
| 17 | Technician route view (mobile) | complete |
| 18 | Location tracking from mobile | complete |
| 19 | Job entry from mobile | complete |
| 22 | Technician web view (`apps/tech-web`) | complete |

**Remaining gate:** Android Maestro E2E tests require AVD — see DEV-01 in
`950-tasks.maintenance.md`. Code is shipped; testing is blocked on hardware.

ADRs: [055 frontend](../architecture/055-adr.frontend.md)

---

## Epic 6 — AI / MCP `[complete]`

Machine-readable interface for AI clients and automation tools.

| Slice | Name | Status |
| ----- | ---- | ------ |
| 23 | MCP server (Python MCP SDK + OpenAPI codegen) | complete |

ADRs: [061 mcp-server](../architecture/061-adr.mcp-server.md)

---

## Epic 7 — Back-office Integrations `[in progress — credential-gated]`

Bi-directional sync with external CRM/ERP systems via the BackOfficeAdapter protocol.

| Slice | Name | Status |
| ----- | ---- | ------ |
| 24 | BackOfficeAdapter ABC + Saga infrastructure + OutboxPoller | complete |
| 25 | ServiceTitan adapter | not started — needs `SERVICETITAN_*` Fly.io secrets |
| 26 | PestPac adapter | not started — needs `PESTPAC_*` Fly.io secrets |
| 27 | Jobber adapter | not started — needs `JOBBER_*` Fly.io secrets + OAuth app |

**Design constraint:** Every integration must implement `BackOfficeAdapter` and run
through the Saga + Transactional Outbox infrastructure from Slice 24. Direct HTTP
calls to external APIs are not permitted outside the adapter layer.

**Before designing Slice 25–27:** Read the existing research artifact for each API
(create under `research/` if absent) and cross-reference ADR 056.

ADRs: [056 backoffice-saga](../architecture/056-adr.backoffice-saga.md)

Research: `research/025-research.servicetitan-api.md` _(not yet written)_,
`research/026-research.pestpac-api.md` _(not yet written)_,
`research/027-research.jobber-api.md` _(not yet written)_

---

## Epic 8 — Quality & E2E `[partially complete]`

Automated quality gates beyond unit tests.

| Item | Status |
| ---- | ------ |
| Playwright: Chromium + Firefox + WebKit (admin-web) | complete — runs on every push |
| Screenshot regression (pre-push hook + CI diff workflow) | complete |
| Demo video CI (`demo-videos.yml`) | complete |
| API pytest against live Fly.io test environment | blocked — needs `office-hero-test` app + secrets |
| MCP integration tests | blocked — needs live env |
| Android Maestro flows | blocked — needs AVD (DEV-01) |
| iOS Maestro flows | deferred — needs macOS (DEV-02) |

---

## Epic 9 — Infrastructure & Operations `[code complete; secrets needed]`

Deployment pipeline and production monitoring.

| Slice | Name | Status |
| ----- | ---- | ------ |
| 29 | Fly.io deployment config (`fly.api.toml`, CI workflow) | complete |
| 30 | Monitoring (Sentry + hourly uptime check workflow) | complete |

**Remaining human actions to go live:**

- `FLY_API_TOKEN` → GitHub repo secret (enables auto-deploy)
- `SENTRY_DSN` + `VITE_SENTRY_DSN` → Fly.io secrets (enables error tracking)
- `PROD_ADMIN_TOKEN` + `PROD_API_URL` → GitHub repo variables (enables uptime monitor)
- Database + JWT + ORS secrets in Fly.io (see `fly.api.toml` comments)

---

## Future Work (not yet sliced)

Ideas that have been deferred but are tracked in `003-slices.office-hero.md`:

- Tenant Admin native mobile app
- iOS EAS Build support
- Self-hosted ORS on Fly.io
- FieldEdge / ServiceMax BackOfficeAdapters
- Real-time route updates via WebSocket
- Tenant-facing analytics dashboard
