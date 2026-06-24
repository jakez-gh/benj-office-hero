---
id: 1.2
title: Open work index
type: open-work
parent: 1
status: active
docType: tasks
project: office-hero
dateUpdated: 20260624
---

# Open Work Index — Office Hero

Single source of truth for all remaining work. Updated at the end of every session.
Start here at the beginning of every session — do not rely on `cf status` alone.

For the epic-level view (what workstream each item belongs to) see:
`project-documents/user/project-guides/000-initiatives.md`

---

## Ready Now (no external dependencies)

### Tenant Management (Epic 7 — Slices 29–30)

- [ ] **Slice 29 — Tenant admin backend** — Add `GET /admin/tenants` (list, with
  `jobber_connected` flag) and `POST /admin/tenants` (create) to `integrations.py`.
  8 integration tests. Effort: 1.5/5.
  Slice: `029-slice.tenant-admin-backend.md` | Tasks: `031-tasks.tenant-admin-backend.md`

- [ ] **Slice 30 — Tenant admin UI** — New `TenantsPage.tsx` with tenant list,
  adapter selector, Jobber OAuth2 connect button, and create form. Depends on Slice 29.
  Effort: 2/5.
  Slice: `030-slice.tenant-admin-ui.md` | Tasks: `032-tasks.tenant-admin-ui.md`

### UX / Polish

- [ ] **Route reorder UX hint** — The "Use ↑↓ to reorder" text on the Routes
  page is subtle. If user testing shows confusion, promote to `CardDescription`
  or add a more visible drag handle. Currently deferred pending feedback.
  File: `apps/admin-web/src/pages/RoutesPage.tsx`
  Effort: 1/5 — one-liner change once the decision is made.

### Infrastructure / Ops

These are human actions (no code changes required):

- [ ] **Activate CI/CD** — Add `FLY_API_TOKEN` GitHub repo secret
  (`flyctl tokens create deploy`). Then every push to `main` auto-deploys.
- [ ] **Activate Sentry** — Create Sentry project (free tier), add `SENTRY_DSN`
  as a Fly.io secret and `VITE_SENTRY_DSN` as a Fly.io build var.
- [ ] **Activate uptime monitoring** — Add `PROD_ADMIN_TOKEN` + `PROD_API_URL`
  as GitHub repo variables to enable the hourly dead-letter check.

---

## Needs External Setup (blocked on credentials or environment)

### Slices 25–27 — Back-office integrations (Epic 7)

Blocked on: External API credentials for each system.

**Adapter wiring complete** (no credentials needed to complete these):

- `BackOfficeSyncService._adapter_name` does lazy DB lookup per tenant
- `_register_back_office_adapters()` called at startup — adapters auto-register
  when their env vars are set on the Fly.io machine
- `PATCH /admin/tenants/{id}/adapter` endpoint lets operators switch a tenant's
  back-office adapter at any time
- `GET /admin/integrations/jobber/connect` + `GET /admin/integrations/jobber/callback`
  complete the Jobber OAuth2 flow and store tokens in `jobber_credentials`

- [ ] **Slice 25 — ServiceTitan** — Needs `SERVICETITAN_CLIENT_ID`,
  `SERVICETITAN_CLIENT_SECRET`, `SERVICETITAN_APP_KEY`, `SERVICETITAN_TENANT_ID`
  as Fly.io secrets. **Pre-impl complete**: adapter (`servicetitan.py`) + 14 tests
  + migration 0015 + slice design `026-slice.servicetitan-integration.md`.
  Research: `research/025-research.servicetitan-api.md` (RES-025).
  Tasks: `026-tasks.servicetitan-integration.md`

- [ ] **Slice 26 — PestPac** — Needs `PESTPAC_API_KEY`, `PESTPAC_COMPANY_KEY`
  as Fly.io secrets; trial access via `APISales@workwave.com`.
  **Pre-impl partial**: scaffold (`pestpac.py`) + 10 tests + migration 0017 +
  slice design `027-slice.pestpac-integration.md` (`status: needs-sandbox`).
  HTTP call layer still blocked on RES-026 Q1 (sync vs. async response model).
  Research: `research/026-research.pestpac-api.md` (RES-026).
  Tasks: `027-tasks.pestpac-integration.md`

