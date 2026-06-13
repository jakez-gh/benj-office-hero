---
docType: slice-design
parent: ../project-guides/003-slices.office-hero.md
project: office-hero
dateCreated: 20260612
dateUpdated: 20260612
status: complete
slice: contract-management
---

# Slice Design 023: Contract management

Implements **Slice 11** of the master slice plan: recurring service agreements
(PestPac-style Contracts) that generate Jobs on a schedule. A Contract belongs to a
Customer + Location, carries a `frequency` and `next_due` date, and produces Jobs via
an explicit, idempotent-by-construction generation pass (no background worker in v1 —
generation is triggered by API/CLI, suitable for cron).

This is the core of the product promise: *"allow a customer to enter a new contract…
and have suggested routes for trucks."* Generated Jobs flow into the existing
routing-options → dispatch pipeline unchanged.

## Contract status lifecycle

```text
create → active ⇄ paused
            │       │
            └── end ┴──→ ended   (terminal)
```

Encoded in `core/contract_status.py` (`ContractStatus` enum + `can_transition()` +
`is_terminal()`), mirroring `core/job_status.py`. Illegal transitions raise
`InvalidContractTransitionError` → HTTP 422.

## Frequency & job generation

* `core/contract_frequency.py` — `ContractFrequency` enum:
  `WEEKLY, BIWEEKLY, MONTHLY, QUARTERLY, SEMIANNUAL, ANNUAL` and a pure helper
  `advance_date(d: date, freq, *, anchor_day) -> date` (calendar-safe month
  arithmetic: the day-of-month **anchor** — `start_date.day` — is clamped per
  occurrence, e.g. Jan 31 + monthly → Feb 28/29 → Mar 31, so the cadence recovers
  after short months instead of drifting permanently).
* `ContractService.generate_due_jobs(tenant_id, user_id, *, as_of: date) -> list[Job]`:
  * For each `active` contract with `next_due <= as_of`:
    * Create a Job (title = `"{contract.title} — {next_due:%b %d, %Y}"`,
      `requested_at = next_due` at 09:00 UTC, fields copied from the contract,
      `contract_id` linkage set) via the Job repository.
    * Advance `next_due` by `frequency`; repeat while still `<= as_of`
      (catch-up, hard cap 24 iterations per contract per run as a runaway guard).
    * If `end_date` is set and the advanced `next_due > end_date`, transition the
      contract to `ended` automatically (audit `contract.ended`, reason `end_date reached`).
  * **Idempotency is by construction**: `next_due` advances in the same unit of work as
    job creation, so a re-run with the same `as_of` generates nothing. Concurrent
    double-runs are out of scope for v1 (single app instance; documented risk).
  * Emits audit `contract.jobs_generated` with `{contract_ids, job_ids, as_of}`.
* `as_of` is capped at today + 31 days (422 beyond): a typo'd year would otherwise
  mass-create jobs, skip every real visit, and irreversibly auto-end contracts.
* Resume semantics: visits whose due date fell **on/after the pause began** roll
  forward (the tenant deliberately skipped them); a `next_due` already overdue
  *before* the pause is left untouched for the next generation run to back-fill.
* Trigger points: `POST /contracts/generate-jobs` (admin/cron) and `tools/cli.py
  generate-jobs` for operator cron use.

## Data model

`models/contract.py` — `Contract`:

* `id`, `tenant_id` (FK tenants, RLS pivot), `customer_id` (FK), `location_id` (FK)
* `industry` (copied from caller-resolved tenant industry at create, immutable — same
  rationale as Job), `title` (255), `description` (Text, nullable)
* `service_type` (120, nullable), `priority` (int, default 50),
  `estimated_duration_min` (default 60) — copied onto generated Jobs
* `frequency` (20, CHECK constraint), `start_date` (Date), `next_due` (Date),
  `end_date` (Date, nullable)
* `status` (20, default `active`, CHECK), `paused_at`, `ended_at`, `end_reason`
* `custom_fields` (JSONB, validated by the industry template registry, copied to Jobs)
* `external_id` (255, nullable — back-office link per ADR 056)
* `created_by_user_id`, `created_at`, `updated_at`
* Indexes: `(tenant_id, status)`, `(tenant_id, next_due)`, `(tenant_id, customer_id)`

