---
docType: slice-design
parent: ../project-guides/003-slices.office-hero.md
project: office-hero
dateCreated: 20260524
status: not_started
---

# Slice Design 014: Routing engine integration

This slice introduces the **routing subsystem**. It defines the `RoutingAdapter` protocol
(per ADR 052) and an `ORSRoutingAdapter` HTTP client against the OpenRouteService API. It
exposes `POST /jobs/{id}/routing-options` returning **three ranked options** — `nearest`,
`earliest-completion`, `balanced-load` — over the candidate vehicles for the requested date.

Routing is **read-only** at this stage: this slice does not persist Routes or commit dispatch
(that is Slice 14 of the master plan, design 015 in this batch). It computes options on demand
and returns them to the caller. Caching is in-memory per-request only.

It implements **Slice 13** of the master slice plan.

## Architecture Overview

```text
POST /jobs/{id}/routing-options
        │
        ▼
RoutingService.compute_options(job_id, date, candidate_vehicle_ids)
        │
        ├── load job (with location lat/lng)
        ├── load candidate vehicles + their crews for date
        ├── load each vehicle's "current position" (Slice 15 will populate; here = home_base)
        ├── load other jobs already scheduled to each candidate vehicle for the date
        │
        ▼
RoutingAdapter.distance_matrix(origins, destinations)  ◄─── (ORS or Stub)
RoutingAdapter.optimize_sequence(start, stops, end?)
        │
        ▼
Rank three options (nearest / earliest / balanced)
        │
        ▼
Return RoutingOptionsResponse
```

## Ranking Strategies

For each candidate vehicle, the service computes:

* `nearest_insertion_cost` — added distance (meters) to insert the new job at its best position
  in that vehicle's existing sequence for the date. Lowest wins.
* `earliest_completion_time` — projected `arrival_at_new_job + estimated_duration` given the
  vehicle's current/last-known position and queued jobs. Earliest wins.
* `balanced_load` — `existing_route_duration + new_job_duration` against the median across
  candidate vehicles. The vehicle whose post-insertion load deviates least from the median
  wins (favours load balancing across the fleet, not raw speed).

The endpoint returns **one** option per strategy, totaling three options. Ties broken
deterministically by `vehicle_id` UUID lex order so tests can assert exact outputs.

## Goals

* Add dependency to `pyproject.toml`: `httpx` (already present).
* Extend `src/office_hero/core/config.py`:
  * `ORS_BASE_URL: str = "https://api.openrouteservice.org"` (community endpoint).
  * `ORS_API_KEY: str | None = None` (Fly.io secret; required when adapter is `ors`).
  * `ORS_PROFILE: str = "driving-car"` (per ORS docs; future: `"driving-hgv"` for box trucks).
  * `ORS_TIMEOUT_S: float = 8.0` (per ADR 052 SLO).
  * `ORS_ALLOWLIST: list[str] = ["api.openrouteservice.org"]` — SSRF defence; the adapter
    refuses to call any host outside this list.
  * `ROUTING_ADAPTER: str = "ors"` (enum: `"ors" | "stub"`); auto-stub under `pytest` unless
    overridden.
  * `ROUTING_MAX_STOPS_PER_OPTIMIZE: int = 50` (ORS community ceiling is 50 for the optimization
    endpoint; we enforce client-side to give a clean error instead of a 4xx).
  * `ROUTING_CACHE_TTL_S: int = 30` — per-request distance matrix cache; in-memory only.
* Extend `src/office_hero/core/exceptions.py`:
  * `class RoutingError(Exception)` — base for routing-subsystem errors.
  * `class RoutingTimeoutError(RoutingError)`.
  * `class RoutingUnavailableError(RoutingError)` — non-2xx from ORS, or empty allowlist hit.
  * `class NoCandidateVehiclesError(RoutingError)` — date has no crewed vehicles.
  * `class JobNotRoutableError(RoutingError)` — job has no geocoded location (`lat/lng` null).
  * `class TooManyStopsError(RoutingError)` — exceeds `ROUTING_MAX_STOPS_PER_OPTIMIZE`.
