---
docType: slice-design
parent: ../project-guides/003-slices.office-hero.md
project: office-hero
dateCreated: 20260524
status: not_started
slice: dispatch-route
dateUpdated: 20260524
---

# Slice Design 015: Dispatch & Route management

This slice commits the result of a routing-options call (Slice 014) into a persistent **Route**
with ordered **RouteStops**. It introduces a strict Route status lifecycle, atomic
dispatch-commit (single transaction across Route + RouteStops + per-Job status transitions),
a manual fourth-option escape hatch, and a daily-view read endpoint.

It implements **Slice 14** of the master slice plan.

## Domain Model

```text
┌──────────────────────────────┐
│ Route                        │
│  vehicle_id, work_date       │ 1
│  status (draft/committed/    │ ──┐
│   in_progress/complete/      │   │  N
│   cancelled)                 │   └────────┐
│  total_distance_m            │            ▼
│  total_duration_s            │   ┌──────────────────┐
└──────────────────────────────┘   │ RouteStop        │
                                   │  job_id          │
                                   │  sequence_index  │
                                   │  eta             │
                                   │  status (pending │
                                   │   /arrived/      │
                                   │   complete/      │
                                   │   skipped)       │
                                   └──────────────────┘
```

* A **Route** is uniquely keyed by `(tenant_id, vehicle_id, work_date)` — at most one Route per
  vehicle per day. A second dispatch to the same vehicle on the same day **updates** the
  existing Route (appending the Job as a new RouteStop) rather than creating a new Route. This
  is the spec's "Commit dispatch creates/updates Route + RouteStops" requirement.
* A **RouteStop** references one Job and pegs its `sequence_index` (0..N) and projected `eta`.
  RouteStops are ordered; the `(route_id, sequence_index)` pair is unique.

## Route Status Lifecycle

```text
draft ──► committed ──► in_progress ──► complete
   │           │                │
   └── cancel ─┴────cancel──────┘
                      │
                      ▼
                  cancelled
```

* `draft` exists only momentarily — the dispatch endpoint commits within the same DB
  transaction. We keep `draft` as a status so a future "preview dispatch" feature has a place
  to land without a migration. **OPEN QUESTION:** stakeholders may prefer omitting `draft`
  entirely; flagged in PR. The default behaviour: dispatch jumps straight to `committed`.
* `committed → in_progress` triggered when the first Job on the Route is started (event from
  Slice 012 `JobService.start`).
* `in_progress → complete` triggered when all RouteStops are `complete` or `skipped` (terminal
  per-stop statuses), via a route-status-recompute callback.
* Cancellation is dispatcher-initiated; cascades to set each non-terminal RouteStop status to
  `skipped` and emits `route.cancelled` audit; **does not** automatically cancel the underlying
  Jobs (those return to `pending` for re-dispatch).

## Goals

* Extend `src/office_hero/core/exceptions.py`:
  * `class RouteNotFoundError(Exception)`.
  * `class InvalidRouteTransitionError(Exception)` — carries `from_status`, `to_status`.
  * `class RouteCommitConflictError(Exception)` — raised when the committed sequence conflicts
    with the latest state (e.g. a referenced Job no longer exists, or the chosen vehicle no
    longer has a crew on the date). Carries machine-readable `reason`.
  * `class ManualSequenceInvalidError(Exception)` — manual fourth-option payload had duplicate
    or non-tenant job ids, etc.
* Create `src/office_hero/core/route_status.py`:
  * `RouteStatus` enum: `DRAFT, COMMITTED, IN_PROGRESS, COMPLETE, CANCELLED`.
  * `RouteStopStatus` enum: `PENDING, ARRIVED, COMPLETE, SKIPPED`.
  * Transition matrix for `RouteStatus` mirroring the lifecycle above.
  * Per-stop transitions: `pending → arrived → complete`, plus `pending|arrived → skipped`.
  * `can_route_transition(from, to)`, `can_stop_transition(from, to)`, `is_terminal_route(...)`,
    `is_terminal_stop(...)`.
