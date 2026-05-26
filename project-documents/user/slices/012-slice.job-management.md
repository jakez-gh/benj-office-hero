---
docType: slice-design
parent: ../project-guides/003-slices.office-hero.md
project: office-hero
dateCreated: 20260524
status: not_started
---

# Slice Design 012: Job management (core CRUD)

This slice implements the **Job** aggregate — the operational unit of Office Hero. A Job
belongs to a `Customer` and a `Location` (from slice 11), carries industry-specific
`custom_fields` in a JSONB column validated against per-industry templates, and has a strict
status lifecycle enforced by the service layer. Illegal transitions return **422 Unprocessable
Entity**; every state-changing operation emits an audit event via `AuditService`.

This slice deliberately scopes to CRUD + state transitions. **Routing** (Slice 13) and
**Dispatch** (Slice 14) consume the Job model created here; **Contracts** (Slice 11 of the
master plan, design doc not in this batch) generate Jobs from recurring schedules later.

It implements **Slice 10** of the master slice plan.

## Job Status Lifecycle

```text
                   ┌──────────┐
       create →    │ pending  │ ──── cancel ───────┐
                   └────┬─────┘                    │
                        │ schedule                 │
                        ▼                          │
                   ┌──────────┐                    │
                   │scheduled │ ──── cancel ───────┤
                   └────┬─────┘                    │
                        │ start                    │
                        ▼                          │
                   ┌──────────────┐                │
                   │ in_progress  │ ─── cancel ────┤
                   └────┬─────────┘                │
                        │ complete                 │
                        ▼                          ▼
                   ┌──────────┐              ┌──────────┐
                   │ complete │              │cancelled │
                   └──────────┘              └──────────┘
```

* Allowed transitions are encoded in a `JobTransition` table (Python dict, not DB):
  `{("pending", "scheduled"), ("pending", "cancelled"), ("scheduled", "in_progress"),
  ("scheduled", "cancelled"), ("in_progress", "complete"), ("in_progress", "cancelled")}`.
* Any other transition raises `InvalidJobTransitionError` → HTTP 422.
* `complete` and `cancelled` are terminal — no transitions out.
* Re-opening a completed/cancelled Job is **out of scope for this slice**; ticket as future work.

## Goals

* Extend `src/office_hero/core/exceptions.py`:
  * `class JobNotFoundError(Exception)`
  * `class InvalidJobTransitionError(Exception)` — carries `from_status` and `to_status`.
  * `class CustomFieldValidationError(Exception)` — carries `field_name`, `errors: list[str]`.
* Create `src/office_hero/core/job_status.py` — `JobStatus` enum (`StrEnum`):
  * `PENDING = "pending"`, `SCHEDULED = "scheduled"`, `IN_PROGRESS = "in_progress"`,
    `COMPLETE = "complete"`, `CANCELLED = "cancelled"`.
  * Module-level constant `ALLOWED_TRANSITIONS: frozenset[tuple[JobStatus, JobStatus]]` as above.
  * Helper `def can_transition(current: JobStatus, target: JobStatus) -> bool`.
  * Helper `def is_terminal(status: JobStatus) -> bool`.
* Create `src/office_hero/core/industry.py` — `Industry` enum:
  * `PLUMBING = "plumbing"`, `HVAC = "hvac"`, `PEST_CONTROL = "pest_control"`,
    `GENERIC = "generic"` (default fallback when Tenant has no industry configured).
* Create `src/office_hero/services/custom_field_templates/__init__.py` — pluggable templates:
  * `class CustomFieldTemplate(Protocol)`:
    * `industry: Industry` (class attribute)
    * `def validate(custom_fields: dict) -> dict` — returns canonicalised dict; raises
      `CustomFieldValidationError` on schema violations.
  * **Phase 4 scope:** define the protocol and ship empty/`pass-through` template implementations
    for each industry. The actual validation rules are Phase 6 implementation detail per the
    Phase 4 charter; we register the seams so Phase 6 only adds rule code, never plumbing.
* Create `src/office_hero/services/custom_field_templates/plumbing.py`:
  * `class PlumbingTemplate`: `industry = Industry.PLUMBING`; `validate()` currently allows any
    dict with string keys; future rule examples documented as comments (`{"fixture_type":
    "toilet|sink|tub|water_heater", "warranty_months": int}`).
