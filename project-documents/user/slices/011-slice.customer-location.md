---
docType: slice-design
parent: ../project-guides/003-slices.office-hero.md
project: office-hero
dateCreated: 20260524
status: not_started
slice: customer-location
dateUpdated: 20260524
---

# Slice Design 011: Customer & Location management

This is the first core FSM (Field Service Management) feature slice. It implements CRUD for
`Customer` and `Location` aggregates with a 1:N relationship (a Customer has many service
Locations). Each Location is geocoded to `lat`/`lng` via a pluggable `GeocodingAdapter`; the
default v1 implementation calls **Nominatim** (OpenStreetMap free tier, no API key) with an
**ORS geocoding adapter** as a future swap. Tenant isolation is enforced by PostgreSQL RLS
per ADR 053; RBAC is enforced via the `@require_role` / `@require_permission` decorators
established in slice 3. State-changing operations emit audit events via the `AuditService`
established in slice 4.

It implements **Slice 9** of the master slice plan.

## Goals

* Add dependency to `pyproject.toml`: `httpx` (already present from slice 4 health check; pin
  `>=0.27`). No new third-party packages required — Nominatim is plain HTTP JSON.
* Extend `src/office_hero/core/config.py` (created in slice 3):
  * `NOMINATIM_BASE_URL: str = "https://nominatim.openstreetmap.org"` (configurable)
  * `NOMINATIM_USER_AGENT: str` (required by Nominatim usage policy; default
    `"office-hero/0.1 (contact@office-hero.example)"`)
  * `GEOCODING_ADAPTER: str = "nominatim"` (enum: `"nominatim" | "ors" | "stub"`)
  * `GEOCODING_TIMEOUT_S: float = 5.0`
  * `GEOCODING_ALLOWLIST: list[str] = ["nominatim.openstreetmap.org", "api.openrouteservice.org"]`
    (SSRF defence; only hosts in this list may be called by the geocoder)
* Create `src/office_hero/adapters/geocoding/__init__.py` (empty).
* Create `src/office_hero/adapters/geocoding/protocol.py` — `GeocodingAdapter` protocol:
  * `async def geocode(address: AddressInput) -> Coordinates | None` — returns `Coordinates`
    (`{lat: float, lng: float, formatted_address: str, source: str}`) or `None` if not resolvable.
  * `AddressInput` dataclass: `{street, city, state, postal_code, country}`.
* Create `src/office_hero/adapters/geocoding/nominatim.py` — `NominatimGeocodingAdapter`:
  * `__init__(base_url, user_agent, timeout, allowlist)` — validates `base_url` host against allowlist
    on construction.
  * `async def geocode(address) -> Coordinates | None` — issues `GET {base_url}/search?format=jsonv2&q=...`
    with the configured `User-Agent` header (per Nominatim ToS).
  * Returns the first result's `lat`/`lng`; logs `geocoding.nominatim.miss` + returns `None` when no result.
  * Raises `GeocodingError` (new in `core/exceptions.py`) on HTTP error, timeout, or response parse failure.
  * Per Nominatim policy: max 1 req/sec — adapter holds an `asyncio.Semaphore(1)` + minimum-interval
    sleeper. Document this constraint in the docstring.
* Create `src/office_hero/adapters/geocoding/stub.py` — `StubGeocodingAdapter` for tests:
  * Deterministic: returns `{lat: 40.0 + hash(street) % 100 / 100, lng: -75.0 + ..., source: "stub"}`
    so test assertions can pin exact coordinates.
* Create `src/office_hero/adapters/geocoding/ors.py` — `ORSGeocodingAdapter` (skeleton, deferred):
  * Class exists but raises `NotImplementedError` from `geocode()`; documented as "enabled in
    Slice 13 follow-up when ORS API key is provisioned". Wired into the factory below so the
    config switch is testable.
* Create `src/office_hero/adapters/geocoding/factory.py` — `build_geocoding_adapter(settings) ->
  GeocodingAdapter` selecting concrete adapter based on `settings.GEOCODING_ADAPTER`. Returns
  the `StubGeocodingAdapter` under `pytest` (detected via `os.environ.get("PYTEST_CURRENT_TEST")`)
  unless overridden by config — keeps unit tests off the live network by default.
