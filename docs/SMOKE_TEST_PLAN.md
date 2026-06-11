# Office Hero MVP — Staging Smoke Test Plan

**Target:** Slices 14–15 (Dispatch & Route Management, Vehicle Location Tracking)
**Scope:** Golden path + critical edge cases + RBAC + idempotency
**Duration:** ~30 min per full run
**Environment:** Staging (PostgreSQL + API server running)

---

## Test Execution Environment

### Prerequisites

- [ ] API running on `http://localhost:8000` (or staging URL)
- [ ] PostgreSQL database seeded with test tenants, users, vehicles, crews, jobs
- [ ] JWT/auth middleware configured (test headers: `X-Test-Tenant-Id`, `X-Test-User-Id`, `X-Test-Permissions`)
- [ ] Rate limiter isolated per test run (reuse `_reset_rate_limiter` fixture)
- [ ] Test data: 2 tenants, 3 users per tenant (admin/dispatcher/technician roles), 3 vehicles, 2 crews per vehicle, 5 sample jobs

### Setup Fixtures

```python
# Reuse from tests/api/test_dispatch_api.py for auth simulation
TENANT_ID = "550e8400-e29b-41d4-a716-446655440000"
USER_DISPATCHER = "550e8400-e29b-41d4-a716-446655440001"
USER_TECHNICIAN = "550e8400-e29b-41d4-a716-446655440002"
USER_NO_PERMS = "550e8400-e29b-41d4-a716-446655440099"

VEHICLE_ID = "550e8400-e29b-41d4-a716-446655550000"
JOB_IDS = [
    "550e8400-e29b-41d4-a716-446655660000",  # PENDING
    "550e8400-e29b-41d4-a716-446655660001",  # PENDING
    "550e8400-e29b-41d4-a716-446655660002",  # PENDING
    "550e8400-e29b-41d4-a716-446655660003",  # Already COMPLETE (error case)
]

CREW_ID = "550e8400-e29b-41d4-a716-446655770000"
WORK_DATE = "2026-06-02"  # Today (must match crew assignment)
```

---

## Phase 1: Environment Validation & Setup

### 1.1 Health Check

**Test:** `GET /health`

```bash
curl -s http://localhost:8000/health | jq '.'
```

**Expected:** `{"status": "healthy"}`
**Validation:** API is responding
**Dependencies:** None

---

### 1.2 Database & RLS Policy Check

**Test:** Verify row-level security is enabled and tenant isolation works

```sql
-- Run against staging DB
SELECT relname, rls_enabled FROM pg_class
WHERE relname IN ('routes', 'route_stops', 'vehicle_locations', 'jobs');

SELECT * FROM routes WHERE tenant_id != $1 LIMIT 1;
-- Should return 0 rows (isolation working)
```

**Expected:** All tables have RLS enabled; tenant isolation enforced
**Validation:** Query returns empty result set when filtering by different tenant
**Dependencies:** None

---

### 1.3 Constraints & Indexes Check

**Test:** Verify critical indexes exist

```sql
SELECT indexname FROM pg_indexes
WHERE tablename = 'routes' AND indexname LIKE '%vehicle%date%';

SELECT indexname FROM pg_indexes
WHERE tablename = 'route_stops' AND indexname LIKE '%route%sequence%';
```

**Expected:** Indexes for vehicle+date, route+sequence exist
**Validation:** Both queries return non-empty results
**Dependencies:** None

---

### 1.4 Test User/Tenant Setup

**Test:** Create or verify test tenant and users in database

```bash
# Insert test tenant
INSERT INTO tenants (id, name) VALUES ($TENANT_ID, 'Smoke Test Tenant')
  ON CONFLICT DO NOTHING;

# Insert test users
INSERT INTO users (id, tenant_id, email, role)
VALUES
  ($USER_DISPATCHER, $TENANT_ID, 'dispatcher@test.local', 'dispatcher'),
  ($USER_TECHNICIAN, $TENANT_ID, 'tech@test.local', 'technician')
  ON CONFLICT DO NOTHING;
```

**Expected:** Users created with roles and permissions attached
**Validation:** Query returns exact user/tenant/role records
**Dependencies:** None (prerequisite for all remaining tests)

---

### 1.5 Vehicle & Crew Setup

