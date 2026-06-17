---
slice: servicetitan-integration
project: office-hero
lld: ../slices/026-slice.servicetitan-integration.md
dependencies: [24]
projectState: >
  BackOfficeAdapter protocol (Slice 24) is complete. ServiceTitan adapter
  requires external API credentials (client_id, client_secret, tenant_id)
  as Fly.io secrets. No implementation started.
dateCreated: 20260617
dateUpdated: 20260617
status: not_started
docType: tasks
---

## Context Summary

Implements the ServiceTitan BackOfficeAdapter. Depends on the Saga orchestration
infrastructure from Slice 24. Gated on external ServiceTitan API credentials.

**Prerequisites before starting:**

- `SERVICETITAN_CLIENT_ID`, `SERVICETITAN_CLIENT_SECRET`, `SERVICETITAN_TENANT_ID`
  added as Fly.io secrets and GitHub Actions repository secrets

---

## Task Breakdown

### Backend

- [ ] `src/office_hero/adapters/servicetitan/` package scaffold
- [ ] `ServiceTitanAdapter(BackOfficeAdapter)` — Customer sync (GET /crm/v2/customers)
- [ ] `ServiceTitanAdapter` — Job / Work Order sync (GET /jpm/v2/jobs)
- [ ] `DispatchJobToServiceTitanSaga` orchestrator + compensating transactions
- [ ] Idempotency key handling (`outbox_events` + `saga_log`)
- [ ] Dead-letter UI entry in admin panel for failed sagas

### Tests

- [ ] Integration tests for each Saga step (mocked ServiceTitan HTTP responses)
- [ ] Saga compensation test (verify rollback on step N failure)
- [ ] Dead-letter trigger and manual retry test

### Future Work

- [ ] Webhook ingestion (ServiceTitan → Office Hero event push)
- [ ] Full field-mapping for technician dispatch status sync
