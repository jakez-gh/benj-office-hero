---
docType: slice-design
parent: ../project-guides/003-slices.office-hero.md
project: office-hero
slice: technician-web
dateCreated: 20260530
dateUpdated: 20260530
status: in_progress
---

# Slice Design 022: Technician Web View

Delivers a lightweight React web app (`apps/tech-web`) where a Technician can see
their assigned jobs for the day, view job details, and enter a new field job.
Runs in a browser — no native app required. Implements **Slice 22** of the master
slice plan.

## User Story

> As a Technician, I open a browser link on my phone or laptop, log in, and
> immediately see the jobs I'm assigned to today — what time, where, what to do.
> I can tap a job to see full details and, if needed, enter a new job from the
> field.

## What Will Be Built

### Backend additions

- `GET /vehicles/my-crew-today` — returns the Technician's active `VehicleCrew`
  entry for today (vehicle_id + crew_date). Returns 404 if none assigned.
- `GET /jobs` already exists; add filter support for `assigned_vehicle_id` and
  `scheduled_for_date` (YYYY-MM-DD) to scope to a vehicle's jobs for a given day.

### `apps/tech-web` (React + TypeScript + Vite)

Reuse the pnpm monorepo shared packages (`packages/api-client`, `packages/types`).
Add a minimal new Vite app with Tailwind v3.

**Pages:**
- **Login** — reuse the same JWT auth flow as admin-web. On success, redirect to
  `/today`.
- **Today** (`/today`) — main screen.
  - Fetches `GET /vehicles/my-crew-today` to get `vehicle_id`.
  - Fetches `GET /jobs?assigned_vehicle_id=<id>&scheduled_for_date=<today>`.
  - Displays a vertical list of jobs sorted by `scheduled_for` time.
  - Each row: time, customer name (from job title), service type, status badge.
  - Tap → JobDetail sheet.
- **JobDetail** (slide-over or full page) — shows all job fields, customer/
  location IDs, notes, priority, duration. "Mark in progress" button transitions
  job status (`pending`/`scheduled` → `in_progress`) via `PATCH /jobs/{id}`.
- **NewJob** (`/jobs/new`) — minimal form: title, customer_id, location_id,
  service type, duration. Calls `POST /jobs`. Returns to Today on success.

### Auth & RBAC

- Login uses the same `POST /auth/login` JWT endpoint.
- The `GET /vehicles/my-crew-today` endpoint requires `vehicle:read` permission
  (Technician role has it).
- `GET /jobs` with vehicle filter requires `job:read`.
- `PATCH /jobs/{id}/status` (new) requires `job:write`, limited to transitions
  the requesting role is permitted (Technician: `scheduled → in_progress`,
  `in_progress → completed`).

## Dependencies

- Slice 5 (frontend scaffold) — `apps/tech-web` exists ✓
- Slice 5a (admin web shell) — auth pattern to copy ✓
- Slice 8 (user management) — JWT roles ✓
- Slice 10 (job management) — `GET /jobs`, `POST /jobs` ✓
- Slice 12 (vehicle/crew) — `VehicleCrew` model, needed for vehicle lookup ✓
- Slice 20 (schedule UI / dispatch) — jobs have `assigned_vehicle_id` ✓

## Out of Scope

- Route/RouteStop model (Slice 14 full) — this slice uses job-level vehicle
  assignment instead, which is sufficient for MVP
- Location tracking (Slice 15)
- Native Android app (Slice 17–18)

## New Backend Endpoints

| Method | Path                          | Permission    | Notes                                    |
| ------ | ----------------------------- | ------------- | ---------------------------------------- |
| GET    | /vehicles/my-crew-today       | vehicle:read  | Returns crew entry for caller's user_id  |
| GET    | /jobs (extended)              | job:read      | Add assigned_vehicle_id + date filters   |
| PATCH  | /jobs/{id}/status             | job:write     | Technician status transitions only       |

## PR

- PR to be opened on `feat/slice-22-technician-web`
