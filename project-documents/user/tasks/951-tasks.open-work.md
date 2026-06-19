---
id: 1.2
title: Open work index
type: open-work
parent: 1
status: active
docType: tasks
project: office-hero
dateUpdated: 20260618
---

# Open Work Index — Office Hero

Single source of truth for all remaining work. Updated at the end of every session.
Start here at the beginning of every session — do not rely on `cf status` alone.

For the epic-level view (what workstream each item belongs to) see:
`project-documents/user/project-guides/000-initiatives.md`

---

## Ready Now (no external dependencies)

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

- [ ] **Slice 25 — ServiceTitan** — Needs `SERVICETITAN_CLIENT_ID`,
  `SERVICETITAN_CLIENT_SECRET`, `SERVICETITAN_TENANT_ID` as Fly.io secrets.
  Research complete: `research/025-research.servicetitan-api.md` (RES-025).
  Tasks: `026-tasks.servicetitan-integration.md`

- [ ] **Slice 26 — PestPac** — Needs `PESTPAC_API_KEY`, `PESTPAC_BASE_URL`
  as Fly.io secrets; also trial access via `APISales@workwave.com`.
  Research complete: `research/026-research.pestpac-api.md` (RES-026).
  **Design blocker:** confirm sync vs. async Odyssey API response model before
  writing the slice design (see RES-026 open questions).
  Tasks: `027-tasks.pestpac-integration.md`

- [ ] **Slice 27 — Jobber** — Needs `JOBBER_CLIENT_ID`, `JOBBER_CLIENT_SECRET`,
  `JOBBER_REFRESH_TOKEN` as Fly.io secrets; OAuth app at developer.getjobber.com.
  Research complete: `research/027-research.jobber-api.md` (RES-027).
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