* Create `src/office_hero/models/route.py`:
  * `class Route(Base)`:
    * `id: Mapped[UUID]` (PK)
    * `tenant_id: Mapped[UUID]` (FK, NOT NULL — RLS)
    * `vehicle_id: Mapped[UUID]` (FK `vehicles.id`, NOT NULL)
    * `vehicle_crew_id: Mapped[UUID]` (FK `vehicle_crews.id`, NOT NULL — pegs the crew
      assignment used at commit time; if the crew is later edited, this link survives)
    * `work_date: Mapped[date]` (NOT NULL)
    * `status: Mapped[str]` (20, NOT NULL, default `"draft"`)
    * `committed_at: Mapped[datetime | None]`
    * `started_at: Mapped[datetime | None]`
    * `completed_at: Mapped[datetime | None]`
    * `cancelled_at: Mapped[datetime | None]`
    * `cancel_reason: Mapped[str | None]` (Text)
    * `total_distance_m: Mapped[int]` (NOT NULL, default 0)
    * `total_duration_s: Mapped[int]` (NOT NULL, default 0)
    * `option_kind_applied: Mapped[str | None]` (20 — `"nearest"|"earliest"|"balanced"|"manual"`;
      provenance for audits)
    * `committed_by_user_id: Mapped[UUID | None]` (FK `users.id`)
    * `notes: Mapped[str | None]` (Text)
    * `created_at`, `updated_at`
    * `vehicle: Mapped["Vehicle"] = relationship()`
    * `crew: Mapped["VehicleCrew"] = relationship()`
    * `stops: Mapped[list["RouteStop"]] = relationship(back_populates="route",
      cascade="all, delete-orphan", order_by="RouteStop.sequence_index")`
    * `__table_args__`: unique `(tenant_id, vehicle_id, work_date)`;
      index `(tenant_id, work_date)`; index `(tenant_id, status)`.
  * `class RouteStop(Base)`:
    * `id: Mapped[UUID]` (PK)
    * `tenant_id: Mapped[UUID]` (FK — denormalised for RLS)
    * `route_id: Mapped[UUID]` (FK `routes.id` ON DELETE CASCADE)
    * `job_id: Mapped[UUID]` (FK `jobs.id`, NOT NULL)
    * `sequence_index: Mapped[int]` (NOT NULL — 0-based; recomputed atomically on insert)
    * `status: Mapped[str]` (20, NOT NULL, default `"pending"`)
    * `planned_eta: Mapped[datetime | None]` (eta at commit time)
    * `actual_arrived_at: Mapped[datetime | None]`
    * `actual_completed_at: Mapped[datetime | None]`
    * `planned_distance_from_prev_m: Mapped[int]` (NOT NULL, default 0)
    * `planned_duration_from_prev_s: Mapped[int]` (NOT NULL, default 0)
    * `created_at`, `updated_at`
    * `route: Mapped["Route"] = relationship(back_populates="stops")`
    * `job: Mapped["Job"] = relationship()`
    * `__table_args__`: unique `(route_id, sequence_index)`; unique `(route_id, job_id)`
      (a Job can appear at most once on a Route — re-dispatching to the same vehicle should
      update the existing stop, not duplicate).
* Update `src/office_hero/models/__init__.py` to import `Route`, `RouteStop`.
* Create `src/office_hero/repositories/route_repository.py`:
  * `RouteRepository` + protocol. Methods:
    * `get_by_id(route_id, tenant_id) -> Route | None` (joinedload stops + job + customer).
    * `get_for_vehicle_date(tenant_id, vehicle_id, work_date) -> Route | None`.
    * `list_for_date(tenant_id, work_date, *, vehicle_id: UUID | None = None,
      status: list[str] | None = None) -> list[Route]` — daily view; ordered by
      `(vehicle.nickname, vehicle.license_plate)` for deterministic UI.
    * `list_for_user_date(tenant_id, user_id, work_date) -> list[Route]` — routes whose crew
      includes the user (technician mobile view).
    * `create(tenant_id, *, vehicle_id, vehicle_crew_id, work_date,
      option_kind_applied, committed_by_user_id, notes, total_distance_m, total_duration_s)
      -> Route`
    * `update_status(route_id, tenant_id, new_status, *, committed_at=None, started_at=None,
      completed_at=None, cancelled_at=None, cancel_reason=None) -> Route`.
    * `update_totals(route_id, tenant_id, *, total_distance_m, total_duration_s) -> Route`.
    * `delete(route_id, tenant_id)` — admin-only; cascade deletes stops.