**Test:** Verify vehicle and crew assignments exist for test date

```bash
# Vehicle must exist
SELECT * FROM vehicles WHERE id = $VEHICLE_ID AND tenant_id = $TENANT_ID;

# Crew must be assigned for WORK_DATE
SELECT * FROM vehicle_crews
WHERE vehicle_id = $VEHICLE_ID AND work_date = $WORK_DATE;
```

**Expected:** One vehicle, one crew for test date
**Validation:** Both queries return exactly 1 row
**Dependencies:** 1.4 (test tenant/user setup)

---

### 1.6 Test Jobs Setup

**Test:** Verify test jobs exist in correct states

```bash
SELECT id, status FROM jobs WHERE id = ANY($JOB_IDS) ORDER BY id;
```

**Expected:** First 3 jobs are PENDING; job[3] is COMPLETE
**Validation:** Status matches expectations above
**Dependencies:** 1.4 (test tenant setup)

---

## Phase 2: Golden Path — Full Dispatch Lifecycle

### 2.1 Dispatch Job (POST /jobs/{job_id}/dispatch)

**Test:** Dispatch first job to vehicle

```bash
curl -X POST http://localhost:8000/jobs/$JOB_IDS[0]/dispatch \
  -H "X-Test-Tenant-Id: $TENANT_ID" \
  -H "X-Test-User-Id: $USER_DISPATCHER" \
  -H "X-Test-Permissions: job:write,vehicle:read" \
  -H "Content-Type: application/json" \
  -d '{
    "vehicle_id": "'$VEHICLE_ID'",
    "scheduled_for": "2026-06-02T09:00:00Z"
  }'
```

**Expected:** 200 OK

```json
{
  "id": "$JOB_IDS[0]",
  "status": "scheduled",
  "assigned_vehicle_id": "$VEHICLE_ID",
  "scheduled_for": "2026-06-02T09:00:00Z",
  "title": "...",
  "customer_id": "...",
  "location_id": "..."
}
```

**Validation:**

- Status is "scheduled" (job transitioned from PENDING)
- Response contains all required fields
- HTTP 200 (not 201 — existing job, status change only)

**Dependencies:** 1.4, 1.5, 1.6

---

### 2.2 Create Route via Dispatch (POST /jobs/{job_id}/commit-dispatch)

**Test:** Commit a dispatch option (or manual) to create a Route

```bash
curl -X POST http://localhost:8000/jobs/$JOB_IDS[0]/commit-dispatch \
  -H "X-Test-Tenant-Id: $TENANT_ID" \
  -H "X-Test-User-Id: $USER_DISPATCHER" \
  -H "X-Test-Permissions: job:write,vehicle:read,route:write" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2026-06-02",
    "option_kind": "nearest"
  }'
```

**Expected:** 200 OK

```json
{
  "id": "route-uuid",
  "tenant_id": "$TENANT_ID",
  "vehicle_id": "$VEHICLE_ID",
  "vehicle_crew_id": "$CREW_ID",
  "work_date": "2026-06-02",
  "status": "committed",
  "stops": [
    {
      "id": "stop-uuid",
      "route_id": "route-uuid",
      "job_id": "$JOB_IDS[0]",
      "sequence_index": 0,
      "status": "pending"
    }
  ],
  "option_kind_applied": "nearest",
  "committed_by_user_id": "$USER_DISPATCHER"
}
```

**Validation:**

- Route status is "committed"
- Single stop with job_id = $JOB_IDS[0]
- Crew assignment captured
- Response includes all stops array

**Dependencies:** 2.1 (job dispatched first)

**Save for later:** `ROUTE_ID = response.id`, `STOP_ID = response.stops[0].id`

---

### 2.3 List Routes (GET /routes)

**Test:** Query routes for the work date

```bash
curl -s "http://localhost:8000/routes?date=2026-06-02&vehicle_id=$VEHICLE_ID" \
  -H "X-Test-Tenant-Id: $TENANT_ID" \
  -H "X-Test-User-Id: $USER_DISPATCHER" \
  -H "X-Test-Permissions: route:read" \
  | jq '.items[] | {id, status, vehicle_id, work_date}'
```

**Expected:** 200 OK, array with at least the route from 2.2

