---
id: 1.1.2.2
type: task
parent: 1.1.2
title: Tasks — PestPac integration
slice: pestpac-integration
project: office-hero
lld: ../slices/027-slice.pestpac-integration.md
dependencies: [24]
projectState: >
  BackOfficeAdapter protocol (Slice 24) is complete. PestPac adapter
  requires external API credentials as Fly.io secrets. No implementation started.
dateCreated: 20260617
dateUpdated: 20260617
status: not_started
docType: tasks
---

## Context Summary

Implements the PestPac BackOfficeAdapter (Customer, Service Order, Contract sync).
Gated on external PestPac API credentials.

**Prerequisites before starting:**

- `PESTPAC_API_KEY`, `PESTPAC_BASE_URL` added as Fly.io secrets

---

## Task Breakdown

### Backend

- [ ] `src/office_hero/adapters/pestpac/` package scaffold
- [ ] `PestPacAdapter(BackOfficeAdapter)` — Customer sync
- [ ] `PestPacAdapter` — Service Order sync
- [ ] `PestPacAdapter` — Contract sync
- [ ] `SyncCustomerFromPestPacSaga` orchestrator + compensating transactions
- [ ] `SyncServiceOrderFromPestPacSaga` orchestrator
- [ ] Idempotency key handling
- [ ] Dead-letter UI entry for failed sagas

### Tests

- [ ] Integration tests for each Saga step (mocked PestPac HTTP responses)
- [ ] Saga compensation test
- [ ] Dead-letter trigger and retry test

### Future Work

- [ ] Recurring service schedule import
- [ ] Pesticide application record sync
