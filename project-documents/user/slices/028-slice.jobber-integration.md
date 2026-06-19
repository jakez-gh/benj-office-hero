---
id: 1.3.3
type: slice-design
parent: 1.1.2
status: ready
slice: jobber-integration
research: RES-027
dateCreated: 20260618
dateUpdated: 20260618
---

# Slice Design 028: Jobber GraphQL Integration

Implements the Jobber back-office adapter against Jobber's GraphQL API
(v2023-11-15), dropping it into the `BackOfficeAdapter` seam from Slice 24.

## What lands

| Artifact | Description |
|---|---|
| `alembic/versions/0015_jobber_tables.py` | `jobber_credentials` + `jobber_entity_map` tables |
| `src/office_hero/adapters/back_office/jobber.py` | Full `JobberAdapter` implementation |
| `tests/unit/test_jobber_adapter.py` | 10 unit tests (respx mocks, no live calls) |
| Registry wiring | `registry.py` registers `"jobber"` → `JobberAdapter.from_tenant` |

## Key design decisions

### OAuth2 token rotation
Jobber uses authorization_code flow with mandatory refresh-token rotation: each
`/token` refresh returns a new `refresh_token` that immediately invalidates the
old one. Tokens are stored per-tenant in `jobber_credentials`. The adapter
refreshes proactively if `expires_at - now < 5 minutes`.

**Production gap:** `_refresh_token_if_needed` updates tokens in memory only.
A `CredentialsPersistCallback` must be wired to upsert `jobber_credentials`
before the access window closes. Without this the rotated refresh_token is
lost on process restart.

### Custom field bootstrap
Jobber has no native external-ID field. We configure two custom fields:

- `hero_client_id` (Text) on Client
- `hero_job_id` (Text) on Job

Their `configurationId` values are stored in `jobber_credentials.custom_field_*_config_id`
after first connect (provisioned via `customFieldConfigurationCreate` on
`APP_CONNECT` webhook or first adapter call). When these IDs are absent,
`get_customer` and `get_job` return `None` rather than guessing.

### Entity cache (scaffold) → entity map table (production)
The in-memory `_entity_cache` dict maps `(entity_type, internal_id)` → Jobber
opaque ID for the lifetime of the adapter instance. Production must query/upsert
`jobber_entity_map` to survive restarts and work across multiple processes.

### Throttle back-off
Jobber's leaky-bucket allows 10,000 points with 500 pts/sec restore.
After every GraphQL response, if `extensions.cost.throttleStatus.currentlyAvailable`
is below 100, the adapter sleeps 1 second before returning. This is conservative
and avoids DDoS-layer blocks without complex point accounting.

### Soft-delete mapping
Jobber has no hard-delete on clients or jobs. `delete_customer` → `clientArchive`,
`delete_job` → `jobArchive`. Archived entities are excluded from normal queries
in Jobber's UI. Our entity-map entries are kept (for idempotency checks).

### `create_job` requires Jobber Client ID
Jobber's `jobCreate` mutation takes a `clientId` (Jobber opaque ID), not our
internal UUID. The adapter resolves this from the entity cache. If no mapping
exists, it raises `ValueError` — callers must ensure `create_customer` runs
before `create_job` for the same tenant.

## Open questions (from RES-027)

1. **Custom field bootstrap trigger**: should we call `customFieldConfigurationCreate`
   on `APP_CONNECT` webhook (cleaner) or lazily on the first adapter call (simpler
   for the scaffold)? Lazy is the current approach; webhook handler is future work.
2. **Multi-tenant DB-backed credentials**: the scaffold uses env vars. Real multi-tenant
   deployment needs the `jobber_credentials` table wired to `from_tenant`.
3. **`jobCreate` title field**: currently hardcoded `"Office Hero Job"`. Should derive
   from the job domain model when Jobber adapter is wired to real job data.
4. **Token persistence callback**: design an interface for the adapter to notify the
   caller that rotated tokens need persisting (avoids coupling the adapter to a DB session).

## Test plan

All unit tests use `respx` to intercept HTTP — zero live network calls.

| Test | Verifies |
|---|---|
| `test_adapter_satisfies_protocol` | `isinstance(adapter, BackOfficeAdapter)` |
| `test_health_check_true` | 200 + `account` data → returns True |
| `test_health_check_false_on_graphql_error` | `errors` in body → returns False |
| `test_create_customer_posts_mutation` | get (empty) + clientCreate → cache populated |
| `test_create_customer_idempotent_on_cache_hit` | cache hit → clientEdit only (1 call) |
| `test_create_job_raises_when_client_not_in_cache` | no client mapping → ValueError |
| `test_create_job_success_with_client_in_cache` | jobCreate → cache populated |
| `test_delete_customer_archives_client` | clientArchive mutation called |
| `test_delete_customer_noop_when_not_in_cache` | no cache entry → None, no HTTP |
| `test_token_refresh_on_expiry` | expired creds → token endpoint + in-memory update |

## Dependencies

- Slice 24 (BackOfficeAdapter seam + NativeAdapter + registry) — `status: complete`
- Migration 0015 (`jobber_credentials`, `jobber_entity_map`)
- `httpx` (runtime dep, already present)
- `respx` (dev dep, already installed, not yet in `pyproject.toml`)

## Effort: 4/5

More complex than a REST adapter due to:
- OAuth2 mandatory token rotation (stateful per-tenant credential store)
- No native external ID → custom field bootstrap + lookup
- GraphQL throttle back-off (point-based, not request-based)
- `create_job` dependency on Jobber Client ID (not our UUID)