```json
{
  "items": [
    {
      "id": "$ROUTE_ID",
      "status": "committed",
      "vehicle_id": "$VEHICLE_ID",
      "work_date": "2026-06-02"
    }
  ],
  "total": 1
}
```

**Validation:**

- Route appears in list with correct status
- Filters work: vehicle_id, date
- Total count is accurate

**Dependencies:** 2.2 (route created)

---

### 2.4 Get Route by ID (GET /routes/{route_id})

**Test:** Fetch full route details

```bash
curl -s http://localhost:8000/routes/$ROUTE_ID \
  -H "X-Test-Tenant-Id: $TENANT_ID" \
  -H "X-Test-User-Id: $USER_DISPATCHER" \
  -H "X-Test-Permissions: route:read" \
  | jq '.'
```

**Expected:** 200 OK with full RouteRead schema

```json
{
  "id": "$ROUTE_ID",
  "status": "committed",
  "stops": [
    {
      "id": "$STOP_ID",
      "job_id": "$JOB_IDS[0]",
      "status": "pending"
    }
  ],
  ...
}
```

**Validation:**

- All nested stops present
- Status field present and correct
- Crew and vehicle summary objects populated

**Dependencies:** 2.2

---

### 2.5 Start Route (POST /routes/{route_id}/start)

**Test:** Transition route from committed → in_progress

```bash
curl -X POST http://localhost:8000/routes/$ROUTE_ID/start \
  -H "X-Test-Tenant-Id: $TENANT_ID" \
  -H "X-Test-User-Id: $USER_TECHNICIAN" \
  -H "X-Test-Permissions: route:write" \
  -H "Content-Type: application/json"
```

**Expected:** 200 OK

```json
{
  "id": "$ROUTE_ID",
  "status": "in_progress",
  "started_at": "2026-06-02T...",
  "stops": [...]
}
```

**Validation:**

- Status changed to "in_progress"
- started_at timestamp is recent (within 10 seconds)
- Stops unchanged

**Dependencies:** 2.4

---

### 2.6 Mark Stop Arrived (POST /routes/{route_id}/stops/{stop_id}/arrived)

**Test:** Technician marks first stop as arrived

```bash
curl -X POST http://localhost:8000/routes/$ROUTE_ID/stops/$STOP_ID/arrived \
  -H "X-Test-Tenant-Id: $TENANT_ID" \
  -H "X-Test-User-Id: $USER_TECHNICIAN" \
  -H "X-Test-Permissions: route:write" \
  -H "Content-Type: application/json"
```

**Expected:** 200 OK

```json
{
  "id": "$ROUTE_ID",
  "status": "in_progress",
  "stops": [
    {
      "id": "$STOP_ID",
      "status": "arrived",
      "actual_arrived_at": "2026-06-02T..."
    }
  ]
}
```

**Validation:**

- Stop status is "arrived"
- actual_arrived_at is set and recent
- Route status still "in_progress"

**Dependencies:** 2.5 (route must be in_progress)

---

### 2.7 Update Vehicle Location (PUT /vehicles/{vehicle_id}/location)

**Test:** Technician app records GPS location

```bash
curl -X PUT http://localhost:8000/vehicles/$VEHICLE_ID/location \
  -H "X-Test-Tenant-Id: $TENANT_ID" \
  -H "X-Test-User-Id: $USER_TECHNICIAN" \
  -H "X-Test-Permissions: location:write" \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 40.7128,
    "longitude": -74.0060,
    "accuracy_meters": 8,
    "recorded_at": "2026-06-02T12:30:00Z"
  }'
```

**Expected:** 201 Created

```json
{
  "id": "location-uuid",
  "vehicle_id": "$VEHICLE_ID",
  "latitude": 40.7128,
  "longitude": -74.0060,
  "accuracy_meters": 8,
  "recorded_at": "2026-06-02T12:30:00Z",
  "created_at": "2026-06-02T..."
}
```

**Validation:**

- Location record created with all fields
- Coordinates valid (within bounds)
- created_at is recent

**Dependencies:** 1.5 (vehicle exists)

---

### 2.8 Get Latest Vehicle Location (GET /vehicles/{vehicle_id}/location)

**Test:** Query latest location for vehicle

