---
id: RES-026
type: research
parent: INIT-001
status: complete
researchId: RES-026
topic: PestPac (WorkWave Service) REST API
question: >
  What do we need to know about PestPac's (WorkWave Service's) auth, rate limits,
  Customer/Location entity model, Service Order/Work Order entity model, webhook
  support, and sandbox availability before designing the BackOfficeAdapter for
  Slice 26?
sources:
  - https://developer.workwave.com/
  - https://sandbox-api.service.workwave.com/Help
  - https://prod-api.service.workwave.com/Help/Api/GET-api-public-v1-workorders-id
  - https://wwrm.workwave.com/api/
  - https://www.pestpac.com/api-integrations
  - https://leadmanagerhelp.clickpointsoftware.com/en/articles/5776541-pestpac-by-workwave
dateCreated: 20260617
dateUpdated: 20260617
---

# Research: PestPac (WorkWave Service) API (Slice 26)

## Summary — 5 decision-ready bullets

1. **Auth is API Key via `X-API-Key` header for the Odyssey API.** Third-party
   integration docs also document a 7-credential tuple (API Key + Tenant ID +
   Client ID + Client Secret + Username + Password + Host URL), suggesting the
   legacy API layer uses a richer flow. Both surfaces appear to coexist. Full
   developer docs require login at `developer.workwave.com` — API access requires
   contacting `APISales@workwave.com` (30-day free trial available).

2. **PestPac's term for Customer is "Location" (BillTo Location).** The entity
   model is a two-level hierarchy: BillTo Location (billing account, analogous to
   our Customer) → ServiceLocation (physical address, analogous to a job site).
   **Required fields on create: Division, Source, Type, and at least one phone.**
   No native `externalId` field is documented — the adapter must maintain a
   UUID-to-PestPac-ID mapping table or use `LocationCode`.

3. **PestPac's term for Job is "Service" (agreement) or "Work Order" (individual
   visit).** The Odyssey API exposes `GET /api/public/v1/workorders/{id}`. No
   native `externalId` on Work Orders — same mapping-table constraint applies.
   `create_job()` likely targets `POST /api/public/v1/workorders` (inferred from
   REST conventions; unconfirmed without authenticated access).

4. **Most critical unknown: synchronous vs. asynchronous response model.** The
   WWRM sibling API returns a `requestId` immediately (async) rather than the
   created entity. If the Odyssey API follows the same pattern, the
   BackOfficeAdapter's `create_customer` / `create_job` cannot return the created
   entity synchronously — the adapter contract would need redesign. This blocks
   implementation design and must be confirmed via sandbox access.

5. **No server-side idempotency key.** The adapter must implement GET-before-POST
   idempotency: query by stored PestPac ID before issuing a create call. API
   access is metered per call/day (additional cost beyond base fee), so
   unnecessary calls should be minimized. Webhooks confirmed to exist (HMAC-SHA256
   pattern from the WWRM sibling platform) but event catalog for the Odyssey
   surface is not publicly documented.

---

## Findings

### Authentication

- **Odyssey API auth:** `X-API-Key` header. Key is obtained from the PestPac
  Users master screen in the tenant's PestPac account.
- **Legacy / partner-tier auth tuple** (seen in third-party integration docs):
  - API Key
  - Tenant ID (6-digit PestPac Company Key)
  - Client ID
  - Client Secret
  - Username (PestPac user account)
  - Password
  - Host URL (tenant-specific base URL)
- **Token lifetime:** Not applicable for API Key; unknown if OAuth2 layer issues
  expiring tokens.
- **Token endpoint:** Unconfirmed for Odyssey API (no public token endpoint URL).
- **API access gating:** Not freely available. Contact `APISales@workwave.com`
  for a 30-day trial. Ongoing usage incurs per-call pricing beyond the base fee.

| Environment | Base URL |
| ----------- | -------- |
| Production  | `https://prod-api.service.workwave.com/api/public/v1` |
| Sandbox     | `https://sandbox-api.service.workwave.com/api/public/v1` |

### Rate Limits

