---
id: 1.1.4
title: Research — ServiceTitan API
type: research
parent: 1.1
status: complete
researchId: RES-025
topic: ServiceTitan REST API
question: >
  What do we need to know about ServiceTitan's auth, rate limits, Customer and
  Job entity models, webhook support, and sandbox environment before designing
  the BackOfficeAdapter for Slice 25?
sources:
  - https://developer.servicetitan.io/docs/oauth20/
  - https://developer.servicetitan.io/docs/get-going-first-api-call/
  - https://partnerapis.servicetitan.io/docs/timeouts-and-pagination/
  - https://developer.servicetitan.io/docs/faqs-environments/
  - https://developer-next.servicetitan.io/docs/webhooks/
  - https://developer-next.servicetitan.io/docs/faqs-v2-webhooks/
  - https://developer.servicetitan.io/docs/api-resources-crm/
  - https://developer.servicetitan.io/docs/api-resources-job-planning/
  - https://prismatic.io/docs/components/servicetitan/
  - https://help.servicetitan.com/problem-solution/what-are-the-default-api-rate-limits-in-servicetitan-for-regular-apis-and
dateCreated: 20260617
dateUpdated: 20260617
---

# Research: ServiceTitan REST API (Slice 25)

## Summary — 5 decision-ready bullets

1. **Auth is 4-credential client_credentials.** No user context, no refresh tokens.
   Token lifetime is 900 s; token endpoint is rate-throttled, so the adapter must
   cache per-tenant and re-fetch proactively at ~840 s. Common trap: form-urlencoded
   body required — JSON body returns 400 even when Postman works.

2. **Customer ≠ Location; technician is on Appointment, not Job.** Jobs link to
   `locationId` (not customer address). Syncing a job fully requires three resources:
   Customer → Location → Job + Appointment. The adapter must handle this hierarchy.
   Customer has no native `externalId` — use `externalData[applicationGuid]` to store
   the Office Hero UUID. Jobs do have `externalId` directly.

3. **Webhooks exist (V2) and are recommended, but polling is still needed.** V1
   webhooks are deprecated 2026-03-31. V2 supports HMAC-SHA256 and exponential retry
   (10 s → 30 s → 60 s → 300 s then drop), but makes no at-least-once guarantee
   beyond the retry window. Hybrid approach: webhooks for low-latency delivery +
   `modifiedOnOrAfter` polling as reconciliation pass.

4. **No server-side idempotency key.** The adapter cannot use a header like Stripe's
   `Idempotency-Key`. On a retry, it must query `externalData` before issuing a POST
   to check whether the record was already created. The Outbox `idem_key` should be
   stored in `externalData` so re-deliveries resolve cleanly.

5. **Slice 25 requires a DB migration.** The `tenants.back_office_adapter` column has
   a CHECK constraint listing known adapter names. Adding `"servicetitan"` to the
   registry must be paired with a migration that adds it to the constraint.

---

## Findings

### Authentication

- **Grant type:** `client_credentials` only — machine-to-machine.
- **Credentials per tenant:** `CLIENT_ID`, `CLIENT_SECRET`, `ST-App-Key` (header),
  `TENANT_ID` (URL path). Per-tenant: `CLIENT_ID`/`CLIENT_SECRET` are unique per
  ServiceTitan tenant; `ST-App-Key` is shared across tenants for the same application.
- **Token endpoints:**
  - Sandbox: `https://auth-integration.servicetitan.io/connect/token`
  - Production: `https://auth.servicetitan.io/connect/token`
- **Token lifetime:** 900 seconds. No refresh token issued; re-POST credentials.
- **Token caching:** mandatory — the token endpoint is separately rate-throttled.
  Cache with 60 s early-refresh buffer (re-fetch at t = 840 s after issue).
- **Body format:** `application/x-www-form-urlencoded` only. JSON body silently fails.
- **Headers on every API call:** `Authorization: Bearer <token>` and
  `ST-App-Key: <app-key>`.
