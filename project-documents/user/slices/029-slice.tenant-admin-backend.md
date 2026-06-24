---
id: 1.1.2.14
type: slice-design
parent: 1.1.2
status: ready
size: small
slice: tenant-admin-backend
dateCreated: 20260624
dateUpdated: 20260624
---

# Slice Design 029: Tenant Admin — Backend CRUD Endpoints

## Goal

Expose `GET /admin/tenants` (list) and `POST /admin/tenants` (create) so the
frontend Tenant management page has data to work with.  `PATCH /admin/tenants/{id}/adapter`
already exists (added in Slice 27 wiring — `integrations.py`).

## Definition of Done

`GET /admin/tenants` returns all tenants with pagination; `POST /admin/tenants` creates
a new tenant row; both are operator-gated and covered by integration tests that pass.

---

## Files Touched

| File | Change |
| ---- | ------ |
| `src/office_hero/api/routes/integrations.py` | Add `GET /admin/tenants` and `POST /admin/tenants` routes |
| `tests/integration/test_tenant_admin_routes.py` | New — 6–8 tests covering list, create, adapter patch |

The `Tenant` ORM model already exists (`models/tenant.py`).  No new migration needed.

---

## API Design

### GET /admin/tenants

```
GET /admin/tenants?limit=50&offset=0
Authorization: Bearer <operator-token>

200 OK
{
  "items": [
    {
      "id": "uuid",
      "name": "Acme Pest Control",
      "industry": "pest_control",
      "back_office_adapter": "native",
      "created_at": "2026-06-01T00:00:00Z"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

### POST /admin/tenants

```
POST /admin/tenants
Authorization: Bearer <operator-token>
Content-Type: application/json

{ "name": "Acme Pest Control", "industry": "pest_control" }

201 Created
{ "id": "uuid", "name": "Acme Pest Control", "industry": "pest_control",
  "back_office_adapter": "native", "created_at": "..." }
```

Valid industry values (from existing `Tenant` model conventions):
`generic`, `pest_control`, `hvac`, `plumbing`, `electrical`, `landscaping`

---

## Implementation Notes

- Add routes directly to `create_integrations_router()` in `integrations.py` — no new
  router file needed.
- Use the lazy `get_engine()` + `get_session()` pattern already established in that file.
- `POST /admin/tenants` inserts a new `Tenant` row using SQLAlchemy ORM; `back_office_adapter`
  defaults to `"native"` (the column default).
- Return `422` if `name` is blank or `industry` is not in the valid set.
- No `DELETE /admin/tenants` in this slice — soft-delete / deactivation is future scope.

---

## Tests

`tests/integration/test_tenant_admin_routes.py`:

1. `test_list_tenants_empty` — `GET /admin/tenants` returns `{"items": [], "total": 0, ...}`
2. `test_list_tenants_returns_created` — create one, then list; appears in result
3. `test_create_tenant_happy_path` — 201 with all fields present
4. `test_create_tenant_blank_name_422` — name="" returns 422
5. `test_create_tenant_invalid_industry_422` — unknown industry returns 422
6. `test_patch_adapter_switches_adapter` — PATCH changes `back_office_adapter`; subsequent GET reflects change
7. `test_patch_adapter_invalid_value_422` — unknown adapter returns 422
8. `test_list_tenants_requires_operator` — 403 without operator token

---

## Dependencies

- Slice 24 (BackOfficeAdapter seam) — complete
- Slice 27 wiring (`integrations.py`, `PATCH /admin/tenants/{id}/adapter`) — complete

## Effort: 1.5/5

Routes are straightforward ORM queries.  Tests need a live DB (SQLite-backed or Postgres
test fixture) or the existing `AsyncClient` + in-memory pattern used elsewhere.
