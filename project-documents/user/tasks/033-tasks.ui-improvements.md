---
id: 1.2.33
title: UI improvements — full-app screenshot review (2026-06-24)
type: tasks
parent: 1.2
status: active
docType: tasks
project: office-hero
dateUpdated: 20260624
---

# UI Improvements — Full-App Screenshot Review

Findings from a full screenshot pass across all 10 admin-web pages on desktop
(1280×800) and mobile (375×812). Reviewed: login, jobs, dispatch, vehicles,
users, customers, contracts, routes, tenants, operator dashboard.

Screenshots live in `apps/admin-web/screenshots/`.

---

## CRITICAL — Breaks functionality

### UI-01: Mobile nav overflow — 5+ pages unreachable on mobile

**File:** `apps/admin-web/src/components/NavShell.tsx`
**Impact:** At 375px, the nav bar fits only "Jobs", "Contracts", and "Sign out".
Routes, Dispatch, Vehicles, Users, Customers — and for operators, Tenants and
Operator — are completely invisible and unreachable. No hamburger menu exists.
**Fix:** Add a hamburger / drawer nav for viewports below `md` breakpoint. All
existing nav items should be accessible in the drawer. Tailwind `hidden md:flex`
on the item list + a `md:hidden` hamburger button that toggles a `<Drawer>`.
**Effort:** 3/5

### UI-02: Tenants table truncates on mobile — not scrollable

**File:** `apps/admin-web/src/pages/TenantsPage.tsx`
**Impact:** At 375px the CREATED column is cut off and the table has no
horizontal scroll container. Operator-role users on mobile cannot see full rows.
**Fix:** Wrap the table in `<div className="overflow-x-auto">` or switch to a
card-stack layout below `md`.
**Effort:** 1/5

---

## HIGH — Inconsistency / missing core affordances

### UI-03: Vehicles page missing "Add Vehicle" primary action

**File:** `apps/admin-web/src/pages/VehiclesPage.tsx`
**Impact:** Every other list page has a primary CTA button (Jobs → "New job",
Customers → "+ Add Customer", Contracts → "New contract"). Vehicles shows only
an error banner and empty state text — no button to add the first vehicle.
**Fix:** Add an "Add vehicle" button aligned right of the heading, matching the
pattern in `CustomersPage.tsx`.
**Effort:** 1/5

### UI-04: Users page missing "Add User" / "Invite User" primary action

**File:** `apps/admin-web/src/pages/UsersPage.tsx`
**Impact:** Same issue as Vehicles — no button to create or invite a user.
**Fix:** Add an "Invite user" button (or "Add user") aligned right of the
heading. Check whether the backend endpoint exists; if not, track that too.
**Effort:** 1/5 (UI) + backend check

### UI-05: Empty-state CTAs are plain bold text, not interactive

**Files:**

- `apps/admin-web/src/pages/JobsPage.tsx` — "Create your first job"
- `apps/admin-web/src/pages/ContractsPage.tsx` — "Create your first contract"
- `apps/admin-web/src/pages/CustomersPage.tsx` — "Add your first customer"
**Impact:** Users who miss the header button have no second affordance; the
empty-state phrase looks actionable ("Create your first job") but clicking does
nothing.
**Fix:** Wrap each in a `<button onClick={openCreateForm}>` or `<a>` that opens
the same create flow as the header button. Tailwind `underline cursor-pointer`
styling is sufficient; keep it inline.
**Effort:** 1/5 per page

### UI-06: Three inconsistent error presentation styles

**Pages:**

- Yellow banner (`amber-100` bg, `amber-600` text) — Jobs, Vehicles, Users,
  Customers, Contracts, Routes, Tenants: "Service temporarily unavailable"
- Red banner (no border) — Operator Dashboard: "Failed to load rate limits"
- Red card (pink bg, red border) — Dispatch: "Could not load jobs — Network Error"
**Fix:** Standardise on one error presentation component. The yellow/amber style
is the most common; use it everywhere as a `<StatusBanner variant="error">` or
similar. The Dispatch and Operator error variants should be updated to match.
**Effort:** 2/5

### UI-07: Operator Dashboard error has no retry action

**File:** `apps/admin-web/src/pages/OperatorDashboardPage.tsx`
**Impact:** "Failed to load rate limits" appears with no way to retry except
refreshing the whole browser tab.
**Fix:** Add a "Retry" button next to the error text that calls the load
function again. Pattern: `<button onClick={loadRateLimits}>Retry</button>`.
**Effort:** 1/5

---

## MEDIUM — Polish and consistency

### UI-08: Button label conventions are inconsistent across pages

| Page | Button label |
|------|-------------|
| Jobs | "New job" |
| Customers | "+ Add Customer" |
| Contracts | "New contract" |
| Tenants | "Create" |