```bash
curl -s http://localhost:8000/vehicles/$VEHICLE_ID/location \
  -H "X-Test-Tenant-Id: $TENANT_ID" \
  -H "X-Test-User-Id: $USER_TECHNICIAN" \
  -H "X-Test-Permissions: location:read" \
  | jq '.'
```

**Expected:** 200 OK with latest location from 2.7

```json
{
  "id": "location-uuid",
  "vehicle_id": "$VEHICLE_ID",
  "latitude": 40.7128,
  "longitude": -74.0060,
  "accuracy_meters": 8,
  "recorded_at": "2026-06-02T12:30:00Z",
  "created_at": "..."
}
```

**Validation:**

- Returned location matches most recent from 2.7
- Coordinates exact match

**Dependencies:** 2.7 (location recorded)

---

### 2.9 Mark Stop Complete (POST /routes/{route_id}/stops/{stop_id}/complete)

**Test:** Technician completes first (only) stop

```bash
curl -X POST http://localhost:8000/routes/$ROUTE_ID/stops/$STOP_ID/complete \
  -H "X-Test-Tenant-Id: $TENANT_ID" \
  -H "X-Test-User-Id: $USER_TECHNICIAN" \
  -H "X-Test-Permissions: route:write" \
  -H "Content-Type: application/json"
```

**Expected:** 200 OK

```json
{
  "id": "$ROUTE_ID",
  "status": "complete",
  "stops": [
    {
      "id": "$STOP_ID",
      "status": "complete",
      "actual_completed_at": "2026-06-02T..."
    }
  ],
  "completed_at": "2026-06-02T..."
}
```

**Validation:**

- Stop status is "complete"
- actual_completed_at is set and recent
- **Route auto-transitioned to "complete"** (because all stops are terminal)
- Route completed_at timestamp is set

**Dependencies:** 2.6 (stop must be "arrived")

---

## Phase 3: Edge Cases & RBAC

### 3.1 Permission Denied — route:read only

**Test:** Attempt to modify route without write permission

```bash
curl -X POST http://localhost:8000/routes/$ROUTE_ID/start \
  -H "X-Test-Tenant-Id: $TENANT_ID" \
  -H "X-Test-User-Id: $USER_DISPATCHER" \
  -H "X-Test-Permissions: route:read" \
  -H "Content-Type: application/json"
```

**Expected:** 403 Forbidden

```json
{
  "detail": "Insufficient permissions"
}
```

**Validation:** Request rejected due to missing route:write
**Dependencies:** Any route exists (use one from Phase 2)

---

### 3.2 Permission Denied — location:write missing

**Test:** Technician without location:write cannot record GPS

```bash
curl -X PUT http://localhost:8000/vehicles/$VEHICLE_ID/location \
  -H "X-Test-Tenant-Id: $TENANT_ID" \
  -H "X-Test-User-Id: $USER_DISPATCHER" \
  -H "X-Test-Permissions: route:write" \
  -H "Content-Type: application/json" \
  -d '{"latitude": 40.7, "longitude": -74.0}'
```

**Expected:** 403 Forbidden
**Validation:** Request rejected
**Dependencies:** 1.5

---

### 3.3 Unauthorized — Missing Tenant ID

**Test:** Request without X-Test-Tenant-Id header

```bash
curl -s http://localhost:8000/routes \
  -H "X-Test-User-Id: $USER_DISPATCHER" \
  -H "X-Test-Permissions: route:read"
```

**Expected:** 401 Unauthorized
**Validation:** Rejected at middleware
**Dependencies:** None

---

### 3.4 Route Not Found

**Test:** Request non-existent route

```bash
curl -s http://localhost:8000/routes/00000000-0000-0000-0000-000000000000 \
  -H "X-Test-Tenant-Id: $TENANT_ID" \
  -H "X-Test-User-Id: $USER_DISPATCHER" \
  -H "X-Test-Permissions: route:read"
```

**Expected:** 404 Not Found

```json
{
  "detail": "Route not found"
}
```

**Validation:** Appropriate error response
**Dependencies:** None

---

### 3.5 Invalid Route Transition — Complete → Started

**Test:** Attempt illegal state transition (complete route cannot restart)

Setup: Create and complete a route (use Phase 2.1–2.9), then try:

