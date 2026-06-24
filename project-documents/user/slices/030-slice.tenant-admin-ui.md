---
id: 1.1.2.15
type: slice-design
parent: 1.1.2
status: complete
size: small
slice: tenant-admin-ui
dateCreated: 20260624
dateUpdated: 20260624
---

# Slice Design 030: Tenant Admin — Frontend Management Page

## Goal

Add a **Tenants** page to the admin web so operators can see all tenants, create new
ones, switch a tenant's back-office adapter, and launch the Jobber OAuth2 connect flow
— all from the browser without touching env vars or the CLI.

## Definition of Done

`/tenants` page renders a list of tenants with an adapter selector per row and a
"Connect Jobber" button; a "New Tenant" form creates a tenant; all interactions go
through the backend API and reflect state correctly.

---

## Files Touched

| File | Change |
| ---- | ------ |
| `apps/admin-web/src/pages/TenantsPage.tsx` | New — main page component |
| `apps/admin-web/src/api.ts` | Add `listTenantsApi`, `createTenantApi`, `patchTenantAdapterApi` |
| `apps/admin-web/src/App.tsx` (or router file) | Add `/tenants` route + nav link |

---

## Page Layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Tenants                                          [+ New Tenant]          │
├──────────────────────────────────────────────────────────────────────────┤
│  Name              Industry       Adapter        Actions                  │
│  ─────────────── ──────────────  ────────────── ────────────────────────  │
│  Acme Pest        pest_control   [native    ▼]  [Connect Jobber]          │
│  Metro HVAC       hvac           [jobber    ▼]  ✓ Connected               │
│  ...                                                                      │
├──────────────────────────────────────────────────────────────────────────┤
│  New Tenant                                                               │
│  Name ____________  Industry [select ▼]           [Create]               │
└──────────────────────────────────────────────────────────────────────────┘
```

- **Adapter selector** — `<select>` with options `native / servicetitan / pestpac / jobber`.
  On change fires `PATCH /admin/tenants/{id}/adapter`.  Shows a spinner while saving.
- **Connect Jobber** button — visible when adapter is `jobber` AND the tenant doesn't
  have credentials yet (backend check via a `jobber_connected: boolean` field on the
  list response, or just always show it).  Opens
  `/admin/integrations/jobber/connect?tenant_id={id}` in the same tab (triggers OAuth2
  redirect).  After the callback, the page reloads and shows "✓ Connected".
- **New Tenant form** — inline at the bottom (not a modal) with name text input,
  industry dropdown, and a Create button.  On success the new tenant appears at the top
  of the list.
- **ServiceTitan / PestPac** — no browser action needed (app-level env var secrets).
  When adapter is `servicetitan`, show a small info chip "Credentials via env vars" so
  the operator knows where to look.

---

## API Client (`api.ts` additions)

```typescript
export interface Tenant {
  id: string;
  name: string;
  industry: string;
  back_office_adapter: string;
  created_at: string;
  jobber_connected?: boolean;
}

export interface CreateTenantRequest {
  name: string;
  industry: string;
}

export async function listTenantsApi(): Promise<{ items: Tenant[]; total: number }>
export async function createTenantApi(body: CreateTenantRequest): Promise<Tenant>
export async function patchTenantAdapterApi(id: string, adapter: string): Promise<{ tenant_id: string; adapter: string }>
```

---

## Notes

- Follow the same patterns as `OperatorDashboardPage.tsx` — loading state, `ErrorBanner`,
  disabled buttons while saving.
- The `jobber_connected` flag can be derived by the backend returning `null` vs populated
  `jobber_credentials` row — add it to the `GET /admin/tenants` response in Slice 029.
  If the backend doesn't have it yet, default the "Connect Jobber" button to always
  showing (idempotent: re-connecting just refreshes the tokens).
- No pagination UI needed for v1 — pass `limit=200` and show all rows.  Add pagination
  later if tenant counts grow.
- Nav placement: add "Tenants" between "Users" and "Operator" in the nav bar.

---

## Dependencies

- Slice 029 (tenant admin backend) — must be complete first; frontend needs
  `GET /admin/tenants` and `POST /admin/tenants` to exist

## Effort: 2/5

Standard React CRUD page following existing patterns in the codebase.  No new libraries
or design patterns needed.
