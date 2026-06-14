# Demos by Development Stage

Three runnable demo scripts walk through Office Hero's capabilities across slices, showing real-world workflows end-to-end with verified output.

## Prereqs

- **Backend:** running with `OFFICE_HERO_TEST_AUTH=1` to enable `X-Test-*` header authentication.
  Start via: `OFFICE_HERO_TEST_AUTH=1 poetry run uvicorn office_hero.main:app --host 127.0.0.1 --port 8000`
  or `python tools/server_manager.py start`.
- **Port configuration:** Backend defaults to `http://127.0.0.1:8000`.
  Override with the `--url` flag or `BACKEND_URL` env var.

## Running all demos (recommended)

**Python runner (no bash/jq dependency):**

```powershell
$env:PYTHONIOENCODING = "utf-8"
python scripts/run-demos.py --stage all
```

Individual stages: `--stage 1`, `--stage 2`, `--stage 2b`.

Each run saves numbered JSON files + `transcript.txt` under `demos/<timestamp>_<stage>/`.

## Stage 1 — Core Dispatch MVP (Slices 1–15)

Creates a customer, location, and single job. Dispatches the job to a vehicle, commits a route,
and walks through the complete technician workflow: start route, mark stop arrived,
mark stop complete, auto-complete route when all stops are terminal. Verifies RBAC enforcement,
tenant isolation, and atomic transactions.

## Stage 2 — Contracts, Route Override, CRM Sync (Slices 11, 14+, 24)

Creates a contract with monthly recurrence (started 2 months ago), pauses and resumes it,
generates due jobs (expect count ≥ 2), creates a vehicle and crew. Dispatches two jobs to the
same vehicle (demonstrating multi-stop route building), then manually reorders the stops via
`POST /routes/{id}/resequence`. Processes the outbox to sync events back to the CRM, verifies
no dead-letters, and completes the route through its full lifecycle.

## Stage 2b — Day-of re-routing: sick-days and emergencies (Slice 16)

Demonstrates two real-world exception flows once routes are committed:

1. **Technician sick-day:** creates two vehicles with routes, starts Vehicle 1's route,
   completes one stop, then reassigns the remaining stops to Vehicle 2 via
   `POST /routes/{id}/reassign`. Source route is finalised; target route receives the
   pending stops.

2. **Emergency dispatch:** creates an urgent job (priority 100) and inserts it at the
   head of Vehicle 2's pending queue via `POST /jobs/{id}/emergency-dispatch`. The
   emergency stop appears before other pending stops.

**Required permissions:**

- Reassign: `X-Test-Permissions: route:write`
- Emergency dispatch: `X-Test-Permissions: jobs:dispatch,route:write`

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
- **Routes page:** View committed routes; reorder stops with the up/down controls and
  click "Save new order" (POST /routes/{id}/resequence); **Reassign** a route to another
  vehicle when a technician is out (POST /routes/{id}/reassign); start/cancel routes.

All screenshots auto-refresh via pre-push git hook (see `docs/screenshots/README.md`).
Latest UI images live in `docs/screenshots/admin-web/`.

## Recorded Demos

Playwright video demos walk through real UI flows against a live backend.
Each demo seeds its own isolated tenant so runs don't interfere.

```powershell
# Ensure backend is running with test auth
$env:OFFICE_HERO_TEST_AUTH = "1"
poetry run uvicorn office_hero.main:app --host 127.0.0.1 --port 8000

# In a second terminal — from apps/admin-web:
$env:RECORD_VIDEO = "on"
npx playwright test src/e2e/demo-flows.spec.ts --project=chromium --reporter=line
```

Videos are written to `apps/admin-web/test-results/` as `.webm` files.

**Demo scenarios:**

- **Demo 1 — Jobs & Dispatch:** Shows jobs list, route page, vehicles page, and the dispatch form.
- **Demo 2 — Contracts lifecycle:** Shows customer list, contracts page, and generated jobs.
- **Demo 3 — Route management:** Shows route list and live route progression after stops complete.
