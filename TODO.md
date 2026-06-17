# Office Hero — Remaining Work

Items are removed as they are completed. Organised by horizon.

---

## Immediate (code quality / CI)

- [ ] **Admin audit-events DB wiring** — `src/office_hero/api/routes/admin.py:126` stub returns an empty list. Wire a real `AuditService` / `AuditRepository` query so the admin panel gets live data.
- [ ] **RLS integration test stubs** — `tests/integration/test_jobs_rls.py` has three skipped `TODO` tests. Requires a live Neon branch; implement once the integration CI harness is provisioned.

---

## Slice 6 — Mobile app scaffold

React Native Expo project (`apps/tech-mobile`). Needed before any Technician app slices.

- [ ] Bootstrap Expo project: `npx create-expo-app apps/tech-mobile --template expo-template-blank-typescript`
- [ ] Add `expo-location` background permission config (Android)
- [ ] Add shared API client dep (`packages/api-client`)
- [ ] Android AVD setup (see `950-tasks.maintenance.md` DEV-01)

---

## Slice 7a — Operator observability dashboard

Metrics & log viewer with live control panel for rate-limit and ban-filter management.

- [ ] Design page in `apps/admin-web/src/pages/OperatorDashboardPage.tsx`
- [ ] Connect to Grafana/Loki (DEV-03 in `950-tasks.maintenance.md`)
- [ ] Rate-limit adjustment UI → `PATCH /admin/rate-limits`
- [ ] Ban-filter management UI → `/admin/ban-filters`
- [ ] Audit-log tab (depends on `admin.py` DB wiring above)

---

## Slices 17–19 — Technician Android app

Depends on Slice 6 (mobile scaffold) and Android AVD setup.

- [ ] **Slice 17** — Auth, view own daily Route, Job details per stop, acknowledge route
- [ ] **Slice 18** — Background `expo-location` posting to `PUT /vehicles/{id}/location`
- [ ] **Slice 19** — Field Job creation from mobile

---

## Slices 25–27 — Back-office integrations

All gated on Slice 24 (BackOfficeAdapter protocol, which is complete).

- [ ] **Slice 25 — ServiceTitan** — Adapter + Saga orchestrator for Customer + Job/Work Order sync. Effort: 5/5. Risk: High.
- [ ] **Slice 26 — PestPac** — Adapter for Customer, Service Order, Contract sync. Effort: 5/5. Risk: High.
- [ ] **Slice 27 — Jobber** — Adapter for Customer and Job sync. Effort: 4/5. Risk: High.

Each integration requires:

- External API credentials (env secrets)
- Saga orchestrator + compensating transactions
- Idempotency keys in `outbox_events`
- Integration tests simulating failure at each Saga step
- Dead-letter UI in admin panel

---

## Slice 28 — Full E2E test suite

Gated on Slices 17–22 being complete.

- [ ] Android Maestro tests (requires AVD — DEV-01)
- [ ] iOS Maestro tests (requires macOS + Xcode — DEV-02, deferred)
- [ ] Playwright: Chromium + Firefox + WebKit web coverage
- [ ] API pytest suite against live test environment (all contracts + RBAC + rate limiting)
- [ ] MCP tool discovery + auth passthrough tests

---

## UX — Priority 7 (deferred)

- [ ] **Onboarding checklist widget** — "Getting started" banner for a new tenant with 0 customers: ① Add customer → ② Add vehicle → ③ Create job → ④ Schedule it. Dismiss once first job dispatched.
- [ ] **Route reorder UX** — Promote hint text to `CardDescription` or add drag-and-drop handles if user research shows confusion with current subtle hints.

---

## Dev environment (human-only tasks)

These require manual setup by Jake; Claude cannot complete them.

- [ ] **DEV-01** — Android Studio + AVD setup (`950-tasks.maintenance.md`)
- [ ] **DEV-02** — iOS Simulator (requires macOS, deferred)
- [ ] **DEV-03** — Grafana Cloud + Loki log shipping from Fly.io
- [ ] **DEV-04** — Context Forge (`cf`) CLI re-registration after moving machines

---

## Recurring maintenance

- [ ] Rotate JWT RS256 key pair annually (next due: ~2027-03)
- [ ] Review and prune dead-letter table monthly
- [ ] Quarterly `pip-audit` dependency review for major version upgrades
- [ ] Review Fly.io + Neon free-tier limits as tenant count grows

---

## Future work (not yet scoped)

- [ ] Tenant Admin native mobile app (if responsive web proves insufficient on phone)
- [ ] iOS EAS Build support
- [ ] Self-hosted ORS on Fly.io (when community ORS rate limits bite)
- [ ] FieldEdge BackOfficeAdapter
- [ ] ServiceMax BackOfficeAdapter
- [ ] Real-time Route updates via WebSocket (upgrade from 30s polling)
- [ ] Tenant-facing analytics dashboard (job completion rates, technician utilisation, route efficiency)
