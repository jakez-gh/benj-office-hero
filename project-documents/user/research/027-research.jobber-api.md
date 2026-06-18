---
id: 1.1.6
title: Research — Jobber API
type: research
parent: 1.1
status: complete
researchId: RES-027
topic: Jobber GraphQL API
question: >
  What do we need to know about Jobber's OAuth2 flow, rate limits, Client and Job
  entity models, webhook support, and sandbox availability before designing the
  BackOfficeAdapter for Slice 27?
sources:
  - https://developer.getjobber.com/docs/building_your_app/app_authorization/
  - https://developer.getjobber.com/docs/building_your_app/refresh_token_rotation/
  - https://developer.getjobber.com/docs/using_jobbers_api/api_rate_limits/
  - https://developer.getjobber.com/docs/using_jobbers_api/api_queries_and_mutations/
  - https://developer.getjobber.com/docs/using_jobbers_api/custom_fields/
  - https://developer.getjobber.com/docs/using_jobbers_api/setting_up_webhooks/
  - https://developer.getjobber.com/docs/building_your_app/testing_your_app/
  - https://dev.to/jobber/refresh-token-rotation-what-why-and-how-2eh
  - https://rollout.com/integration-guides/jobber/api-essentials
  - https://github.com/GetJobber/Jobber-AppTemplate-RailsAPI
dateCreated: 20260617
dateUpdated: 20260617
---

# Research: Jobber GraphQL API (Slice 27)

## Summary — 5 decision-ready bullets

1. **OAuth2 authorization_code with mandatory refresh token rotation.** Access
   tokens expire in 60 minutes; refresh token rotation means each refresh issues
   a new refresh token that invalidates the previous one immediately. Per-tenant
   tokens must be stored in the DB (new `jobber_credentials` table) and written
   atomically on every refresh. If both tokens expire (user disconnects), the
   tenant must re-authorize via browser — no programmatic recovery.

2. **Jobber is GraphQL, not REST.** Single endpoint:
   `https://api.getjobber.com/api/graphql`. Requires `X-JOBBER-GRAPHQL-VERSION`
   header (date-format, e.g. `2023-11-15`). Two independent rate limiters:
   (a) DDoS layer — 2,500 requests/5 min per app+account; (b) query cost leaky
   bucket — 10,000 points max, 500 points/sec restore. The adapter must read
   `extensions.cost.throttleStatus` on every response and back off before the
   bucket empties.

3. **No native externalId on Client or Job.** The Jobber-recommended pattern is
   to create a Text-type app-configured custom field (`hero_client_id`,
   `hero_job_id`) via `customFieldConfigurationCreate` on first connection, then
   pass the value in every `clientCreate`/`jobCreate` input. Custom field
   bootstrap must run once per tenant on `APP_CONNECT`, idempotently. This also
   enables the GET-before-POST idempotency guard: query by custom field value
   before each create mutation.

4. **`delete_customer` / `delete_job` map to soft-delete only.** Jobber exposes
   `clientArchive` and `jobArchive` — there are no hard-delete mutations.
   `get_customer` after archiving may not find the record in the standard `clients`
   query; the adapter must handle this gracefully (return `None`).

5. **No server-side idempotency keys.** The adapter must implement
   try-fetch-before-create for all create mutations: query by `hero_client_id` /
   `hero_job_id` custom field value before calling `clientCreate` / `jobCreate`.
   `jobCreate` also requires the Jobber-encoded Client ID (not our UUID) — the
   adapter needs a `jobber_entity_map` table (internal UUID ↔ Jobber opaque ID)
   to resolve this on every job create.

---

## Findings

### Authentication

- **Flow:** OAuth2 `authorization_code` — requires browser-based tenant
  authorization (the tenant admin must click through a Jobber consent screen once
  per app registration).