* Create `src/office_hero/repositories/route_stop_repository.py`:
  * `RouteStopRepository` + protocol. Methods:
    * `bulk_insert(tenant_id, route_id, stops: list[StopRow]) -> list[RouteStop]` — within an
      ambient transaction; respects `(route_id, sequence_index)` invariant.
    * `delete_for_route(tenant_id, route_id) -> int` (returns count).
    * `replace_all(tenant_id, route_id, stops: list[StopRow]) -> list[RouteStop]` — atomic
      delete-then-insert (within a single transaction); for re-dispatch of the same vehicle
      with a re-sequenced set of stops.
    * `update_status(stop_id, tenant_id, new_status, *, arrived_at=None, completed_at=None)
      -> RouteStop` — guarded by `can_stop_transition`.
    * `get_for_route(tenant_id, route_id) -> list[RouteStop]`.
* Create `src/office_hero/services/dispatch_service.py` — `DispatchService`:
  * `__init__(route_repo, stop_repo, job_repo, vehicle_repo, vehicle_crew_repo,
    routing_service: RoutingService, audit: AuditService)`.
  * `async def commit_dispatch(tenant_id, user_id, *, job_id: UUID,
    payload: DispatchCommitRequest) -> Route`:
    * **Branch A (option mode):** `payload.option_kind` is set (one of
      `"nearest"|"earliest"|"balanced"`):
      1. Re-fetch the latest routing options via `routing_service.compute_options(...)` to
         ensure we commit a fresh sequence (the cached options on the client may be stale —
         tenant data could have changed between options call and commit).
      2. Select the option matching `option_kind`.
    * **Branch B (manual mode):** `payload.manual_vehicle_id` and
      `payload.manual_sequence: list[UUID]` are set:
      1. Validate the vehicle has a crew on `payload.date` (else `RouteCommitConflictError`).
      2. Validate every UUID in `manual_sequence` is a known, non-cancelled, non-complete
         Job in the tenant (else `ManualSequenceInvalidError`); the new job_id from the URL
         **must be present exactly once** in `manual_sequence` (else
         `ManualSequenceInvalidError`).
      3. Validate `manual_sequence` contains no duplicates.
      4. Compute totals by calling `routing_service.adapter.optimize_sequence` with the manual
         sequence to derive `total_distance_m`, `total_duration_s`, per-segment ETAs. Honour
         the manual order — do not re-optimize.
    * Common path (transactional):
      * Open a single DB transaction (`async with session.begin():`).
      * Look up or create the Route for `(tenant_id, vehicle_id, work_date)`:
        * If exists with status `committed`: replace its stops atomically (`stop_repo.replace_all`)
          and update totals; status remains `committed`.
        * If exists with status `in_progress|complete|cancelled`: refuse with
          `RouteCommitConflictError`. (You cannot re-dispatch into a route that has already
          started or ended on the day.)
        * If exists with status `draft`: same path as `committed` for now (draft is a future
          handle).
        * If none exists: create one in status `committed` directly (skip `draft` per the
          OPEN QUESTION note above).
      * Update the underlying Job's status to `scheduled` if currently `pending`. If the Job is
        already `scheduled` or `in_progress`, leave its status alone — but ensure the Route
        references it. If the Job is `complete|cancelled`, refuse with
        `RouteCommitConflictError`.
      * Set `committed_at`, `committed_by_user_id`, `option_kind_applied`.
      * Emit audit `route.committed` with `{route_id, vehicle_id, work_date, option_kind,
        job_ids: [...], total_distance_m, total_duration_s, manual: bool}`.
      * Return the route with embedded stops.
    * Idempotency: a client retrying the same dispatch must not duplicate stops. The
      `(route_id, job_id)` unique index plus the `replace_all` semantics guarantee this; we
      also add a soft idempotency check at the service: if the requested manual_sequence (or
      computed sequence from option_kind) **equals** the existing route's job_ids in order,
      return the existing route as-is without writes.
  * `async def cancel_route(tenant_id, user_id, route_id, *, reason: str) -> Route`:
    * Guards transition via `can_route_transition`.
    * Sets all non-terminal stops to `skipped`.
    * Returns the route. Emits audit `route.cancelled` with `{route_id, reason,
      affected_stop_count}`.
    * **Does not** cancel the underlying Jobs (they return to `pending` from `scheduled`).
      The service issues `job_service.transition_route_cancelled(job_id)` for each affected
      stop — a new method we add to `JobService` for this slice:
      `async def transition_route_cancelled(tenant_id, user_id, job_id) -> Job` — only legal
      from `scheduled`; moves Job back to `pending`; emits `job.route_cancelled` audit. If the
      Job is `in_progress` we leave it as-is.
  * `async def mark_stop_arrived(tenant_id, user_id, stop_id) -> RouteStop`.
  * `async def mark_stop_complete(tenant_id, user_id, stop_id) -> RouteStop`:
    * Stop transition `pending|arrived → complete`. Emits `route.stop_completed`.
    * After commit, if all stops on the route are terminal, transitions the Route to `complete`
      (audit `route.completed`).
  * `async def mark_stop_skipped(tenant_id, user_id, stop_id, reason: str) -> RouteStop`:
    * Same terminal-check.
  * `async def start_route(tenant_id, user_id, route_id) -> Route`:
    * Transition `committed → in_progress`. Sets `started_at = now()`.
    * Emits `route.started`.
    * Side effect: `job_service.start(first_unstarted_job)` is **not** called here; technician
      starts individual jobs explicitly. `route.started` is a route-level handle (used by
      Slice 16 dynamic re-routing).