`models/job.py` — add nullable `contract_id` FK (provenance of generated jobs; exposed
in `JobRead`/`JobSummary` so the UI can badge contract-generated work).

Migration `alembic/versions/0011_contracts.py`: contracts table + RLS policy
(`tenant_id = current_setting('app.tenant_id')::uuid`) + CHECK constraints + indexes;
`ALTER TABLE jobs ADD COLUMN contract_id uuid NULL REFERENCES contracts(id)`.

## Layers (mirroring the Job stack exactly)

* `repositories/contract_repository.py` — `ContractRepositoryProtocol` +
  `ContractRepository` (SQLAlchemy) + `InMemoryContractRepository`. Methods: `create`,
  `get_by_id`, `list(status, customer_id, search, due_before, limit, offset)`,
  `update_fields`, `update_status`, `list_due(tenant_id, as_of)`.
* `services/contract_service.py` — `ContractService(repo, customer_repo, location_repo,
  job_repo, audit, template_registry)`: create (customer/location tenant + ownership
  checks, custom-field template validation), get, list, update (immutable: `tenant_id`,
  `customer_id`, `industry`, `status`, `created_by_user_id`; `next_due` IS patchable —
  "skip a visit" is a real workflow), pause/resume/end transitions, generate_due_jobs.
* `api/schemas/contract.py` — `ContractCreate` (extra="forbid"), `ContractUpdate`,
  `ContractEndRequest {reason?}`, `GenerateJobsRequest {as_of?: date}`,
  `ContractSummary`, `ContractRead`, `ContractList`, `GenerateJobsResponse`.
* `api/routes/contracts.py` — `create_contract_router(service_provider)`:
  * `POST /contracts` — `contracts:write` (TenantAdmin, Sales) — 60/min
  * `GET /contracts`, `GET /contracts/{id}` — `contracts:read` — 120/min
  * `PATCH /contracts/{id}` — `contracts:write`
  * `POST /contracts/{id}/pause|resume|end` — `contracts:write`
  * `POST /contracts/generate-jobs` — `contracts:write` **and** `jobs:write`
* Wire into `api/app.py` (+ in-memory default), `api/state.py`
  (`set_contract_service`/`get_contract_service`).
* `core/exceptions.py` — `ContractNotFoundError` (404),
  `InvalidContractTransitionError` (422, carries from/to).

## Frontend (admin-web)

* `api.ts`: Contract types + list/create/get/update/pause/resume/end/generate functions.
* `pages/ContractsPage.tsx`: list (status filter, search, next-due column, frequency
  labels, status badges), Create modal (customer → location pickers, frequency,
  start date, service type, duration, priority), row actions (pause/resume/end),
  "Generate due jobs" action surfacing how many Jobs were created.
* Nav + route registration; design-system components only.

## Tests

* `tests/unit/test_contract_frequency.py` — advance_date matrix incl. month-end
  clamping and leap years.
* `tests/unit/test_contract_service.py` — create validation (cross-tenant customer,
  location/customer mismatch, template validation), transition matrix, update
  immutability, generation: single due, catch-up multiple periods, paused/ended
  skipped, end_date auto-end, idempotent re-run, audit events.
* `tests/api/test_contracts_api.py` — 401/403/404 RBAC + cross-tenant, CRUD, filters
  and pagination, Sales role can create, generate endpoint requires both permissions.
* admin-web: Jest test for ContractsPage rendering + create flow (mocked api).

## Dependencies

Slices 2–4 (DB/auth/observability), 9 (customers/locations), 10 (jobs — generated jobs
reuse JobRepository), 12-design custom-field template registry. ADRs 053, 056 (the
`external_id` seam; outbox wiring lands in the back-office slice), 058–060, 062–063.

## Effort: 3/5

## Risk callouts

* **Generation concurrency** — two simultaneous generate calls can double-create. v1
  accepts this (single instance + manual/cron trigger); revisit with `SELECT … FOR
  UPDATE` when a worker lands.
* **Time-zone semantics** — `next_due` is a date; jobs materialise at 09:00 UTC.
  Tenant-local business hours are future work (needs tenant timezone column).
* **`requested_at` vs dispatch** — generated jobs are `pending`; dispatch (slice 14)
  remains the human-in-the-loop step that turns them into routed work. No auto-dispatch.