* Extend `src/office_hero/core/exceptions.py`:
  * `class GeocodingError(Exception)` — raised by adapter on network/parse failures.
  * `class CustomerNotFoundError(Exception)` — raised by service when ID unknown / cross-tenant.
  * `class LocationNotFoundError(Exception)` — same for locations.
* Create `src/office_hero/models/customer.py` — SQLAlchemy ORM model `Customer`:
  * `id: Mapped[UUID]` (PK, `default=uuid4`)
  * `tenant_id: Mapped[UUID]` (FK `tenants.id`, NOT NULL — RLS pivot)
  * `name: Mapped[str]` (255, NOT NULL)
  * `email: Mapped[str | None]` (255, nullable; CITEXT in migration)
  * `phone: Mapped[str | None]` (50, nullable)
  * `notes: Mapped[str | None]` (Text, nullable)
  * `archived: Mapped[bool]` (default False — soft delete)
  * `external_id: Mapped[str | None]` (255, nullable — back-office adapter link; ADR 056)
  * `created_at`, `updated_at` (TIMESTAMPTZ, server defaults)
  * `__table_args__`: unique `(tenant_id, lower(email))` partial index where email is not null;
    GIN trigram index on `name` for search (created in migration via raw SQL).
  * `locations: Mapped[list["Location"]] = relationship(back_populates="customer", cascade="all, delete-orphan")`
* Create `src/office_hero/models/location.py` — SQLAlchemy ORM model `Location`:
  * `id`, `tenant_id`, `customer_id` (FK `customers.id`, NOT NULL)
  * `label: Mapped[str | None]` (255 — e.g. "Main Office", "Warehouse #2")
  * `street: Mapped[str]` (255, NOT NULL)
  * `street2: Mapped[str | None]` (255)
  * `city: Mapped[str]` (120, NOT NULL)
  * `state: Mapped[str]` (60, NOT NULL — US state code or province)
  * `postal_code: Mapped[str]` (20, NOT NULL)
  * `country: Mapped[str]` (2, NOT NULL, default `"US"` — ISO 3166-1 alpha-2)
  * `lat: Mapped[float | None]` (Numeric(9,6))
  * `lng: Mapped[float | None]` (Numeric(9,6))
  * `geocode_source: Mapped[str | None]` (50 — `"nominatim" | "ors" | "manual" | "stub"`)
  * `geocode_status: Mapped[str]` (20, default `"pending"` — `"pending" | "ok" | "failed" | "manual"`)
  * `geocoded_at: Mapped[datetime | None]`
  * `archived: Mapped[bool]` (default False)
  * `created_at`, `updated_at`
  * `customer: Mapped["Customer"] = relationship(back_populates="locations")`
  * `__table_args__`: index on `(tenant_id, customer_id)`; index on `(tenant_id, geocode_status)`
    so the geocoding worker can find `pending` rows quickly.
* Update `src/office_hero/models/__init__.py` to import `Customer` and `Location` so they
  register with `Base.metadata`.
* Create `src/office_hero/repositories/customer_repository.py`:
  * `CustomerRepository` (concrete) and `CustomerRepositoryProtocol` (ABC) per repo-pattern.
  * Methods (all `async`):
    * `create(tenant_id, name, email, phone, notes, external_id=None) -> Customer`
    * `get_by_id(customer_id, tenant_id) -> Customer | None` (tenant check is defence-in-depth on
      top of RLS; never trust the JWT-extracted tenant_id alone — re-verify on the row)
    * `list(tenant_id, *, search: str | None, archived: bool = False, limit: int = 50,
      offset: int = 0) -> tuple[list[Customer], int]` (returns rows + total count for pagination;
      uses `ILIKE` on name + email; total via `SELECT COUNT(*)`)
    * `update(customer_id, tenant_id, **patch) -> Customer` (raises `CustomerNotFoundError` on miss)
    * `archive(customer_id, tenant_id) -> Customer` (sets `archived=True`; soft delete)
    * `restore(customer_id, tenant_id) -> Customer` (clears `archived`)