* Create `src/office_hero/adapters/routing/__init__.py` (empty).
* Create `src/office_hero/adapters/routing/types.py`:
  * `@dataclass(frozen=True) class Coordinates`: `lat: float`, `lng: float`. Helper
    `to_lonlat_tuple() -> tuple[float, float]` for ORS (which is lon-first).
  * `@dataclass(frozen=True) class Stop`: `id: UUID` (job_id), `coords: Coordinates`,
    `service_duration_s: int`, `priority: int = 50`.
  * `@dataclass(frozen=True) class VehicleState`: `vehicle_id: UUID`, `current: Coordinates`,
    `available_from: datetime`, `available_until: datetime`, `existing_sequence: list[Stop]`.
  * `@dataclass(frozen=True) class DistanceCell`: `distance_m: int`, `duration_s: int`.
  * `@dataclass(frozen=True) class RouteSegment`: `from_id: UUID | None` (None for the start),
    `to_id: UUID`, `distance_m: int`, `duration_s: int`, `eta: datetime`.
  * `@dataclass(frozen=True) class OptimizedRoute`: `vehicle_id: UUID`,
    `sequence: list[UUID]` (job IDs in visit order), `segments: list[RouteSegment]`,
    `total_distance_m: int`, `total_duration_s: int`, `arrival_at_target_s: int | None`.
* Create `src/office_hero/adapters/routing/protocol.py`:
  * `class RoutingAdapter(Protocol)`:
    * `async def distance_matrix(self, origins: list[Coordinates],
       destinations: list[Coordinates]) -> list[list[DistanceCell]]`
    * `async def optimize_sequence(self, start: Coordinates, stops: list[Stop],
       end: Coordinates | None = None) -> OptimizedRoute` — start is fixed (vehicle's current
      position); `end` optional return-to-base; stops are reordered for minimum total time.
    * `async def health_check(self) -> bool` — used by `GET /health` (slice 4).
