---
id: 1.2
title: Open work index
type: open-work
parent: 1
status: active
docType: tasks
project: office-hero
dateUpdated: 20260627b
---

# Open Work Index — Office Hero

Single source of truth for all remaining work. Updated at the end of every session.
Start here at the beginning of every session — do not rely on `cf status` alone.

For the epic-level view (what workstream each item belongs to) see:
`project-documents/user/project-guides/000-initiatives.md`

---

## Ready Now (no external dependencies)

### Tenant Management (Epic 7 — Slices 29–30)

- [x] **Slice 29 — Tenant admin backend** — `GET /admin/tenants`, `POST /admin/tenants`,
  `PATCH /admin/tenants/{id}/adapter`, Jobber OAuth2 connect/callback. Complete.
  Slice: `029-slice.tenant-admin-backend.md` | Tasks: `031-tasks.tenant-admin-backend.md`

- [x] **Slice 30 — Tenant admin UI** — `TenantsPage.tsx` with list, adapter selector,
  Jobber connect button, create form. Operator nav wired. TypeScript clean. Complete (081f80f).
  Slice: `030-slice.tenant-admin-ui.md` | Tasks: `032-tasks.tenant-admin-ui.md`

### UX / Polish

Full findings: `project-documents/user/tasks/033-tasks.ui-improvements.md`

**CRITICAL — app broken on mobile:**

- [x] **UI-01: Mobile nav overflow** — hamburger drawer shipped by gamma (WS-09, 50cd9bd)
- [x] **UI-02: Tenants table overflow-x-auto** — (d0d4bae)
- [x] **UI-03: Vehicles "New Vehicle" button** — (d0d4bae)
- [x] **UI-04: Users "New User" button** — (d0d4bae)
- [x] **UI-05: CustomersPage empty-state CTA now a Button** — (d0d4bae)
- [x] **UI-06: OperatorDashboardPage error style** — now uses inline ErrorBanner + Retry (d0d4bae)
- [x] **UI-07: Operator Dashboard retry button** — (d0d4bae)
- [x] **UI-08: Button labels standardised** — "New Job", "New Contract", "New Customer" (d0d4bae)
- [x] **UI-09: Onboarding suppressed on /tenants and /operator** — (d0d4bae)
- [x] **UI-10: Forgot password link added to LoginPage** — (d0d4bae)

- [ ] **Route reorder UX hint** — The "Use ↑↓ to reorder" text on the Routes
  page is subtle. If user testing shows confusion, promote to `CardDescription`
  or add a more visible drag handle. Currently deferred pending feedback.
  File: `apps/admin-web/src/pages/RoutesPage.tsx`
  Effort: 1/5 — one-liner change once the decision is made.

**LOW:**

- [x] **UI-11: Routes native date picker** — added `[color-scheme:light]` for
  consistent cross-browser appearance (a40b4c6). Full shadcn Calendar deferred.

- [x] **UI-12/13/14** — UI-12 confirmed no-change (CardDescription already
  `text-neutral-500`); "0 jobs/contracts" count hidden when total=0 (a40b4c6);
  Dispatch retry button added + optionsRetryKey state (a40b4c6).

**QA / Screenshot & Demo Coverage:**

- [x] **QA-01: screenshots-seeded.spec.ts** — `/tenants` and `/operator` routes
  added with tenant seeding + lowercase role fix (ccba43b).

- [x] **QA-02: Demo 4 — Tenants admin + Operator Dashboard** — Demo 4 added to
  `demo-flows.spec.ts` with 2 seeded tenants + create flow + operator page
  (ccba43b). Role case bug fixed: `Operator` → `operator` (a40b4c6).

### Live Route Events (Slice 032-LRE)

- [ ] **Slice 032-LRE — Live route events via SSE** — PR #143 open, awaiting merge.
  Backend: `GET /routes/{id}/events` SSE endpoint + `route_events.py` pub/sub hub.
  Frontend: `useRouteEvents` hook + `RouteCard` subscribes when `in_progress`.
  5 pub/sub hub tests, 569 backend tests all pass. TypeScript clean.
  Slice: `032-slice.live-route-events.md` | ADR: `064-adr.server-sent-events.md`

### Sales &amp; Documentation (Slices 032–033)

- [x] **Slice 032 — Sales materials** — 12-slide A4 HTML/PDF deck (`docs/sales/sales-deck.html`),
  Playwright PDF generator (`scripts/generate-sales-pdf.mjs`), sales DEMO_GUIDE.md,
  demo-flows `networkidle` → `load` fix. Complete (2026-06-27).
  Slice: `032-slice.sales-materials.md` | Tasks: `034-tasks.sales-materials.md`

- [x] **Slice 033 — Customer docs** — Nine-file documentation suite in `docs/customer/`:
  index, getting-started, admin-guide, dispatch-guide, contracts-guide, technician-guide,
  integrations-guide, security-guide, faq. Complete (2026-06-27).
  Slice: `033-slice.customer-docs.md` | Tasks: `035-tasks.customer-docs.md`

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
- [x] Real-time route updates — implemented via SSE (Slice 032-LRE, PR #143)
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
| 2026-06-24 | Full-app UI screenshot review (all 10 pages, desktop + mobile). 14 findings logged in `033-tasks.ui-improvements.md`. Critical: mobile nav overflow (5+ pages unreachable). High: missing Vehicles/Users add buttons, non-clickable empty-state CTAs, 3 inconsistent error styles. Medium/low: button label consistency, onboarding on operator pages, forgot-password. WS-09–12 added to workstreams. |
| 2026-06-24 | QA coverage audit: screenshots.spec.ts complete (all 10 pages). Added QA-01 (seeded spec missing tenants/operator) and QA-02 (Demo 4 — Tenants + Operator Dashboard). WS-14 added. |
| 2026-06-25 | Slice 031 complete: all UI-01–14 done, QA-01/02 done. UI-11 partial fix (color-scheme:light on date input). UI-12 confirmed no-change. UI-13/14 + demo role fix shipped (a40b4c6). Multi-agent coordination bootstrapped (.agents/ dir, WORKSTREAMS.md, ROSTER.md, per-agent heartbeats). All WS-01–14 done. Coverage: 558 tests, 77.95%. 526c12a pushed. |
| 2026-06-27 | Session close. No new code work. Confirmed: all Ready-Now code items done, slice 031 marked complete (000e304). Framework-check PASS (36 artifacts). Memory updated (ux-backlog-status, slice-completion-status). Remaining open work = external-credential-gated (Slices 25–27), hardware-gated (Slice 28 E2E), and human-action ops items. |
| 2026-06-27 | Sales materials (Slice 032) + Customer docs (Slice 033) complete. Sales deck: docs/sales/sales-deck.html (12 slides, A4 landscape), scripts/generate-sales-pdf.mjs, docs/sales/DEMO_GUIDE.md. Demo fix: networkidle → load in demo-flows.spec.ts. Customer docs: 9-file suite in docs/customer/. |
| 2026-06-27 | Slice 032-LRE (Live Route Events via SSE) implementation complete, PR #143 open. route_events.py pub/sub hub + GET /routes/{id}/events SSE endpoint + useRouteEvents React hook. 569 backend tests pass, TypeScript clean. Removed "Real-time via WebSocket" from Future Work (done as SSE). |