```bash
curl -X POST http://localhost:8000/routes/$COMPLETED_ROUTE_ID/start \
  -H "X-Test-Tenant-Id: $TENANT_ID" \
  -H "X-Test-User-Id: $USER_TECHNICIAN" \
  -H "X-Test-Permissions: route:write" \
  -H "Content-Type: application/json"
```

**Expected:** 422 Unprocessable Entity

```json
{
  "detail": "Cannot transition from complete to in_progress"
}
```

**Validation:** State machine enforced at service layer
**Dependencies:** Completed route from Phase 2

---

### 3.6 Invalid Stop Transition — Complete → Arrived

**Test:** Attempt reverse transition

Setup: Complete a stop, then try to mark arrived again:

```bash
curl -X POST http://localhost:8000/routes/$ROUTE_ID/stops/$COMPLETED_STOP_ID/arrived \
  -H "X-Test-Tenant-Id: $TENANT_ID" \
  -H "X-Test-User-Id: $USER_TECHNICIAN" \
  -H "X-Test-Permissions: route:write" \
  -H "Content-Type: application/json"
```

**Expected:** 422 Unprocessable Entity
**Validation:** Stop transition matrix enforced
**Dependencies:** Completed stop from Phase 2

---

### 3.7 Dispatch Terminal Job — Cannot Dispatch Completed Job

**Test:** Attempt to dispatch job with status=complete

```bash
curl -X POST http://localhost:8000/jobs/$JOB_IDS[3]/commit-dispatch \
  -H "X-Test-Tenant-Id: $TENANT_ID" \
  -H "X-Test-User-Id: $USER_DISPATCHER" \
  -H "X-Test-Permissions: job:write,vehicle:read,route:write" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2026-06-02",
    "option_kind": "nearest"
  }'
```

**Expected:** 409 Conflict

```json
{
  "detail": "Job ... is complete and cannot be dispatched"
}
```

**Validation:** Business logic prevents terminal job dispatch
**Dependencies:** 1.6 (job[3] is complete)

---

### 3.8 Cancel Route — Revert Scheduled Jobs to Pending

**Test:** Cancel a route with multiple pending stops

Setup: Create a new route with 2 jobs (manually sequence them), then cancel:

```bash
# Dispatch 2 jobs to same route
curl -X POST http://localhost:8000/jobs/$JOB_IDS[1]/commit-dispatch \
  -H "X-Test-Tenant-Id: $TENANT_ID" \
  -H "X-Test-User-Id: $USER_DISPATCHER" \
  -H "X-Test-Permissions: job:write,vehicle:read,route:write" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2026-06-03",
    "manual_vehicle_id": "'$VEHICLE_ID'",
    "manual_sequence": ["'$JOB_IDS[1]'", "'$JOB_IDS[2]'"]
  }'
  # Capture $CANCEL_ROUTE_ID

# Cancel the route
curl -X POST http://localhost:8000/routes/$CANCEL_ROUTE_ID/cancel \
  -H "X-Test-Tenant-Id: $TENANT_ID" \
  -H "X-Test-User-Id: $USER_DISPATCHER" \
  -H "X-Test-Permissions: route:write" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Customer reschedule due to emergency"}'
```

**Expected:** 200 OK

```json
{
  "id": "$CANCEL_ROUTE_ID",
  "status": "cancelled",
  "cancel_reason": "Customer reschedule due to emergency",
  "cancelled_at": "2026-06-02T...",
  "stops": [
    {
      "id": "...",
      "job_id": "$JOB_IDS[1]",
      "status": "skipped"
    },
    {
      "id": "...",
      "job_id": "$JOB_IDS[2]",
      "status": "skipped"
    }
  ]
}
```

**Validation:**

- Route status is "cancelled"
- All stops are "skipped"
- Verify in DB that associated jobs are back to PENDING:

  ```sql
  SELECT id, status FROM jobs WHERE id IN ($JOB_IDS[1], $JOB_IDS[2]);
  -- Expected: both PENDING
  ```

**Dependencies:** 1.6

---

### 3.9 Skip Single Stop (not full route cancel)

**Test:** Skip one stop in a multi-stop route (should not affect route status)

Setup: Route with 2 stops created but not yet started:

