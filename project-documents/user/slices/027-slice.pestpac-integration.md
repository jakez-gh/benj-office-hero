---
id: 1.1.2.12
type: slice-design
parent: 1.1.2
status: needs-sandbox
slice: pestpac-integration
research: RES-026
dateCreated: 20260618
dateUpdated: 20260618
---

# Slice Design 027: PestPac (WorkWave Odyssey API) BackOfficeAdapter

## Status: needs-sandbox

This slice is fully designed and scaffolded but has one CRITICAL BLOCKER that
prevents completing the HTTP call layer:

> **Does the Odyssey API return the created entity synchronously, or does it
> return a `requestId` immediately (like the WWRM sibling API)?**

If the API is asynchronous (requestId pattern), the `BackOfficeAdapter`
protocol contract (`create_customer` returns `Customer`) cannot be satisfied
without a polling loop — which may require amending the protocol (new ADR).
Resolve this with the first sandbox request before writing any HTTP call code.

See `research/026-research.pestpac-api.md` (RES-026), open question #1.

---

## What lands when the blocker is resolved

| Deliverable | File | Notes |
| ----------- | ---- | ----- |
| Entity map migration | `alembic/versions/0017_pestpac_entity_map.py` | **Already written** — ready to run |
| Adapter scaffold | `src/office_hero/adapters/back_office/pestpac.py` | **Already written** — HTTP call layer stubbed |
| Scaffold tests | `tests/unit/test_pestpac_adapter.py` | **Already written** — 10 pass; HTTP layer tests TBD |
| Adapter config model | `PestPacConfig` in `pestpac.py` | **Already written** |
| Slice design | this file | **Already written** |
| HTTP call layer | complete `pestpac.py` TODOs | Blocked — needs sandbox |
| Registry registration | add to `registry.py` | After HTTP layer works |
| HTTP mock tests | extend `test_pestpac_adapter.py` | After HTTP layer works |

---

## Architecture

### Auth

`X-API-Key` header on every request. Key from `PESTPAC_API_KEY` env var.
All requests also carry `companyKey` (6-digit PestPac Company Key) as a query
or body parameter. No token expiry to manage.

**Required env vars:**

| Var | Purpose |
| --- | ------- |
| `PESTPAC_API_KEY` | Header credential from PestPac Users master screen |
| `PESTPAC_COMPANY_KEY` | 6-digit PestPac tenant identifier |
| `PESTPAC_SANDBOX` | `true` to use sandbox endpoint (default: `false`) |
| `PESTPAC_DEFAULT_DIVISION` | Division code for Location create (default: `"1"`) |
| `PESTPAC_DEFAULT_SOURCE` | Source field for Location create (default: `"Office Hero"`) |
| `PESTPAC_DEFAULT_TYPE` | Location type for Location create (default: `"Residential"`) |

### Entity Mapping

PestPac uses integer IDs (`LocationCode` for customers, `WorkOrderId` for
jobs). The `pestpac_entity_map` table (migration 0017) stores the
bidirectional mapping: `(tenant_id, entity_type, internal_id UUID) ↔ pestpac_id`.

The adapter scaffold uses an in-memory `_entity_cache` dict. Replace with
table queries for multi-process/restart durability (production step).

### Customer → PestPac Location Mapping

Our `Customer(id, name)` maps to a PestPac **BillTo Location**. PestPac requires
`Division`, `Source`, and `Type` fields on create — these come from
`PestPacConfig` with per-tenant defaults.

Creating a customer also creates a `ServiceLocation` (the physical service
address) linked to the BillTo Location. The stub sends a placeholder address
(`zip: "00000"`) — production should extend the `Customer` dataclass with an
`address` field or accept the placeholder for initial sync.

### Job → PestPac Work Order Mapping

Our `Job(id, customer_id)` maps to a PestPac **Work Order** (individual
scheduled visit). `create_job` requires the PestPac `LocationCode` for the
customer — the Saga/Outbox must ensure `create_customer` runs before
`create_job` for the same tenant session.

### Idempotency

No server-side idempotency key in the Odyssey API (confirmed in RES-026).
Pattern: check `_entity_cache` (or `pestpac_entity_map` table) before every
create call. If the mapping exists, skip the create and return the entity.

### Rate Limits

Publicly undocumented — likely daily quota-based (per-call pricing). Implement
exponential backoff on 429 (already in `_request()`). Contact WorkWave to
confirm exact limits before production deployment.

### Webhooks (inbound sync — future scope)

PestPac webhooks use HMAC-SHA256 signatures (from WWRM sibling platform
pattern). Event catalog for the Odyssey surface needs sandbox access to
confirm. Inbound sync is out of scope for this slice.

---

## Completion Checklist

When sandbox access (`APISales@workwave.com`) is available:

1. Make one `GET /workorders?companyKey=X&pageSize=1` call to confirm:
   - Endpoint path is correct
   - Auth (`X-API-Key` header) works
   - Response is synchronous (entity in body) vs. async (`requestId`)

2. If **synchronous**: complete the TODO blocks in `pestpac.py`:
   - `create_customer`: POST `/locations`, cache the returned `LocationCode`
   - `get_customer`: GET `/locations/{pestpac_id}` by cache lookup
   - `update_customer`: PATCH `/locations/{pestpac_id}`
   - `delete_customer`: PATCH to set `active: false`
   - `create_job`: POST `/workorders` with `locationCode`, cache `WorkOrderId`
   - `get_job`, `update_job`, `delete_job`: analogous pattern

3. If **asynchronous (requestId)**: file a design blocker issue, evaluate:
   - Add polling loop in `create_customer`/`create_job` (latency hit)
   - Or amend `BackOfficeAdapter` protocol to return `None` on async creates
     (requires ADR update; affects all 3 adapters)

4. Write respx mock tests for all HTTP call paths.

5. Register in `registry.py`:
   ```python
   from office_hero.adapters.back_office.pestpac import PestPacAdapter
   register_adapter("pestpac", PestPacAdapter.from_tenant)
   ```

6. Update `pestpac.py` to use `pestpac_entity_map` table (replace `_entity_cache`).

---

## Tests

Already passing (10 tests in `tests/unit/test_pestpac_adapter.py`):
- Protocol isinstance check
- Config sandbox/prod URL switching
- `from_tenant` factory satisfies protocol
- `get_customer` / `get_job` return None when not in cache
- `delete_customer` / `delete_job` are no-ops when not in cache
- `create_customer` raises `NotImplementedError` (HTTP layer blocked)
- `create_job` raises `ValueError` when customer not in cache
- `create_job` raises `NotImplementedError` when customer IS in cache (HTTP layer)
- `create_customer` idempotent when already in cache
- `create_job` idempotent when already in cache

HTTP-layer tests to add after completing the TODOs (see checklist above).

---

## Dependencies

- Slice 24 (BackOfficeAdapter protocol seam) — complete
- Migration 0017 (`pestpac_entity_map`) — written, not yet applied
- `PestPac_*` Fly.io secrets — not yet provisioned
- Sandbox trial from `APISales@workwave.com` — required before HTTP layer

## Effort: 2/5 remaining

Scaffold and migration are done. The HTTP call layer is straightforward once
the sync/async question is resolved — it's ~6 methods each with a
GET-before-POST pattern. The bulk of the work is already done.