* Create `src/office_hero/adapters/routing/ors.py` — `ORSRoutingAdapter`:
  * `__init__(base_url, api_key, profile, timeout, allowlist, http_client: httpx.AsyncClient
    | None = None)`.
    * Validates `base_url` host against `allowlist` on construction (raises
      `RoutingUnavailableError`).
    * If `api_key is None and base_url.host != "localhost"`, raises a config-time error
      (catch in app startup).
  * `async def distance_matrix(...)`:
    * Calls `POST {base_url}/v2/matrix/{profile}` with body
      `{"locations": [[lng,lat], ...], "sources": [...], "destinations": [...],
       "metrics": ["distance", "duration"]}`.
    * Header: `Authorization: <api_key>` (per ORS spec — no `Bearer` prefix).
    * Translates the response into `list[list[DistanceCell]]`. Both `distances` and
      `durations` arrays returned by ORS are aligned with `sources × destinations`.
    * Catches `httpx.TimeoutException` → `RoutingTimeoutError`; non-2xx →
      `RoutingUnavailableError(detail=status_code, body_excerpt)`.
  * `async def optimize_sequence(...)`:
    * Two-tier strategy:
      1. If `len(stops) <= 10`, call `/v2/directions/{profile}/json` with the stop list in input
         order — used to surface segment-level ETAs for already-optimized sequences (cheap).
      2. Otherwise call `/optimization` (ORS Optimization API, VROOM-based) with one vehicle
         and stops as jobs; profile mapped to ORS `vehicles[0].profile`.
    * Validates `len(stops) <= ROUTING_MAX_STOPS_PER_OPTIMIZE`; else `TooManyStopsError`.
    * Builds `OptimizedRoute`. ETAs are derived by summing segment durations starting from
      `available_from` of the vehicle (the *service* passes that as a base time; the adapter
      doesn't know wall-clock semantics).
  * `async def health_check(self) -> bool`:
    * Calls `GET {base_url}/v2/health` (or the documented health endpoint at the time of
      implementation; document the exact path in code).
    * Returns True on 200 within timeout, False otherwise (never raises).
  * Logging: every call emits structured logs `routing.ors.request_started` and
    `routing.ors.request_completed` with `duration_ms`, `status_code`, and a **redacted**
    `endpoint`. The API key is never logged.
* Create `src/office_hero/adapters/routing/stub.py` — `StubRoutingAdapter` for tests:
  * Deterministic euclidean distance × 1.3 (rough road-detour factor); 40 km/h average speed
    → duration_s. Optimization runs a nearest-neighbour pass from `start`, then a single
    2-opt sweep. Cheap, predictable, no network.
  * `health_check()` returns True.
* Create `src/office_hero/adapters/routing/factory.py` — `build_routing_adapter(settings) ->
  RoutingAdapter`. Honours `pytest` auto-stub.
* Create `src/office_hero/services/routing_service.py` — `RoutingService`:
  * `__init__(adapter: RoutingAdapter, job_repo, location_repo, vehicle_repo,
    vehicle_crew_repo, audit: AuditService)`.
  * `async def compute_options(tenant_id, user_id, *, job_id: UUID, work_date: date,
    vehicle_ids: list[UUID] | None = None) -> RoutingOptionsResponse`:
    1. Load the target job + its location. If `lat/lng` is missing → `JobNotRoutableError`.
    2. Resolve candidate vehicles:
       * If `vehicle_ids` provided, validate each belongs to the tenant and has a crew on
         `work_date` (`vehicle_crew_repo.get_for_vehicle_date`). Reject the lot if any single
         vehicle is invalid → `NoCandidateVehiclesError` with reasons.
       * Else: `vehicle_repo.list_active_for_date(tenant_id, work_date)`. Empty → raise.
    3. For each candidate vehicle, build a `VehicleState`:
       * `current = vehicle.home_base_lat/lng` (Slice 15 will replace with last-known position).
       * `available_from = combine(work_date, crew.shift_start, tenant_timezone)`.
       * `available_until = combine(work_date, crew.shift_end, ...)`.
       * `existing_sequence`: `job_repo.list_due_for_routing(tenant_id, work_date)` filtered
         to jobs already pegged to this vehicle (joins added in slice 15). For this slice,
         `existing_sequence` is the empty list — populated once Slice 15 lands routes.
         **OPEN QUESTION:** confirm with stakeholders that v1 routing assumes no prior
         commitments on the truck on the date; flagged in PR.
    4. Build the **distance matrix** for `[vehicle_current, ...existing_stops, new_job]`
       once per vehicle. Cache by `(vehicle_id, work_date)` for the request.
    5. Compute three strategies via internal helpers:
       * `_strategy_nearest(states)` → vehicle with min insertion cost.
       * `_strategy_earliest(states)` → vehicle whose insertion has earliest arrival_at_target.
       * `_strategy_balanced(states)` → vehicle minimising `abs(load_after - median_load)`.
    6. For each chosen vehicle, call `adapter.optimize_sequence(start=vehicle.current,
       stops=existing_stops + [new_stop], end=vehicle.current_or_home)` to get the canonical
       segment-level route.
    7. Assemble `RoutingOption` per strategy; emit audit `routing.options_computed` with
       `{job_id, work_date, candidate_count, chosen_vehicle_ids: {nearest, earliest, balanced}}`.
       No PII; just IDs.
    8. Return `RoutingOptionsResponse`.
  * If any **two** strategies pick the **same** vehicle with the same sequence, both options
    are still returned (deduplication is the UI's job in Slice 14); but the service includes a
    `note` on each duplicate option for the caller to deduplicate cleanly.
* Create `src/office_hero/api/schemas/routing.py`:
  * `RoutingOptionsRequest`: `{vehicle_ids?: list[UUID], date: date}`.
    * `vehicle_ids` optional; when omitted, all vehicles with crews on `date` are candidates.
    * `model_config = ConfigDict(extra="forbid")`.
  * `RouteSegmentRead`: `{from_id?: UUID, to_id: UUID, distance_m: int, duration_s: int,
    eta: datetime}`.
  * `RoutingOptionRead`: `{kind: Literal["nearest","earliest","balanced"], vehicle_id: UUID,
    route_sequence: list[UUID], segments: list[RouteSegmentRead], total_distance_m: int,
    estimated_duration_s: int, notes: list[str]}`.
  * `RoutingOptionsResponse`: `{options: list[RoutingOptionRead]}` (always length 3 unless
    `NoCandidateVehiclesError` raised earlier, which maps to 422).
* Create `src/office_hero/api/routes/routing.py`:
  * `POST /jobs/{job_id}/routing-options` — `@require_permission("jobs:dispatch")`. Body
    `RoutingOptionsRequest`. Tagged `["routing"]`.
  * Rate-limited at a **dedicated** tier: `routing` = 30 req/min/user (lower than `write` 60
    because each call may fan out to ORS). The slowapi limiter manager (slice 4) already
    supports per-name limits — define `routing` in the bootstrap config record.
* Update `src/office_hero/api/state.py`:
  * `get_routing_adapter() -> RoutingAdapter`
  * `get_routing_service() -> RoutingService`
* Update `src/office_hero/api/routes/health.py` (from slice 4):
  * Health check calls `routing_adapter.health_check()`; degraded state if False but DB ok.
  * Result reported as `"ors": "ok|degraded|error"`.
* Update `src/office_hero/api/exception_handlers.py`:
  * `RoutingTimeoutError` → **504 Gateway Timeout** (`{detail: "Routing engine timed out"}`).
  * `RoutingUnavailableError` → **502 Bad Gateway** (`{detail, request_id}`).
  * `NoCandidateVehiclesError` → **422** (`{detail, vehicle_id?, reason?}`).
  * `JobNotRoutableError` → **422** (`{detail: "Job location not geocoded"}`).
  * `TooManyStopsError` → **422** (`{detail, limit}`).
* **No migration in this slice.** No new tables. (Persistence comes in slice 015 / master 14.)
* Unit tests `tests/unit/test_routing_service.py`:
  * `test_compute_options_returns_three_kinds`
  * `test_compute_options_orders_kinds_consistently` (always nearest, earliest, balanced)
  * `test_compute_options_with_explicit_vehicle_ids_filters_candidates`
  * `test_compute_options_job_without_location_lat_raises_not_routable`
  * `test_compute_options_no_crewed_vehicles_raises_no_candidates`
  * `test_compute_options_explicit_vehicle_without_crew_raises_no_candidates`
  * `test_compute_options_explicit_vehicle_in_other_tenant_raises_not_found_then_no_candidates`
  * `test_compute_options_caches_distance_matrix_per_request`
  * `test_compute_options_emits_audit_event_with_ids_only_no_pii`
  * `test_nearest_strategy_picks_min_insertion`
  * `test_earliest_strategy_picks_min_arrival_time`
  * `test_balanced_strategy_picks_closest_to_median_load`
  * `test_tie_break_by_vehicle_id_uuid_lex_order`
* Unit tests `tests/unit/test_ors_routing_adapter.py` (httpx mocked):
  * `test_ors_distance_matrix_translates_response`
  * `test_ors_distance_matrix_4xx_raises_unavailable`
  * `test_ors_distance_matrix_5xx_raises_unavailable`
  * `test_ors_distance_matrix_timeout_raises_routing_timeout`
  * `test_ors_distance_matrix_sends_api_key_header`
  * `test_ors_distance_matrix_uses_lonlat_order`
  * `test_ors_optimize_small_stops_uses_directions_endpoint`
  * `test_ors_optimize_large_stops_uses_optimization_endpoint`
  * `test_ors_optimize_exceeds_max_stops_raises_too_many_stops`
  * `test_ors_constructor_rejects_host_outside_allowlist` (SSRF)
  * `test_ors_constructor_rejects_private_ip_in_url` (SSRF — `192.168.*`, `10.*`, `127.0.0.1`,
    `169.254.169.254` metadata)
  * `test_ors_does_not_log_api_key`
  * `test_ors_health_check_returns_false_on_timeout`
* Unit tests `tests/unit/test_stub_routing_adapter.py`:
  * `test_stub_distance_matrix_deterministic_for_fixed_inputs`
  * `test_stub_optimize_sequence_returns_consistent_ordering`
  * `test_stub_health_check_always_true`
* API tests `tests/api/test_routing_api.py`:
  * `test_post_routing_options_requires_jwt_401`
  * `test_post_routing_options_without_jobs_dispatch_perm_403` (Technician)
  * `test_post_routing_options_unknown_job_404`
  * `test_post_routing_options_cross_tenant_job_404`
  * `test_post_routing_options_job_without_geocode_422`
  * `test_post_routing_options_no_crewed_vehicles_422`
  * `test_post_routing_options_returns_three_options` (stub adapter)
  * `test_post_routing_options_explicit_vehicle_ids_respected`
  * `test_post_routing_options_response_shape_matches_schema`
  * `test_post_routing_options_rate_limited_30_per_min`
  * `test_post_routing_options_ors_timeout_returns_504` (httpx mock makes adapter raise)
  * `test_post_routing_options_ors_5xx_returns_502`
  * `test_post_routing_options_ors_does_not_leak_api_key_to_client`
    (force an error path, assert response body contains no env or header data)
* Integration test (optional, gated on `RUN_ORS_INTEGRATION=1`):
  * `tests/integration/test_routing_ors_live.py` — runs against a **Dockerized** ORS instance
    (`openrouteservice/openrouteservice:latest` with a small OSM extract — `docs/ors-dev.md` to
    be written). Asserts a real distance matrix call succeeds and the response shape matches.
    Skipped in default CI; on-demand only.
* Document the local ORS Docker setup in `docs/ors-dev.md` (new):
  * Pull image, mount a tiny OSM `.pbf` extract (US-Northeast small region from Geofabrik),
    expose on `localhost:8080`, set `ORS_BASE_URL=http://localhost:8080/ors`.
  * Note: integration test only — production is community ORS until Slice 13 self-host
    promotion (see ADR 052).

## Structure

```text
src/office_hero/
├── adapters/
│   └── routing/
│       ├── __init__.py
│       ├── protocol.py          # RoutingAdapter Protocol + types
│       ├── types.py             # Coordinates, Stop, VehicleState, OptimizedRoute, ...
│       ├── ors.py               # ORSRoutingAdapter
│       ├── stub.py              # StubRoutingAdapter
│       └── factory.py
├── services/
│   └── routing_service.py
├── api/
│   ├── schemas/
│   │   └── routing.py
│   └── routes/
│       └── routing.py
└── core/
    ├── config.py                # +ORS_*, +ROUTING_*
    └── exceptions.py            # +RoutingError, +RoutingTimeoutError,
                                 #  +RoutingUnavailableError, +NoCandidateVehiclesError,
                                 #  +JobNotRoutableError, +TooManyStopsError

tests/
├── unit/
│   ├── test_routing_service.py
│   ├── test_ors_routing_adapter.py
│   └── test_stub_routing_adapter.py
├── api/
│   └── test_routing_api.py
└── integration/
    └── test_routing_ors_live.py  # gated; runs against local Dockerized ORS

docs/
└── ors-dev.md                    # Local Dockerized ORS setup notes
```

## Failing Test Outline

```python
# tests/unit/test_routing_service.py
import pytest
from datetime import date
from office_hero.core.exceptions import (
    JobNotRoutableError, NoCandidateVehiclesError,
)


@pytest.mark.asyncio
async def test_compute_options_job_without_location_lat_raises_not_routable(
    routing_service, ungeocoded_job
):
    """A job with null lat/lng cannot be routed → 422 mapped error."""
    with pytest.raises(JobNotRoutableError):
        await routing_service.compute_options(
            tenant_id=TENANT_A, user_id=DISPATCHER, job_id=ungeocoded_job.id,
            work_date=date(2026, 6, 1), vehicle_ids=None,
        )


@pytest.mark.asyncio
async def test_compute_options_returns_three_kinds(
    routing_service, routable_job, two_crewed_vehicles
):
    """A normal call yields exactly three options, one per strategy."""
    resp = await routing_service.compute_options(
        tenant_id=TENANT_A, user_id=DISPATCHER, job_id=routable_job.id,
        work_date=date(2026, 6, 1), vehicle_ids=None,
    )
    kinds = [o.kind for o in resp.options]
    assert kinds == ["nearest", "earliest", "balanced"]


# tests/unit/test_ors_routing_adapter.py
@pytest.mark.asyncio
async def test_ors_constructor_rejects_host_outside_allowlist():
    """Passing a base_url outside ORS_ALLOWLIST must fail at construction (SSRF)."""
    with pytest.raises(RoutingUnavailableError):
        ORSRoutingAdapter(
            base_url="http://attacker.example.com",
            api_key="k", profile="driving-car", timeout=5.0,
            allowlist=["api.openrouteservice.org"],
        )


# tests/api/test_routing_api.py
def test_post_routing_options_ors_timeout_returns_504(
    client, dispatcher_token, routable_job, ors_timeout_mock
):
    """An ORS timeout propagates as 504 with no stack trace."""
    resp = client.post(
        f"/jobs/{routable_job.id}/routing-options",
        json={"date": "2026-06-01"},
        headers={"Authorization": f"Bearer {dispatcher_token}"},
    )
    assert resp.status_code == 504
    assert "traceback" not in resp.text.lower()
    assert "request_id" in resp.json()
```

## Dependencies

* **Slice 2 (Database foundation)** — async engine; no new tables here.
* **Slice 3 (Auth & RBAC)** — JWT, `@require_permission("jobs:dispatch")`.
* **Slice 4 (Observability)** — health endpoint, exception handler integration, rate limit
  manager (needs a new `routing` limit row in `rate_limits` seed).
* **Slice 11 (Customer & Location)** — provides `Location.lat/lng` and the
  `LocationRepository.get_by_id` used to fetch the job's location.
* **Slice 12 (Job management)** — provides `Job`, `JobRepository.get_by_id`, and
  `list_due_for_routing` (used for vehicle existing-sequence loading; currently returns []).
* **Slice 13 (Vehicle & VehicleCrew)** — provides `Vehicle`, `VehicleCrew`,
  `vehicle_repo.list_active_for_date`, `vehicle_crew_repo.get_for_vehicle_date`.
* Relevant ADRs: **052** (ORS choice), **053** (RLS), **060** (RBAC),
  **062** (rate limiting — new `routing` tier), **063** (logging; no PII in audit), and the
  HLD §Security A10 (SSRF allowlist).
* This slice **does not** depend on Slice 15 (vehicle location tracking) — vehicle "current"
  position falls back to `home_base_lat/lng`. Slice 15 will replace that source without changing
  this slice's API surface.

## Effort

Estimate: **3/5**. The adapter is moderate: two ORS endpoints (matrix + optimization), an
allowlist check, error-class translation, and a deterministic stub adapter. The ranking logic
is the substantive design work — three strategies that must be reproducible for tests. ORS
quirks (lon/lat ordering, header without `Bearer`, optimization endpoint vs directions
endpoint, response shape) absorb a chunk of implementation time. The integration test against
Dockerized ORS is optional but recommended once before merge.

## Risk Callouts

* **SSRF.** The biggest risk. The ORS adapter must refuse any host outside
  `ORS_ALLOWLIST`. We also block private IP ranges (`10.0.0.0/8`, `172.16.0.0/12`,
  `192.168.0.0/16`, `127.0.0.0/8`, `169.254.0.0/16`, `0.0.0.0/8`, `::1`, link-local) at the
  HTTP-client layer using a custom `httpx` transport that resolves and validates before
  connecting. Tested. The `Coordinates` payload itself cannot trigger SSRF because the URL is
  static.
* **API key leakage.** The ORS API key sits in Fly.io secrets; never logged, never in error
  responses. Test `test_ors_does_not_log_api_key` asserts this on every error path.
* **Rate limiting against ORS community.** ORS community is 500 req/day per ADR 052. We add
  the in-process `routing` slowapi limit (30 req/min/user) and document that under load, this
  slice's effective ceiling is the **upstream** quota — a 502/504 from us is the visible
  symptom. **Mitigation:** the Operator dashboard can adjust `rate_limits.routing.limit`
  downward at runtime per ADR 062.
* **Distance matrix complexity.** Naive distance matrix scales O(N²) in stops; ORS matrix call
  is capped at 50 sources × 50 destinations. We pre-validate `stops_count <= 50` and surface
  `TooManyStopsError → 422` before calling ORS. **Future work:** for fleets > 50 stops/day
  we partition the matrix into per-vehicle chunks (each vehicle's existing sequence + the new
  job ≤ 50 in practice).
* **Optimization correctness vs determinism.** ORS VROOM optimization is deterministic given
  the same input but the input includes timestamps that we generate. Tests use the stub
  adapter for service-level determinism; the ORS-live integration test only asserts shape and
  monotonicity (e.g. `total_duration_s > 0`).
* **Empty existing sequences (v1).** Until Slice 15 commits Routes, every vehicle's
  `existing_sequence` is empty. Strategies will collapse: `nearest` reduces to "vehicle closest
  to the new job"; `earliest` becomes "vehicle whose home base + travel arrives soonest";
  `balanced` becomes "vehicle whose lone-job load is closest to the median (i.e., basically a
  tie among all vehicles)". **OPEN QUESTION:** is a single-job v1 worth shipping? Stakeholder
  alignment needed; flagged in PR. Mitigation: ship now to unblock Slice 14 UI; revisit
  ranking quality once Slice 15 is in.
* **Vehicle current position fallback to home base.** Honest about the v1 limitation in API
  schema docstrings and response notes (`option.notes: ["Vehicle position is home_base; live
  tracking not yet enabled."]`).
* **ORS health endpoint path.** The exact `/v2/health` path has changed across ORS versions;
  implementer must verify against the ORS version at integration time and document in
  `adapters/routing/ors.py`. Marked as a code-review checklist item.
* **Audit payload privacy.** The audit event records job_id + vehicle_ids only — no
  coordinates, no customer info. ADR 063 alignment.

---

Once approved, implementation proceeds adapter-first: types + protocol + stub + tests (full
green), then the ORS adapter with httpx mocks (no live calls in CI), then `RoutingService`
with ranking strategies (TDD with the stub), then the API route + error handlers, then the
`routing` rate-limit seed. The optional Dockerized ORS test runs manually before merge to
sanity-check the live wiring.