```bash
curl -X POST http://localhost:8000/routes/$ROUTE_ID/stops/$FIRST_STOP_ID/skip \
  -H "X-Test-Tenant-Id: $TENANT_ID" \
  -H "X-Test-User-Id: $USER_DISPATCHER" \
  -H "X-Test-Permissions: route:write" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Customer not available"}'
```

**Expected:** 200 OK

```json
{
  "id": "$ROUTE_ID",
  "status": "committed",  # Not auto-complete (other stops still pending)
  "stops": [
    {
      "id": "$FIRST_STOP_ID",
      "status": "skipped",
      "reason": "Customer not available"
    },
    {
      "id": "$SECOND_STOP_ID",
      "status": "pending"
    }
  ]
}
```

**Validation:**

- Single stop is skipped
- Route does NOT auto-complete (only one stop done, one pending)
- Reason captured in response

**Dependencies:** Multi-stop route created

---

## Phase 4: Database Integrity & Idempotency

### 4.1 Idempotency — Redispatch Same Sequence

**Test:** Commit same dispatch twice (should return cached route, not error)

Setup: Create route with jobs [A, B], then redispatch with same sequence:

```bash
ROUTE_ID_1=$(curl -X POST http://localhost:8000/jobs/A/commit-dispatch \
  -H "X-Test-Tenant-Id: $TENANT_ID" \
  -H "X-Test-User-Id: $USER_DISPATCHER" \
  -H "X-Test-Permissions: job:write,vehicle:read,route:write" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2026-06-04",
    "manual_vehicle_id": "'$VEHICLE_ID'",
    "manual_sequence": ["'$JOB_A'", "'$JOB_B'"]
  }' | jq -r '.id')

# Redispatch with identical sequence
ROUTE_ID_2=$(curl -X POST http://localhost:8000/jobs/A/commit-dispatch \
  -H "X-Test-Tenant-Id: $TENANT_ID" \
  -H "X-Test-User-Id: $USER_DISPATCHER" \
  -H "X-Test-Permissions: job:write,vehicle:read,route:write" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2026-06-04",
    "manual_vehicle_id": "'$VEHICLE_ID'",
    "manual_sequence": ["'$JOB_A'", "'$JOB_B'"]
  }' | jq -r '.id')
```

**Expected:**

- Both calls return HTTP 200
- ROUTE_ID_1 == ROUTE_ID_2 (same route returned)
- Response includes all 2 stops

**Validation:**

```sql
SELECT COUNT(*) FROM routes
WHERE vehicle_id = $VEHICLE_ID AND work_date = '2026-06-04';
-- Expected: 1 (not 2)

SELECT COUNT(*) FROM route_stops WHERE route_id = $ROUTE_ID_1;
-- Expected: 2 (stops not duplicated)
```

**Dependencies:** 1.5, 1.6

---

### 4.2 Atomicity — Rollback on Partial Failure

**Test:** Dispatch with manual sequence containing invalid job (should not create route)

```bash
curl -X POST http://localhost:8000/jobs/A/commit-dispatch \
  -H "X-Test-Tenant-Id: $TENANT_ID" \
  -H "X-Test-User-Id: $USER_DISPATCHER" \
  -H "X-Test-Permissions: job:write,vehicle:read,route:write" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2026-06-05",
    "manual_vehicle_id": "'$VEHICLE_ID'",
    "manual_sequence": ["'$JOB_A'", "00000000-0000-0000-0000-000000000000"]
  }'
```

**Expected:** 409 Conflict

```json
{
  "detail": "Manual sequence contains invalid jobs",
  "errors": [
    "job 00000000... not found in tenant"
  ]
}
```

**Validation:**

```sql
SELECT COUNT(*) FROM routes
WHERE vehicle_id = $VEHICLE_ID AND work_date = '2026-06-05';
-- Expected: 0 (transaction rolled back)
```

**Dependencies:** 1.5

---

### 4.3 RLS Isolation — Tenant Cannot See Other Tenant's Routes

**Test:** Query routes from different tenant

Setup: Create routes for TENANT_A, then query as TENANT_B:

```bash
curl -s "http://localhost:8000/routes?date=2026-06-02" \
  -H "X-Test-Tenant-Id: 00000000-0000-0000-0000-000000000002" \
  -H "X-Test-User-Id: $USER_DISPATCHER" \
  -H "X-Test-Permissions: route:read"
```

**Expected:** 200 OK with empty items array