- **Secret lifecycle:** visible only once at creation; max 2 active secrets (plan for
  blue/green rotation).

### Rate Limits

| API type | Limit |
| -------- | ----- |
| Standard (CRUD, lists) | 60 req/s per application per tenant |
| Reporting API | 1 identical report/min per tenant |
| Token endpoint | Rate-throttled (exact limit undocumented) |

- 429 on breach. `Retry-After` header presence is unconfirmed — implement exponential
  backoff with jitter regardless.
- Per-tenant buckets are independent: 5 tenants → 5 × 60 RPS independently.
- Operate at ~50 RPS sustained per tenant to give headroom.

### Customer Entity

- **Namespace/endpoint:** `GET /crm/v2/tenant/{tenantId}/customers`
- **Key fields:** `id` (integer), `name`, `active`, `type`, `address` (object),
  `contacts` (array — phone/email not top-level), `customFields`, `createdOn`,
  `modifiedOn`
- **externalId:** No native `externalId` on Customer. Use
  `externalData: [{ applicationGuid, key, value }]` to store internal Office Hero UUID.
- **Locations:** Every customer has ≥1 `Location` (separate entity). Jobs reference
  `locationId` not the customer address. Sync requires `POST /crm/v2/tenant/{id}/locations`
  after creating the customer.
- **Delta sync:** `?modifiedOnOrAfter=<ISO8601>` — but note: contact/membership
  updates do NOT increment `modifiedOn` on the customer record (requires separate
  Contacts/Memberships polling if those change independently).
- **Pagination:** offset-based. `page` (1-indexed), `pageSize` (1–5000, default 50),
  `ids` (comma-separated batch lookup).

### Job / Work Order Entity

- **Namespace/endpoint:** `GET /jpm/v2/tenant/{tenantId}/jobs`
- **Key fields:** `id` (integer), `number` (human), `status` (enum), `customerId`,
  `locationId`, `externalId` (string — use this for Office Hero Job UUID), `summary`,
  `jobType`, `priority`, `customFields`, `createdOn`, `modifiedOn`
- **Job status enum:** `Scheduled`, `InProgress`, `Completed`, `Hold`, `Canceled`
- **Technician assignment:** NOT on the Job — on the Appointment sub-resource.
  `GET /jpm/v2/tenant/{tenantId}/appointments?jobId={id}` — appointment has
  `status`, `assignedTechnicians[]`, `startTime`, `endTime`.
- **Appointment status enum:** `Scheduled`, `Dispatched`, `Working`, `Done`, `Hold`,
  `Canceled`, `Unused`
- **externalId on Job:** native string field — store Office Hero Job UUID here.
- **Delta sync:** `?modifiedOnOrAfter=<ISO8601>` works for incremental polling.

### Webhooks

- **V1:** deprecated 2026-03-31 — do not use.
- **V2:** production-ready. Self-service subscription in dev portal. HMAC-SHA256
  signature in `x-servicetitan-signature` header; compute HMAC of raw payload.
- **Confirmed V2 events:** `job.created`, `job.updated`. Customer events exist but
  exact catalog requires portal access to enumerate.
- **Retry on non-2xx:** 10 s → 30 s → 60 s → 300 s, then drop. No dead-letter queue
  outside the manual replay window in the portal.
- **Reliability:** no at-least-once guarantee beyond the retry window. Polling
  reconciliation is required for production use.
- **Recommended pattern:** webhooks (primary, low-latency) + `modifiedOnOrAfter`
  polling every N minutes (gap-fill / reconciliation). This is standard across all
  production ServiceTitan integrations reviewed.

### Sandbox Environment

- **Domain:** `https://api-integration.servicetitan.io` (separate from production)
- **Access:** request at `developer.servicetitan.io` — ServiceTitan provisions one
  integration environment per developer org.
- **Key caveat:** the sandbox is a **shared instance** across all developers.
  Seed data can be polluted; specific record IDs should not be hardcoded in tests.
