---
id: 1.1.2.15.1
type: tasks
parent: 1.1.2.15
status: not_started
size: small
slice: tenant-admin-ui
dateCreated: 20260624
dateUpdated: 20260624
---

# Tasks — Slice 030: Tenant Admin Frontend

Parent slice: `030-slice.tenant-admin-ui.md`

## Tasks

- [ ] **T1** — Add API client functions to `apps/admin-web/src/api.ts`
  - `listTenantsApi()`, `createTenantApi(body)`, `patchTenantAdapterApi(id, adapter)`
  - `Tenant` interface: `id, name, industry, back_office_adapter, created_at, jobber_connected?`
  - DoD: functions exist and TypeScript compiles cleanly

- [ ] **T2** — Create `apps/admin-web/src/pages/TenantsPage.tsx`
  - Tenant list table: name, industry, adapter selector (`<select>`), Connect Jobber / status column
  - Adapter `<select>` fires `patchTenantAdapterApi` on change; show spinner while saving
  - "Connect Jobber" button navigates to `/admin/integrations/jobber/connect?tenant_id={id}`
    (shows when adapter is `jobber` and `jobber_connected !== true`)
  - New Tenant form at bottom: name input + industry dropdown + Create button
  - Loading / error states following `OperatorDashboardPage.tsx` pattern
  - DoD: page renders, adapter changes save, Create adds a new row

- [ ] **T3** — Wire route and nav link
  - Add `<Route path="/tenants" element={<TenantsPage />}>` to `App.tsx` (or wherever routes live)
  - Add "Tenants" nav link between Users and Operator entries
  - DoD: clicking the nav link opens the page; browser back works

## Notes

- Follow the `ErrorBanner` + `Button` component patterns already in use.
- No new npm packages needed — this is standard React + Tailwind.
- `industry` dropdown options: `generic`, `pest_control`, `hvac`, `plumbing`,
  `electrical`, `landscaping`
- Adapter options: `native`, `servicetitan`, `pestpac`, `jobber`
- When adapter is `servicetitan` or `pestpac`, show a muted chip "Env vars" instead of
  a connect button — those use app-level secrets, not per-tenant OAuth2.