```json
{
  "items": [],
  "total": 0
}
```

**Validation:**

- No routes visible (RLS working)
- No error; empty result is correct

**Dependencies:** Phase 2 (routes created in TENANT_ID)

---

### 4.4 Unique Constraint — One Route per Vehicle per Date

**Test:** Verify unique index on (tenant_id, vehicle_id, work_date)

```sql
SELECT constraint_name FROM information_schema.table_constraints
WHERE table_name = 'routes'
AND constraint_type = 'UNIQUE';
-- Should include constraint on (tenant_id, vehicle_id, work_date)
```

**Validation:** Constraint exists in schema
**Dependencies:** Database setup (Phase 1)

---

### 4.5 Referential Integrity — Delete Vehicle Cascade Behavior

**Test:** Verify foreign key constraint (should prevent orphans or cascade)

```sql
-- Verify routes.vehicle_id has FK to vehicles.id
SELECT constraint_name, delete_action FROM information_schema.referential_constraints
WHERE table_name = 'routes' AND column_name = 'vehicle_id';
```

**Expected:** Constraint exists with CASCADE or RESTRICT action
**Validation:** FK constraint present and correctly configured
**Dependencies:** Database setup

---

### 4.6 Location Recording — No Constraint Violations

**Test:** Record 10 location updates rapidly, verify all inserted

```bash
for i in {1..10}; do
  curl -X PUT http://localhost:8000/vehicles/$VEHICLE_ID/location \
    -H "X-Test-Tenant-Id: $TENANT_ID" \
    -H "X-Test-User-Id: $USER_TECHNICIAN" \
    -H "X-Test-Permissions: location:write" \
    -H "Content-Type: application/json" \
    -d '{
      "latitude": '$(echo "40.7 + $i * 0.001" | bc)',
      "longitude": -74.0,
      "accuracy_meters": 8
    }' &
done
wait
```

**Expected:** All 10 requests return 201 Created
**Validation:**

```sql
SELECT COUNT(*) FROM vehicle_locations
WHERE vehicle_id = $VEHICLE_ID;
-- Expected: >= 10 (from this test + earlier tests)
```

**Dependencies:** 1.5, 2.7

---

## Phase 5: Rate Limiting

### 5.1 Route Endpoints Rate Limit (60/minute)

**Test:** Exceed rate limit on route read

```bash
for i in {1..65}; do
  curl -s http://localhost:8000/routes/$ROUTE_ID \
    -H "X-Test-Tenant-Id: $TENANT_ID" \
    -H "X-Test-User-Id: $USER_DISPATCHER" \
    -H "X-Test-Permissions: route:read" &
done
wait
```

**Expected:** First 60 succeed (200), remaining get 429 Too Many Requests
**Validation:** Rate limiter enforced per endpoint
**Dependencies:** Route exists from Phase 2

---

### 5.2 Location Endpoints Rate Limit (300/minute)

**Test:** Verify location endpoints have higher limit

```bash
# Should succeed at 150 requests
for i in {1..150}; do
  curl -s http://localhost:8000/vehicles/$VEHICLE_ID/location \
    -H "X-Test-Tenant-Id: $TENANT_ID" \
    -H "X-Test-User-Id: $USER_TECHNICIAN" \
    -H "X-Test-Permissions: location:read" > /dev/null &
done
wait

# Verify all succeeded
echo "All 150 requests should succeed"
```

**Expected:** 200 on all 150 (< 300/minute limit)
**Validation:** Location endpoints have higher rate limit than route ops
**Dependencies:** 1.5

---

## Test Execution Summary

| Phase | Test | Golden Path? | RBAC? | Edge Case? | DB Check? | Approx Duration |
|-------|------|--------------|-------|-----------|-----------|-----------------|
| 1     | 1.1–1.6 | N/A | N | N | Y | 2 min |
| 2     | 2.1–2.9 | Y | N | N | N | 8 min |
| 3     | 3.1–3.9 | N | Y | Y | N | 10 min |
| 4     | 4.1–4.6 | N | N | N | Y | 8 min |
| 5     | 5.1–5.2 | N | N | N | N | 4 min |
|       | **Total** | | | | | **~32 min** |

---

## Pass/Fail Criteria

**PASS:** All of the following

