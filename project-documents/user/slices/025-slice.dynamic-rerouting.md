---
docType: slice-design
parent: ../project-guides/003-slices.office-hero.md
project: office-hero
dateCreated: 20260613
dateUpdated: 20260613
status: complete
slice: dynamic-rerouting
---

# Slice Design 025: Dynamic re-routing (day-of exceptions)

Implements **Slice 16** of the master plan and closes the last unbuilt clause of the
original concept: route trucks *"adapting to real-world events like sick-days or
emergencies."* New-contract routing (slices 13–14) and manual override (slice 14+)
already exist; this slice adds day-of re-planning.

Two operations, matching the concept's two named events, plus the job-cancellation
gap they expose:

## 1. Reassign a route — "technician sick / vehicle down"

`DynamicDispatchService.reassign_route(tenant_id, user_id, route_id, *, target_vehicle_id)`

* Source route must exist and be `committed` or `in_progress` (not terminal).
* Target vehicle must differ from the source and have a crew for the route's
  `work_date`; otherwise `RouteCommitConflictError` (409).
* Partition source stops: terminal stops (`arrived`/`complete`/`skipped`) stay on the
  source route as history; **pending** stops move.
* If there are no pending stops → 409 ("nothing to reassign").
* Append the moved jobs to the target vehicle's route for that date (creating the route
  if absent; 409 if the target route is already terminal), preserving order and planned
  metrics, sequenced after any existing target stops.
* Skip the moved stops on the source, then finalise the source route: `complete` if it
  has completed stops, else `cancelled` (reason `reassigned to vehicle …`).
* Returns `{source_route, target_route, moved_count}`; audits `route.reassigned`.

## 2. Emergency dispatch — "emergency job added"

`DynamicDispatchService.add_emergency_job(tenant_id, user_id, job_id, *,
target_vehicle_id=None, window_start, window_end)`

* Job must exist and be `pending`.
* Resolve the vehicle: explicit `target_vehicle_id`, else the top-ranked vehicle from
  `ScheduleSuggestionService.get_options` for the window. No target and no options → 409.
* Target vehicle must have a crew today; get/create its route for today.
* Insert the emergency job at the **front of the pending queue** (after any
  arrived/in-progress stop) — emergencies jump the line — and reindex.
* Job → `scheduled`, `assigned_vehicle_id` set. Returns `{route, inserted_stop_id, job}`;
  audits `job.emergency_dispatched`.

## 3. Job-cancellation hook (deferred)

When a job already on a route is cancelled its open stop should be skipped and the
route auto-finalised. This needs a "routes containing job" repo lookup plus a
`JobService.cancel` callback seam, so it is **deferred to a follow-up** to keep this
slice focused on the two headline day-of events. Tracked here as future work.

## API

* `POST /routes/{route_id}/reassign` — `route:write`. Body `RouteReassignRequest
  {target_vehicle_id}`. Returns `RouteReassignResponse {source, target, moved_count}`.
* `POST /jobs/{job_id}/emergency-dispatch` — `jobs:dispatch` + `route:write`. Body
  `EmergencyDispatchRequest {target_vehicle_id?, window_start?, window_end?}`. Returns
  `RouteRead` (the route the job landed on).

Wired in `api/app.py`; `DynamicDispatchService` shares the route/stop/job/vehicle/crew
repos and the schedule service with the existing dispatch services.

## Frontend (admin-web)

Routes page: a **Reassign** action on `committed`/`in_progress` route cards → modal to
pick a target vehicle → `reassignRouteApi`. The two affected routes refresh in place.

## Tests

* `tests/services/test_dynamic_dispatch_service.py` — reassign (moves pending, keeps
  terminal, finalises source, target-no-crew 409, terminal-source 409, nothing-to-move
  409, cross-tenant); emergency (auto-pick best, explicit target, front-insert
  ordering, no-options 409, job-not-pending 409); cancellation hook skips the stop.
* `tests/api/test_dynamic_rerouting_api.py` — both endpoints: RBAC, happy path,
  conflicts, tenant isolation.
* admin-web Jest: Reassign modal renders + calls the API.

## Dependencies

Slices 12 (vehicles/crews), 13 (schedule suggestions), 14 (routes/stops + DispatchService).
ADRs 053, 058, 063. Risk: High (the master plan's highest-effort feature slice). Effort: 4/5.

## Risk callouts

* **In-progress source routes** carry real completed work; reassign only moves pending
  stops and never rewrites history (arrived/completed stops stay put).
* **Emergency front-insert** preserves any already-arrived stop at index 0 so a
  technician mid-visit isn't reordered under them.
* **Concurrency** — same single-instance assumption as contract generation; two
  simultaneous reassigns of the same route can race. Documented; revisit with row locks.
