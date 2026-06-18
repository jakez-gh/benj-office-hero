---
id: 1.1.2.3
type: task
parent: 1.1.2
title: Tasks — Jobber integration
slice: jobber-integration
project: office-hero
lld: ../slices/028-slice.jobber-integration.md
dependencies: [24]
projectState: >
  BackOfficeAdapter protocol (Slice 24) is complete. Jobber adapter requires
  OAuth2 credentials as Fly.io secrets. No implementation started.
dateCreated: 20260617
dateUpdated: 20260617
status: not_started
docType: tasks
---

## Context Summary

Implements the Jobber BackOfficeAdapter (Customer and Job sync via Jobber GraphQL API).
Gated on Jobber OAuth2 credentials.

**Prerequisites before starting:**

- `JOBBER_CLIENT_ID`, `JOBBER_CLIENT_SECRET`, `JOBBER_REFRESH_TOKEN`
  added as Fly.io secrets
- Jobber app registered at developer.getjobber.com

---

## Task Breakdown

### Backend

- [ ] `src/office_hero/adapters/jobber/` package scaffold
- [ ] OAuth2 token refresh helper (Jobber uses short-lived access tokens)
- [ ] `JobberAdapter(BackOfficeAdapter)` — Customer sync (GraphQL clients query)
- [ ] `JobberAdapter` — Job sync (GraphQL jobs query)
- [ ] `SyncCustomerFromJobberSaga` orchestrator + compensating transactions
- [ ] `SyncJobFromJobberSaga` orchestrator
- [ ] Idempotency key handling
- [ ] Dead-letter UI entry for failed sagas

### Tests

- [ ] Integration tests for each Saga step (mocked Jobber GraphQL responses)
- [ ] OAuth2 token refresh test (mock expiry + refresh)
- [ ] Saga compensation test

### Future Work

- [ ] Jobber webhook ingestion for real-time sync
- [ ] Invoice / quote sync