- Phase 1 (environment): All 6 checks pass
- Phase 2 (golden path): All 9 steps complete in sequence, final route is "complete"
- Phase 3 (RBAC): All 9 permission/state tests return expected error codes
- Phase 4 (DB integrity): Idempotency verified, RLS isolation verified, no orphans
- Phase 5 (rate limits): Both endpoints respect their limits

**FAIL:** Any test returns unexpected status code, wrong data, or violates state machine

---

## Debugging Checklist

| Issue | Check |
|-------|-------|
| 401 Unauthorized on all requests | Verify middleware loading test headers; check `request.state.tenant_id`, `request.state.user_id` |
| 404 on route endpoints | Verify route created successfully in 2.2; check tenant_id isolation |
| 409 on state transition | Verify current status first with GET; check route_status.py transition matrix |
| 500 on location PUT | Check vehicle_location_repository.create() exception; verify tenant_id in schema |
| Idempotency failed (duplicate routes) | Check dispatch_service.commit_dispatch() logic at line 147–154; verify job_id list comparison |
| RLS test shows other tenant's routes | Check RLS policies on routes table; verify tenant_id filter applied in queries |
| Rate limit not enforced | Check limiter initialization in app; verify rate_limit decorators applied to all route handlers |

---

## Appendix: Quick Test Script

Run all tests in sequence:

```bash
#!/bin/bash
set -e

BASE_URL="http://localhost:8000"
TENANT_ID="550e8400-e29b-41d4-a716-446655440000"
USER_DISPATCHER="550e8400-e29b-41d4-a716-446655440001"
USER_TECHNICIAN="550e8400-e29b-41d4-a716-446655440002"

echo "=== Phase 1: Environment Setup ==="
curl -s $BASE_URL/health | jq '.status'

echo "=== Phase 2: Golden Path ==="
JOB_ID="550e8400-e29b-41d4-a716-446655660000"
VEHICLE_ID="550e8400-e29b-41d4-a716-446655550000"

# 2.2: Create route
ROUTE_RESPONSE=$(curl -s -X POST $BASE_URL/jobs/$JOB_ID/commit-dispatch \
  -H "X-Test-Tenant-Id: $TENANT_ID" \
  -H "X-Test-User-Id: $USER_DISPATCHER" \
  -H "X-Test-Permissions: job:write,vehicle:read,route:write" \
  -H "Content-Type: application/json" \
  -d '{"date": "2026-06-02", "option_kind": "nearest"}')

ROUTE_ID=$(echo $ROUTE_RESPONSE | jq -r '.id')
STOP_ID=$(echo $ROUTE_RESPONSE | jq -r '.stops[0].id')
echo "Created route $ROUTE_ID with stop $STOP_ID"

# 2.5: Start route
curl -s -X POST $BASE_URL/routes/$ROUTE_ID/start \
  -H "X-Test-Tenant-Id: $TENANT_ID" \
  -H "X-Test-User-Id: $USER_TECHNICIAN" \
  -H "X-Test-Permissions: route:write" | jq '.status'

# 2.6: Arrived
curl -s -X POST $BASE_URL/routes/$ROUTE_ID/stops/$STOP_ID/arrived \
  -H "X-Test-Tenant-Id: $TENANT_ID" \
  -H "X-Test-User-Id: $USER_TECHNICIAN" \
  -H "X-Test-Permissions: route:write" | jq '.stops[0].status'

# 2.9: Complete
curl -s -X POST $BASE_URL/routes/$ROUTE_ID/stops/$STOP_ID/complete \
  -H "X-Test-Tenant-Id: $TENANT_ID" \
  -H "X-Test-User-Id: $USER_TECHNICIAN" \
  -H "X-Test-Permissions: route:write" | jq '.status'

echo "=== Phase 3: RBAC ==="
# 3.1: Permission denied
curl -s -X POST $BASE_URL/routes/$ROUTE_ID/start \
  -H "X-Test-Tenant-Id: $TENANT_ID" \
  -H "X-Test-User-Id: $USER_DISPATCHER" \
  -H "X-Test-Permissions: route:read" \
  -H "Content-Type: application/json" | jq '.detail' || echo "403 OK"

echo "=== All golden path tests passed ==="
```

Save as `tests/smoke_test.sh`, make executable, and run in CI/staging environment.
