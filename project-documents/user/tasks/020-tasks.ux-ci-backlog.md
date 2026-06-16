# UX, CI/CD, and Quality Backlog

## Purpose

This file is the canonical backlog for UX improvements, automation, testing,
and quality issues identified in the June 2026 UI/UX review. It is the first
place any new Claude session should look after reading the slice plan and
architecture docs.

**Quick start for Claude:** `cf build` → read this file → pick the next
`[ ]` item → implement → check it off.

---

## Priority 1 — UX Defects (fix immediately)

- [x] **Error copy** — Removed developer-facing "port 8000" from `ErrorBanner.tsx`.
  Now reads: _"Service temporarily unavailable — we'll reconnect automatically."_

- [x] **Vehicles / Users offline state** — Both pages now show a helpful
  empty-state message beneath the error banner ("Vehicles could not be loaded."
  / "Users could not be loaded.") even when the error is active.

- [x] **Contracts mobile — button overflow** — Fixed: `flex-col gap-2 sm:flex-row`
  on the action button container.

- [x] **Login subtitle color** — Not a real bug. `CardDescription` renders as
  `text-neutral-500` (gray). Confirmed by reading the component source.

- [x] **Skeleton race condition (Users mobile)** — Fixed in `screenshots.spec.ts`
  (2026-06-16, commit 74d3666). Replaced 1200ms flat wait with a
  `waitForSelector('[role="alert"]', { timeout: 4000 })` for all auth routes.
  The fetch is always aborted → error banner always appears; waiting for it is
  deterministic on any machine speed.

---

## Priority 2 — Loading & Progress Indicators

- [x] **Consistent skeleton loaders** — All 6 data pages (Jobs, Contracts,
  Routes, Vehicles, Users, Customers) already render 3–5 `<Skeleton>` rows
  while the initial fetch is in flight. Confirmed by code review (2026-06-16).

- [x] **Inline action feedback** — Every mutation button already disables
  itself and shows loading text ("Dispatching…", "Generating…", "Creating…",
  "Saving…", etc.) while in-flight. Confirmed by code review (2026-06-16).
  No silent no-ops found.

- [x] **Full-page transition** — `PageProgressBar` component added
  (2026-06-16). Fixed 3px strip at top of viewport; three CSS phases:
  scaleX 0→0.8 via keyframe (loading), scaleX→1 (complete), opacity→0
  (fading). Mounted in `NavShell`; uses `useLocation()` to detect
  navigation; no external packages required.

---

## Priority 3 — Auto-Recovery

- [x] **Backend connectivity polling** — `useAutoRecover` hook created
  (`apps/admin-web/src/hooks/useAutoRecover.ts`). Polls `/health` every 5 s
  when a network error is active. Wired to all 6 data pages: Jobs, Contracts,
  Routes, Customers, Vehicles, Users.

- [x] **Error banner dismiss on recovery** — When backend recovers, the page
  re-fetches data; on success the error state clears and the banner disappears.

---

## Priority 4 — Dispatch Page Redesign

**Status: COMPLETE** (2026-06-16).

- [x] Tenant ID field removed — auto-populated from session (`localStorage.tenant_id`
  or auth user).
- [x] Job field → inline search + listbox (filters pending jobs by title in
  real-time; shows selected job summary below).
- [x] Technician field → dropdown (users with `technician`/`tech` role).
- [x] Dispatch result card — shows saga state live with step, status badge,
  and link to Routes page on `done`.

---

## Priority 5 — CI/CD Automation

- [x] **Screenshots with real data** — `screenshots-seeded.spec.ts` added
  (2026-06-16). Requires `DEMO_BACKEND=1`. Seeds one tenant with customer,
  3 jobs (2 dispatched, 1 pending for Dispatch page), vehicle, crew,
  contract. Captures all 8 routes × 2 viewports with real data visible.
  Images go to `screenshots-seeded/` (gitignored; download from CI artifacts).

- [x] **Demo videos in CI** — `.github/workflows/demo-videos.yml` added
  (2026-06-16). Triggers: nightly 02:00 UTC + push to main. Spins up Postgres
  16 service, runs Alembic migrations, starts uvicorn, records
  `demo-flows.spec.ts` with `RECORD_VIDEO=1`, uploads `.webm`/`.mp4` as
  `demo-videos-{sha}` artifacts (30d retention).

- [x] **Screenshot diff in PR** — `.github/workflows/screenshot-diff.yml`
  added (2026-06-16). Triggers on PRs touching `apps/admin-web/**`. Runs
  offline screenshot spec (chromium), diffs vs committed baseline via `cmp`,
  posts/updates a sticky PR comment listing changed/new/missing screenshots,
  uploads `pr-screenshots-{PR#}` artifact (14d) for side-by-side comparison.

---

