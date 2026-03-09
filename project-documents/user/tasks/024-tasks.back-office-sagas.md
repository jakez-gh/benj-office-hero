---
slice: back-office-sagas
slices: [24, 25, 26, 27]
project: office-hero
lld: ../slices/024-slice.back-office-adapter-saga.md
dependencies: [9, 10, 11, 12, 13, 14]
projectState: Foundation (Slices 1–4) and Core FSM (Slices 9–14) complete. PostgreSQL with RLS and Alembic migrations stable. Database includes outbox_events and saga_log tables (from Slice 2). Ready to implement BackOfficeAdapter protocol and Saga orchestration infrastructure for distributed transaction handling.
dateCreated: 20260308
dateUpdated: 20260308
status: not_started
---

## Context Summary

- Working on **Slices 24–27: Back-Office Integration with Saga Pattern** — implementing distributed transaction safety using Saga orchestration + Transactional Outbox + Idempotency keys
- Current state: Core FSM (Customers, Jobs, Routes, Vehicles, Dispatch) is stable; database foundation ready
- Deliverable (Slice 24): BackOfficeAdapter protocol ABC, Saga orchestrator base class, SagaService, OutboxPoller worker, idempotency handling, dead-letter management
- Slices 25–27: ServiceTitan, PestPac, Jobber adapters implementing the protocol and orchestrating their specific Saga flows
- Next: After Slice 24 infrastructure is tested, each integration slice (25–27) will implement specific Saga orchestrators

---

## Architecture Overview

**Saga Pattern + Transactional Outbox:**

1. API endpoint receives request (e.g., "sync Customer to ServiceTitan")
2. Service writes domain record + outbox event in one DB transaction → returns to client
3. Background OutboxPoller reads unprocessed outbox events
4. For each event, Saga orchestrator executes a sequence of steps with compensating transactions
5. On step failure, orchestrator unwinds via compensation; on success, marks outbox event done
6. Failed/exhausted-retry events move to dead-letter table for operator review

**Idempotency:** Every external API call includes an idempotency key; retries are safe.

---

## Task Breakdown (35 Granular Tasks)

### Phase 1: Setup — Configuration, Tables, Base Classes (8 tasks)

- [ ] Verify outbox_events table exists with correct columns: id, tenant_id, event_type, payload, idem_key, status, attempt_count, created_at, processed_at
- [ ] Verify saga_log table exists with correct columns: id, tenant_id, saga_type, current_step, status, context, created_at, updated_at
- [ ] Confirm RLS policies on outbox_events (tenant_id filtering)
- [ ] Confirm RLS policies on saga_log (tenant_id filtering)
- [ ] Create core/saga.py with SagaStatus enum (running, done, compensating, failed)
- [ ] Create core/saga.py with StepStatus enum (pending, done, failed, compensated)
- [ ] Create core/saga.py with SagaStep class (name, execute, compensate, idempotency_key)
- [ ] Create core/saga.py with SagaDefinition class (saga_type, steps list, context dict)

### Phase 2: Exceptions & Protocol (4 tasks)

- [ ] Create core/exceptions.py with SagaError exception (includes request_id, step_name, saga_id)
- [ ] Create core/exceptions.py with SagaCompensationFailed exception
- [ ] Create core/exceptions.py with BackOfficeAdapterError exception
- [ ] Create adapters/protocol.py with BackOfficeAdapter ABC (health_check, get_customer, create_customer, sync_job, cancel_job)

### Phase 3: Data Layer — Repositories (6 tasks)

- [ ] Create repositories/saga_repository.py with create(saga_type, tenant_id, context) method
- [ ] Create repositories/saga_repository.py with get_by_id(saga_id) and get_by_type_and_context() methods
- [ ] Create repositories/saga_repository.py with update_status(saga_id, new_status, context_update) method
- [ ] Create repositories/saga_repository.py with update_current_step(saga_id, step_num) method
- [ ] Create repositories/outbox_repository.py with create(tenant_id, event_type, payload, idem_key) method
- [ ] Create repositories/outbox_repository.py with get_pending(tenant_id, limit), mark_processing, mark_done, mark_dead_letter, increment_attempt_count, get_dead_letters methods

### Phase 4: Service Layer — Orchestration & Polling (5 tasks)

- [ ] Create services/saga_service.py with execute_saga() method (orchestrates all steps sequentially)
- [ ] Create services/saga_service.py with compensate() method (unwinds saga in reverse on failure)
- [ ] Create services/saga_service.py with get_saga_status() method (returns current saga state)
- [ ] Create services/outbox_poller.py with poll_and_process() method (background loop reading/processing events)
- [ ] Create services/outbox_poller.py with process_event() and register_handler() methods