* Create `src/office_hero/services/custom_field_templates/hvac.py` — same pattern; sample fields
  in comments (`{"unit_model": str, "refrigerant_lbs": float, "filter_size": str}`).
* Create `src/office_hero/services/custom_field_templates/pest_control.py` — same pattern;
  comments (`{"pest_type": "termite|rodent|ant|...", "chemical_used": str,
  "epa_registration_number": str}`).
* Create `src/office_hero/services/custom_field_templates/generic.py` — accepts any keys.
* Create `src/office_hero/services/custom_field_templates/registry.py` — `dict[Industry,
  CustomFieldTemplate]`; `def get_template(industry: Industry) -> CustomFieldTemplate`.
* Create `src/office_hero/models/job.py` — SQLAlchemy ORM model `Job`:
  * `id: Mapped[UUID]` (PK)
  * `tenant_id: Mapped[UUID]` (FK `tenants.id`, NOT NULL — RLS pivot)
  * `customer_id: Mapped[UUID]` (FK `customers.id`, NOT NULL)
  * `location_id: Mapped[UUID]` (FK `locations.id`, NOT NULL)
  * `industry: Mapped[str]` (50, NOT NULL — copies `tenant.industry` at create time so historical
    Jobs aren't broken by tenant industry changes)
  * `title: Mapped[str]` (255, NOT NULL — short description, used in dispatch UI lists)
  * `description: Mapped[str | None]` (Text)
  * `status: Mapped[str]` (20, NOT NULL, default `"pending"`)
  * `priority: Mapped[int]` (NOT NULL, default 50 — 0=highest, 100=lowest; used by routing
    ranking in slice 13)
  * `service_type: Mapped[str | None]` (120 — e.g. "leak_repair", "inspection";
    free-text v1, controlled list v2)
  * `requested_at: Mapped[datetime | None]` (TIMESTAMPTZ — customer's preferred window start)
  * `requested_until: Mapped[datetime | None]` (TIMESTAMPTZ — customer's preferred window end)
  * `estimated_duration_min: Mapped[int]` (NOT NULL, default 60 — used by routing)
  * `scheduled_for: Mapped[datetime | None]` (set when status moves to scheduled)
  * `started_at: Mapped[datetime | None]` (set when status moves to in_progress)
  * `completed_at: Mapped[datetime | None]`
  * `cancelled_at: Mapped[datetime | None]`
  * `cancel_reason: Mapped[str | None]` (Text — required when cancelling, see service)
  * `custom_fields: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")`
  * `external_id: Mapped[str | None]` (255 — back-office link per ADR 056)
  * `created_by_user_id: Mapped[UUID]` (FK `users.id`)
  * `created_at`, `updated_at` (TIMESTAMPTZ)
  * `customer: Mapped["Customer"] = relationship()`
  * `location: Mapped["Location"] = relationship()`
  * `__table_args__`:
    * Index `(tenant_id, status)` — dispatch dashboard filters by status.
    * Index `(tenant_id, scheduled_for)` — daily view + routing.
    * Index `(tenant_id, customer_id)` — customer detail view.
    * GIN index on `custom_fields` (`USING gin (custom_fields jsonb_path_ops)`) — future
      Tenant-side queries on industry fields.
* Update `src/office_hero/models/__init__.py` to import `Job`.
* Update `Tenant` model (in `models/tenant.py`) — add `industry: Mapped[str]` (50, NOT NULL,
  default `"generic"`) via migration. Note: stakeholders may prefer industry as a separate
  enum table for multi-industry tenants; **OPEN QUESTION** flagged in PR (treated as a single
  default industry per tenant for v1).
* Create `src/office_hero/repositories/job_repository.py`:
  * `JobRepository` + `JobRepositoryProtocol`.
  * Methods (all `async`):
    * `create(tenant_id, *, customer_id, location_id, industry, title, description,
      priority, service_type, requested_at, requested_until, estimated_duration_min,
      custom_fields, created_by_user_id) -> Job`
    * `get_by_id(job_id, tenant_id) -> Job | None`
    * `list(tenant_id, *, status: list[str] | None, customer_id: UUID | None,
      scheduled_for_date: date | None, search: str | None, limit: int = 50,
      offset: int = 0) -> tuple[list[Job], int]`
    * `update_fields(job_id, tenant_id, **patch) -> Job` — partial field update; does NOT
      change status (status changes go through `update_status`).
    * `update_status(job_id, tenant_id, new_status, *, scheduled_for=None, started_at=None,
      completed_at=None, cancelled_at=None, cancel_reason=None) -> Job` — sets the lifecycle
      timestamp matching `new_status` atomically.
    * `list_due_for_routing(tenant_id, date) -> list[Job]` — status in
      `("pending", "scheduled")` and `scheduled_for::date = date` OR `requested_at::date = date`.
      (consumed by Slice 13 routing.)
* Create `src/office_hero/services/job_service.py`:
  * `class JobService`:
    * `__init__(repo: JobRepositoryProtocol, customer_repo, location_repo, audit: AuditService,
      template_registry)`.
    * `async def create(tenant_id, user_id, payload: JobCreate) -> Job`:
      * Verify `customer_id` belongs to tenant via `customer_repo.get_by_id`.
      * Verify `location_id` belongs to same customer (defence-in-depth).
      * Look up tenant's industry; copy onto Job row.
      * Validate `custom_fields` against `template_registry[industry].validate(...)`.
      * Persist with `status="pending"`, `created_by_user_id=user_id`.
      * Emit audit `job.created` with `{job_id, customer_id, location_id, industry, priority,
        title}`.
    * `async def update(tenant_id, user_id, job_id, patch: JobUpdate) -> Job`:
      * Disallow patching `status` here — status uses dedicated endpoints.
      * Disallow patching `tenant_id`, `customer_id`, `industry`, `created_by_user_id` (immutable).
      * If `custom_fields` present, re-validate via the template for the Job's industry.
      * If `location_id` changes, verify new location belongs to same customer.
      * Compute diff for audit `job.updated`.
    * `async def schedule(tenant_id, user_id, job_id, scheduled_for: datetime) -> Job`:
      * Verifies current status is `pending` (the only legal source for `scheduled`).
      * Calls `repo.update_status(..., new_status="scheduled", scheduled_for=scheduled_for)`.
      * Emits `job.scheduled` audit with `{from: "pending", to: "scheduled", scheduled_for}`.
      * Note: dispatch (Slice 14) is the more usual way to enter `scheduled` because dispatch
        creates the Route and pegs the Job to it. This bare `schedule()` method exists for
        manual non-dispatched scheduling (e.g. "we have an appointment, no specific vehicle yet").
    * `async def start(tenant_id, user_id, job_id) -> Job` — transition `scheduled → in_progress`.
      Sets `started_at = now()`. Emits `job.started`. (Technician-callable; commonly via mobile.)
    * `async def complete(tenant_id, user_id, job_id, *, completion_notes: str | None) -> Job`
      — transition `in_progress → complete`. Sets `completed_at = now()`. Audit `job.completed`
      with completion_notes truncated to 1024 chars.
    * `async def cancel(tenant_id, user_id, job_id, *, reason: str) -> Job`:
      * Transition any non-terminal status → `cancelled`. `reason` is required (min length 3).
      * Sets `cancelled_at = now()`, `cancel_reason = reason`.
      * Audit `job.cancelled` with `{from_status, reason}`.
    * `async def get(tenant_id, job_id) -> Job` — raises `JobNotFoundError`.
    * `async def list(tenant_id, *, filters, pagination) -> tuple[list[Job], int]`.
  * Each transition method internally calls a private `_transition(job, target)` that uses
    `can_transition()` from `core/job_status.py` and raises `InvalidJobTransitionError`
    (mapped to **422** by the global exception handler) when illegal.
* Create `src/office_hero/api/schemas/job.py`:
  * `JobCreate`:
    * `customer_id: UUID`, `location_id: UUID`
    * `title: str` (1..255)
    * `description: str | None` (0..10_000)
    * `priority: int = 50` (0..100)
    * `service_type: str | None` (0..120)
    * `requested_at: datetime | None`, `requested_until: datetime | None`
    * `estimated_duration_min: int = 60` (5..1440)
    * `custom_fields: dict = {}` — `dict[str, Any]`; deep validation happens in service.
    * `model_config = ConfigDict(extra="forbid")`.
  * `JobUpdate` — all of the above optional except `customer_id`, `industry` not patchable.
    Model validator: at least one field set.
  * `JobScheduleRequest` — `{scheduled_for: datetime}`.
  * `JobCompleteRequest` — `{completion_notes: str | None}` (≤1024 chars).
  * `JobCancelRequest` — `{reason: str}` (3..512).
  * `JobRead` — full DTO; embeds `customer: CustomerSummary` and `location: LocationRead`
    on detail.
  * `JobList` — `{items: list[JobSummary], total, limit, offset}`.
  * `JobSummary` — `id`, `title`, `status`, `priority`, `scheduled_for`, `customer_name`,
    `location_city`.
* Create `src/office_hero/api/routes/jobs.py` — `prefix="/jobs"`, `tags=["jobs"]`:
  * `POST /jobs` — `@require_permission("jobs:write")`. Body `JobCreate`.
    Rate-limited at `write` tier (60 req/min).
  * `GET /jobs` — `@require_permission("jobs:read")`. Query: `status` (multi-select), `customer_id`,
    `scheduled_for_date` (ISO date), `search`, `limit (max 200)`, `offset`.
  * `GET /jobs/{id}` — `@require_permission("jobs:read")`.
  * `PATCH /jobs/{id}` — `@require_permission("jobs:write")`.
  * `POST /jobs/{id}/schedule` — `@require_permission("jobs:dispatch")` (Dispatcher, TenantAdmin,
    Operator). Body `JobScheduleRequest`.
  * `POST /jobs/{id}/start` — `@require_role([Technician, TechnicianHelper, Dispatcher,
    TenantAdmin, Operator, OperatorStaff])`. (Most often called from mobile.)
  * `POST /jobs/{id}/complete` — same role set as `/start`. Body `JobCompleteRequest`.
  * `POST /jobs/{id}/cancel` — `@require_permission("jobs:cancel")` (Dispatcher, TenantAdmin,
    Operator).
* Update `src/office_hero/api/state.py` — `get_job_service() -> JobService`.
* Register the jobs router in `src/office_hero/api/app.py`.
* Update `src/office_hero/api/exception_handlers.py` (from slice 4):
  * Map `InvalidJobTransitionError` → 422 `{detail: "Invalid job status transition", from, to}`.
  * Map `CustomFieldValidationError` → 422 `{detail, field, errors: [...]}` .
  * Map `JobNotFoundError` → 404.
* Create migration `alembic/versions/0005_jobs.py`:
  * `ALTER TABLE tenants ADD COLUMN industry varchar(50) NOT NULL DEFAULT 'generic';`
    (back-fill is the default).
  * Create `jobs` table; columns per model.
  * Indexes: `(tenant_id, status)`, `(tenant_id, scheduled_for)`, `(tenant_id, customer_id)`.
  * GIN index: `idx_jobs_custom_fields_gin ON jobs USING gin (custom_fields jsonb_path_ops);`
  * `ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;`
  * `CREATE POLICY job_tenant_isolation ON jobs
       USING (tenant_id = current_setting('app.tenant_id')::uuid);`
  * CHECK constraints:
    * `CHECK (status IN ('pending','scheduled','in_progress','complete','cancelled'))`
    * `CHECK (priority BETWEEN 0 AND 100)`
    * `CHECK (estimated_duration_min BETWEEN 5 AND 1440)`
  * Downgrade drops policy, indexes, jobs table, then `industry` column.
* Create unit tests in `tests/unit/test_job_service.py`:
  * `test_create_job_with_valid_custom_fields_emits_audit`
  * `test_create_job_unknown_customer_raises_not_found`
  * `test_create_job_location_belongs_to_other_customer_raises`
  * `test_create_job_other_tenant_customer_raises_not_found` (cross-tenant defence-in-depth)
  * `test_create_job_invalid_custom_fields_raises_422_via_template`
  * `test_schedule_job_from_pending_succeeds`
  * `test_schedule_job_from_in_progress_raises_invalid_transition`
  * `test_start_job_from_scheduled_succeeds_and_sets_started_at`
  * `test_complete_job_from_in_progress_sets_completed_at_and_audits`
  * `test_cancel_job_from_any_non_terminal_status_succeeds`
  * `test_cancel_job_requires_reason_min_3_chars`
  * `test_cancel_job_from_complete_raises_invalid_transition` (terminal)
  * `test_cancel_job_from_cancelled_raises_invalid_transition` (terminal)
  * `test_update_job_status_field_via_patch_is_rejected`
  * `test_update_job_industry_field_via_patch_is_rejected`
  * `test_update_job_custom_fields_revalidates_against_template`
* Unit tests `tests/unit/test_job_status.py`:
  * `test_can_transition_matrix` — parameterised over the full 5×5 grid; asserts only the
    documented transitions are allowed.
  * `test_is_terminal` — complete and cancelled true; others false.
* Unit tests `tests/unit/test_custom_field_templates.py`:
  * `test_registry_returns_template_per_industry`
  * `test_generic_template_accepts_any_dict`
  * `test_plumbing_template_passes_through_for_now` (Phase 6 will add real rules)
  * Same for hvac, pest_control.
* API tests `tests/api/test_jobs_api.py`:
  * `test_post_job_requires_jwt_401`
  * `test_post_job_without_jobs_write_perm_403`
  * `test_post_job_201_and_returns_id`
  * `test_post_job_invalid_customer_404`
  * `test_get_job_cross_tenant_404`
  * `test_list_jobs_filter_by_status_and_date`
  * `test_list_jobs_pagination`
  * `test_patch_job_returns_422_when_status_field_supplied`
  * `test_schedule_job_dispatcher_succeeds`
  * `test_schedule_job_technician_403` (Technician lacks `jobs:dispatch`)
  * `test_start_job_technician_succeeds`
  * `test_complete_job_technician_succeeds_with_notes`
  * `test_cancel_job_dispatcher_with_reason_succeeds`
  * `test_cancel_job_without_reason_422`
  * `test_illegal_status_transition_returns_422`
  * `test_jobs_write_endpoint_rate_limited_60_per_min`
* Integration test `tests/integration/test_jobs_rls.py`:
  * `test_tenant_isolation_jobs_hidden_by_rls` — tenant A jobs are not visible when
    `app.tenant_id = tenantB`.
  * `test_custom_fields_jsonb_roundtrip` — write nested JSON, read back, verify shape preserved.
  * `test_jobs_gin_index_used_for_jsonb_contains_query` — `EXPLAIN ANALYZE` shows
    Bitmap Index Scan on `idx_jobs_custom_fields_gin` (smoke; not a hard assertion in CI but
    a debug aid documented in the test).

## Structure

```text
src/office_hero/
├── core/
│   ├── exceptions.py            # +JobNotFoundError, +InvalidJobTransitionError,
│   │                            #  +CustomFieldValidationError
│   ├── industry.py              # Industry enum
│   └── job_status.py            # JobStatus enum + transition matrix + helpers
├── models/
│   └── job.py                   # Job ORM model
├── repositories/
│   └── job_repository.py
├── services/
│   ├── job_service.py
│   └── custom_field_templates/
│       ├── __init__.py          # CustomFieldTemplate Protocol
│       ├── registry.py
│       ├── generic.py
│       ├── plumbing.py
│       ├── hvac.py
│       └── pest_control.py
└── api/
    ├── schemas/
    │   └── job.py
    └── routes/
        └── jobs.py

alembic/
└── versions/
    └── 0005_jobs.py             # +industry on tenants; jobs table + RLS + indexes

tests/
├── unit/
│   ├── test_job_service.py
│   ├── test_job_status.py
│   └── test_custom_field_templates.py
├── api/
│   └── test_jobs_api.py
└── integration/
    └── test_jobs_rls.py
```

## Failing Test Outline

```python
# tests/unit/test_job_service.py
import pytest
from office_hero.core.job_status import JobStatus
from office_hero.core.exceptions import InvalidJobTransitionError


@pytest.mark.asyncio
async def test_cancel_job_from_complete_raises_invalid_transition(job_service, job_in_complete):
    """A completed Job cannot be cancelled — terminal state."""
    with pytest.raises(InvalidJobTransitionError) as exc:
        await job_service.cancel(
            tenant_id=TENANT_A,
            user_id=USER_A,
            job_id=job_in_complete.id,
            reason="changed my mind",
        )
    assert exc.value.from_status == JobStatus.COMPLETE
    assert exc.value.to_status == JobStatus.CANCELLED


# tests/api/test_jobs_api.py
def test_illegal_status_transition_returns_422(client, dispatcher_token, completed_job_id):
    """Cancelling a completed job returns 422 with structured error."""
    resp = client.post(
        f"/jobs/{completed_job_id}/cancel",
        json={"reason": "no longer needed"},
        headers={"Authorization": f"Bearer {dispatcher_token}"},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["from"] == "complete"
    assert body["to"] == "cancelled"
```

## Dependencies

* **Slice 2 (Database foundation)** — async engine, RLS helpers, Alembic.
* **Slice 3 (Auth & RBAC)** — JWT, `@require_role`, `@require_permission`, Role enum.
* **Slice 4 (Observability)** — `AuditService`, exception handler integration, slowapi.
* **Slice 7 (Tenant management)** — `tenants` table + the new `industry` column will be added
  here as the *first* Job slice but a tenant-edit endpoint to change industry is owned by
  Slice 7's later iteration (out of scope for this slice).
* **Slice 11 (Customer & Location)** — provides `customers`, `locations`, `customer_repo`,
  `location_repo`. Job FKs both.
* Relevant ADRs: **053** (RLS), **056** (back-office Saga is *not* implemented here, but the
  `external_id` column is reserved for it; `outbox_events` plumbing comes later), **058**, **059**,
  **060**, **062**, **063**.

## Effort

Estimate: **3/5**. Despite "core CRUD" framing, the slice carries non-trivial design: status
machine, custom_fields template plumbing, rich relationships to Customer + Location, six
distinct status endpoints, and ~16 unit + 14 API tests. The migration is moderate (one new
table + GIN index + check constraints + a column add on `tenants`). The template registry is
deliberately scaffolded with empty rules so Phase 6 can land industry logic without rewiring.

## Risk Callouts

* **Status machine drift.** Future slices (15 location tracking, 16 dynamic re-routing,
  17 mobile) will want to mutate status. Centralising `can_transition()` in
  `core/job_status.py` and forcing every transition through `JobService._transition()`
  is non-negotiable; reviewers should reject any direct `job.status = ...` outside the service.
* **JSONB validation surface.** The Phase 4 design leaves rules empty per project charter,
  but the template seam must be honoured: callers must never bypass `template.validate()`.
  Add a lint rule or PR-time review check for direct writes to `Job.custom_fields`.
* **Tenant industry mutation.** If a Tenant changes industry, existing Jobs keep their original
  industry (copied at create time). New Jobs use the new industry. We do *not* re-validate
  historical custom_fields. **OPEN QUESTION:** stakeholders may want an explicit
  "industry migration tool" — out of scope here but worth flagging.
* **Soft-delete vs cancel semantics.** Cancelling a Job is a status transition, not a soft
  delete. There is *no* `archived` flag on Jobs in this slice. If listings need to hide
  cancelled jobs by default, that's a query filter. Confirmed against the master plan: cancelled
  is a terminal status; no separate archive flag needed.
* **Performance: GIN index on JSONB.** `jsonb_path_ops` keeps index size sane but only supports
  `@>` containment queries; an operator who wants `?` key-existence queries needs a second
  index. Documented as future work.
* **Audit payload size.** Job description + completion_notes can be large. We truncate
  completion_notes to 1024 chars in audit payloads; description is referenced by job_id only
  (audit reader can dereference if needed).

---

Once approved, implementation proceeds with `core/job_status.py` (pure, no deps) and its
matrix test, then the model + migration, then `JobService` under TDD with the template
registry stubbed, then the routers. The mobile slices (17 onward) will exercise `start` and
`complete` end-to-end on hardware.
