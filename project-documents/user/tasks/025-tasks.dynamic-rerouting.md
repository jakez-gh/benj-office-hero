---
slice: dynamic-rerouting
project: office-hero
lld: user/slices/025-slice.dynamic-rerouting.md
dependencies: [12, 13, 14]
projectState: >
  Dynamic re-routing fully implemented. DynamicDispatchService handles
  reassign_route and add_emergency_job. Both API endpoints and admin-web
  Reassign modal are complete. Job-cancellation hook is deferred.
  Verified passing in the 506-test suite.
dateCreated: 20260616
dateUpdated: 20260616
status: complete
docType: tasks
---

## Context Summary

Slice 025 implements day-of re-planning: reassign a route when a technician
is sick or a vehicle breaks down, and insert emergency jobs at the front of
the pending queue. Both operations are complete. The job-cancellation hook
(auto-skip open stop when a routed job is cancelled) is explicitly deferred.

---

## Task Breakdown

### Backend

- [x] `services/dynamic_dispatch_service.py` — `DynamicDispatchService`
  - [x] `reassign_route(tenant_id, user_id, route_id, *, target_vehicle_id)` — moves pending stops, keeps terminal history, finalises source, 409 on conflicts
  - [x] `add_emergency_job(tenant_id, user_id, job_id, *, target_vehicle_id, window_start, window_end)` — front-queue insert on target vehicle route, audits `job.emergency_dispatched`
- [x] `api/routes/routes.py` — `POST /routes/{id}/reassign` (route:write)
- [x] `api/routes/dispatch.py` / jobs routes — `POST /jobs/{id}/emergency-dispatch` (jobs:dispatch + route:write)
- [x] `api/schemas/route.py` — RouteReassignRequest, RouteReassignResponse
- [x] Wired into `api/app.py`

### Tests

- [x] `tests/services/test_dynamic_dispatch_service.py` — reassign (moves pending, keeps terminal, finalises source, no-crew 409, terminal-source 409, nothing-to-move 409, cross-tenant); emergency (auto-pick, explicit target, front-insert, no-options 409, job-not-pending 409)
- [x] `tests/api/test_dynamic_rerouting_api.py` — both endpoints: RBAC, happy path, conflicts, tenant isolation

### Frontend

- [x] `apps/admin-web/src/pages/RoutesPage.tsx` — Reassign action on committed/in_progress route cards → ReassignRouteModal (target vehicle picker) → `reassignRouteApi` → both routes refresh

### Deferred

- [ ] **Job-cancellation hook** — when a routed job is cancelled, auto-skip its open stop and finalise the route if all stops are terminal. Requires `routes_containing_job` repo lookup + `JobService.cancel` callback seam. Tracked here as future work; not blocking any current slice.