## Priority 6 — E2E User-Flow Tests

**Status: INITIAL SUITE COMPLETE** (2026-06-16).

- [x] `user-flows.spec.ts` — 11 tests: customer CRUD, job create/search/
  status-filter, route appearance, manual-schedule flow, vehicles empty state,
  contracts pause/resume and create, Dispatch dropdown end-to-end.
- [x] `multi-tenant.spec.ts` — 6 API isolation tests: jobs, customers,
  vehicles, contracts, routes — all verified 404/empty across tenant boundary.
- [x] `demo-flows.spec.ts` — updated Demo 1 Dispatch section for new
  dropdown UI (old UUID label selectors removed).

**Still to add:**

- [x] **Route lifecycle test** — Start route via API → reload Routes page →
  verify `in_progress` badge → complete stop via API → reload → verify stop
  shows `complete`. (`user-flows.spec.ts` — "Route lifecycle" suite, 2026-06-16)

- [x] **Contract → job generation** — Create contract with `start_date=TODAY`
  → navigate to Contracts → click "Generate due jobs" → navigate to Jobs →
  verify generated job appears. (`user-flows.spec.ts` — "Contract job
  generation" suite, 2026-06-16)

---

## Priority 7 — Interactive Tour

**Assessment (2026-06-16): Full tour NOT required at this stage.**

After the Dispatch redesign and auto-recovery work, the app is sufficiently
intuitive for the target user (office dispatcher). Key observations:

- Every page has clear empty states with "Create your first X" CTAs.
- Dispatch now uses plain language + dropdowns; no UUID inputs.
- Routes page now shows a hint: "Use ↑↓ to reorder stops before starting."
  with tooltips on the reorder buttons — the previously most non-intuitive area.
- Error states auto-recover silently.

**Still worth considering:**

- [ ] **Onboarding checklist widget** — "Getting started" banner for a new
  tenant with 0 customers: ① Add a customer → ② Add a vehicle → ③ Create a
  job → ④ Schedule it. Dismiss once first job is dispatched. Low-code; high
  value for first-run experience.

- [ ] **Route reorder UX** — The hint text ("Use ↑↓ to reorder") is subtle.
  If user research shows confusion, promote to a `CardDescription` or add a
  drag-and-drop handle (more discoverable). Deferred pending feedback.

---

## Multi-Tenant Architecture Verification

**Status: CONFIRMED working** (2026-06-16).

- Every entity model (`Job`, `Customer`, `Vehicle`, `Route`, etc.) carries a
  `tenant_id` FK column pointing to `tenants.id`.
- Every repository method takes `tenant_id` as a required argument and applies
  it as a `WHERE` clause — both the SQLAlchemy impl and the in-memory mock.
- `Tenant.industry` supports `"generic"`, `"plumbing"`, `"hvac"`,
  `"pest_control"` (and future verticals via the `back_office_adapter` field).
- The test auth middleware (`OFFICE_HERO_TEST_AUTH=1`) reads
  `X-Test-Tenant-Id` from headers, which auto-provisions new tenant rows.
- `demo-flows.spec.ts` proves isolation: each of the 3 demo tests seeds its
  own `randomUUID()` tenant and asserts data is visible only to that tenant.

**Isolation confirmed by `multi-tenant.spec.ts`** (2026-06-16): jobs, customers,
vehicles, contracts, and routes all return 404 or empty list when accessed from
the wrong tenant.

---

## Done

- [x] Local CI/CD setup (pre-commit + pre-push hooks)
- [x] Demo runner (`scripts/run-demos.py`) — stages 1, 2, 2b all passing
- [x] Playwright video demo spec (`demo-flows.spec.ts`) — 3 videos recorded
- [x] CORS middleware on FastAPI (dev/test only, gated on `OFFICE_HERO_TEST_AUTH`)
- [x] Error banners changed from red to amber on all 6 data pages
- [x] Mobile nav scroll gradient for discoverability
- [x] `waitUntil: 'load'` fix in screenshot spec (was: networkidle hung on Vite HMR WebSocket)
- [x] `server_manager.py` — Windows venv path + 120 s startup timeouts
- [x] 16 screenshots captured (8 routes × 2 viewports) and committed
- [x] `useAutoRecover` hook — all 6 data pages auto-recover from network errors
- [x] `ErrorBanner.tsx` — removed "port 8000" developer copy
- [x] Vehicles / Users offline empty state fixed
- [x] Contracts mobile button stack fixed
- [x] Dispatch page redesign — dropdowns, auto-populate tenant, saga result card
- [x] Routes page reorder tooltips + hint text
- [x] `user-flows.spec.ts` — 11 E2E user-flow tests
- [x] `multi-tenant.spec.ts` — 6 tenant isolation tests
- [x] `demo-flows.spec.ts` updated for new Dispatch UI
