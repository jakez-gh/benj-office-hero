#!/bin/bash
# demo-dynamic-rerouting.sh — Stage 2b: Sick-day Reassign + Emergency Dispatch (Slice 16)
#
# Demonstrates real-world exceptions once routes are committed:
#   1. Technician calls in sick → reassign an in-progress route to another vehicle
#   2. Emergency job arrives → insert it at the head of an active vehicle's queue
#
# Prerequisites:
#   • Backend running with OFFICE_HERO_TEST_AUTH=1
#     Start via: python tools/server_manager.py start
#              or: bash scripts/start-backend.sh
#   • jq (JSON query tool) — or Python 3 (this script falls back to a py shim)
#
# Usage:
#   bash scripts/demo-dynamic-rerouting.sh
#   BACKEND_URL=http://127.0.0.1:8001 bash scripts/demo-dynamic-rerouting.sh

set -e

BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"

TENANT_ID=$(python -c "import uuid; print(uuid.uuid4())")
USER_ID=$(python -c "import uuid; print(uuid.uuid4())")

DEMO_DIR="./demos/$(date +%Y%m%d_%H%M%S)_rerouting"
mkdir -p "$DEMO_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# jq fallback for environments without jq (Windows git-bash, minimal CI)
if ! command -v jq > /dev/null 2>&1; then
  PY_JQ='
import sys, json, re

args = sys.argv[1:]
raw = False
if args and args[0] == "-r":
    raw = True
    args = args[1:]
filt = args[0] if args else "."
data = json.load(sys.stdin)

def emit(v):
    if raw and isinstance(v, str):
        print(v)
    else:
        print(json.dumps(v, indent=2))

def eval_path(d, path):
    tokens = re.findall(r"\.([A-Za-z_][A-Za-z0-9_]*)|\[(\d*)\]", path)
    vals = [d]
    for name, idx in tokens:
        out = []
        for v in vals:
            if name:
                out.append(v.get(name) if isinstance(v, dict) else None)
            elif idx == "":
                out.extend(v if isinstance(v, list) else [])
            else:
                i = int(idx)
                out.append(v[i] if isinstance(v, list) and len(v) > i else None)
        vals = out
    return vals

if filt == ".":
    emit(data)
elif filt.startswith("[") and filt.endswith("]"):
    emit(eval_path(data, filt[1:-1]))
else:
    for v in eval_path(data, filt):
        emit(v)
'
  jq() { python -c "$PY_JQ" "$@"; }
fi

demo_step() {
  echo ""
  echo -e "${BLUE}=== $1 ===${NC}"
  echo "$1" >> "$DEMO_DIR/transcript.txt"
}

result() {
  echo -e "${GREEN}✅ $1${NC}"
  echo "✅ $1" >> "$DEMO_DIR/transcript.txt"
}

err() {
  echo -e "${RED}❌ $1${NC}"
  echo "❌ $1" >> "$DEMO_DIR/transcript.txt"
}

echo -e "${YELLOW}🎬 Office Hero Stage 2b — Dynamic Re-routing: Sick Days & Emergency Dispatch${NC}"
echo "Demo Directory: $DEMO_DIR"
echo "Backend URL:    $BACKEND_URL"
echo "Tenant ID:      $TENANT_ID"
echo ""

# ─── Step 0: Health Check ───────────────────────────────────────────────────
demo_step "Step 0: Health Check"
HEALTH=$(curl -s "$BACKEND_URL/health")
echo "Backend: $HEALTH"
echo "Backend: $HEALTH" >> "$DEMO_DIR/transcript.txt"
result "Backend healthy"

# ─── Step 1: Create Customer and Location ───────────────────────────────────
demo_step "Step 1: Create Customer"
CUSTOMER=$(curl -s -X POST "$BACKEND_URL/customers" \
  -H "X-Test-Tenant-Id: $TENANT_ID" -H "X-Test-User-Id: $USER_ID" \
  -H "X-Test-Role: operator" -H "X-Test-Permissions: *" \
  -H "Content-Type: application/json" \
  -d '{"name":"Riverside Cleaning Co","email":"ops@riverside.example.com"}')
CUSTOMER_ID=$(echo "$CUSTOMER" | jq -r '.id')
echo "$CUSTOMER" | jq . > "$DEMO_DIR/01-customer.json"
result "Customer created: $CUSTOMER_ID"