### Phase 5: Idempotency & Service Integration (4 tasks)

- [ ] Create services/idempotency_service.py with generate_key(), store_result(), get_cached_result() methods
- [ ] Integrate IdempotencyService into SagaService.execute_saga() (cache step results by idem_key)
- [ ] Integrate IdempotencyService into OutboxPoller.process_event() (prevent duplicate external calls)
- [ ] Test idempotency with mock adapter: same step called twice with same key → cached result, no double API call

### Phase 6: API Endpoints (6 tasks)

- [ ] Create api/routes/sagas.py with GET /sagas/{saga_id}/state endpoint (returns saga status + context)
- [ ] Create api/routes/sagas.py with POST /sagas/{saga_id}/transition endpoint (retry/advance saga, Operator only)
- [ ] Create api/routes/admin.py with GET /admin/dead-letters endpoint (list failed events, Operator only)
- [ ] Create api/routes/admin.py with POST /admin/dead-letters/{event_id}/retry endpoint (move to pending)
- [ ] Create api/routes/admin.py with POST /admin/sagas/{saga_id}/compensate endpoint (manually trigger compensation)
- [ ] Wire saga and admin routes into api/app.py; verify auth/RBAC enforced

### Phase 7: Comprehensive Testing (7 tasks)

- [ ] Write tests/test_saga_repository.py: create, get_by_id, update_status, update_current_step (4+ tests)
- [ ] Write tests/test_outbox_repository.py: create, get_pending, mark_done, mark_dead_letter (4+ tests)
- [ ] Write tests/test_saga_state_machine.py: 3-step saga success path, failure at step 2 with compensation, compensation failure to dead-letter (3+ tests with mocked adapter)
- [ ] Write tests/test_compensation.py: compensation idempotency, reverse order, partial failure (3+ tests)
- [ ] Write tests/test_idempotency_e2e.py: repeated step call with same key returns cached result, no double external API call (2+ tests)
- [ ] Write tests/test_outbox_poller_resilience.py: crash during processing, retry after 3 failures, dead-letter recovery (3+ tests)
- [ ] Write tests/test_saga_rls.py: tenant A saga invisible to tenant B query (2+ tests); run full suite with coverage ≥80% for saga modules

### Phase 8: Documentation (4 tasks)

- [ ] Write docs/saga_tutorial.md: pattern overview, happy path diagram, failure path diagram, idempotency explanation, code example (ServiceTitan create customer + link)
- [ ] Write docs/saga_recovery.md: procedures for stuck compensation, missing events, incorrect compensation unwinding (3+ procedures with steps)
- [ ] Create adapters/template_adapter.py: skeleton class with health_check(), create_customer(), sync_job() placeholders + comments on idempotency expectations
- [ ] Write docs/saga_monitoring.md: key metrics (saga_execution_time, failures, compensations, pending events, dead-letter size), alert rules (dead-letter > 10, failures increasing)

### Phase 9: Final Validation & Commit (1 task)

- [ ] Run full test suite: `pytest tests/ -v --cov=src/office_hero`; all saga tests pass (≥35 tests), coverage ≥80%; verify app starts; commit all changes; push to feature branch

---

## Success Criteria (Phase 5 Complete)

- ✅ Task breakdown file created with 35 granular tasks across 9 phases
- ✅ Phase 1 (Setup): Database tables verified, SagaStatus/StepStatus enums, SagaStep and SagaDefinition classes (8 tasks)
- ✅ Phase 2 (Exceptions & Protocol): All exception types and BackOfficeAdapter ABC (4 tasks)
- ✅ Phase 3 (Data Layer): SagaRepository and OutboxRepository with all CRUD + RLS methods (6 tasks)
- ✅ Phase 4 (Service Layer): SagaService (orchestration + compensation), OutboxPoller (polling + processing) (5 tasks)
- ✅ Phase 5 (Idempotency): IdempotencyService and integration into saga execution (4 tasks)
- ✅ Phase 6 (API): Saga endpoints (/state, /transition), admin endpoints (/dead-letters, retry, compensate) (6 tasks)
- ✅ Phase 7 (Testing): Repositories, state machine, compensation, idempotency E2E, resilience, RLS, full suite (7 tasks)
- ✅ Phase 8 (Documentation): Tutorial, recovery procedures, adapter template, monitoring guide (4 tasks)
- ✅ Phase 9 (Final): Full test suite run + commit + push (1 task)
- ✅ All Saga pattern elements addressed: event sourcing, compensation, idempotency, dead-letter queue
- ✅ Tasks are actionable, granular, and independent
- ✅ Ready for Phase 6 execution (implementation)
