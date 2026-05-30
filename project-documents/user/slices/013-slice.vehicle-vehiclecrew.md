---
docType: slice-design
parent: ../project-guides/003-slices.office-hero.md
project: office-hero
dateCreated: 20260524
status: not_started
slice: vehicle-vehiclecrew
dateUpdated: 20260524
---

# Slice Design 013: Vehicle & VehicleCrew management

This slice introduces the **Vehicle** aggregate and a date-scoped **VehicleCrew**
assignment that pegs Technicians (existing `User` rows from slice 3) to a Vehicle for a single
calendar date. A Vehicle can host **at most one VehicleCrew per date** (enforced by a unique
constraint, not just service logic). VehicleCrew is the input the routing engine (Slice 13 of
the master plan / design 014 in this batch) consumes when generating dispatch options.

It implements **Slice 12** of the master slice plan.

## Domain Model

```text
┌──────────┐     ┌───────────────────────┐     ┌────────────────────┐
│ Vehicle  │ 1──N│  VehicleCrew (per     │ N──N│ Technician (User   │
│          │     │  vehicle_id + date)   │     │ with role          │
│          │     │                       │     │ Technician/Helper) │
└──────────┘     └───────────────────────┘     └────────────────────┘
                          │
                          │ 1──N
                          ▼
                ┌─────────────────────────┐
                │ VehicleCrewMember       │
                │ (User + role_on_crew)   │
                └─────────────────────────┘
```

* **Vehicle** is long-lived; identifies a physical truck/van.
* **VehicleCrew** is for one day (`work_date`). Each entry lists the users on the truck for
  that date and each user's role on that crew (Lead, Helper).
* The unique constraint `(tenant_id, vehicle_id, work_date)` prevents a vehicle being assigned
  to two crews on the same day.
* A Technician (User) *can* appear on multiple Vehicles' crews on the same date — this is a
  legal field operation if a tech rides as helper on a second truck after lunch — but is
  flagged by `list_user_crew_conflicts()` for the Dispatcher UI. See Risk callouts.

## Goals

* Extend `src/office_hero/core/exceptions.py`:
  * `class VehicleNotFoundError(Exception)`
  * `class VehicleCrewNotFoundError(Exception)`
  * `class CrewAssignmentConflictError(Exception)` — raised when a vehicle already has a crew
    on `work_date`; carries existing `crew_id`.
  * `class InvalidCrewMemberError(Exception)` — raised when a user is not a Technician /
    Helper, is in another tenant, or is inactive.
* Create `src/office_hero/core/crew_role.py` — `CrewRole` enum:
  * `LEAD = "lead"` (one and only one per crew; the "driver" / journey-responsible tech)
  * `HELPER = "helper"`
  * `TRAINEE = "trainee"` (counted toward crew size but cannot lead a Job)
  * Note: this is a **per-crew role** distinct from the user's RBAC `Role`. A user with RBAC
    role `Technician` typically takes `LEAD`; `TechnicianHelper` users default to `HELPER`.
* Create `src/office_hero/models/vehicle.py` — `Vehicle` ORM model:
  * `id: Mapped[UUID]` (PK)
  * `tenant_id: Mapped[UUID]` (FK, NOT NULL — RLS pivot)
  * `license_plate: Mapped[str]` (20, NOT NULL — unique per tenant)
  * `nickname: Mapped[str | None]` (120 — operator-friendly name, e.g. "Truck 7")
  * `make: Mapped[str | None]` (60)
  * `model: Mapped[str | None]` (60)
  * `year: Mapped[int | None]` (CHECK 1980..2100)
  * `vin: Mapped[str | None]` (17 — Vehicle Identification Number)
  * `gps_device_id: Mapped[str | None]` (120 — optional hardware ID; used by Slice 15
    location tracking to disambiguate when phone GPS is unavailable)
  * `capacity_kg: Mapped[int | None]` (CHECK >= 0 — for plumbing/HVAC equipment limits;
    informational for v1, may feed routing constraints later)
  * `home_base_lat: Mapped[float | None]` (Numeric(9,6))
  * `home_base_lng: Mapped[float | None]` (Numeric(9,6))
  * `notes: Mapped[str | None]` (Text)
  * `archived: Mapped[bool]` (default False — soft delete; archived vehicles are excluded from
    routing candidate lists)
  * `created_at`, `updated_at`
  * `__table_args__`: unique `(tenant_id, license_plate)` where `archived=false`;
    unique `(tenant_id, vin)` partial index where `vin IS NOT NULL`.
  * `crews: Mapped[list["VehicleCrew"]] = relationship(back_populates="vehicle")`
