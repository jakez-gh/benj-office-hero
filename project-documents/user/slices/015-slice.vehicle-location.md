---
docType: slice-design
parent: ../project-guides/003-slices.office-hero.md
project: office-hero
slice: vehicle-location
dateCreated: 20260530
dateUpdated: 20260530
status: in_progress
---

# Slice Design 015: Vehicle Location Tracking

Delivers `PUT /vehicles/{id}/location` — technicians post their current GPS
position from the field, enabling the routing engine to use live positions
rather than defaulting to depot. Implements **Slice 15** of the master slice plan.

## User Story

> As a Technician driving between jobs, my app periodically posts my GPS
> position. When the dispatcher triggers routing, the engine uses my current
> location rather than the depot address, producing tighter route options.

## What Will Be Built

### Data model

New table **`vehicle_locations`** (time-series):

| Column         | Type                     | Notes                          |
| -------------- | ------------------------ | ------------------------------ |
| id             | UUID PK                  |                                |
| tenant_id      | UUID NOT NULL            | RLS scope                      |
| vehicle_id     | UUID NOT NULL            | FK → vehicles.id               |
| lat            | DECIMAL(9,6) NOT NULL    |                                |
| lng            | DECIMAL(9,6) NOT NULL    |                                |
| accuracy_m     | DECIMAL(8,2)             | GPS accuracy in metres         |
| recorded_at    | TIMESTAMPTZ NOT NULL     | client-side timestamp          |
| created_at     | TIMESTAMPTZ DEFAULT NOW  | server receipt time            |

Index on `(tenant_id, vehicle_id, recorded_at DESC)` for efficient latest-position lookup.

No FK enforce on `vehicle_id` to allow async writes without locking the vehicles table.

### Alembic migration

`0008_vehicle_locations.py` — creates the table and index.

### Repository

`VehicleLocationRepository` protocol + SQLAlchemy impl + InMemory impl:

- `create(tenant_id, vehicle_id, lat, lng, accuracy_m, recorded_at)` → `VehicleLocation`
- `get_latest(tenant_id, vehicle_id)` → `VehicleLocation | None`

### Service

`VehicleLocationService`:

- `record(tenant_id, vehicle_id, *, lat, lng, accuracy_m, recorded_at)` → validates vehicle
  exists in tenant before writing, raises `VehicleNotFoundError` if not.

### API

`PUT /vehicles/{vehicle_id}/location`

- Permission: `vehicle:write` (Technician role has it)
- Rate-limited: `120/minute` (higher than most endpoints — GPS updates are frequent)
- Request body:
  ```json
  { "lat": 37.7749, "lng": -122.4194, "accuracy_m": 5.0, "recorded_at": "2026-05-30T14:00:00Z" }
  ```
- Response: `200` with the stored location record
- `recorded_at` is `AwareDatetime` (rejects naive timestamps)
- Returns `404` if vehicle not found in tenant

### Routing engine integration

Update `RoutingAdapter` / `ScheduleSuggestionService` to call
`VehicleLocationRepository.get_latest` when building routing requests —
uses the stored lat/lng as vehicle start position instead of a static depot.
Fall back to depot coordinates if no location has been recorded.

## Dependencies

- Slice 2 (DB foundation) ✓
- Slice 12 (Vehicle management) ✓
- Slice 13 (Routing engine) ✓ — location data feeds into it

## Out of Scope

- Location history query endpoint (not needed for routing)
- WebSocket or SSE push (polling is sufficient for MVP)
- Geofencing or alerts

## PR

- PR to be opened on `feat/slice-15-vehicle-location`