* Create `src/office_hero/repositories/location_repository.py`:
  * `LocationRepository` + `LocationRepositoryProtocol`.
  * Methods:
    * `create(tenant_id, customer_id, *, street, street2, city, state, postal_code, country, label)
      -> Location`
    * `get_by_id(location_id, tenant_id) -> Location | None`
    * `list_for_customer(customer_id, tenant_id, *, archived: bool = False) -> list[Location]`
    * `list_pending_geocode(tenant_id, limit: int = 50) -> list[Location]` (worker hook)
    * `update(location_id, tenant_id, **patch) -> Location`
    * `set_coordinates(location_id, tenant_id, lat, lng, source) -> Location`
      (sets `lat`, `lng`, `geocode_source`, `geocode_status="ok"`, `geocoded_at=now()`)
    * `mark_geocode_failed(location_id, tenant_id, error: str) -> Location`
      (sets `geocode_status="failed"`)
    * `archive(location_id, tenant_id) -> Location`
* Create `src/office_hero/repositories/mocks.py` additions (or `tests/mocks/...`):
  * `InMemoryCustomerRepository`, `InMemoryLocationRepository` honouring the protocols, used in
    unit tests for the service layer.
* Create `src/office_hero/services/customer_service.py`:
  * `class CustomerService`:
    * `__init__(repo: CustomerRepositoryProtocol, audit: AuditService)`
    * `async def create(tenant_id, user_id, *, name, email, phone, notes) -> Customer` — calls
      `repo.create`, emits audit `customer.created`, returns customer.
    * `async def update(tenant_id, user_id, customer_id, patch) -> Customer` — re-fetches to
      enforce tenant scope, computes diff for audit `customer.updated`.
    * `async def archive(tenant_id, user_id, customer_id) -> Customer` — audit `customer.archived`.
    * `async def restore(...)` — audit `customer.restored`.
    * `async def get(tenant_id, customer_id) -> Customer` — raises `CustomerNotFoundError`.
    * `async def list(tenant_id, *, search, archived, limit, offset) -> tuple[list[Customer], int]`.
  * Audit `details` payload must NEVER contain raw PII unless necessary; for now persist the diff
    (changed field names + before/after) but redact `notes` (free-text) when length > 256 chars.
* Create `src/office_hero/services/location_service.py`:
  * `class LocationService`:
    * `__init__(repo: LocationRepositoryProtocol, customer_repo, audit, geocoder)`.
    * `async def create(tenant_id, user_id, customer_id, address_fields, label, *,
      geocode: bool = True) -> Location`:
      * Verify customer exists (cross-tenant safety).
      * Insert row with `geocode_status="pending"`.
      * If `geocode=True`, call `geocoder.geocode(address)` synchronously; on success call
        `set_coordinates`, on failure call `mark_geocode_failed`. Both paths emit audit
        `location.created` (with `geocode_status` field).
      * If `geocode=False`, just emit `location.created` with status pending.
    * `async def update(tenant_id, user_id, location_id, patch, *, regeocode: bool = "auto")`:
      * `regeocode="auto"` re-geocodes when any address field changes; `regeocode=True` always;
        `regeocode=False` never.
      * Emits `location.updated` with diff.
    * `async def manual_set_coordinates(tenant_id, user_id, location_id, lat, lng) -> Location`
      — Dispatcher override; sets `geocode_source="manual"`, `geocode_status="manual"`. Emits
      `location.coordinates_set_manual` audit event.
    * `async def archive(...)`, `async def get(...)`, `async def list_for_customer(...)`.
* Create `src/office_hero/api/schemas/customer.py` — Pydantic v2 request/response schemas with
  `model_config = ConfigDict(extra="forbid")` (per HLD §Security A03):
  * `CustomerCreate` — `{name, email?, phone?, notes?}`. `name` min 1 / max 255.
  * `CustomerUpdate` — same fields, all optional. At least one must be set (model validator).
  * `CustomerRead` — full read view, `id`, `tenant_id`, `name`, `email`, `phone`, `notes`,
    `archived`, `external_id`, `created_at`, `updated_at`, embedded `locations: list[LocationRead]`
    only on detail endpoint (`include_locations=True`).
  * `CustomerList` — `{items: list[CustomerSummary], total: int, limit: int, offset: int}`.
  * `CustomerSummary` — id, name, location_count, primary_city (cheap projection).
* Create `src/office_hero/api/schemas/location.py`:
  * `LocationCreate` — `{customer_id: UUID, label?, street, street2?, city, state, postal_code,
    country (default "US"), geocode: bool = True}`.
  * `LocationUpdate` — all optional plus `regeocode: bool | "auto" = "auto"`.
  * `LocationCoordinatesSet` — `{lat: float (-90..90), lng: float (-180..180)}` (manual override).
  * `LocationRead` — full view including `lat`, `lng`, `geocode_status`, `geocode_source`.
