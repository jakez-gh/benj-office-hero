---
docType: slice-design
parent: ../project-guides/003-slices.office-hero.md
project: office-hero
dateCreated: 20260612
dateUpdated: 20260612
status: complete
slice: backoffice-adapter
---

# Slice Design 024: BackOfficeAdapter protocol seam

Implements **Slice 24** of the master plan: make the back-office integration seam
explicit, tested, and persistent, with `NativeAdapter` (Office Hero as system of
record) as the working default. This is what "works with the customer's existing CRM
or whatever" hangs off: ServiceTitan/PestPac/Jobber adapters (slices 25–27) drop into
this seam without touching domain services.

Existing scaffolding (saga base, protocols, in-memory mocks, dead-letter admin routes)
stays; this slice fills the gaps ADR 056 mandates.

## What lands

### 1. Persistent outbox/saga (DB-backed repositories)

* `models/outbox_event.py` + `models/saga_log.py` — ORM models mapping the existing
  `outbox_events` / `saga_log` tables from migration 0001 (string-36 ids preserved).
* Migration `0012_backoffice_seam.py`:
  * `outbox_events`: + `dead_letter_reason TEXT` (the protocol and admin UI already
    expect it), index `(tenant_id, status, created_at)`, RLS policy (ADR 053 pattern).
  * `saga_log`: + `last_error TEXT`, index `(tenant_id, saga_type)`, RLS policy.
  * `tenants`: + `back_office_adapter VARCHAR(50) NOT NULL DEFAULT 'native'` with a
    CHECK constraint on known adapter names.
* `repositories/outbox_repository.py` — `SqlOutboxRepository` implementing the full
  `OutboxRepository` protocol (incl. `list_events`, so the admin dead-letter routes
  work unchanged against Postgres).
* `repositories/saga_repository.py` — `SqlSagaRepository` implementing `SagaRepository`.

### 2. NativeAdapter for real + adapter registry

* `NativeAdapter(tenant_id, customer_repo, job_repo)` — implements every protocol
  method against local repositories; no more `NotImplementedError`. Create/update
  calls are upsert-by-`external_id` no-ops in the native case (Office Hero IS the
  system of record), reads delegate to the repos.
* `adapters/back_office/registry.py` — `get_adapter_factory(name)`; `'native'` is
  registered; unknown names raise `UnknownBackOfficeAdapterError` (422 at the API).
  Slices 25–27 register `'servicetitan'`, `'pestpac'`, `'jobber'` here.

### 3. The sync seam, end-to-end on Contracts

* `ContractService` gains an optional `outbox` dependency: `create()` enqueues a
  `backoffice.contract.created` outbox event (idempotency key = contract id) in the
  same unit of work — the Transactional Outbox of ADR 056.
* `services/back_office_sync_service.py` — `BackOfficeSyncService.process_pending
  (tenant_id, limit)`: claims pending events, resolves the tenant's adapter via the
  registry, dispatches by event type, marks done; failures increment `attempt_count`
  and dead-letter after `MAX_ATTEMPTS=5` with the error as `dead_letter_reason`.
  Retry of a dead-letter (existing admin endpoint) resets it to pending.
* `POST /admin/outbox/process` (Operator-only) — processes pending events for a
  tenant. v1 trigger is manual/cron (same posture as contract job generation); a
  background poller is future work, the seam doesn't change.

## Out of scope (tracked)

* ServiceTitan/PestPac/Jobber concrete adapters (slices 25–27) — need credentials
  and sandbox accounts.
* Background outbox poller (cron calls the admin endpoint for now).
* Tenant admin UI for choosing an adapter (operator sets the column; UI rides the
  tenant management page when slices 25+ make multiple adapters real).
* Production DB wiring of these repos into `create_app` defaults follows the
  existing per-service injection pattern.

## Tests

* `tests/unit/test_native_adapter.py` — every protocol method against in-memory
  repos; tenant scoping enforced; registry resolution incl. unknown name.
* `tests/integration/test_sql_outbox_repository.py` — full lifecycle (create →
  pending → processing → done / dead-letter → retry → list_events filters) against
  aiosqlite.
* `tests/integration/test_sql_saga_repository.py` — create/get/update status +
  step/context merge/last_error against aiosqlite.
* `tests/unit/test_back_office_sync_service.py` — happy path marks done; failing
  adapter increments attempts; exhaustion dead-letters with reason; unknown event
  type dead-letters; idempotent reprocessing.
* `tests/unit/test_contract_service.py` — contract create enqueues outbox event
  with idem key (new test in existing file).
* `tests/api/test_admin_outbox_api.py` — operator-only process endpoint.

## Dependencies

Slices 2 (DB), 3 (RBAC), existing saga/outbox scaffolding, Slice 11 (contracts —
first producer through the seam). ADRs 053, 056, 058, 063.

## Effort: 3/5

## Risk callouts

* **String-36 ids on legacy tables** — kept as-is to avoid a risky type migration;
  repos convert at the boundary. Revisit when slices 25–27 land.
* **RLS + operator flows** — outbox/saga tables get the standard tenant policy;
  operator dead-letter views run per-tenant (matching how admin routes already pass
  tenant context). Cross-tenant operator dashboards are slice 7a's problem.
* **At-least-once delivery** — process_pending marks processing before dispatch; a
  crash between dispatch and mark_done re-delivers. Adapters must be idempotent
  (idem_key is in every payload). Documented on the protocol.