* Create `src/office_hero/api/schemas/dispatch.py`:
  * `DispatchCommitRequest`:
    * `date: date` (REQUIRED).
    * `option_kind: Literal["nearest","earliest","balanced"] | None`.
    * `manual_vehicle_id: UUID | None`.
    * `manual_sequence: list[UUID] | None`.
    * `notes: str | None` (≤2048).
    * Model validator: **exactly one** of `option_kind` OR `(manual_vehicle_id +
      manual_sequence)` must be provided. If both or neither, return 422 with a structured
      message.
    * `model_config = ConfigDict(extra="forbid")`.
* Create `src/office_hero/api/schemas/route.py`:
  * `RouteStopRead`: `{id, job_id, sequence_index, status, planned_eta, actual_arrived_at,
    actual_completed_at, planned_distance_from_prev_m, planned_duration_from_prev_s,
    job: JobSummary}`.
  * `RouteRead`: `{id, vehicle_id, vehicle_crew_id, work_date, status, committed_at,
    started_at, completed_at, cancelled_at, cancel_reason, total_distance_m,
    total_duration_s, option_kind_applied, committed_by_user_id, notes,
    stops: list[RouteStopRead], vehicle: VehicleSummary, crew: VehicleCrewSummary}`.
  * `RouteListResponse`: `{items: list[RouteRead], total: int}`.
  * `RouteCancelRequest`: `{reason: str}` (3..512).
  * `StopSkipRequest`: `{reason: str}` (3..512).
* Create `src/office_hero/api/routes/dispatch.py`:
  * `POST /jobs/{job_id}/dispatch` — `@require_permission("jobs:dispatch")`. Body
    `DispatchCommitRequest`. Returns 201 with `RouteRead` (whether new or updated). Rate-limit
    `write` tier 60 req/min.