* Create `src/office_hero/models/vehicle_crew.py` — `VehicleCrew` and `VehicleCrewMember`:
  * `class VehicleCrew(Base)`:
    * `id: Mapped[UUID]` (PK)
    * `tenant_id: Mapped[UUID]` (FK, NOT NULL — RLS)
    * `vehicle_id: Mapped[UUID]` (FK `vehicles.id`, NOT NULL)
    * `work_date: Mapped[date]` (NOT NULL)
    * `shift_start: Mapped[time]` (NOT NULL, default `08:00`)
    * `shift_end: Mapped[time]` (NOT NULL, default `17:00`)
    * `notes: Mapped[str | None]` (Text — dispatcher's free-form annotation)
    * `created_by_user_id: Mapped[UUID]` (FK users.id)
    * `created_at`, `updated_at`
    * `vehicle: Mapped["Vehicle"] = relationship(back_populates="crews")`
    * `members: Mapped[list["VehicleCrewMember"]] = relationship(back_populates="crew",
      cascade="all, delete-orphan")`
    * `__table_args__`: unique `(tenant_id, vehicle_id, work_date)` — **the core invariant**.
  * `class VehicleCrewMember(Base)`:
    * `id: Mapped[UUID]` (PK)
    * `tenant_id: Mapped[UUID]` (FK — denormalised for RLS even though redundant via crew)
    * `crew_id: Mapped[UUID]` (FK `vehicle_crews.id` ON DELETE CASCADE)
    * `user_id: Mapped[UUID]` (FK `users.id`, NOT NULL)
    * `role_on_crew: Mapped[str]` (20 — `lead|helper|trainee`)
    * `created_at`
    * `__table_args__`: unique `(crew_id, user_id)` — a user can only appear once on a given
      crew; CHECK constraint `role_on_crew IN ('lead','helper','trainee')`.
* Update `src/office_hero/models/__init__.py` to import `Vehicle`, `VehicleCrew`,
  `VehicleCrewMember`.
* Create `src/office_hero/repositories/vehicle_repository.py`:
  * `VehicleRepository` + `VehicleRepositoryProtocol`. Methods:
    * `create(tenant_id, *, license_plate, nickname, make, model, year, vin, gps_device_id,
      capacity_kg, home_base_lat, home_base_lng, notes) -> Vehicle`
    * `get_by_id(vehicle_id, tenant_id) -> Vehicle | None`
    * `list(tenant_id, *, archived=False, search=None, limit=50, offset=0)
      -> tuple[list[Vehicle], int]`
    * `update(vehicle_id, tenant_id, **patch) -> Vehicle`
    * `archive(vehicle_id, tenant_id) -> Vehicle`
    * `restore(vehicle_id, tenant_id) -> Vehicle`
    * `list_active_for_date(tenant_id, work_date) -> list[Vehicle]` — vehicles that have a
      VehicleCrew for the given date (used by routing in slice 14).
* Create `src/office_hero/repositories/vehicle_crew_repository.py`:
  * `VehicleCrewRepository` + protocol. Methods:
    * `create(tenant_id, *, vehicle_id, work_date, shift_start, shift_end, notes,
      created_by_user_id, members: list[CrewMemberInput]) -> VehicleCrew` — single transaction;
      raises `CrewAssignmentConflictError` on duplicate `(vehicle_id, work_date)` via the unique
      constraint (catch `IntegrityError`, look up existing, raise typed exception).
    * `get_by_id(crew_id, tenant_id) -> VehicleCrew | None` — joinedload `members.user`.
    * `get_for_vehicle_date(tenant_id, vehicle_id, work_date) -> VehicleCrew | None` —
      the common query "what's this truck doing today?".
    * `list_for_date(tenant_id, work_date) -> list[VehicleCrew]` — daily dispatch view.
    * `list_for_user_date(tenant_id, user_id, work_date) -> list[VehicleCrew]` — "what am I on
      today?", used by mobile auth + multi-truck conflict detection.
    * `update(crew_id, tenant_id, *, shift_start, shift_end, notes) -> VehicleCrew` — fields
      only; member changes go through dedicated methods.
    * `replace_members(crew_id, tenant_id, members: list[CrewMemberInput]) -> VehicleCrew` —
      atomic delete-then-insert (within transaction) so the unique `(crew_id, user_id)` invariant
      is preserved.
    * `add_member(crew_id, tenant_id, user_id, role_on_crew) -> VehicleCrewMember`
    * `remove_member(crew_id, tenant_id, user_id) -> None`
    * `delete(crew_id, tenant_id) -> None` — cascade deletes members.
    * `find_user_crew_conflicts(tenant_id, work_date) -> list[tuple[UUID, list[UUID]]]` —
      returns `[(user_id, [crew_id_a, crew_id_b]), ...]` for any user double-booked on the date.
* Create `src/office_hero/services/vehicle_service.py`:
  * `class VehicleService`:
    * `__init__(repo, audit)`.
    * `async def create(tenant_id, user_id, payload: VehicleCreate) -> Vehicle` — audit
      `vehicle.created`.
    * `async def update(tenant_id, user_id, vehicle_id, patch) -> Vehicle` — diff audit
      `vehicle.updated`.
    * `async def archive(tenant_id, user_id, vehicle_id) -> Vehicle` — refuses to archive a
      vehicle with active (today's date or later) crews; raises a typed error mapped to 409.
    * `async def restore(...)`, `async def get(...)`, `async def list(...)`.
* Create `src/office_hero/services/vehicle_crew_service.py`:
  * `class VehicleCrewService`:
    * `__init__(crew_repo, vehicle_repo, user_repo, audit)`.
    * `async def create(tenant_id, user_id, payload: VehicleCrewCreate) -> VehicleCrew`:
      * Verifies vehicle exists and is not archived.
      * Verifies `work_date` is not in the past more than 30 days (configurable;
        prevents accidental backdated assignments — operators can override via a separate
        admin-only endpoint, not in this slice).
      * Verifies each `member.user_id`:
        * Belongs to the same tenant.
        * Is active (`user.active == True`).
        * Has RBAC role in `{Technician, TechnicianHelper}`.
        * Otherwise → `InvalidCrewMemberError`.
      * Verifies exactly one member has `role_on_crew=LEAD`.
      * `shift_end > shift_start`; both within 0..24h.
      * Calls `crew_repo.create(...)` — relies on DB unique to enforce one crew per
        `(vehicle, date)`; converts IntegrityError → `CrewAssignmentConflictError`.
      * Audits `crew.created` with `{crew_id, vehicle_id, work_date, member_user_ids}`.
    * `async def update_details(tenant_id, user_id, crew_id, patch) -> VehicleCrew` — shift,
      notes only.
    * `async def replace_members(tenant_id, user_id, crew_id, members) -> VehicleCrew` —
      re-validates the LEAD constraint and per-user eligibility.
    * `async def add_member(tenant_id, user_id, crew_id, user_id_to_add, role_on_crew)` — also
      validates eligibility.
    * `async def remove_member(tenant_id, user_id, crew_id, user_id_to_remove)` — refuses to
      remove the LEAD without replacing it (server-side guard; UI also prevents).
    * `async def delete(tenant_id, user_id, crew_id)` — audits `crew.deleted` with
      `{crew_id, work_date, vehicle_id}`. Refuses to delete if a Route already references
      this crew for the date (cross-slice safety; will become a real check once Slice 14 lands).
    * `async def get(...)`, `async def list_for_date(...)`,
      `async def get_for_vehicle_date(...)`,
      `async def conflicts_for_date(tenant_id, work_date) -> list[CrewConflict]`.
* Create `src/office_hero/api/schemas/vehicle.py`:
  * `VehicleCreate`: `license_plate (1..20)`, `nickname?`, `make?`, `model?`, `year?
    (1980..2100)`, `vin? (==17)`, `gps_device_id?`, `capacity_kg? (>=0)`,
    `home_base_lat? (-90..90)`, `home_base_lng? (-180..180)`, `notes?`. `extra="forbid"`.
  * `VehicleUpdate` — all fields optional, model_validator: at least one set.
  * `VehicleRead`, `VehicleSummary`, `VehicleList`.
* Create `src/office_hero/api/schemas/vehicle_crew.py`:
  * `CrewMemberInput`: `{user_id: UUID, role_on_crew: CrewRole}`.
  * `VehicleCrewCreate`: `{vehicle_id, work_date, shift_start (default "08:00"),
    shift_end (default "17:00"), notes?, members: list[CrewMemberInput] (min 1)}`. Model
    validator: exactly one member with `role_on_crew == "lead"`.
  * `VehicleCrewUpdate`: `{shift_start?, shift_end?, notes?}`. (Member edits via dedicated endpoints.)
  * `VehicleCrewMembersReplace`: `{members: list[CrewMemberInput]}` with lead invariant.
  * `VehicleCrewRead`: full DTO with embedded `members: list[CrewMemberRead]` where
    `CrewMemberRead = {user_id, email, full_name (when available), role_on_crew}`.
  * `CrewConflictRead`: `{user_id, email, crew_ids: list[UUID], work_date}`.
* Create `src/office_hero/api/routes/vehicles.py` — `prefix="/vehicles"`, `tags=["vehicles"]`:
  * `POST /vehicles` — `@require_role([TenantAdmin, Operator, OperatorStaff])`.
    (Dispatchers do not create vehicles; only admins.)
  * `GET /vehicles` — `@require_permission("vehicles:read")` (granted to Dispatcher,
    TenantAdmin, Operator).
  * `GET /vehicles/{id}` — same.
  * `PATCH /vehicles/{id}` — `@require_role([TenantAdmin, Operator, OperatorStaff])`.
  * `POST /vehicles/{id}/archive` — same admin gate; 409 if active crews exist.
  * `POST /vehicles/{id}/restore` — same admin gate.
  * Rate-limited at `write` tier (60 req/min).
* Create `src/office_hero/api/routes/vehicle_crews.py` — `prefix=""`, `tags=["crews"]`:
  * `POST /vehicle-crews` — `@require_role([Dispatcher, TenantAdmin, Operator, OperatorStaff])`.
    Body `VehicleCrewCreate`. **409** on `CrewAssignmentConflictError`; **422** on
    `InvalidCrewMemberError`.
  * `GET /vehicle-crews` — `@require_role([Dispatcher, TenantAdmin, Operator, Technician,
    TechnicianHelper])`. Query: `work_date` (required), `vehicle_id?`, `user_id?`.
    Technicians can list but are scoped to their own crews (service enforces).
  * `GET /vehicle-crews/{id}` — same role set; Technicians can only read crews they're on.
  * `PATCH /vehicle-crews/{id}` — `@require_role([Dispatcher, TenantAdmin, Operator])`.
  * `PUT /vehicle-crews/{id}/members` — replace member roster atomically. Same gate.
  * `POST /vehicle-crews/{id}/members` — add one. Same gate.
  * `DELETE /vehicle-crews/{id}/members/{user_id}` — remove one. Same gate.
  * `DELETE /vehicle-crews/{id}` — same gate.
  * `GET /vehicle-crews/conflicts?date=YYYY-MM-DD` — `@require_role([Dispatcher,
    TenantAdmin, Operator])`. Returns double-booked users for the day.
* Update `src/office_hero/api/state.py` — `get_vehicle_service()`, `get_vehicle_crew_service()`.
* Register routers in `src/office_hero/api/app.py`.
* Update `src/office_hero/api/exception_handlers.py`:
  * Map `VehicleNotFoundError`, `VehicleCrewNotFoundError` → 404.
  * Map `CrewAssignmentConflictError` → **409** with `{detail, existing_crew_id}`.
  * Map `InvalidCrewMemberError` → **422** with `{detail, user_id, reason}`.
* Create migration `alembic/versions/0006_vehicles_and_crews.py`:
  * Create `vehicles` table; FK `tenants(id)`; CHECK constraints on `year`, `capacity_kg`.
  * Indexes: unique `(tenant_id, license_plate)` WHERE `archived=false`; partial unique
    `(tenant_id, vin)` WHERE `vin IS NOT NULL`.
  * `ALTER TABLE vehicles ENABLE ROW LEVEL SECURITY;` + tenant_isolation policy.
  * Create `vehicle_crews` table; FK `tenants(id)`, FK `vehicles(id)`, FK
    `users(id) as created_by`.
  * Unique constraint `uq_vehicle_crew_vehicle_date` ON `(tenant_id, vehicle_id, work_date)`.
  * Index `(tenant_id, work_date)` — daily view.
  * `ALTER TABLE vehicle_crews ENABLE ROW LEVEL SECURITY;` + policy.
  * Create `vehicle_crew_members` table; FK `tenants(id)`, FK `vehicle_crews(id) ON DELETE
    CASCADE`, FK `users(id)`.
  * Unique `(crew_id, user_id)`. CHECK `role_on_crew IN ('lead', 'helper', 'trainee')`.
  * `ALTER TABLE vehicle_crew_members ENABLE ROW LEVEL SECURITY;` + policy.
  * Downgrade drops everything in reverse.
* Unit tests `tests/unit/test_vehicle_service.py`:
  * `test_create_vehicle_returns_vehicle_and_audits`
  * `test_create_vehicle_duplicate_plate_raises_conflict`
  * `test_archive_vehicle_with_active_crew_today_refused`
  * `test_archive_vehicle_with_only_past_crews_succeeds`
  * `test_update_vehicle_partial_patch_emits_diff_audit`
* Unit tests `tests/unit/test_vehicle_crew_service.py`:
  * `test_create_crew_with_one_lead_succeeds`
  * `test_create_crew_without_lead_raises`
  * `test_create_crew_with_two_leads_raises`
  * `test_create_crew_member_in_other_tenant_raises_invalid_member`
  * `test_create_crew_member_with_inactive_user_raises_invalid_member`
  * `test_create_crew_member_with_non_technician_role_raises_invalid_member`
    (e.g. Dispatcher cannot be a crew lead)
  * `test_create_crew_duplicate_vehicle_date_raises_assignment_conflict`
  * `test_create_crew_archived_vehicle_raises_not_found`
  * `test_create_crew_backdated_more_than_30_days_raises`
  * `test_create_crew_shift_end_before_start_raises_422`
  * `test_replace_members_keeps_lead_invariant`
  * `test_remove_lead_member_without_replacement_refused`
  * `test_conflicts_for_date_finds_double_booked_user`
  * `test_delete_crew_when_routed_refused` (smoke; full check lands in slice 14)
* API tests `tests/api/test_vehicles_api.py`:
  * `test_post_vehicle_requires_admin_role` (Dispatcher 403)
  * `test_post_vehicle_201_returns_id`
  * `test_get_vehicles_dispatcher_can_read`
  * `test_get_vehicles_technician_403`
  * `test_archive_vehicle_with_today_crew_409`
  * `test_vehicles_rate_limited_60_per_min`
* API tests `tests/api/test_vehicle_crews_api.py`:
  * `test_post_crew_dispatcher_succeeds`
  * `test_post_crew_technician_403`
  * `test_post_crew_duplicate_assignment_409`
  * `test_post_crew_member_other_tenant_422_invalid_member`
  * `test_post_crew_no_lead_422`
  * `test_get_crews_for_date_dispatcher_sees_all`
  * `test_get_crews_for_date_technician_sees_only_their_own`
  * `test_get_crew_conflicts_returns_double_booked_user`
  * `test_replace_members_keeps_unique_user_invariant`
  * `test_remove_lead_without_replacement_refused`
* Integration test `tests/integration/test_vehicle_crews_rls.py`:
  * `test_rls_hides_other_tenant_vehicles`
  * `test_unique_constraint_blocks_concurrent_double_assign` — two concurrent inserts of crews
    for the same (vehicle, date); one wins, one gets IntegrityError → 409.
  * `test_cascade_delete_members_on_crew_delete`

## Structure

```text
src/office_hero/
├── core/
│   ├── exceptions.py            # +VehicleNotFoundError, +VehicleCrewNotFoundError,
│   │                            #  +CrewAssignmentConflictError, +InvalidCrewMemberError
│   └── crew_role.py             # CrewRole enum (lead/helper/trainee)
├── models/
│   ├── vehicle.py               # Vehicle ORM model
│   └── vehicle_crew.py          # VehicleCrew + VehicleCrewMember
├── repositories/
│   ├── vehicle_repository.py
│   └── vehicle_crew_repository.py
├── services/
│   ├── vehicle_service.py
│   └── vehicle_crew_service.py
└── api/
    ├── schemas/
    │   ├── vehicle.py
    │   └── vehicle_crew.py
    └── routes/
        ├── vehicles.py
        └── vehicle_crews.py

alembic/
└── versions/
    └── 0006_vehicles_and_crews.py

tests/
├── unit/
│   ├── test_vehicle_service.py
│   └── test_vehicle_crew_service.py
├── api/
│   ├── test_vehicles_api.py
│   └── test_vehicle_crews_api.py
└── integration/
    └── test_vehicle_crews_rls.py
```

## Failing Test Outline

```python
# tests/unit/test_vehicle_crew_service.py
import pytest
from datetime import date
from office_hero.core.exceptions import (
    CrewAssignmentConflictError, InvalidCrewMemberError,
)


@pytest.mark.asyncio
async def test_create_crew_duplicate_vehicle_date_raises_assignment_conflict(
    vehicle_crew_service, vehicle, tech_a, tech_b, dispatcher_user
):
    """A second crew on the same (vehicle, date) is rejected by the unique constraint."""
    payload = make_crew_payload(vehicle_id=vehicle.id, work_date=date(2026, 6, 1),
                                lead=tech_a)
    await vehicle_crew_service.create(TENANT_A, dispatcher_user.id, payload)
    with pytest.raises(CrewAssignmentConflictError) as exc:
        dupe = make_crew_payload(vehicle_id=vehicle.id, work_date=date(2026, 6, 1),
                                 lead=tech_b)
        await vehicle_crew_service.create(TENANT_A, dispatcher_user.id, dupe)
    assert exc.value.existing_crew_id is not None


# tests/api/test_vehicle_crews_api.py
def test_get_crews_for_date_technician_sees_only_their_own(
    client, tech_a_token, todays_crew_with_tech_a, todays_crew_without_tech_a
):
    """Technician listing /vehicle-crews?work_date=today returns only crews they're on."""
    resp = client.get(
        f"/vehicle-crews?work_date={today_iso}",
        headers={"Authorization": f"Bearer {tech_a_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    ids = {c["id"] for c in body["items"]}
    assert todays_crew_with_tech_a.id in ids
    assert todays_crew_without_tech_a.id not in ids
```

## Dependencies

* **Slice 2 (Database foundation)** — RLS, Alembic.
* **Slice 3 (Auth & RBAC)** — Role enum, JWT, decorators, `users` table for FK.
* **Slice 4 (Observability)** — `AuditService`, exception handler.
* **Slice 7 (Tenant management)** — tenants table for FK.
* **Slice 8 (User management)** — user creation + activation flow (we re-use the existing
  `users` table but tests need both Technician and Dispatcher users available).
* Slice 11 (Customer & Location) is *not* a hard dependency — vehicles don't reference customers
  — but file naming places it before this slice in the merge order.
* Relevant ADRs: **053**, **058**, **059**, **060**, **062** (write tier), **063**.

## Effort

Estimate: **2/5**. Three tables, two services, two routers. Most rules are simple invariants
(one lead per crew, unique vehicle+date assignment). The interesting work is `replace_members`
needing to be transactional + atomic, and the cross-cutting `find_user_crew_conflicts` query.
The `vehicle.archived` cross-check against active crews introduces a small temporal join but
nothing exotic.

## Risk Callouts

* **Double-booked technicians.** A user appearing on two crews on the same date is *legal*
  (split-shift help) but worth surfacing. The `conflicts` endpoint exists so the Dispatcher UI
  can flag it. We do **not** enforce uniqueness on `(tenant_id, user_id, work_date)` — that
  would break legitimate split-shift cases. **OPEN QUESTION:** stakeholders may want a configurable
  per-tenant policy ("never allow double-booking"); deferred.
* **Capacity_kg as a hint, not a constraint.** Routing (Slice 13) will ignore this in v1 — see
  routing design risk callout. Document the field's intent in the model docstring.
* **Vehicle archival ordering.** Archiving a vehicle with a future crew is refused with 409;
  callers must delete the crew first. The error response must include the offending crew_id(s)
  for the UI to act on. Tests assert this.
* **Crew member RBAC role check.** We restrict crew membership to RBAC roles `Technician` and
  `TechnicianHelper`. If a Dispatcher rides along, they cannot be on the crew — only
  Technicians/Helpers can be assigned. **OPEN QUESTION:** should "Dispatcher in the truck for
  the day" be representable? The current model says no; flagged in PR.
* **GPS device ID nullable in v1.** Slice 15 (vehicle location tracking) will treat missing
  `gps_device_id` as "phone-only tracking." Document this in the field comment.

---

Once approved, implementation proceeds: vehicle model + migration + service + tests; then the
crew tables + service + tests; then the routers; conflicts query last. Slice 13 (routing) and
14 (dispatch) consume the `list_active_for_date` and `get_for_vehicle_date` repository
methods, so those must be locked down by the time this slice merges.
