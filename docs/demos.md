# Demos by Development Stage

Three runnable demo scripts walk through Office Hero's capabilities across slices, showing real-world workflows end-to-end with verified output.

## Prereqs

All scripts require:

- **Backend:** running with `OFFICE_HERO_TEST_AUTH=1` to enable X-Test-* header authentication.
  Start via: `python tools/server_manager.py start` or `scripts/start-backend.ps1` or
  `scripts/start-backend.sh` (each sets the auth flag automatically).
- **jq:** JSON query tool for parsing responses. Install via package manager or <https://stedolan.github.io/jq/download/>.
- **Port configuration:** Backend defaults to `http://127.0.0.1:8000`.
  Override by passing `BACKEND_URL=http://127.0.0.1:PORT bash scripts/<script-name>`.

## Stage 1 — Core Dispatch MVP (Slices 1–15)

**Script:** `scripts/run-demo.sh`

Creates a customer, location, and single job. Dispatches the job to a vehicle, commits a route,
and walks through the complete technician workflow: start route, mark stop arrived, record GPS location,
mark stop complete, auto-complete route when all stops are terminal. Verifies RBAC enforcement,
tenant isolation, and atomic transactions. Outputs 11 numbered JSON files capturing all API responses.

Run: `bash scripts/run-demo.sh`

## Stage 2 — Contracts, Route Override, CRM Sync (Slices 11, 14+, 24)

**Script:** `scripts/demo-contracts-routes.sh`

Creates a contract with monthly recurrence (started 2 months ago), pauses and resumes it,
generates due jobs (expect count >= 2), creates a vehicle and crew. Dispatches two jobs to the
same vehicle (demonstrating multi-stop route building), then manually reorders the stops via
POST /routes/{id}/resequence. Processes the outbox to sync events back to the CRM, verifies
no dead-letters, and completes the route through its full lifecycle. Demonstrates dispatcher override,
event outbox mechanics, and back-office integration.

Run: `BACKEND_URL=http://127.0.0.1:8000 bash scripts/demo-contracts-routes.sh`

## Stage 3 — Admin Web UI (Slices 5, 11, 14+, 24)

**Web UI:** Start the React frontend at <http://localhost:3000>

```bash
pnpm --filter admin-web dev
```

Navigate through:

- **Contracts page:** View/create/edit contracts; initiate "Generate due jobs" button.
- **Jobs page:** See generated and assigned jobs; filter by status/date.
- **Schedule (Dispatcher):** Two workflows — "Suggested dispatch" (auto-routing suggestions)
  and "Assign manually" (pick vehicle + date/time yourself).
- **Routes page:** View committed routes; expand stops to see sequence; reorder by dragging
  and click "Save order" (calls POST /routes/{id}/resequence).

All screenshots auto-refresh via pre-push git hook (see `docs/screenshots/README.md`).
Latest UI images live in `docs/screenshots/admin-web/`.

## Recorded Demos

For video capture:

- **PowerShell recording script:** `scripts/record-demo.ps1` (Windows-only; uses OBS or system screen capture).
- **Admin-web demo mode:** `apps/admin-web/demo-recording.ts` provides mock data for repeatable UI walkthroughs.

See individual scripts for recording setup and video codec details.
