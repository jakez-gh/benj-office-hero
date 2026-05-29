---
docType: slice-design
parent: ../project-guides/003-slices.office-hero.md
project: office-hero
slice: schedule-ui
dateCreated: 20260528
dateUpdated: 20260529
status: complete
---

# Slice Design 016: Tenant Admin Web — Job Entry & Schedule UI

This slice delivers the sales-rep scheduling flow in the admin web: look up or create a
customer/job, fetch ranked vehicle slots from the routing engine, pick one, and confirm
dispatch. It implements **Slice 20** of the master slice plan.

It builds directly on Slice 13 (`POST /jobs/{id}/schedule-options`) and Slice 14
(`POST /jobs/{id}/dispatch`) which are now merged to main.

## User Story

> As a sales rep, I receive a new service call. I open the admin web, find or create the
> customer, enter the job, see ranked truck options with travel times, pick the best slot,
> and confirm — all without leaving the Jobs list view.

## What Was Built

- **`ScheduleModal`** in `apps/admin-web/src/pages/JobsPage.tsx`
  - "Schedule" action button appears on every `pending` job row
  - Modal opens with default window: tomorrow 8am–5pm (local time)
  - User adjusts window if needed, then clicks "Find available slots"
  - Calls `POST /jobs/{id}/schedule-options` → renders ranked option cards
  - Each card shows: rank, vehicle display name, travel time, suggested start time
  - User selects a card; "Confirm booking" calls `POST /jobs/{id}/dispatch`
  - On success: modal closes, row updates in-place (status → `scheduled`, time shown)
  - Errors surface inline in the modal (no full-page reload)

- **`apps/admin-web/src/api.ts`** additions:
  - `getScheduleOptionsApi(jobId, { window_start, window_end, max_results })`
  - `dispatchJobApi(jobId, { vehicle_id, scheduled_for })`
  - Types: `ScheduleOptionItem`, `ScheduleOptionsResponse`, `ScheduleOptionsRequest`,
    `DispatchRequest`, `DispatchResponse`

## PR

- PR #82 (`feat/slice-20-schedule-ui`) — open, CI running

## Dependencies

- Slice 13 (routing engine) — merged ✓
- Slice 14 (dispatch endpoint) — PR #80, merging imminently
- Slice 5a (admin web shell) — merged ✓
- Slice 10 (job management) — merged ✓

## Out of Scope for This Slice

- Customer/location creation flow (the modal assumes IDs are known)
- Dispatch dashboard (Slice 21)
- Mobile job entry (Slice 19)