No published rate limit figures for the Odyssey/PestPac API were found in public
documentation. The WWRM sibling API uses a leaky-bucket algorithm (example:
bucket size 5, refill 1 per 5 minutes per endpoint) and returns HTTP 429 with a
queue cap of 10.

The pricing model ("additional costs dependent on data access and API calls per
day") implies a **daily quota-based model** rather than per-second rate limits.
Exact quotas require contacting WorkWave.

**Implementation rule:** exponential backoff with jitter on any 429 response,
regardless of confirmed limits.

### Customer / Location Entity

- **PestPac term:** "Location" (specifically "BillTo Location")
- **Endpoint (inferred):** `POST /api/public/v1/locations` (unconfirmed; Odyssey
  docs require auth to view)
- **Entity hierarchy:**
  - `BillTo Location` — the billing account; our Customer maps here
  - `ServiceLocation` — the physical address where work is performed; maps to our
    Job's location

| Field | Notes |
| ----- | ----- |
| `LocationCode` | PestPac-assigned integer identifier |
| `Division` | Required on create |
| `Source` | Required on create |
| `Type` | Required on create |
| `Phone` / `AlternatePhone` / `MobilePhone` | At least one required |
| `CompanyKey` | 6-digit tenant identifier; required on all requests |

- **ExternalId:** No native `externalId` or `externalRef` field documented
  publicly. The adapter must maintain a separate mapping table
  (`pestpac_entity_map`) or store the `LocationCode` in the outbox event record.

### Service / Work Order Entity

- **PestPac terms:** "Service" (the recurring/one-time service agreement) and
  "Work Order" / "Service Order" (individual scheduled visit instance)
- **Confirmed Odyssey endpoint:** `GET /api/public/v1/workorders/{id}` (URL
  confirmed in search index; full docs require auth)
- **Our `create_job()` mapping:** Most likely targets `POST /api/public/v1/workorders`
  (inferred from REST conventions; must confirm with sandbox access)

| Field | Notes |
| ----- | ----- |
| `WorkOrderId` | PestPac-assigned integer ID |
| `LocationCode` | Links to the BillTo Location (customer) |
| `ServiceDate` / `ScheduledDate` | Visit date |
| `Status` | Enum; exact values unconfirmed without auth access |
| `ServiceType` / `Description` | Service category |
| `AssignedEmployee` / `TechnicianId` | Technician assignment |

- **ExternalId:** No native `externalId` field documented. Same mapping-table
  constraint as Customer/Location.
- **Status enum:** Exact values unconfirmed. Likely includes Scheduled, Completed,
  Cancelled, Open, Closed — must confirm via sandbox.

### Webhooks

- **Available:** Confirmed on PestPac marketing page ("Receive notifications of
  updates to your data via webhooks").
- **Pattern (from WWRM sibling platform):**
  - POST callback URL registration
  - HMAC-SHA256 optional signature via `signaturePassword` parameter → `signature`
    query param on callback
  - 5 retries at 20/40/60/80/100 s then drop
  - JSON payload with `requestId`, `event`, `data`
- **Odyssey-specific event catalog:** Not publicly documented. Contact WorkWave
  or check sandbox to enumerate available event types.
- **Recommended pattern:** Use webhooks for inbound sync (PestPac → Office Hero
  status changes) once sandbox access is established. Out of scope for the initial
  Outbox-driven write path.

### Sandbox Environment

- **Available:** Confirmed — `https://sandbox-api.service.workwave.com/Help`
  is accessible.
- **Access:** Provisioned via 30-day trial from `APISales@workwave.com`, or
  request sandbox-only access separately.
- **Caveat:** Sandbox appears to share the same API surface as production (only
  the host prefix changes). No isolated data — treat as a shared integration
  environment.

---

## Codebase Constraints

**BackOfficeAdapter Protocol** — the adapter must implement all 9 async methods
with `Customer(id: UUID, name: str)` and `Job(id: UUID, customer_id: UUID)`.

**Key design implications for PestPac:**

1. **UUID-to-PestPac-ID mapping table required.** No native `externalId` field
   on Location or WorkOrder means the adapter cannot encode our internal UUID in
   the PestPac record. A `pestpac_entity_map` table (or equivalent) with columns
   `tenant_id`, `entity_type`, `internal_id UUID`, `pestpac_id INTEGER` is
   required. This is a new migration.

2. **Multi-credential config.** A `PestPacAdapterConfig` Pydantic model with
   all credential fields (at minimum: `api_key`, `company_key`, `host_url`; full
   7-field tuple if legacy flow is required). Store in Fly.io secrets per tenant.

3. **Synchronous vs. async response model (CRITICAL BLOCKER).** If the Odyssey
   API returns a `requestId` rather than the created entity (like the WWRM
   sibling), the `create_customer`/`create_job` return type cannot be satisfied
   synchronously. This requires either:
   - Polling the Odyssey API for completion (adds latency and complexity), or
   - Redesigning the adapter's return contract to allow `None` on async creates
     (breaking change to the Protocol)

   **Resolve this via sandbox before writing any HTTP call code.**

4. **Required fields on Location create.** Our `Customer(id, name)` model doesn't
   carry Division, Source, or Type. The adapter must either hardcode sensible
   defaults per tenant or add a `PestPacAdapterConfig` field for each. Coordinate
   with the tenant onboarding flow.

5. **`tenants.back_office_adapter` CHECK constraint migration.** Adding
   `"pestpac"` to the adapter registry requires a new Alembic migration.

**Outbox event types the adapter handles:**

- `backoffice.customer.created` → `adapter.create_customer(...)` → POST to
  PestPac Location, store returned `LocationCode` in `pestpac_entity_map`
- `backoffice.customer.updated` → `adapter.update_customer(...)` → PATCH Location
- `backoffice.job.created` → `adapter.create_job(...)` → POST to PestPac
  WorkOrder, store `WorkOrderId`
- `backoffice.contract.created` → `adapter.create_job(...)` (contracts sync as
  work orders/services)

---

## Open Questions

1. **Synchronous vs. async Odyssey API response model.** Does `POST
   /api/public/v1/workorders` return the created entity immediately, or a
   `requestId` (like the WWRM API)? This is the single most critical unknown
   and blocks adapter contract design.

2. **ExternalId field availability.** Is there any metadata bag or custom field
   on Location or WorkOrder that can store our internal UUID, avoiding a mapping
   table?

3. **Exact credential requirements.** Does the Odyssey API require only
   `X-API-Key`, or the full 7-credential tuple? The discrepancy between sources
   needs resolution before writing the config model.

4. **Exact Work Order status enum values** for the Odyssey API.

5. **Daily API call quota and overage pricing.** What is the included daily call
   count before overage charges?

6. **Webhook event catalog for Odyssey API.** Do Location and WorkOrder CRUD
   events exist? What are the exact topic names?

7. **Service vs. Work Order for `create_job()`.** Should we create a Service
   (the agreement/contract) or a Work Order (individual visit)? This affects
   whether `create_job()` targets the services endpoint or workorders endpoint.

---

## Recommended Next Step

Gate G2 is **not fully satisfied** — the synchronous/asynchronous response model
question blocks adapter contract design. Do NOT write the Slice 26 design or any
HTTP call code until sandbox access is obtained and this question is resolved.

**Immediate actions (no credentials needed):**

1. Write the `PestPacAdapterConfig` Pydantic model (credential fields stub).
2. Write the `pestpac_entity_map` Alembic migration (UUID ↔ PestPac integer ID).
3. Write the `tenants.back_office_adapter` CHECK constraint migration to add
   `"pestpac"`.

**Blocked on sandbox access (`APISales@workwave.com`):**

- Confirm sync vs. async response model
- Confirm externalId availability
- Confirm exact credential requirements
- Enumerate webhook event catalog

No new ADR is warranted. ADR 056 (Saga + Outbox) covers the architectural
approach. The potential sync/async response model issue may require an ADR
amendment if the Protocol contract needs changing.