* Create `src/office_hero/api/routes/customers.py` — `prefix="/customers"`, `tags=["customers"]`:
  * `POST /customers` — `@require_permission("customers:write")`; rate-limit `write` tier
    (60 req/min per slice 4 defaults).
  * `GET /customers` — `@require_permission("customers:read")`; query params `search`, `archived`,
    `limit (max 200)`, `offset`.
  * `GET /customers/{id}` — `@require_permission("customers:read")`; returns embedded locations.
  * `PATCH /customers/{id}` — `@require_permission("customers:write")`.
  * `POST /customers/{id}/archive` — `@require_role([TenantAdmin, Operator, OperatorStaff])`
    (archive is destructive-ish; restrict to admins).
  * `POST /customers/{id}/restore` — same role gate as archive.
* Create `src/office_hero/api/routes/locations.py` — `prefix=""`, `tags=["locations"]`:
  * `POST /customers/{customer_id}/locations` — `@require_permission("customers:write")`.
  * `GET /customers/{customer_id}/locations` — `@require_permission("customers:read")`.
  * `GET /locations/{id}` — `@require_permission("customers:read")`.
  * `PATCH /locations/{id}` — `@require_permission("customers:write")`.
  * `POST /locations/{id}/coordinates` — `@require_role([Dispatcher, TenantAdmin, Operator])` for
    manual override.
  * `POST /locations/{id}/regeocode` — `@require_role([Dispatcher, TenantAdmin, Operator])` to
    force re-geocoding (e.g. after correcting an address). Rate-limit at 5 req/min/user to
    protect the Nominatim quota.
  * `POST /locations/{id}/archive` — `@require_role([TenantAdmin, Operator, OperatorStaff])`.
* Register both routers in `src/office_hero/api/app.py`.
* Wire dependency providers in `src/office_hero/api/state.py`:
  * `get_customer_service() -> CustomerService`
  * `get_location_service() -> LocationService`
  * `get_geocoding_adapter() -> GeocodingAdapter` (built from settings).
* Create migration `alembic/versions/0004_customers_and_locations.py`:
  * Enable `CITEXT` extension if not already present (`CREATE EXTENSION IF NOT EXISTS citext;`).
  * Enable `pg_trgm` extension for trigram search.
  * Create `customers` table; columns per model above; `tenant_id` FK to `tenants(id)`.
  * Create unique partial index `uq_customer_tenant_email_active`
    ON `customers (tenant_id, lower(email))` WHERE `email IS NOT NULL AND archived = false`.
  * Create trigram GIN index `idx_customer_name_trgm`
    ON `customers USING GIN (name gin_trgm_ops)`.
  * `ALTER TABLE customers ENABLE ROW LEVEL SECURITY;`
  * `CREATE POLICY customer_tenant_isolation ON customers
       USING (tenant_id = current_setting('app.tenant_id')::uuid);`
  * Create `locations` table; FK to `customers(id) ON DELETE CASCADE`, FK to `tenants(id)`.
  * Index `idx_location_tenant_customer` ON `locations (tenant_id, customer_id)`.
  * Index `idx_location_tenant_status` ON `locations (tenant_id, geocode_status)`.
  * `ALTER TABLE locations ENABLE ROW LEVEL SECURITY;`
  * `CREATE POLICY location_tenant_isolation ON locations
       USING (tenant_id = current_setting('app.tenant_id')::uuid);`
  * Downgrade drops policies, indexes, tables in reverse order.