* Create `src/office_hero/api/routes/routes.py` — `prefix="/routes"`, `tags=["routes"]`:
  * `GET /routes` — `@require_permission("routes:read")`. Query params:
    * `date: ISO date` (required).
    * `vehicle_id: UUID | None`.
    * `status: list[str] | None` (multi-select).
    * `user_id: UUID | None` (Dispatcher/Admin only — Technician role auto-filters to self).
    * Default sort: `(vehicle.nickname, vehicle.license_plate, sequence_index)`.
  * `GET /routes/{id}` — `@require_permission("routes:read")`. Technicians may only read
    routes whose crew they are a member of (service enforces; mismatch returns 404, not 403,
    to avoid leaking existence).
  * `POST /routes/{id}/start` — `@require_role([Dispatcher, TenantAdmin, Operator, Technician,
    TechnicianHelper])`. Service further restricts: Technicians can only start a route they're
    on.
  * `POST /routes/{id}/cancel` — `@require_role([Dispatcher, TenantAdmin, Operator])`. Body
    `RouteCancelRequest`.
  * `POST /routes/{id}/stops/{stop_id}/arrived` —
    `@require_role([Technician, TechnicianHelper, Dispatcher, TenantAdmin, Operator])`.
  * `POST /routes/{id}/stops/{stop_id}/complete` — same role gate; service auto-finalises the
    Route on all-stops-terminal.
  * `POST /routes/{id}/stops/{stop_id}/skip` — same; body `StopSkipRequest`.
* Update `src/office_hero/api/state.py`:
  * `get_route_repository()`, `get_route_stop_repository()`, `get_dispatch_service()`.
* Register routers in `src/office_hero/api/app.py`.
* Update `src/office_hero/api/exception_handlers.py`:
  * `RouteNotFoundError` → 404.
  * `InvalidRouteTransitionError` → 422 with `{from, to}`.
  * `RouteCommitConflictError` → 409 with `{detail, reason}`.
  * `ManualSequenceInvalidError` → 422 with `{detail, errors: [...]}`.
* Update `JobService` (from slice 012):
  * Add `async def transition_route_cancelled(tenant_id, user_id, job_id) -> Job` — moves
    scheduled jobs back to pending when their route is cancelled.
  * Already-defined `JobService.schedule` is the path used inside the dispatch transaction.
    Service is responsible for ensuring the call is idempotent (no-op if Job is already
    scheduled).
* Create migration `alembic/versions/0007_routes.py`:
  * Create `routes` table; columns per model; FKs to `tenants`, `vehicles`, `vehicle_crews`,
    `users`.
  * Unique `uq_route_tenant_vehicle_date` ON `(tenant_id, vehicle_id, work_date)`.
  * Indexes: `(tenant_id, work_date)`, `(tenant_id, status)`.
  * CHECK `status IN ('draft','committed','in_progress','complete','cancelled')`.
  * RLS enable + `route_tenant_isolation` policy.
  * Create `route_stops` table; FKs `tenants`, `routes (ON DELETE CASCADE)`, `jobs`.
  * Unique `(route_id, sequence_index)`; unique `(route_id, job_id)`.
  * Index `(tenant_id, route_id)`.
  * CHECK `status IN ('pending','arrived','complete','skipped')`.
  * RLS enable + policy.
  * Downgrade drops policies, tables in reverse.
