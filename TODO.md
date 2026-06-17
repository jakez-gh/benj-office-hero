# Office Hero — Remaining Work

Items are removed as they are completed. Organised by horizon.

---

## UX — Priority 7

- [ ] **Route reorder UX** — Promote hint text to `CardDescription` or add explicit
  drag handles if user research shows confusion with the current subtle hints.
  Deferred pending feedback.

---

## Slices 25–27 — Back-office integrations

All gated on Slice 24 (BackOfficeAdapter protocol, complete). Each requires
external API credentials added as Fly.io secrets.

- [ ] **Slice 25 — ServiceTitan** — Adapter + Saga for Customer + Job/Work Order sync.
  Effort: 5/5. Risk: High.
- [ ] **Slice 26 — PestPac** — Adapter for Customer, Service Order, Contract sync.
  Effort: 5/5. Risk: High.
- [ ] **Slice 27 — Jobber** — Adapter for Customer and Job sync. Effort: 4/5. Risk: High.

Each integration requires: external API credentials, Saga orchestrator +
compensating transactions, idempotency keys, integration tests per Saga step,
dead-letter UI in admin panel.

---

## Slice 28 — Full E2E test suite

Gated on Slices 17–22 being stable (all complete).

- [x] Playwright: Firefox + WebKit already in `playwright.config.ts`; CI runs all three on main pushes
- [ ] API pytest suite against live Fly.io test environment (needs live env secrets)
- [ ] MCP tool discovery + auth passthrough tests (needs live env)
- [ ] Android Maestro tests (requires AVD — DEV-01 in `950-tasks.maintenance.md`)
- [ ] iOS Maestro tests (requires macOS + Xcode — DEV-02, deferred)

---

## Dev environment (human-only tasks)

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
- [ ] Tenant-facing analytics dashboard (job completion rates, technician utilisation,
  route efficiency)