- **Token endpoint:** `https://api.getjobber.com/api/oauth/token`
- **Authorize endpoint:** `https://api.getjobber.com/api/oauth/authorize`
- **Access token lifetime:** 3,600 seconds (60 minutes)
- **Refresh token rotation:** MANDATORY for Jobber App Marketplace apps. Each
  call to the token endpoint with `grant_type=refresh_token` returns a brand-new
  `refresh_token` that immediately invalidates the previous one. The adapter must
  write the new token pair atomically before making any subsequent API call.
- **Scopes required:**
  - `read_clients` / `write_clients`
  - `read_jobs` / `write_jobs`
  - `custom_field_configurations_read_write` (to create `hero_client_id` /
    `hero_job_id` custom field configs on first connect)
  - Exact scope string names (e.g. `read_clients` vs `clients:read`) must be
    confirmed in Developer Center — docs describe them conceptually only.

### Rate Limits

Two independent limiters run simultaneously:

| Layer | Limit | Response |
| ----- | ----- | -------- |
| DDoS middleware | 2,500 requests / 5 minutes per app+account | HTTP 429 |
| GraphQL query cost (leaky bucket) | 10,000 points max; 500 points/sec restore | `throttleStatus` in `extensions` |

The query cost layer is the binding constraint for non-trivial workloads.
Deeply nested queries (e.g. client → jobs → visits) compound cost exponentially.
Keep all adapter queries and mutations shallow (one level of nesting maximum).

**Required adapter behavior:** After every GraphQL response, read
`response.extensions.cost.throttleStatus.currentlyAvailable`. If the next
expected query cost exceeds the available points, sleep for
`(needed - available) / restoreRate` seconds before proceeding.

### Client Entity

- **GraphQL type:** `Client`
- **Create mutation:** `clientCreate(input: ClientCreateInput!) -> ClientCreatePayload`
- **Update mutation:** `clientEdit(input: ClientEditInput!) -> ClientEditPayload`
- **Delete mutation:** `clientArchive(id: ID!) -> ClientArchivePayload` (soft-delete)
- **Fetch:** `client(id: ID!)` / `clients(filter: ...) { nodes { ... } pageInfo { ... } }`
- **ExternalId:** No native field. Use app-configured custom field:
  1. On APP_CONNECT: call `customFieldConfigurationCreate` with `label: "hero_client_id"`, `type: TEXT`, `appliesTo: CLIENT`.
  2. On every `clientCreate`: pass `customFields: [{ configurationId: <cfgId>, value: <our UUID> }]`.
  3. For idempotency guard: query `clients(filter: { customField: { ... } })` by `hero_client_id` value before creating.

**Key input fields for `clientCreate`:**

| Field | Notes |
| ----- | ----- |
| `firstName` / `lastName` | Split from `Customer.name` if it contains a space |
| `companyName` | Used if `Customer.name` has no space |
| `emails[]` | Optional |
| `phones[]` | Optional |
| `billingAddress` | Optional |
| `customFields[]` | Pass `hero_client_id` here |

### Job Entity

- **GraphQL type:** `Job`
- **Create mutation:** `jobCreate(input: JobCreateInput!) -> JobCreatePayload`
- **Update mutation:** `jobEdit(input: JobEditInput!) -> JobEditPayload`
- **Delete mutation:** `jobArchive(id: ID!) -> JobArchivePayload` (soft-delete)
- **Fetch:** `job(id: ID!)` / `jobs { nodes { ... } pageInfo { ... } }`
- **ExternalId:** No native field. Same custom field pattern — `hero_job_id` on `JOB` object.
- **Critical constraint:** `jobCreate` requires the Jobber-encoded Client ID
  (`clientId: ID!`), not our internal UUID. The adapter must look up the Jobber
  Client ID from `jobber_entity_map` before calling `jobCreate`.

**Key fields:**

| Field | Notes |
| ----- | ----- |
| `id` | Jobber opaque encoded ID (not an integer — do not parse) |
| `jobNumber` | Auto-assigned sequential integer (human-readable) |
| `title` | Job description |
| `client { id }` | Links to Client |
| `jobStatus` | Status enum (see below) |
| `startAt` / `endAt` | ISO8601DateTime |
| `customFields[]` | Includes `hero_job_id` |