- [ ] **Slice 27 — Jobber** — Needs `JOBBER_CLIENT_ID`, `JOBBER_CLIENT_SECRET`
  as Fly.io secrets + OAuth app at developer.getjobber.com.
  **Pre-impl complete**: adapter (`jobber.py`) + 10 tests + migration 0016 +
  slice design `028-slice.jobber-integration.md`. Credentials stored in DB via
  OAuth2 callback; `from_tenant` loads them lazily on first API call.
  Research: `research/027-research.jobber-api.md` (RES-027).
  Tasks: `028-tasks.jobber-integration.md`

All three implement `BackOfficeAdapter` + Saga + Transactional Outbox.
See ADR 056: `project-documents/user/architecture/056-adr.backoffice-saga.md`

### Slice 28 / 29 — Remaining E2E tests (Epic 8)

Web Playwright is complete and runs on every push. What's blocked:

- [ ] **API pytest against live env** — Needs a `office-hero-test` Fly.io app
  with `LIVE_TEST_API_URL` and `LIVE_TEST_ADMIN_TOKEN` GitHub secrets.
  Tasks: `029-tasks.e2e-test-suite.md`

- [ ] **Android Maestro flows** — Needs Android Studio + AVD (DEV-01 in
  `950-tasks.maintenance.md`). Code is written; testing requires hardware setup.

- [ ] **iOS Maestro flows** — Deferred. Requires macOS (DEV-02).

---

## Dev Environment (human-only tasks)

See `950-tasks.maintenance.md` for full detail.

- [ ] **DEV-01** — Android Studio + AVD setup (unlocks Maestro E2E tests)
- [ ] **DEV-02** — iOS Simulator (requires macOS, deferred)
- [ ] **DEV-03** — Grafana Cloud + Loki log shipping from Fly.io
- [ ] **DEV-04** — Context Forge (`cf`) CLI re-registration after moving machines

---

## Inbox (drive-by capture — triage to a section above)

_(empty)_

---

## Future Work (not yet sliced — from `003-slices.office-hero.md`)

Promote to a numbered slice + task file when scheduling.

- [ ] Tenant Admin native mobile app
- [ ] iOS EAS Build support
- [ ] Self-hosted ORS on Fly.io
- [ ] FieldEdge / ServiceMax BackOfficeAdapters
- [ ] Real-time route updates via WebSocket (upgrade from polling)
- [ ] Tenant-facing analytics dashboard

---

## Update Log

| Date | What changed |
| --- | --- |
| 2026-06-17 | Created; initial state |
| 2026-06-17 | Removed stale Slice 7a entry (implemented 2026-06-17); removed Slices 6/17-19 (code complete in apps/tech-mobile + apps/tech-web — only Maestro tests remain, tracked under Slice 28); added initiatives file reference; added research/ prereq notes for Slices 25-27 |
| 2026-06-18 | Adopted segmented-decimal spine ids (ADR 1.1.7) across the active path: concept→spec→HLD→14 ADRs→slice plan→initiatives→open tasks (26-29)→research (RES-025/026/027). `/framework-check` PASS (27 artifacts, 0 warn). Added `## Inbox` drive-by capture section. |
| 2026-06-18 | Pre-impl: ServiceTitan adapter (14 tests pass), Jobber adapter (10 tests pass), PestPac scaffold (10 tests pass); migrations 0015/0016/0017; slice designs 026/027/028; CLAUDE.md Gate 1 updated with /framework-check pointer + spine IDs. Cleared Inbox. |
| 2026-06-24 | Adapter wiring: lazy DB lookup in `_adapter_name`; `_register_back_office_adapters()` in lifespan; `JobberAdapter` lazy credential load + DB token persist; `JobberCredentials` ORM model; integrations router (`PATCH /admin/tenants/{id}/adapter`, Jobber OAuth2 connect/callback). 37 adapter tests pass. |
