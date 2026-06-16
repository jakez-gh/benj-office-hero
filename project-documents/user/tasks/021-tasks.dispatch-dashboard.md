---
slice: dispatch-dashboard
project: office-hero
lld: user/slices/021-slice.dispatch-dashboard.md
dependencies: [12, 13, 14, 15, 16, 20]
projectState: >
  Dispatch dashboard fully implemented. Routes page provides the per-day route
  board, drag-and-drop stop resequencing, live GPS polling, start/cancel/reassign
  actions. All slice 21 items are complete.
dateCreated: 20260616
dateUpdated: 20260616
status: complete
docType: tasks
---

## Context Summary

Slice 21 builds the Tenant Admin route board for daily dispatch operations.
The Routes page replaced the placeholder and now provides full dispatch-day
functionality. Day-of exception handling is covered by the Reassign modal
(slice 025/16).

---

## Task Breakdown

### Routes page — board view

- [x] `apps/admin-web/src/pages/RoutesPage.tsx` — full route board:
  date picker, per-vehicle RouteCard list, summary stats (stops, travel time, distance)
- [x] `apps/admin-web/src/api.ts` — `listRoutesApi`, `getRouteApi`, `resequenceRouteApi`,
  `startRouteApi`, `cancelRouteApi`, `reassignRouteApi`
- [x] Nav registration (Routes link in NavShell)

### Stop resequencing

- [x] ↑↓ move-up / move-down buttons with aria labels + tooltips (committed routes)
- [x] "Save new order" / "Discard order" controls when unsaved changes exist
- [x] HTML5 native drag-and-drop: ⠿ grab handle + blue drop-target highlight
- [x] `POST /routes/{id}/resequence` wired to both DnD and ↑↓ flows
- [x] Hint text: "Drag stops or use ↑↓ to reorder before starting."

### Live vehicle positions

- [x] `api.ts` — `VehicleLocationResponse` type + `getVehicleLatestLocationApi`
- [x] `useVehicleLocation(vehicleId, enabled)` — polls `GET /vehicles/{id}/location`
  every 30s; cleans up on unmount; silently ignores 404 (no fix yet)
- [x] RouteCard header shows "· GPS X min ago" when an in_progress route has a fix

### Route lifecycle actions

- [x] "Start route" button (committed → in_progress)
- [x] CancelRouteModal with free-text reason (all terminal statuses)
- [x] ReassignRouteModal — move pending stops to another vehicle
  (covered by slice 025; design: 025-slice.dynamic-rerouting.md)
- [x] `onUpdated` upsert: reassign can surface a freshly-created target route

### Day-of exception handling UI

- [x] Reassign modal satisfies "technician sick / vehicle down" flow
- [x] Emergency dispatch accessible from Jobs page ("Emergency dispatch" per job)