* Unit tests `tests/unit/test_dispatch_service.py`:
  * `test_commit_dispatch_option_kind_creates_route_and_stops`
  * `test_commit_dispatch_manual_mode_creates_route_with_exact_sequence`
  * `test_commit_dispatch_requires_option_or_manual` (both/neither → 422)
  * `test_commit_dispatch_manual_sequence_must_include_target_job`
  * `test_commit_dispatch_manual_sequence_rejects_duplicates`
  * `test_commit_dispatch_manual_vehicle_without_crew_on_date_409`
  * `test_commit_dispatch_target_job_complete_409`
  * `test_commit_dispatch_target_job_cancelled_409`
  * `test_commit_dispatch_existing_in_progress_route_409`
  * `test_commit_dispatch_existing_committed_route_replaces_stops_atomically`
  * `test_commit_dispatch_idempotent_when_sequence_unchanged`
  * `test_commit_dispatch_sets_job_status_to_scheduled`
  * `test_commit_dispatch_audit_event_emitted_with_ids_and_totals`
  * `test_cancel_route_marks_non_terminal_stops_skipped`
  * `test_cancel_route_returns_scheduled_jobs_to_pending`
  * `test_cancel_route_does_not_revert_in_progress_jobs`
  * `test_start_route_transitions_committed_to_in_progress`
  * `test_start_route_from_complete_raises_invalid_transition`
  * `test_complete_last_stop_finalises_route_to_complete`
  * `test_skip_stop_with_other_pending_stops_keeps_route_in_progress`
  * `test_arrive_then_complete_stop_sets_actual_timestamps`
* Unit tests `tests/unit/test_route_status.py`:
  * Parameterised transition matrix tests for both route and stop status enums.
* API tests `tests/api/test_dispatch_api.py`:
  * `test_post_dispatch_requires_jobs_dispatch_permission` (Technician 403)
  * `test_post_dispatch_with_option_kind_201_returns_route`
  * `test_post_dispatch_with_manual_sequence_201_returns_route`
  * `test_post_dispatch_with_both_modes_422`
  * `test_post_dispatch_with_neither_mode_422`
  * `test_post_dispatch_cross_tenant_job_404`
  * `test_post_dispatch_completed_job_409`
  * `test_post_dispatch_rate_limited_60_per_min`
  * `test_post_dispatch_idempotent_replay_returns_same_route_no_dup_stops`
* API tests `tests/api/test_routes_api.py`:
  * `test_get_routes_date_required_422_when_missing`
  * `test_get_routes_dispatcher_sees_all_for_date`
  * `test_get_routes_technician_sees_only_own_crew_routes`
  * `test_get_route_by_id_includes_ordered_stops_and_job_summaries`
  * `test_get_route_cross_tenant_404`
  * `test_post_route_start_dispatcher_succeeds`
  * `test_post_route_start_technician_not_on_crew_404`
  * `test_post_route_cancel_dispatcher_succeeds`
  * `test_post_route_cancel_technician_403`
  * `test_post_stop_arrived_technician_succeeds`
  * `test_post_stop_complete_auto_finalises_route_when_last`
  * `test_post_stop_skip_with_reason_succeeds`
* Integration test `tests/integration/test_dispatch_transaction.py`:
  * `test_dispatch_commit_is_atomic_under_concurrent_calls` — two threads concurrently dispatch
    different jobs to the *same* vehicle for the same day; both must succeed (route gets two
    stops) without violating `(route_id, sequence_index)` invariant. Uses
    `SELECT ... FOR UPDATE` on the Route row inside the service to serialise.
  * `test_dispatch_commit_rolls_back_on_routing_engine_failure` — force the routing adapter
    to raise after the Route row is inserted; assert no Route row remains (full rollback).
  * `test_rls_hides_other_tenant_routes`
* Integration test `tests/integration/test_route_lifecycle.py`:
  * End-to-end: create customer + location + job + vehicle + crew; dispatch with `nearest`;
    start route; mark stop arrived; mark stop complete; assert route auto-finalises.

## Structure

```text
src/office_hero/
├── core/
│   ├── exceptions.py            # +RouteNotFoundError, +InvalidRouteTransitionError,
│   │                            #  +RouteCommitConflictError, +ManualSequenceInvalidError
│   └── route_status.py          # RouteStatus + RouteStopStatus enums + transition matrices
├── models/
│   └── route.py                 # Route + RouteStop
├── repositories/
│   ├── route_repository.py
│   └── route_stop_repository.py
├── services/
│   ├── dispatch_service.py
│   └── job_service.py           # +transition_route_cancelled()
└── api/
    ├── schemas/
    │   ├── dispatch.py
    │   └── route.py
    └── routes/
        ├── dispatch.py
        └── routes.py

alembic/
└── versions/
    └── 0007_routes.py

tests/
├── unit/
│   ├── test_dispatch_service.py
│   └── test_route_status.py
├── api/
│   ├── test_dispatch_api.py
│   └── test_routes_api.py
└── integration/
    ├── test_dispatch_transaction.py
    └── test_route_lifecycle.py
```