**Job status enum** (inferred from Jobber help docs; confirm via GraphiQL
introspection):

```
unscheduled | scheduled | active | completed | archived | requires_invoicing | late
```

### Webhooks

- **Available:** Yes.
- **Registration:** Configured via Developer Center UI per application — not via
  GraphQL mutation. Select `WebHookTopicEnum` values in the UI.
- **Authentication:** `X-Jobber-Hmac-SHA256` header — base64-encoded HMAC-SHA256
  of the raw request payload, keyed with the app's OAuth `client_secret`.
- **Response deadline:** 1 second — use an async task queue for processing.
- **Payload structure:** `{ topic, app_id, account_id, item_id, occurred_at }`
  — the `item_id` is the Jobber entity ID. Fetch full entity via GraphQL on receipt.

**Key webhook topics:**

| Topic | Trigger |
| ----- | ------- |
| `APP_CONNECT` | Tenant installs/authorizes the app (use for custom field bootstrap) |
| `CLIENT_CREATE` | New client created in Jobber |
| `JOB_CREATE` | New job created in Jobber |
| `JOB_COMPLETE` | Job marked complete |
| `QUOTE_CREATE` | New quote (out of scope) |
| `INVOICE_CREATE` | New invoice (out of scope) |

Webhooks enable inbound sync (Jobber → Office Hero) but are **out of scope for
the Outbox-driven write path** (Office Hero → Jobber).

### Sandbox / Test Environment

- **Available:** Yes — special developer test account (separate from a 14-day
  trial).
- **Access:** Sign up at `https://developer.getjobber.com/signup/` or email
  `api-support@getjobber.com` to convert an existing trial.
- **Important caveat:** No isolated sandbox URL — the developer test account
  connects to the **same GraphQL endpoint** (`https://api.getjobber.com/api/graphql`)
  as production. Mutations create real records in the test account.
- **GraphiQL playground:** Available from Developer Center > Manage Apps >
  Test in Playground. Use for schema introspection and mutation testing.

### GraphQL Specifics

- **Endpoint:** `https://api.getjobber.com/api/graphql` (POST only)
- **Auth header:** `Authorization: Bearer <access_token>`
- **Version header:** `X-JOBBER-GRAPHQL-VERSION: <YYYY-MM-DD>` (REQUIRED — omit
  and Jobber silently upgrades to earliest supported version)
- **Known current version:** `2023-11-15` (latest confirmed; check changelog at
  `developer.getjobber.com/docs/changelog/` before implementing)
- **Version support:** 12–18 months; deprecation warnings appear 3 months before
  EOL in `response.extensions`
- **Pagination:** Relay cursor-based (`Connection / nodes / pageInfo { hasNextPage
  endCursor }`)
- **Error handling:** `errors[]` array at root + `userErrors[]` on mutation
  payloads + `throttleStatus` in `extensions.cost`
- **HTTP client:** Use `httpx.AsyncClient` (already a project dependency) with a
  thin GraphQL wrapper — no SDK required, but `gql` library is an option.

---

## Codebase Constraints

1. **New `jobber_credentials` table.** Per-tenant encrypted token storage:
   `tenant_id`, `access_token`, `refresh_token`, `expires_at`. Must support
   atomic write on token refresh (use `SELECT ... FOR UPDATE` or optimistic lock).

2. **New `jobber_entity_map` table.** UUID ↔ Jobber opaque ID mapping:
   `tenant_id`, `entity_type ENUM('client','job')`, `internal_id UUID`,
   `jobber_id VARCHAR`. Required for `create_job` to resolve Jobber Client ID,
   and for all idempotency guards.

3. **Custom field bootstrap on `APP_CONNECT`.** When the APP_CONNECT webhook
   fires (or on first adapter call): create `hero_client_id` (Client) and
   `hero_job_id` (Job) custom field configurations via
   `customFieldConfigurationCreate`. Must be idempotent — check if the config
   already exists before creating.