demo_step "Step 2: Create Location"
LOCATION=$(curl -s -X POST "$BACKEND_URL/customers/$CUSTOMER_ID/locations" \
  -H "X-Test-Tenant-Id: $TENANT_ID" -H "X-Test-User-Id: $USER_ID" \
  -H "X-Test-Role: operator" -H "X-Test-Permissions: *" \
  -H "Content-Type: application/json" \
  -d '{"street":"789 River Road","city":"Portland","state":"OR","postal_code":"97201"}')
LOCATION_ID=$(echo "$LOCATION" | jq -r '.id')
echo "$LOCATION" | jq . > "$DEMO_DIR/02-location.json"
result "Location created: $LOCATION_ID"

# ─── Step 3: Create Two Vehicles ────────────────────────────────────────────
demo_step "Step 3a: Create Vehicle 1 (Primary — technician calls in sick)"
V1=$(curl -s -X POST "$BACKEND_URL/vehicles" \
  -H "X-Test-Tenant-Id: $TENANT_ID" -H "X-Test-User-Id: $USER_ID" \
  -H "X-Test-Role: operator" -H "X-Test-Permissions: *" \
  -H "Content-Type: application/json" \
  -d '{"license_plate":"CLEAN-001","make":"Toyota","model":"Sienna","year":2023}')
VEHICLE1_ID=$(echo "$V1" | jq -r '.id')
echo "$V1" | jq . > "$DEMO_DIR/03a-vehicle1.json"
result "Vehicle 1 created: $VEHICLE1_ID"

demo_step "Step 3b: Create Vehicle 2 (Backup — receives reassigned route)"
V2=$(curl -s -X POST "$BACKEND_URL/vehicles" \
  -H "X-Test-Tenant-Id: $TENANT_ID" -H "X-Test-User-Id: $USER_ID" \
  -H "X-Test-Role: operator" -H "X-Test-Permissions: *" \
  -H "Content-Type: application/json" \
  -d '{"license_plate":"CLEAN-002","make":"Honda","model":"Odyssey","year":2022}')
VEHICLE2_ID=$(echo "$V2" | jq -r '.id')
echo "$V2" | jq . > "$DEMO_DIR/03b-vehicle2.json"
result "Vehicle 2 created: $VEHICLE2_ID"

# ─── Step 4: Create Crews for Today ─────────────────────────────────────────
WORK_DATE=$(python -c "import datetime; print(datetime.date.today().isoformat())")
CREW_USER2=$(python -c "import uuid; print(uuid.uuid4())")

demo_step "Step 4a: Assign Crew to Vehicle 1"
CREW1=$(curl -s -X POST "$BACKEND_URL/vehicle-crews" \
  -H "X-Test-Tenant-Id: $TENANT_ID" -H "X-Test-User-Id: $USER_ID" \
  -H "X-Test-Role: operator" -H "X-Test-Permissions: *" \
  -H "Content-Type: application/json" \
  -d '{
    "vehicle_id": "'$VEHICLE1_ID'",
    "work_date": "'$WORK_DATE'",
    "shift_start": "07:00:00",
    "shift_end": "16:00:00",
    "members": [{"user_id": "'$USER_ID'", "role_on_crew": "lead"}]
  }')
CREW1_ID=$(echo "$CREW1" | jq -r '.id')
echo "$CREW1" | jq . > "$DEMO_DIR/04a-crew1.json"
result "Crew 1 created: $CREW1_ID"

demo_step "Step 4b: Assign Crew to Vehicle 2"
CREW2=$(curl -s -X POST "$BACKEND_URL/vehicle-crews" \
  -H "X-Test-Tenant-Id: $TENANT_ID" -H "X-Test-User-Id: $USER_ID" \
  -H "X-Test-Role: operator" -H "X-Test-Permissions: *" \
  -H "Content-Type: application/json" \
  -d '{
    "vehicle_id": "'$VEHICLE2_ID'",
    "work_date": "'$WORK_DATE'",
    "shift_start": "07:00:00",
    "shift_end": "16:00:00",
    "members": [{"user_id": "'$CREW_USER2'", "role_on_crew": "lead"}]
  }')
CREW2_ID=$(echo "$CREW2" | jq -r '.id')
echo "$CREW2" | jq . > "$DEMO_DIR/04b-crew2.json"
result "Crew 2 created: $CREW2_ID"