## Failing Test Outline

```python
# tests/unit/test_dispatch_service.py
import pytest
from datetime import date
from office_hero.core.exceptions import (
    RouteCommitConflictError, ManualSequenceInvalidError,
)


@pytest.mark.asyncio
async def test_commit_dispatch_existing_committed_route_replaces_stops_atomically(
    dispatch_service, scheduled_job_a, scheduled_job_b, vehicle, crew, dispatcher_user
):
    """Re-dispatch to the same vehicle replaces stops without duplicating."""
    # First dispatch — vehicle gets job_a as its only stop.
    r1 = await dispatch_service.commit_dispatch(
        TENANT_A, dispatcher_user.id, job_id=scheduled_job_a.id,
        payload=manual_payload(date(2026, 6, 1), vehicle.id, [scheduled_job_a.id]),
    )
    assert [s.job_id for s in r1.stops] == [scheduled_job_a.id]

    # Second dispatch — same vehicle, both jobs in sequence.
    r2 = await dispatch_service.commit_dispatch(
        TENANT_A, dispatcher_user.id, job_id=scheduled_job_b.id,
        payload=manual_payload(date(2026, 6, 1), vehicle.id,
                               [scheduled_job_a.id, scheduled_job_b.id]),
    )
    assert r1.id == r2.id
    assert [s.job_id for s in r2.stops] == [scheduled_job_a.id, scheduled_job_b.id]
    assert len(r2.stops) == 2  # no duplicates


@pytest.mark.asyncio
async def test_commit_dispatch_manual_sequence_rejects_duplicates(
    dispatch_service, scheduled_job_a, vehicle, dispatcher_user
):
    """Manual sequence with duplicate job_ids is rejected."""
    with pytest.raises(ManualSequenceInvalidError):
        await dispatch_service.commit_dispatch(
            TENANT_A, dispatcher_user.id, job_id=scheduled_job_a.id,
            payload=manual_payload(
                date(2026, 6, 1), vehicle.id,
                [scheduled_job_a.id, scheduled_job_a.id],
            ),
        )


# tests/integration/test_dispatch_transaction.py
@pytest.mark.asyncio
async def test_dispatch_commit_is_atomic_under_concurrent_calls(
    integration_session, dispatch_service, scheduled_job_a, scheduled_job_b,
    vehicle, dispatcher_user
):
    """Two concurrent dispatches to the same vehicle serialise correctly."""
    async def dispatch_a():
        return await dispatch_service.commit_dispatch(
            TENANT_A, dispatcher_user.id, job_id=scheduled_job_a.id,
            payload=manual_payload(date(2026, 6, 1), vehicle.id, [scheduled_job_a.id]),
        )

    async def dispatch_b():
        return await dispatch_service.commit_dispatch(
            TENANT_A, dispatcher_user.id, job_id=scheduled_job_b.id,
            payload=manual_payload(date(2026, 6, 1), vehicle.id, [scheduled_job_b.id]),
        )

    import asyncio
    results = await asyncio.gather(dispatch_a(), dispatch_b())
    final_route = await dispatch_service.get_route_for_vehicle_date(
        TENANT_A, vehicle.id, date(2026, 6, 1),
    )
    job_ids = {s.job_id for s in final_route.stops}
    assert job_ids == {scheduled_job_a.id, scheduled_job_b.id}
```

## Dependencies

* **Slice 2 (Database foundation)** — async engine, RLS, Alembic, transaction primitives.
* **Slice 3 (Auth & RBAC)** — JWT, decorators, Role enum.
* **Slice 4 (Observability)** — `AuditService`, exception handler integration, rate limiting.
* **Slice 7 (Tenant management)** — tenants table for FKs.
* **Slice 11 (Customer & Location)** — Location for stop ETA computation.
* **Slice 12 (Job management)** — Job status lifecycle; `JobService.schedule`,
  `transition_route_cancelled` (added in this slice on the same JobService class).
