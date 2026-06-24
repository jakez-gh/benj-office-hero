---
id: 1.1.2.14.1
type: tasks
parent: 1.1.2.14
status: not_started
size: small
slice: tenant-admin-backend
dateCreated: 20260624
dateUpdated: 20260624
---

# Tasks — Slice 029: Tenant Admin Backend

Parent slice: `029-slice.tenant-admin-backend.md`

## Tasks

- [ ] **T1** — Add `GET /admin/tenants` to `integrations.py`
  - Query `Tenant` table, ordered by `created_at DESC`, with `limit`/`offset` params
  - Response: `{"items": [...], "total": int, "limit": int, "offset": int}`
  - Include `jobber_connected: bool` derived from a LEFT JOIN / subquery on `jobber_credentials`
  - Operator-gated (`Depends(require_operator)`)
  - DoD: endpoint returns tenant list with correct `jobber_connected` flag

- [ ] **T2** — Add `POST /admin/tenants` to `integrations.py`
  - Request body: `{"name": str, "industry": str}` (validate with Pydantic; `ConfigDict(extra="forbid")`)
  - Validate `industry` is in known set; return 422 if not
  - Insert `Tenant` row; return 201 with full tenant object
  - DoD: creates a real DB row; re-fetchable via `GET /admin/tenants`

- [ ] **T3** — Write `tests/integration/test_tenant_admin_routes.py`
  - 8 tests per slice design (list empty, list after create, create happy path, blank name,
    invalid industry, patch adapter, patch invalid, missing auth)
  - Use the existing `AsyncClient` + `create_app()` test pattern
  - DoD: all 8 tests pass with no DB required (in-memory or test DB fixture)

## Notes

- The `PATCH /admin/tenants/{id}/adapter` route already exists in `integrations.py` —
  no changes needed there.
- `jobber_connected` in T1: query `jobber_credentials` for the tenant's row; True if
  a row exists and `expires_at > now()`.  Use a subquery or Python post-process.