* Create unit tests in `tests/unit/`:
  * `tests/unit/test_customer_service.py`:
    * `test_create_customer_emits_audit_event`
    * `test_create_customer_rejects_duplicate_email_same_tenant`
    * `test_update_customer_redacts_long_notes_in_audit`
    * `test_archive_customer_sets_flag_and_audit`
    * `test_get_customer_cross_tenant_returns_not_found` (defence-in-depth, simulates RLS-bypass attempt)
    * `test_list_customer_search_matches_name_substring`
  * `tests/unit/test_location_service.py`:
    * `test_create_location_calls_geocoder_and_sets_coordinates`
    * `test_create_location_geocoder_failure_marks_failed_but_still_returns_location`
    * `test_create_location_geocode_false_skips_geocoder`
    * `test_update_location_address_auto_regeocodes`
    * `test_update_location_label_only_does_not_regeocode`
    * `test_manual_set_coordinates_overrides_geocoder_status`
    * `test_create_location_unknown_customer_raises`
    * `test_create_location_other_tenant_customer_raises_not_found`
  * `tests/unit/test_nominatim_adapter.py`:
    * `test_nominatim_returns_coordinates_on_match` (httpx mock)
    * `test_nominatim_returns_none_on_no_match`
    * `test_nominatim_rate_limit_one_per_second` (asserts second call waits ≥1s)
    * `test_nominatim_rejects_host_outside_allowlist` (SSRF)
    * `test_nominatim_timeout_raises_geocoding_error`
    * `test_nominatim_sends_user_agent_header` (Nominatim ToS)
