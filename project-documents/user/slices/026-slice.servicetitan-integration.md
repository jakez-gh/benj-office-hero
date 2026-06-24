---
id: 1.1.2.11
type: slice-design
parent: 1.1.2
status: ready
slice: servicetitan-integration
research: RES-025
dateCreated: 20260618
dateUpdated: 20260618
---

# Slice 26 — ServiceTitan Integration

## What lands

| Artifact | Path |
|---|---|
| DB migration | `alembic/versions/0015_servicetitan_entity_map.py` |
| Adapter implementation | `src/office_hero/adapters/back_office/servicetitan.py` |
| Unit tests | `tests/unit/test_servicetitan_adapter.py` |
| This slice design | `project-documents/user/slices/026-slice.servicetitan-integration.md` |

The adapter is ready for real credentials. Registration into the adapter registry
happens at app startup via the credential check pattern described below.

## Key design decisions

### Token caching
Access tokens last 900 s. We cache in-memory with an 840 s reuse window (60 s
margin) keyed on monotonic time. Multi-process deployments will re-auth on each
worker start — acceptable given token cost is negligible.

### externalData idempotency (customers)
ServiceTitan has no native externalId on the customer entity. We tag every
customer at creation with:
```json
{"applicationGuid": "office-hero", "key": "internal_id", "value": "<our UUID>"}
```
Every mutating customer method calls `_find_customer_by_external_id` first and
returns early if found. The filter
`?externalData.applicationGuid=office-hero&externalData.key=internal_id&externalData.value={id}`
is the ST-recommended approach from the v2 API docs.

### externalId idempotency (jobs)
Jobs have a native `externalId` string field. We store our UUID there. The
idempotency check is `?externalId={job.id}&pageSize=1` before every POST.

### Location requirement
Every ST customer requires at least one location. `create_customer` always
POSTs a stub location (`name: "Default", zip: "00000"`) immediately after the
customer POST. The stub satisfies the constraint; field operators can fill real
address data later via the ST back-office UI.

### create_job dependency on create_customer
`create_job` needs the ST integer customerId. Rather than maintaining a local
mapping table (deferred to future slice), it calls `_find_customer_by_external_id`
at job-creation time. If the customer isn't in ST yet, a `ValueError` is raised
— the Saga/Outbox retry loop will redeliver and succeed once the customer event
processes first.

### 429 retry
Up to 3 retries with exponential backoff (1 s → 2 s → 4 s). `asyncio.sleep`
is patched in tests to avoid wall-clock delays.

### Sentinel customer_id in get_job
`get_job` returns `Job(id=id, customer_id=UUID(int=0))` as a sentinel when the
job exists but we can't round-trip the ST integer customerId back to our UUID
without a second externalData lookup. Callers that need the real customer link
should call `get_customer` separately. Full bidirectional linkage is deferred
to Slice 27+.

## Out of scope

- Webhook inbound sync (ST → Office Hero push). Event subscriptions require a
  public HTTPS endpoint and a separate ST webhook configuration. Deferred.
- Per-tenant ST credential table. Currently credentials are env-global. Slice
  28 will support per-tenant credential storage in a `tenant_integrations` table.
- Populating `servicetitan_entity_map` at write time. The migration creates the
  table; the population path is wired in Slice 27 when the integer-ID round-trip
  becomes load-bearing.
- ST Reporting API / revenue sync. Out of current initiative scope.

## Test plan

| Test | What it validates |
|---|---|
| `test_get_token_posts_form_urlencoded` | Auth body is `application/x-www-form-urlencoded`, not JSON |
| `test_get_token_caches_within_840s` | 2 token calls → 1 HTTP request |
| `test_get_token_refreshes_after_expiry` | Token refreshed when monotonic clock passes expiry |
| `test_health_check_true_on_200` | `health_check()` returns True on 200 |
| `test_health_check_false_on_exception` | `health_check()` returns False on 5xx |
| `test_create_customer_posts_with_external_data` | GET → POST customers → POST locations; body has externalData |
| `test_create_customer_idempotent_when_exists` | GET finds existing → no POST |
| `test_get_customer_returns_none_when_not_found` | Empty page → None |
| `test_get_customer_returns_customer_when_found` | Populated page → Customer |
| `test_create_job_idempotent_when_exists` | GET finds existing job → no POST |
| `test_create_job_raises_on_missing_customer_in_st` | ValueError when customer not in ST |
| `test_create_job_posts_with_correct_fields` | Full create path; externalId, customerId, locationId in body |
| `test_adapter_satisfies_protocol` | `isinstance(adapter, BackOfficeAdapter)` |
| `test_api_retries_on_429` | 429 + 200 → 2 requests, sleep patched |

All 14 tests pass.

## Dependencies

- **Slice 24** (`status: complete`) — BackOfficeAdapter protocol, NativeAdapter, registry
- **Migration 0014** (`0014_performance_indexes`) — `down_revision` for 0015
- **respx** >= 0.23 — HTTP mock library for tests (already installed)
- **httpx** >= 0.24 — async HTTP client (already in runtime deps)

## Effort

3 / 5

## Environment variables required (not in repo)

```
SERVICETITAN_CLIENT_ID=<from ST developer portal>
SERVICETITAN_CLIENT_SECRET=<from ST developer portal>
SERVICETITAN_APP_KEY=<from ST developer portal>
SERVICETITAN_TENANT_ID=<integer tenant id in ST>
SERVICETITAN_SANDBOX=true   # omit or set false for production
```