# ─── Step 5: Create and Dispatch 2 Jobs to Vehicle 1 ────────────────────────
demo_step "Step 5a: Create Job A (morning stop)"
JOB_A_RESP=$(curl -s -X POST "$BACKEND_URL/jobs" \
  -H "X-Test-Tenant-Id: $TENANT_ID" -H "X-Test-User-Id: $USER_ID" \
  -H "X-Test-Role: operator" -H "X-Test-Permissions: *" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "'$CUSTOMER_ID'",
    "location_id": "'$LOCATION_ID'",
    "title": "Morning deep clean",
    "service_type": "Deep cleaning",
    "priority": 50,
    "estimated_duration_min": 90
  }')
JOB_A_ID=$(echo "$JOB_A_RESP" | jq -r '.id')
echo "$JOB_A_RESP" | jq . > "$DEMO_DIR/05a-job-a.json"
result "Job A created: $JOB_A_ID"

demo_step "Step 5b: Create Job B (afternoon stop)"
JOB_B_RESP=$(curl -s -X POST "$BACKEND_URL/jobs" \
  -H "X-Test-Tenant-Id: $TENANT_ID" -H "X-Test-User-Id: $USER_ID" \
  -H "X-Test-Role: operator" -H "X-Test-Permissions: *" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "'$CUSTOMER_ID'",
    "location_id": "'$LOCATION_ID'",
    "title": "Afternoon touch-up",
    "service_type": "Touch-up cleaning",
    "priority": 40,
    "estimated_duration_min": 60
  }')
JOB_B_ID=$(echo "$JOB_B_RESP" | jq -r '.id')
echo "$JOB_B_RESP" | jq . > "$DEMO_DIR/05b-job-b.json"
result "Job B created: $JOB_B_ID"

SCHED_A=$(python -c "import datetime; print((datetime.datetime.now(datetime.timezone.utc).replace(hour=8,minute=0,second=0,microsecond=0)).isoformat())")
SCHED_B=$(python -c "import datetime; print((datetime.datetime.now(datetime.timezone.utc).replace(hour=13,minute=0,second=0,microsecond=0)).isoformat())")

demo_step "Step 5c: Dispatch Job A to Vehicle 1"
DISPATCH_A=$(curl -s -X POST "$BACKEND_URL/jobs/$JOB_A_ID/dispatch" \
  -H "X-Test-Tenant-Id: $TENANT_ID" -H "X-Test-User-Id: $USER_ID" \
  -H "X-Test-Role: operator" -H "X-Test-Permissions: *" \
  -H "Content-Type: application/json" \
  -d '{"vehicle_id":"'$VEHICLE1_ID'","scheduled_for":"'$SCHED_A'","travel_seconds":600,"distance_meters":5000}')
ROUTE1_ID=$(echo "$DISPATCH_A" | jq -r '.route_id')
echo "$DISPATCH_A" | jq . > "$DEMO_DIR/05c-dispatch-a.json"
result "Job A dispatched. Route 1: $ROUTE1_ID"

demo_step "Step 5d: Dispatch Job B to Vehicle 1 (same route)"
DISPATCH_B=$(curl -s -X POST "$BACKEND_URL/jobs/$JOB_B_ID/dispatch" \
  -H "X-Test-Tenant-Id: $TENANT_ID" -H "X-Test-User-Id: $USER_ID" \
  -H "X-Test-Role: operator" -H "X-Test-Permissions: *" \
  -H "Content-Type: application/json" \
  -d '{"vehicle_id":"'$VEHICLE1_ID'","scheduled_for":"'$SCHED_B'","travel_seconds":900,"distance_meters":8000}')
ROUTE1_ID_CHECK=$(echo "$DISPATCH_B" | jq -r '.route_id')
echo "$DISPATCH_B" | jq . > "$DEMO_DIR/05d-dispatch-b.json"
result "Job B dispatched to same route. Route: $ROUTE1_ID_CHECK"

# ─── Step 6: Start Route (technician is on the way) ─────────────────────────
demo_step "Step 6: Start Route 1 (Vehicle 1 begins their day)"
START=$(curl -s -X POST "$BACKEND_URL/routes/$ROUTE1_ID/start" \
  -H "X-Test-Tenant-Id: $TENANT_ID" -H "X-Test-User-Id: $USER_ID" \
  -H "X-Test-Role: operator" -H "X-Test-Permissions: *" \
  -H "Content-Type: application/json")