* Create API tests in `tests/api/test_customers_api.py`:
  * `test_post_customer_requires_jwt` (401)
  * `test_post_customer_wrong_permission_403` (Sales role without `customers:write`)
  * `test_post_customer_201_and_returns_id`
  * `test_get_customer_cross_tenant_returns_404` (tenant A cannot see tenant B's customer)
  * `test_list_customers_pagination`
  * `test_list_customers_search`
  * `test_archive_then_restore_roundtrip`
  * `test_create_customer_rate_limit_60_per_min` (61st write returns 429)
* Create API tests in `tests/api/test_locations_api.py`:
  * `test_post_location_geocodes_and_returns_lat_lng` (using stub adapter)
  * `test_post_location_geocode_failure_still_returns_201_with_status_failed`
  * `test_get_locations_for_customer_other_tenant_404`
  * `test_manual_coordinates_requires_dispatcher_or_admin` (Technician 403)
  * `test_regeocode_endpoint_rate_limited_5_per_min`
  * `test_patch_location_address_triggers_regeocode`
* Integration test `tests/integration/test_customer_location_rls.py` (Neon branch):
  * `test_tenant_a_cannot_select_tenant_b_customer_via_rls` — set
    `app.tenant_id = tenantB_id`; `SELECT * FROM customers WHERE id = tenantA_customer_id`
    returns 0 rows (RLS hides the row, not 403 — silent isolation).
  * `test_cascade_delete_locations_when_customer_hard_deleted` (admin-only escape hatch, if/when
    a hard delete is exposed in a later slice).

## Structure

```text
src/office_hero/
├── adapters/
│   └── geocoding/
│       ├── __init__.py
│       ├── protocol.py        # GeocodingAdapter Protocol + AddressInput, Coordinates
│       ├── nominatim.py       # NominatimGeocodingAdapter (default)
│       ├── ors.py             # ORSGeocodingAdapter (stubbed, future)
│       ├── stub.py            # StubGeocodingAdapter (deterministic, tests)
│       └── factory.py         # build_geocoding_adapter(settings)
├── models/
│   ├── customer.py            # Customer ORM model
│   └── location.py            # Location ORM model
├── repositories/
│   ├── customer_repository.py
│   └── location_repository.py
├── services/
│   ├── customer_service.py
│   └── location_service.py
├── api/
│   ├── schemas/
│   │   ├── customer.py
│   │   └── location.py
│   └── routes/
│       ├── customers.py
│       └── locations.py
└── core/
    └── exceptions.py          # +GeocodingError, +CustomerNotFoundError, +LocationNotFoundError

alembic/
└── versions/
    └── 0004_customers_and_locations.py

tests/
├── unit/
│   ├── test_customer_service.py
│   ├── test_location_service.py
│   └── test_nominatim_adapter.py
├── api/
│   ├── test_customers_api.py
│   └── test_locations_api.py
└── integration/
    └── test_customer_location_rls.py
```

## Failing Test Outline

```python
# tests/unit/test_location_service.py
import pytest
from uuid import uuid4
from office_hero.services.location_service import LocationService
from office_hero.adapters.geocoding.stub import StubGeocodingAdapter


@pytest.mark.asyncio
async def test_create_location_calls_geocoder_and_sets_coordinates(
    location_repo, customer_repo, audit_service
):
    """LocationService.create geocodes the address and persists lat/lng."""
    svc = LocationService(location_repo, customer_repo, audit_service, StubGeocodingAdapter())
    cust = await customer_repo.create(tenant_id=TENANT_A, name="Acme Plumbing", ...)
    loc = await svc.create(
        tenant_id=TENANT_A, user_id=USER_A, customer_id=cust.id,
        address_fields={"street": "123 Main St", "city": "Philadelphia",
                        "state": "PA", "postal_code": "19103", "country": "US"},
        label="Main Office",
    )
    assert loc.lat is not None and loc.lng is not None
    assert loc.geocode_status == "ok"
    assert loc.geocode_source == "stub"
    assert any(e.event_type == "location.created" for e in audit_service.events)


@pytest.mark.asyncio
async def test_create_location_other_tenant_customer_raises(
    location_repo, customer_repo, audit_service
):
    """Creating a location for a customer in another tenant raises CustomerNotFoundError."""
    svc = LocationService(location_repo, customer_repo, audit_service, StubGeocodingAdapter())
    cust = await customer_repo.create(tenant_id=TENANT_A, name="Acme", ...)
    with pytest.raises(CustomerNotFoundError):
        await svc.create(
            tenant_id=TENANT_B, user_id=USER_B, customer_id=cust.id,
            address_fields={...}, label="x",
        )


# tests/api/test_customers_api.py
def test_get_customer_cross_tenant_returns_404(client, tenant_a_token, tenant_b_customer_id):
    """Tenant A cannot see Tenant B's customer; RLS hides → 404 (not 403)."""
    resp = client.get(
        f"/customers/{tenant_b_customer_id}",
        headers={"Authorization": f"Bearer {tenant_a_token}"},
    )
    assert resp.status_code == 404
```

## Dependencies

* **Slice 2 (Database foundation)** — async engine, `get_session`, RLS helper, Alembic env.
* **Slice 3 (Auth & RBAC)** — JWT middleware, `@require_role` / `@require_permission`, `Role` enum,
  `tenant_id` request state.
* **Slice 4 (Observability)** — `AuditService`, structured logging, security headers, slowapi
  limiter (write tier defaults).
* **Slice 7 (Tenant management)** — `tenants` table + provisioning (required for FK on
  `customers.tenant_id`).
* Relevant ADRs: **053** (RLS), **058** (SQLAlchemy 2.x), **059** (PostgreSQL JSONB / CITEXT /
  pg_trgm), **060** (RBAC), **062** (rate limiting tiers), **063** (audit events).

## Effort

Estimate: **2/5**. Two tables, one adapter family, two services, two routers. The geocoding
adapter is the only externally-coupled component; everything else is canonical CRUD over RLS.
The main effort is comprehensive TDD coverage (≈14 unit + 14 API tests) and getting the
Nominatim rate-limit semaphore correct so we never trip their ToS in CI. The migration is
slightly non-trivial because of `citext` and `pg_trgm` extension handling.

## Risk Callouts

* **Nominatim usage policy.** 1 req/sec hard ceiling and a *real* `User-Agent` are required;
  Nominatim aggressively blocks abusive clients. The adapter enforces both, and tests assert
  the rate-limit sleeper. **Mitigation:** stub adapter is the default in CI; live calls are
  guarded by `GEOCODING_ADAPTER=nominatim` (off by default in tests).
* **SSRF risk in geocoder.** Adapter base URL is operator-configurable; allowlist enforcement
  on construction prevents pointing the geocoder at an internal IP. Tested explicitly.
* **PII in audit log.** `customer.notes` may contain free-form PII; we truncate long notes in
  the audit `details` payload. Reviewed against ADR 063.
* **Email uniqueness.** Scoped per tenant + only enforced when email is non-null and customer
  is not archived. Confirm with stakeholders that two active customers in the same tenant cannot
  share an email — if there's a real-world case (e.g. spouses on one billing email), drop the
  partial-unique index. **OPEN QUESTION** flagged in PR.
* **Re-geocoding on update.** Auto-regeocode behaviour could create unbounded background work
  if a power user mass-updates addresses. Rate-limit on the API endpoint (5 req/min) plus
  audit logging makes this auditable. Bulk import flows in a later slice will need a different
  pattern (queue-based, separate worker).

---

Once approved, implementation proceeds with the failing unit tests for `CustomerService`,
then the model + repository + migration, then `LocationService` with the stub geocoder, then
the Nominatim adapter under TDD, and finally the API routers. The integration test for RLS
runs against a Neon branch in CI.
