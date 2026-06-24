---
id: 1.1.2.16
type: slice-design
parent: 1.1.2
status: in_progress
size: small
slice: ui-improvements
dateCreated: 20260624
dateUpdated: 20260624
---

# Slice Design 031: UI Improvements (UI-01 through UI-14)

## Goal

Fix the CRITICAL mobile nav overflow (UI-01), plus HIGH/MEDIUM/LOW polish items
identified by the gamma UI audit: table scroll, missing CTAs, error style
consistency, button label convention, onboarding suppression, login forgot-password.

## Definition of Done

- UI-01: All nav items reachable on 375px (hamburger drawer)
- UI-02 through UI-14: each item fixed and TypeScript clean
- QA-01: `/tenants` and `/operator` added to `screenshots-seeded.spec.ts`
- QA-02: Demo 4 (Tenants + Operator Dashboard) added to `demo-flows.spec.ts`
- `sq review code` returns APPROVE or APPROVE_WITH_NITS; no FAIL
- Open-work index updated, slice marked complete

---

## Work Breakdown

Items grouped by WS (workstream) as registered in `.agents/WORKSTREAMS.md`:

### WS-09 (gamma): UI-01 — Mobile nav hamburger
- `apps/admin-web/src/components/NavShell.tsx`
- `hidden md:flex` on the nav scroll area; hamburger icon + slide-out drawer for `md:hidden`
- Owned by gamma

### WS-10 (alpha): UI-02/03/04/05 — Table scroll + missing add buttons + empty-state CTAs
- `TenantsPage.tsx`: wrap table in `<div className="overflow-x-auto">`
- `VehiclesPage.tsx`: add "New Vehicle" button (opens existing modal/form)
- `UsersPage.tsx`: add "New User" / "Invite User" button
- `JobsPage.tsx`, `ContractsPage.tsx`, `CustomersPage.tsx`: make empty-state text into `<Button onClick={openForm}>` 

### WS-11 (alpha): UI-06/07 — Error style + retry button
- Standardise all pages on the amber `ErrorBanner` component
- `OperatorDashboardPage.tsx`: add a Retry button next to the error banner

### WS-12 (alpha): UI-08/09/10 — Button labels, onboarding suppression, forgot-password
- Rename button labels to "New [entity]" convention across all pages
- Suppress `OnboardingChecklist` for operator role or on `/tenants`+`/operator` routes
- `LoginPage.tsx`: add "Forgot password?" link placeholder

### WS-14 (alpha): QA-01/02 — Screenshot & demo coverage gaps

- `screenshots-seeded.spec.ts`: add `09-tenants` + `10-operator-dashboard` to `ROUTES` array
- `demo-flows.spec.ts`: add Demo 4 — seed 2–3 tenants, walk `/tenants` then `/operator`

---

## Dependencies

- Slice 30 complete — TenantsPage exists
- No new API endpoints needed

## Effort: 2.5/5

Mostly one-liner / small component edits. UI-01 is the only non-trivial item (owned by gamma).