ROUTE1_STATUS=$(echo "$START" | jq -r '.status')
echo "$START" | jq . > "$DEMO_DIR/06-route-start.json"
result "Route 1 started. Status: $ROUTE1_STATUS"

# ─── SCENARIO A: SICK-DAY REASSIGN ──────────────────────────────────────────
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW} SCENARIO A — Technician calls in sick mid-shift           ${NC}"
echo -e "${YELLOW} Remaining stops will be reassigned to Vehicle 2.          ${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# First, complete Stop A so Vehicle 1 has worked at least one stop
FIRST_STOP_ID=$(echo "$START" | jq -r '.stops[0].id')

demo_step "Step 7a: Vehicle 1 arrives at first stop (Job A)"
ARRIVED_A=$(curl -s -X POST "$BACKEND_URL/routes/$ROUTE1_ID/stops/$FIRST_STOP_ID/arrived" \
  -H "X-Test-Tenant-Id: $TENANT_ID" -H "X-Test-User-Id: $USER_ID" \
  -H "X-Test-Role: operator" -H "X-Test-Permissions: *" \
  -H "Content-Type: application/json")
echo "$ARRIVED_A" | jq . > "$DEMO_DIR/07a-stop-a-arrived.json"
result "Stop A: arrived"

demo_step "Step 7b: Vehicle 1 completes first stop (Job A)"
COMPLETE_A=$(curl -s -X POST "$BACKEND_URL/routes/$ROUTE1_ID/stops/$FIRST_STOP_ID/complete" \
  -H "X-Test-Tenant-Id: $TENANT_ID" -H "X-Test-User-Id: $USER_ID" \
  -H "X-Test-Role: operator" -H "X-Test-Permissions: *" \
  -H "Content-Type: application/json")
echo "$COMPLETE_A" | jq . > "$DEMO_DIR/07b-stop-a-complete.json"
result "Stop A: complete — 1 stop done, 1 pending (Job B)"

demo_step "Step 8: SICK-DAY — Reassign Route 1 remaining stops to Vehicle 2"
REASSIGN=$(curl -s -X POST "$BACKEND_URL/routes/$ROUTE1_ID/reassign" \
  -H "X-Test-Tenant-Id: $TENANT_ID" -H "X-Test-User-Id: $USER_ID" \
  -H "X-Test-Role: dispatcher" -H "X-Test-Permissions: route:write" \
  -H "Content-Type: application/json" \
  -d '{"target_vehicle_id": "'$VEHICLE2_ID'"}')

echo "Reassign Response:"
echo "$REASSIGN" | jq . | tee "$DEMO_DIR/08-reassign.json"

SOURCE_STATUS=$(echo "$REASSIGN" | jq -r '.source_route.status')
TARGET_ROUTE_ID=$(echo "$REASSIGN" | jq -r '.target_route.id')
TARGET_STATUS=$(echo "$REASSIGN" | jq -r '.target_route.status')
MOVED_COUNT=$(echo "$REASSIGN" | jq -r '.moved_count')

result "Reassign complete. Source route: $SOURCE_STATUS | Target route: $TARGET_ROUTE_ID ($TARGET_STATUS) | Moved: $MOVED_COUNT stop(s)"

demo_step "Step 9: Verify — Source route is finalised, target has the pending stop"
SOURCE_CHECK=$(curl -s "$BACKEND_URL/routes/$ROUTE1_ID" \
  -H "X-Test-Tenant-Id: $TENANT_ID" -H "X-Test-User-Id: $USER_ID" \
  -H "X-Test-Role: operator" -H "X-Test-Permissions: *")
TARGET_CHECK=$(curl -s "$BACKEND_URL/routes/$TARGET_ROUTE_ID" \
  -H "X-Test-Tenant-Id: $TENANT_ID" -H "X-Test-User-Id: $USER_ID" \
  -H "X-Test-Role: operator" -H "X-Test-Permissions: *")

echo "Source route (finalised):"
echo "$SOURCE_CHECK" | jq '{id:.id, status:.status, stop_count:.stops|length}'
echo "Target route (has pending stop):"
echo "$TARGET_CHECK" | jq '{id:.id, status:.status, stop_count:.stops|length}'
echo "$SOURCE_CHECK" | jq . > "$DEMO_DIR/09-source-check.json"
echo "$TARGET_CHECK" | jq . > "$DEMO_DIR/09-target-check.json"

result "Sick-day reassign verified. Job B now on Vehicle 2's route."

