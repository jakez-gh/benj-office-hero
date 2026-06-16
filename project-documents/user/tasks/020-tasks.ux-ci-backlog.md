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

- [ ] **Error copy** — Remove developer-facing "check that the server is running
  on port 8000" from all amber banners. Replace with user-facing copy:
  _"Service temporarily unavailable — we'll reconnect automatically."_
  Affected: `ErrorBanner.tsx` default message and any page-level inline copy.

- [ ] **Vehicles / Users offline state** — When the backend is unreachable,
  these pages show only the amber banner with nothing below. Jobs, Contracts,
  and Routes show a helpful empty-state message beneath the banner. Vehicles
  and Users should do the same (e.g. "No vehicles on record." / "No users on
  record.").

- [ ] **Contracts mobile — button overflow** — "Generate due jobs" + "New
  contract" sit side-by-side at 375 px and collide. Stack them vertically on
  `sm:` breakpoint or below.

- [ ] **Login subtitle color** — The subtitle "Enter your credentials to access
  your account" inherits a blue link-color class instead of muted gray.
  Change to `text-muted-foreground` (or equivalent Tailwind class in use).

- [ ] **Skeleton race condition (Users mobile)** — The mobile screenshot of
  Users captures the skeleton-loading state instead of the offline-error state.
  Root cause: 1200 ms wait isn't always enough. Fix: add
  `await page.waitForSelector('[data-testid="error-banner"], [data-testid="users-empty"]', { timeout: 5000 })`
  before the screenshot in `screenshots.spec.ts`, or detect the error/empty
  state explicitly.

---

## Priority 2 — Loading & Progress Indicators

- [ ] **Consistent skeleton loaders** — Every list/table page (Jobs, Contracts,
  Routes, Vehicles, Users, Customers) should show skeleton rows while the
  initial fetch is in flight. Confirm each page renders skeletons before the
  first API response (not just a blank area or spinner).

- [ ] **Inline action feedback** — Buttons that trigger mutations (Dispatch Job,
  Generate due jobs, route start/complete, etc.) should disable themselves and
  show a spinner/loading text while the request is in flight. No silent no-ops.

- [ ] **Full-page transition** — When navigating between pages, if data takes
  >200 ms to load, show a top-of-page progress bar (e.g. NProgress or Tailwind
  animate-pulse bar) so the user knows something is happening.

---

## Priority 3 — Auto-Recovery

- [ ] **Backend connectivity polling** — When the amber "unavailable" banner
  appears, the app should silently poll `GET /health` every 5 seconds. When
  the backend returns 200, trigger a refetch and auto-dismiss the banner. No
  user interaction required to recover.

- [ ] **Error banner dismiss on recovery** — The banner should disappear as
  soon as connectivity is restored, not require a page reload.

---

## Priority 4 — Dispatch Page Redesign

The current Dispatch page asks operators to type raw UUIDs for Tenant ID,
Job ID, and Technician ID. This is unusable in production.

- [ ] **Remove Tenant ID field** — tenant is already known from the logged-in
  session; it should never appear as a form field.

- [ ] **Job field → searchable dropdown** — Replace "Job ID" text input with
  a combobox that searches pending jobs by title/customer name. On selection,
  show the job title, customer, and address.

- [ ] **Technician field → searchable dropdown** — Replace "Technician ID" with
  a combobox showing crew members (Users with technician role) by name.

- [ ] **Vehicle field → searchable dropdown** — Add a Vehicle selector showing
  vehicles with their license plate and model.

- [ ] **Dispatch result feedback** — After a successful dispatch, show the
  created route ID and a link to the Routes page. On failure, show a readable
  error (not a raw 422 JSON blob).

---

## Priority 5 — CI/CD Automation

- [ ] **Screenshots with real data** — The current screenshot spec runs without
  a backend and captures offline/empty shells. Add a second spec
  `screenshots-seeded.spec.ts` that seeds a tenant, creates sample data, and
  captures screenshots of the app with real data visible.

- [ ] **Demo videos in CI** — `demo-flows.spec.ts` currently requires
  `DEMO_BACKEND=1 RECORD_VIDEO=on` to be set manually. Add a GitHub Actions
  workflow (`.github/workflows/demo-videos.yml`) that runs nightly (or on
  main push) with these env vars, uploads the `.webm` files as artifacts, and
  optionally converts them to GIF/MP4 for embedding in docs.

- [ ] **Screenshot diff in PR** — Add a GitHub Actions step that runs the shell
  screenshot spec on every PR and posts a comment with any changed screenshots
  as an image diff, so reviewers can see UI changes without checking out the
  branch.

---

## Priority 6 — E2E User-Flow Tests

These tests should run against a live backend (similar to `demo-flows.spec.ts`)
and assert correctness, not just that the page renders.

- [ ] **Job CRUD flow** — Create → verify in list → search by title → cancel.

- [ ] **Contract → job generation** — Create contract → "Generate due jobs" →
  verify jobs appear in Jobs page filtered by this customer.

- [ ] **Full dispatch flow** — Create job → go to Dispatch → select job from
  dropdown → select vehicle/technician → submit → verify route appears on
  Routes page with correct status.

- [ ] **Route lifecycle** — Start route → arrive at stop → complete stop → verify
  job status changes to `completed`.

- [ ] **Customer & Vehicle CRUD** — Create, view, (edit if supported), list
  with search filter.

- [ ] **Multi-tenant isolation test** — Seed Tenant A (plumber) and Tenant B
  (pest control) with separate jobs. Assert that listing jobs as Tenant A
  returns zero results from Tenant B, and vice versa.

---

## Priority 7 — Interactive Tour

- [ ] **Assess which areas need a tour** — After Dispatch redesign and
  auto-recovery land, walk through the app as a first-time user and list any
  steps that remain non-obvious.

- [ ] **Implement tour** — If justified, add a lightweight guided tour library
  (e.g. `driver.js` or `intro.js`) triggered on first login. Tour should cover
  at minimum: creating a job, dispatching it, viewing the route.

- [ ] **Onboarding checklist** — Consider a "getting started" checklist widget
  on the Jobs page for new tenants with 0 data: ① Add a customer → ② Add a
  vehicle → ③ Create a job → ④ Dispatch.

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

**What still needs a test:**

- Explicit cross-tenant read attempt (Tenant A tries to GET Tenant B's job ID
  → should 404).

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