* **Slice 13 (Vehicle & VehicleCrew)** — Vehicle, VehicleCrew; FK references.
* **Slice 14 / Design 014 (Routing engine)** — `RoutingService.compute_options` for option
  mode; `routing_service.adapter.optimize_sequence` for manual-mode totals.
* Relevant ADRs: **053** (RLS), **056** (saga/outbox — *not* used here because dispatch is
  all local DB; back-office push of route/dispatch info to ServiceTitan/PestPac is Slice 25+),
  **058**, **059**, **060**, **062** (write tier; routing tier from slice 14), **063**
  (audit + structured logs).

## Effort

Estimate: **3/5**. Two tables, two services (one extended), two routers, but the transactional
correctness in `commit_dispatch` carries weight: atomic replace-all of stops, idempotent retry,
Job status side effects all inside one transaction, plus the manual-mode validation matrix.
Concurrency under same-vehicle-same-day is non-trivial — `SELECT ... FOR UPDATE` on the Route
row is the cleanest serialisation hook and is tested. The route auto-finalisation on
all-stops-terminal is a subtle invariant; centralised in `dispatch_service` and tested.

## Risk Callouts

* **Transactional atomicity.** `commit_dispatch` mutates Route + RouteStops + Jobs in one
  transaction. Any partial failure must roll back the whole thing. Tested with deliberate
  routing-adapter failures injected mid-transaction. **Important:** the call to
  `routing_service.adapter.optimize_sequence` happens *before* the DB writes so a network
  failure cannot corrupt half-committed state. Reviewers should reject any refactor that
  reorders those steps.
* **Stale options.** Option mode re-fetches options instead of trusting client-supplied
  vehicle_id, because the underlying world may have changed since the
  `/jobs/{id}/routing-options` call. **OPEN QUESTION:** stakeholders may prefer trusting the
  client's already-shown choice (UX argument); flagged in PR. Default is re-fetch.
* **Concurrency on same vehicle + date.** Two simultaneous dispatches to the same vehicle/day
  must not corrupt sequence indices. Service uses `SELECT ... FOR UPDATE` on the Route row
  (creating it inside the same lock if absent) so calls serialise. The unique
  `(route_id, sequence_index)` index is a backstop.
* **Re-dispatch into in_progress route.** Refused with 409. Re-dispatching a single new Job
  to a vehicle whose route is *committed but not started* is the common case and is the
  primary code path under test.
* **Route cancellation cascade.** Cancelling a route reverts `scheduled` jobs to `pending`
  but does not touch `in_progress` jobs. Tested. The cascade emits one audit event per affected
  job; reviewers should consider whether that is too chatty for very large routes (low risk;
  routes are bounded to ≤50 stops via `ROUTING_MAX_STOPS_PER_OPTIMIZE` in slice 014).
* **No back-office push yet.** Slice 25+ will use the `outbox_events` table to push committed
  routes to ServiceTitan etc. via the Saga pattern (ADR 056). This slice writes nothing to
  `outbox_events` — that's a follow-up. Documented in the service docstring.
* **Idempotency without idem keys.** True idempotency comes from the `(route_id, job_id)`
  uniqueness on RouteStops plus the "sequence unchanged → no-op" guard. Clients should still
  use a request ID in the audit log for traceability.
* **RLS hides vs 403.** Per the auth slice pattern, RLS hides cross-tenant rows; we return
  404, not 403, to avoid leaking existence. Same applies to Technicians querying routes they
  are not assigned to. Tests assert 404 consistently.

---

Once approved, implementation proceeds: model + migration first, then the `route_status.py`
matrix and its tests, then `DispatchService.commit_dispatch` under TDD (with the routing
service stubbed), then the route-lifecycle methods, then routers. The concurrency
integration test is gated on a Neon branch; reviewers should run it manually before merge.
