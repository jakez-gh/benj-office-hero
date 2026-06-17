---
docType: tasks
project: office-hero
dateUpdated: 20260617
---

# Open Work Index — Office Hero

Single source of truth for all remaining work. Updated at the end of every session.
Start here at the beginning of every session — do not rely on `cf status` alone.

---

## Ready Now (no external dependencies)

### UX / Polish

- [ ] **Route reorder UX hint** — The "Use ↑↓ to reorder" text on the Routes
  page is subtle. If user testing shows confusion, promote to `CardDescription`
  or add a more visible drag handle. Currently deferred pending feedback.
  File: `apps/admin-web/src/pages/RoutesPage.tsx`
  Effort: 1/5 — one-liner change once the decision is made.

### Infrastructure / Ops

- [ ] **Activate Sentry** — Set `SENTRY_DSN` + `VITE_SENTRY_DSN` in Fly.io
  once a Sentry project is created (free tier). No code change needed.
- [ ] **Activate CI/CD** — Add `FLY_API_TOKEN` GitHub repo secret
  (`flyctl tokens create deploy`). Then every push to `main` auto-deploys.
- [ ] **Activate uptime monitoring** — Add `PROD_ADMIN_TOKEN` + `PROD_API_URL`
  as GitHub repo variables to enable the dead-letter count check in
  `.github/workflows/uptime.yml`.

---

## Needs External Setup (blocked on credentials or environment)

### Slice 6 — Mobile scaffold

Blocked on: Android emulator / real device setup.

- [ ] React Native Expo project (`apps/tech-mobile`)
- [ ] Android build config, `expo-location` background permission setup
- [ ] See `010-tasks.mobile-scaffold.md`

### Slices 17–19 — Technician Android app

Blocked on: Slice 6 completion.

- [ ] Route view, location tracking, job entry from mobile
- [ ] See slice plan entries 17–19 in `003-slices.office-hero.md`

### Slices 25–27 — Back-office integrations

Blocked on: External API credentials (ServiceTitan, PestPac, Jobber).

- [ ] Each implements `BackOfficeAdapter` protocol (Slice 24, complete)
- [ ] Each requires Saga + Transactional Outbox (see ADR 056)
- [ ] See slice plan entries 25–27 in `003-slices.office-hero.md`

### Slice 28 — E2E test suite

Blocked on: Slices 17–19 (mobile) completion.

- [ ] Playwright (web), Maestro (Android/iOS), pytest+httpx (API), pytest (MCP)
- [ ] See `003-slices.office-hero.md` slice 28

---

## Viable Next Slice Work (no external blockers, just needs design + scheduling)

### Slice 7a — Operator observability dashboard

Effort: 3/5. Frontend-heavy. Unblocked.

- [ ] Metrics + log viewer for Operators
- [ ] Live rate-limit control panel (adjust limits at runtime)
- [ ] Audit-log tab
- [ ] Design doc needed: create `project-documents/user/slices/007a-slice.operator-dashboard.md`

---

## Future Work (from slice plan, not yet scheduled)

These items are in the "Future Work" section of `003-slices.office-hero.md`.
Not tracked as slices yet — promote to a numbered slice when scheduling.

- [ ] Tenant Admin native mobile app (if responsive web admin proves insufficient)
- [ ] iOS support (EAS Build for React Native Expo)
- [ ] Self-hosted ORS (when rate limits or latency become problematic)
- [ ] FieldEdge integration (BackOfficeAdapter)
- [ ] ServiceMax integration (BackOfficeAdapter)
- [ ] Real-time Route updates via WebSocket (upgrade from polling)
- [ ] Tenant-facing analytics dashboard (completion rates, utilisation, route efficiency)

---

## Update Log

| Date | What changed |
| --- | --- |
| 2026-06-17 | Initial creation; onboarding checklist moved to [x] (implemented); Slices 1–16, 1a, 21–24, 29–30 all complete; 020-tasks fully checked except Route reorder UX hint |