Pick one pattern. Recommendation: use "New [entity]" without the `+` prefix
(cleaner, consistent with shadcn-ui conventions). Update Customers and Tenants
to match.
**Effort:** 1/5

### UI-09: Onboarding checklist shows on operator-only pages

**File:** `apps/admin-web/src/components/NavShell.tsx` (or wherever the banner lives)
**Impact:** The "Getting started — complete these steps to dispatch your first
job" banner appears on Tenants and Operator Dashboard, where it is irrelevant.
Operators manage infrastructure; they don't need dispatching guidance.
**Fix:** Hide the onboarding banner on `/tenants` and `/operator` routes. Or
suppress it entirely once the user role is `operator`.
**Effort:** 1/5

### UI-10: Login page missing "Forgot password?" link

**File:** `apps/admin-web/src/components/LoginPage.tsx`
**Impact:** Standard user expectation for any auth form. No recovery path
visible.
**Fix:** Add a "Forgot password?" link below the password field. Even if the
flow is not yet built, link to a "coming soon" page or show a toast directing
users to contact support.
**Effort:** 1/5

---

## LOW — Minor polish

### UI-11: Routes date picker uses native `<input type="date">`

**File:** `apps/admin-web/src/pages/RoutesPage.tsx`
**Impact:** Native date inputs look inconsistent across browsers (especially
Chrome vs Safari). The styling is out of place next to the rest of the Tailwind
UI.
**Fix:** Replace with a lightweight date picker component (e.g. shadcn/ui
`Calendar` + `Popover`) or at minimum apply Tailwind classes to constrain
the native input appearance.
**Effort:** 2/5

### UI-12: Login subtitle uses amber/muted color

**File:** `apps/admin-web/src/components/LoginPage.tsx`
**Impact:** "Enter your credentials to access your account" renders in what
appears to be `text-muted-foreground` or `text-amber-*`. Minor brand mismatch
against the blue title.
**Fix:** Set to `text-muted-foreground` or `text-slate-500` — confirm the exact
class is intentional.
**Effort:** trivial

### UI-13: Job/Contract count subtitle is redundant with empty state

**Files:** `JobsPage.tsx`, `ContractsPage.tsx`
**Impact:** The "0 jobs" / "0 contracts" line under the heading reads as noise
when the empty state below also says "No jobs found."
**Fix:** Hide the count subtitle when count is 0, or omit it entirely on first
load before data arrives.
**Effort:** trivial

### UI-14: Dispatch page has large empty space below error card

**File:** `apps/admin-web/src/pages/DispatchPage.tsx`
**Impact:** When jobs fail to load, the bottom 60% of the page is blank white.
**Fix:** Add a full-height flex container with `items-start` or shift the error
card to a centred layout. Or add a placeholder/skeleton that occupies the space.
**Effort:** 1/5

---

---

## QA / Screenshot & Demo Coverage

### QA-01: screenshots-seeded.spec.ts — add Tenants and Operator Dashboard routes

**File:** `apps/admin-web/src/e2e/screenshots-seeded.spec.ts`
**Gap:** `screenshots.spec.ts` covers all 10 routes (including `09-tenants` and
`10-operator-dashboard`). The seeded-screenshot variant stops at 8 — `/tenants`
and `/operator` were added to the committed spec but never backported here.
**Fix:** Add two entries to the `ROUTES` array. Tenants: wait for `text=No tenants`
or a tenant row element once tenant seeding is added to `seedScenario`. Operator
Dashboard: wait for `h1` or a rate-limit element.
**Effort:** 1/5

### QA-02: demo-flows.spec.ts — Demo 4 (Tenants admin + Operator Dashboard)

**File:** `apps/admin-web/src/e2e/demo-flows.spec.ts`
**Gap:** Demos 1–3 cover Jobs, Dispatch, Routes, Vehicles, Customers, Contracts.
Tenants and Operator Dashboard have no video demo — they are unreachable in any
recorded walkthrough.
**Fix:** Add Demo 4: seed 2–3 tenants via `POST /admin/tenants` using the operator
seed headers, navigate to `/tenants` (show list, adapter badges), then navigate to
`/operator` (show rate-limit panel). Include the same deliberate `pause()` cadence
as other demos so the video is reviewable.
**Effort:** 2/5

---

## Work assignment in WORKSTREAMS.md

| WS-ID | Item |
|-------|------|
| WS-09 | UI-01: Mobile nav hamburger drawer |
| WS-10 | UI-02: Tenants table mobile scroll |
| WS-11 | UI-03/04/05: Vehicles/Users add buttons + empty-state CTAs |
| WS-12 | UI-06/07: Standardise error presentation + add retry actions |
| WS-13 | UI-08/09/10: Button labels, onboarding suppression, forgot-password |
| WS-14 | QA-01/02: seeded-screenshots + Demo 4 coverage |