4. **Throttle-backoff middleware.** A wrapper around every GraphQL call that reads
   `extensions.cost.throttleStatus` and sleeps before the next call if needed.
   This should be a reusable component, not copy-pasted per method.

5. **`tenants.back_office_adapter` CHECK constraint migration.** Adding
   `"jobber"` to the registry requires a new Alembic migration.

6. **All async.** The adapter must use `httpx.AsyncClient` — no blocking HTTP
   calls in the event loop.

7. **Soft-delete mapping.** `delete_customer` → `clientArchive`,
   `delete_job` → `jobArchive`. After archiving, the record may not appear in
   standard list queries — `get_customer`/`get_job` must handle `None` gracefully.

8. **`create_job` requires 2-step resolution.**
   1. Look up Jobber Client ID from `jobber_entity_map` by `customer_id` UUID.
   2. Call `jobCreate` with the resolved Jobber Client ID.
   If the client isn't in the map yet (race condition), the saga step must retry
   or fail with a retryable error.

**Outbox event types the adapter handles:**

- `backoffice.customer.created` → `adapter.create_customer(...)` → `clientCreate`
  mutation; store Jobber Client ID in `jobber_entity_map`
- `backoffice.customer.updated` → `adapter.update_customer(...)` → `clientEdit`
- `backoffice.job.created` → `adapter.create_job(...)` → resolve Client ID →
  `jobCreate`; store Jobber Job ID in `jobber_entity_map`
- `backoffice.contract.created` → `adapter.create_job(...)` (same as above)

---

## Open Questions

1. **Exact scope string names** (e.g. `read_clients` vs `clients:read`) — check
   Developer Center UI at app registration time.

2. **Latest API version string** — check changelog at
   `developer.getjobber.com/docs/changelog/` before implementing; `2023-11-15`
   is the newest confirmed from third-party sources.

3. **Custom field queryability** — does Jobber support
   `clients(filter: { customField: { configId: X, value: Y } })`? This would
   enable efficient `hero_client_id` lookup without full pagination scan. If not,
   the idempotency guard requires scanning all clients and filtering client-side.

4. **HTTP status on expired access token** — 401 or 403? Affects token-refresh
   trigger logic.

5. **Exact `JobStatusTypeEnum` values** — confirm via GraphiQL introspection
   (unscheduled, scheduled, active, completed, archived, late are inferred, not
   confirmed).

6. **`clientArchive` and list query visibility** — does archiving a client
   exclude it from `clients { nodes { ... } }` by default? Affects `get_customer`
   implementation.

7. **Batch mutations** — does Jobber support multiple `clientCreate` in one
   request to reduce cost-point consumption? Not documented publicly.

---

## Recommended Next Step

Gate G2 is satisfied — Jobber's API is fully publicly documented and all
decision-blocking questions have clear enough answers to write the slice design.
The open questions above are implementation details that can be resolved via
GraphiQL introspection once a developer test account is provisioned.

Proceed to write `027-slice.jobber-integration.md` when `JOBBER_*` credentials
are available. The design should specify:

- OAuth2 authorization_code flow with browser-initiated tenant connect
- `jobber_credentials` table schema with atomic token refresh
- `jobber_entity_map` table schema
- Custom field bootstrap sequence on `APP_CONNECT` webhook
- Throttle-backoff middleware design (shared across all GraphQL calls)
- Idempotency guard pattern (query by custom field before every create mutation)
- DB migration to add `"jobber"` to `tenants.back_office_adapter` CHECK constraint
- Soft-delete mapping (`delete_customer`/`delete_job` → `clientArchive`/`jobArchive`)

No new ADR required — ADR 056 (Saga + Outbox) and ADR 060 (JWT / Auth) cover the
architectural approach. The OAuth2 token rotation pattern is a well-known
implementation detail, not an architectural decision.