- **Credentials:** separate `CLIENT_ID`/`CLIENT_SECRET` from production; same
  `ST-App-Key`.

### Namespace → URL Map

| Domain | URL Namespace |
| ------ | ------------- |
| Customers, Locations, Bookings | `crm` |
| Jobs, Appointments, Projects | `jpm` |
| Invoices, Payments | `accounting` |
| Technicians, Business Units | `settings` |
| Dispatch | `dispatch` |
| Equipment | `equipment-systems` |
| Supply Chain / POs | `supplychain` |

### Existing Codebase Constraints

**BackOfficeAdapter Protocol** (`src/office_hero/adapters/back_office/__init__.py`):

```python
# Adapter dataclasses (thin — only fields the protocol currently needs)
@dataclass
class Customer:
    id: UUID
    name: str

@dataclass
class Job:
    id: UUID
    customer_id: UUID

# Protocol methods (all async):
async def health_check(self) -> bool
async def get_customer(self, id: UUID) -> Customer | None
async def create_customer(self, customer: Customer) -> Customer
async def update_customer(self, customer: Customer) -> Customer
async def delete_customer(self, id: UUID) -> None
async def get_job(self, id: UUID) -> Job | None
async def create_job(self, job: Job) -> Job
async def update_job(self, job: Job) -> Job
async def delete_job(self, id: UUID) -> None
```

**Adapter registry** (`src/office_hero/adapters/back_office/registry.py`):

```python
AdapterFactory = Callable[[UUID, Any, Any], BackOfficeAdapter]
# Registration:
register_adapter("servicetitan", ServiceTitanAdapter.from_tenant)
```

**Outbox event types the adapter must handle:**

- `backoffice.customer.created` → `adapter.create_customer(...)`
- `backoffice.customer.updated` → `adapter.update_customer(...)`
- `backoffice.job.created` → `adapter.create_job(...)`
- `backoffice.contract.created` → `adapter.create_job(...)` (contracts sync as jobs)

Every event payload includes `idem_key` (UUID string). Forward this as idempotency
key — no server-side header equivalent exists in ServiceTitan; instead, query
`externalData` before POST to detect already-created records.

**`tenants.back_office_adapter` CHECK constraint:** adding `"servicetitan"` to the
registry requires a migration to update the constraint. Slice 25 must include this.

**ADR 056 hard constraints:**

- No direct HTTP calls outside `adapters/back_office/`
- All cross-system steps are SagaSteps with compensating transactions
- Max 5 outbox delivery attempts before dead-lettering
- `external_id` on Customer/Job models is where ServiceTitan's integer ID is stored

---

## Open Questions

1. **V2 webhook customer event names** — exact event types for customer
   create/update are not documented in public pages; need sandbox access to confirm.
2. **externalData query syntax** — does ST support `?externalData.key=X&externalData.value=Y`
   on list endpoints? Prismatic docs imply yes but the official docs don't show the
   exact filter parameter names.
3. **Rate limit 429 headers** — `Retry-After` presence unconfirmed. Test in sandbox
   before implementing backoff strategy.
4. **Location sync scope** — does the slice need to sync Locations (for the
   Customer → Location hierarchy) or does it leave Locations as pass-through using
   Office Hero's existing `location_id` on the Job?

---

## Recommended Next Step

Gate G2 is satisfied — proceed to write the slice design
(`026-slice.servicetitan-integration.md`) when `SERVICETITAN_*` credentials are
available. No new ADR is warranted; the existing ADR 056 (Saga + Outbox) covers the
architectural approach. The design should specify:

- Token cache layer (per-tenant, 840 s TTL, form-urlencoded enforcement)
- `externalData`-based idempotency check in `create_customer` / `create_job`
- Hybrid webhook + polling sync strategy
- DB migration to add `"servicetitan"` to the `back_office_adapter` CHECK constraint
- Location creation as part of the Customer sync step