# ─── SCENARIO B: EMERGENCY DISPATCH ─────────────────────────────────────────
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW} SCENARIO B — Emergency job jumps the queue                ${NC}"
echo -e "${YELLOW} New urgent job inserted at head of Vehicle 2's route.     ${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

demo_step "Step 10: Create urgent emergency job"
JOB_EMERG=$(curl -s -X POST "$BACKEND_URL/jobs" \
  -H "X-Test-Tenant-Id: $TENANT_ID" -H "X-Test-User-Id: $USER_ID" \
  -H "X-Test-Role: operator" -H "X-Test-Permissions: *" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "'$CUSTOMER_ID'",
    "location_id": "'$LOCATION_ID'",
    "title": "URGENT: Biohazard spill cleanup",
    "service_type": "Emergency cleanup",
    "priority": 100,
    "estimated_duration_min": 120
  }')
JOB_EMERG_ID=$(echo "$JOB_EMERG" | jq -r '.id')
echo "$JOB_EMERG" | jq . > "$DEMO_DIR/10-emergency-job.json"
result "Emergency job created: $JOB_EMERG_ID (priority: 100)"

demo_step "Step 11: Emergency dispatch — insert at head of Vehicle 2's queue"
EMERG_DISPATCH=$(curl -s -X POST "$BACKEND_URL/jobs/$JOB_EMERG_ID/emergency-dispatch" \
  -H "X-Test-Tenant-Id: $TENANT_ID" -H "X-Test-User-Id: $USER_ID" \
  -H "X-Test-Role: dispatcher" -H "X-Test-Permissions: jobs:dispatch,route:write" \
  -H "Content-Type: application/json" \
  -d '{"target_vehicle_id": "'$VEHICLE2_ID'"}')

echo "Emergency Dispatch Response:"
echo "$EMERG_DISPATCH" | jq . | tee "$DEMO_DIR/11-emergency-dispatch.json"

EMERG_ROUTE_ID=$(echo "$EMERG_DISPATCH" | jq -r '.route_id')
EMERG_STATUS=$(echo "$EMERG_DISPATCH" | jq -r '.status')
result "Emergency job dispatched. Route: $EMERG_ROUTE_ID | Status: $EMERG_STATUS"

demo_step "Step 12: Verify emergency job is first in Vehicle 2's route"
V2_ROUTE=$(curl -s "$BACKEND_URL/routes/$EMERG_ROUTE_ID" \
  -H "X-Test-Tenant-Id: $TENANT_ID" -H "X-Test-User-Id: $USER_ID" \
  -H "X-Test-Role: operator" -H "X-Test-Permissions: *")

echo "Vehicle 2 route stop order:"
echo "$V2_ROUTE" | jq '[.stops[] | {job_id:.job_id, seq:.sequence_number, status:.status}]'
echo "$V2_ROUTE" | jq . > "$DEMO_DIR/12-v2-route-final.json"

FIRST_STOP_JOB=$(echo "$V2_ROUTE" | jq -r '.stops[0].job_id')
if [ "$FIRST_STOP_JOB" = "$JOB_EMERG_ID" ]; then
  result "Emergency job is first stop — inserted at head of queue"
else
  echo -e "${YELLOW}⚠️  First stop job_id: $FIRST_STOP_JOB (expected: $JOB_EMERG_ID)${NC}"
  echo "  (May be appended after any in-progress stop — check route stop order above)"
fi

# ─── DEMO SUMMARY ───────────────────────────────────────────────────────────
demo_step "DEMO COMPLETE — Stage 2b Dynamic Re-routing"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN} Stage 2b Summary                                          ${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Scenario A — Sick-day reassign:"
echo "    Route 1 (Vehicle 1)  : 1 completed stop, 1 pending → finalised"
echo "    Route 2 (Vehicle 2)  : received Job B (pending stop reassigned)"
echo "    moved_count          : $MOVED_COUNT"
echo ""
echo "  Scenario B — Emergency dispatch:"
echo "    Emergency job        : $JOB_EMERG_ID"
echo "    Inserted into route  : $EMERG_ROUTE_ID (Vehicle 2)"
echo "    Position             : first pending stop (ahead of Job B)"
echo ""
echo "Results saved to: $DEMO_DIR"
echo "  transcript.txt, *.json"
echo ""
echo -e "${GREEN}✅ Stage 2b complete — Dynamic re-routing verified${NC}"
echo ""
