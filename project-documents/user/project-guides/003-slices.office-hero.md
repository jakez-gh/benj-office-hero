---
docType: slice-plan
parent: 002-spec.office-hero.md
hld: ../architecture/050-arch.hld-office-hero.md
project: office-hero
dateCreated: 20260308
dateUpdated: 20260308
status: not_started
---

# Slice Plan: Office Hero

## Parent Document

[002-spec.office-hero.md](002-spec.office-hero.md)
HLD: [050-arch.hld-office-hero.md](../architecture/050-arch.hld-office-hero.md)

---

## GUI Visibility Strategy

> **Principle:** Users and stakeholders should see a working UI as early as possible.
> Slice 5 (Frontend scaffold) produces a running React app, but it shows nothing meaningful.
> Slice 5a (Admin web shell) adds login + navigation immediately after Auth is working.
> All subsequent feature slices deliver visible UI alongside their API work wherever
> the dependency chain allows.

---

## Foundation Work

Must be complete before any feature slices begin.
Each foundation slice leaves the system in a runnable, tested state.

1. [ ] **Python project scaffold** — Package structure (`src/office_hero/`), pyproject.toml,
   Dockerfile, Fly.io config, environment config via pydantic-settings, Makefile targets.
   `outbox_events` and `saga_log` tables included in initial migration (required by back-office
   slices). Dependencies: none. Effort: 1/5

1a. [ ] **CLI & tooling baseline** — `tools/` directory with a simple Python CLI for
   migrations, health checks, and operator maintenance commands; shared code for
   generating JWTs and invoking the REST API. Establishes the presentation-tier CLI
   mentioned in the concept. Dependencies: Slice 1. Effort: 1/5

2. [ ] **Database foundation** — Neon connection, SQLAlchemy async session factory,
   Alembic migration workflow, base `tenant_id` column pattern, RLS policy helpers,
   per-request session context. `outbox_events` + `saga_log` migrations (see ADR 056).
   Integration test infrastructure (Neon branch per CI run).
   Dependencies: Slice 1. Effort: 2/5

3. [ ] **Auth & RBAC** — JWT RS256 issue/validate, bcrypt password hashing,
   `@require_role` / `@require_permission` decorators, Tenant context middleware
   (sets `app.tenant_id` from JWT), all six roles defined, rate limiting on auth
   endpoints (`slowapi`), refresh token support (15 min access / 7 day refresh).
   Dependencies: Slices 1–2. Effort: 2/5

4. [ ] **Observability & security middleware foundation** — structlog structured logging
   (JSON, request-id), `GET /health` endpoint (DB + ORS reachability), global FastAPI
   exception handler (no stack traces to client), request-id middleware, CSP/security
   headers middleware (`X-Frame-Options`, `X-Content-Type-Options`, `Content-Security-Policy`),
   and basic `slowapi` integration wired to the RateLimitManager with database table and
   cache hooks ready to accept operator-configurable limits. Dependencies: Slices 1–2.
   Effort: 1/5

5. [ ] **Frontend scaffold** — pnpm monorepo (`packages/api-client`, `packages/types`,
   `apps/admin-web`, `apps/tech-web`, `apps/tech-mobile`), TypeScript config, ESLint,
   Prettier, shared API client skeleton. Dependencies: Slice 1. Effort: 2/5

5a. [ ] **Admin web shell (login + navigation stub)** — **EARLY GUI VISIBILITY.**
    Working login page connected to real JWT auth, top-level navigation shell with
    placeholder pages for all major sections (Jobs, Dispatch, Vehicles, Users).
    Demonstrates full auth flow end-to-end. Deployable and demeable after this slice.
    Dependencies: Slices 3, 5. Risk: Low. Effort: 2/5

6. [ ] **Mobile app scaffold** — React Native Expo project (`apps/tech-mobile`),
   Android build config, `expo-location` background permission setup (tested on device
   early — known to require OS-level configuration). Dependencies: Slice 5. Effort: 2/5

---

## Feature Slices

Ordered by dependency and value. Each slice is independently demonstrable.

### Platform / Operator

7. [ ] **Tenant management** — Operator CRUD for Tenants; Tenant provisioning creates
   DB schema, sets back\_office\_adapter. Dependencies: Slices 1–4. Risk: Low. Effort: 2/5

7a. [ ] **Operator observability dashboard** — Metrics & log viewer with live control panel
   (rate-limit adjustments, ban filter management) and an audit-log tab. Provides quick
   access to health metrics and enables operators to alter protection rules at runtime.
   Dependencies: Slices 3–4. Risk: Medium. Effort: 3/5

8. [ ] **User management** — TenantAdmin CRUD for Users within their Tenant (all roles
   except Operator). Includes role-builder UI allowing TenantAdmins to create and modify
   tenant‑scoped roles/permission sets. Self-registration disabled by default (Operator or
   TenantAdmin invites). **GUI:** User list + invite form in Admin web shell (depends on 5a).
   Dependencies: Slices 3, 7. Risk: Low. Effort: 2/5

### Core FSM

9. [ ] **Customer & Location management** — CRUD for Customers and their Locations
   (geocoded lat/lng via ORS or Nominatim). RLS enforced. **GUI:** Customer list +
   create form visible in Admin web. Dependencies: Slices 2–3, 7. Risk: Low. Effort: 2/5

10. [ ] **Job management (core CRUD)** — Create/read/update/cancel Jobs; industry-specific
    `custom_fields` JSONB with per-industry templates; Job status lifecycle (pending →
    scheduled → in\_progress → complete / cancelled). **GUI:** Job list + create/edit
    forms. Dependencies: Slices 3, 7, 9. Risk: Low. Effort: 3/5

11. [ ] **Contract management** — Recurring service agreements; scheduled Job generation
    (cron-style); links to Customer + service type + frequency.
    Dependencies: Slice 10. Risk: Medium. Effort: 3/5

12. [ ] **Vehicle & VehicleCrew management** — CRUD for Vehicles; daily crew assignment
    (VehicleCrew: Vehicle + Technicians + date + roles). **GUI:** Vehicle list + crew
    assignment UI. Dependencies: Slices 3, 7–8. Risk: Low. Effort: 2/5

### Dispatch & Routing

13. [ ] **Routing engine integration** — ORS adapter (`RoutingAdapter` protocol + ORS
    HTTP client, with SSRF allowlist); `POST /jobs/{id}/routing-options` returns three
    ranked options (nearest, earliest-completion, balanced-load). Unit tests mock adapter.
    Dependencies: Slices 4, 10, 12. Risk: High. Effort: 3/5

14. [ ] **Dispatch & Route management** — Commit dispatch (creates/updates Route +
    RouteStops); Route status lifecycle; TenantAdmin selects option or enters custom
    fourth; `GET /routes` for daily view. **GUI:** Route selection UI in Admin web.
    Dependencies: Slice 13. Risk: Medium. Effort: 3/5

15. [ ] **Vehicle location tracking** — `PUT /vehicles/{id}/location` endpoint;
    VehicleLocation time-series storage; latest-position query for routing engine.
    Dependencies: Slices 2, 12. Risk: Low. Effort: 2/5

16. [ ] **Dynamic re-routing** — Day-of event handling (Technician sick → reassign
    Route; Job cancelled → update Route; emergency Job added → re-route); presents new
    options via routing engine. Dependencies: Slices 13–15. Risk: High. Effort: 4/5

### Mobile & Technician App

17. [ ] **Technician Android app — Route view** — React Native Expo: auth, view own
    daily Route, view Job details per stop, acknowledge route. Uses shared API client.
    Dependencies: Slices 5–6, 8, 14. Risk: Medium. Effort: 3/5

18. [ ] **Technician Android app — Location tracking** — Background `expo-location`
    posting to `PUT /vehicles/{id}/location` on configurable interval. Handles
    foreground/background/off-route states. Dependencies: Slices 6, 15, 17.
    Risk: High. Effort: 3/5

19. [ ] **Technician Android app — Job entry in field** — Technician creates new Job
    from mobile; triggers routing options flow. Dependencies: Slices 10, 17.
    Risk: Low. Effort: 2/5

### Web GUIs

20. [ ] **Tenant Admin web — Job entry & customer lookup** — React SPA: search/create
    Customer + Location, enter Job, view routing options, dispatch. Uses shared API client.
    Dependencies: Slices 5a, 9–10, 13–14. Risk: Medium. Effort: 3/5

21. [ ] **Tenant Admin web — Dispatch dashboard** — Route board view (all Vehicles + their
    Routes for the day), drag-and-drop resequencing, live Vehicle positions (polling),
    day-of exception handling UI. Dependencies: Slices 12–16, 20. Risk: High. Effort: 4/5

22. [ ] **Technician web view** — Lighter React view: own Route for the day, Job details,
    basic Job entry. Separate from Technician Android app; useful for desktop/laptop use.
    Dependencies: Slices 5a, 14. Risk: Low. Effort: 2/5

### AI Integration

23. [ ] **MCP server** — Python MCP server wrapping the REST API as MCP tools.
    Auto-generated from FastAPI's OpenAPI spec where possible; manual tools for
    complex operations (dispatch, routing). Same auth/RBAC as API.
    Dependencies: Slices 3, 10, 14. Risk: Medium. Effort: 3/5

---

## Back-Office Integration Slices

Each integration is a separate slice. All implement the `BackOfficeAdapter` protocol.

 > **Risk note (see ADR 056):** Back-office integrations involve multi-step distributed
> operations (create in Office Hero + create in external system). Each integration slice
> **must** implement the Saga pattern with compensating transactions and the Transactional
> Outbox pattern for reliable event delivery. Idempotency keys are required on all
> external API calls. The ordering of steps within each Saga is critical — skipping or
> reordering steps can cause data inconsistency that is expensive to repair.
>
> Each integration slice must include:
>
> - Saga orchestrator class for all multi-step operations
> - Compensating transaction for every Saga step
> - Idempotency key generation and storage in `outbox_events`
> - Integration test simulating failure at each Saga step
> - Dead-letter handling via `GET /admin/dead-letters` (Operator-only)

24. [ ] **BackOfficeAdapter protocol** — Define the full protocol ABC; refactor all
    existing code to call the NativeAdapter through it (NativeAdapter is already
    the default; this slice makes the seam explicit and tested). Includes `health_check()`
    method and Saga base class.
    Dependencies: Slices 10–12. Risk: Medium. Effort: 2/5

25. [ ] **ServiceTitan integration** — Adapter implementing BackOfficeAdapter against
    the ServiceTitan API. Saga orchestrator for Customer sync + Job/Work Order sync.
    Field mapping, auth, error handling, dead-letter UI.
    Dependencies: Slice 24. Risk: High. Effort: 5/5

26. [ ] **PestPac integration** — Adapter for PestPac API. Saga orchestrator for
    Customer, Service Order, and Contract sync.
    Dependencies: Slice 24. Risk: High. Effort: 5/5

27. [ ] **Jobber integration** — Adapter for Jobber API. Saga orchestrator for
    Customer and Job sync.
    Dependencies: Slice 24. Risk: High. Effort: 4/5

*(Additional integrations added as future work entries below.)*

---

## Integration Work

28. [ ] **E2E test suite** — Full cross-platform coverage across all client types.
    Emulator setup is a prerequisite (see `950-tasks.maintenance.md`):

    - **Android** — Maestro against Android Emulator (AVD). Auth, Route view,
      Job entry, location tracking (foreground + background).
    - **iOS** — Maestro against iOS Simulator (Xcode/macOS required). Same
      flows as Android. Gated on iOS Expo build being enabled.
    - **Web** — Playwright (Chromium + Firefox + WebKit). Login, Job entry,
      routing options, dispatch, Dispatch dashboard drag-and-drop.
    - **API** — pytest + httpx AsyncClient against live test environment. All
      endpoint contracts, auth flows, RBAC enforcement, rate limiting responses.
    - **MCP** — pytest invokes MCP tools against test environment. Tool
      discovery, auth passthrough, response schema validation.

    Core flow (all platforms): Job entry → routing options → dispatch →
    Technician receives Route → location update posted.
    Dependencies: Slices 17–22. Effort: 4/5

29. [ ] **Deployment automation** — Fly.io deployment pipeline (GitHub Actions);
    Neon branch promotion (dev → production); zero-downtime deploys via Fly.io
    rolling restart. Dependencies: Slice 1. Effort: 2/5

30. [ ] **Monitoring & alerting** — Sentry error tracking (free tier); Fly.io metrics
    dashboard; uptime check against `GET /health`; SLO reporting (99.5% target);
    dead-letter growth alerting (back-office Saga failures).
    Dependencies: Slices 4, 29. Effort: 2/5

---

## Notes

- Slices 1–6 (Foundation) must be done in order. All others can proceed in
  parallel once their listed dependencies are met.
- Slice 5a (Admin web shell) is inserted between Foundation and Feature slices to
  give stakeholders a working GUI as early as possible. It can be worked in parallel
  with Slice 6 (Mobile scaffold).
- Back-office integration slices (25–27) are gated on Slice 24 (protocol),
  which itself is gated on the core FSM slices being stable.
- Dynamic re-routing (Slice 16) is the highest-effort single feature slice
  and should be prototyped early to surface complexity.
- Mobile location tracking (Slice 18) is marked High risk because background
  location on Android requires OS-level permissions that can vary by device/OS
  version — test on real hardware as early as possible.
- Back-office integration slices are upgraded to 5/5 effort (from 4/5) due to
  the Saga + Outbox pattern requirement. See ADR 056.

---

## Parallel Work Streams

Once Foundation slices 1–4 are complete, work can proceed in parallel across streams.
Use git worktrees to run independent context sessions without conflict:

| Stream | Branch | Slices | Notes |
| ------ | ------ | ------ | ----- |
| Backend core | `stream/backend-core` | 7–16 | API + DB only |
| Frontend | `stream/frontend` | 5a, 8–10, 20–22 | React SPA |
| Mobile | `stream/mobile` | 6, 17–19 | React Native Expo |
| Back-office | `stream/backoffice` | 24–27 | After FSM stable |
| AI/MCP | `stream/ai` | 23 | After core dispatching works |

See `docs/worktrees.md` for setup instructions.

---

## Future Work

Items to track for later planning cycles:

1. [ ] **Tenant Admin native mobile app** — If the responsive web admin view proves
   insufficient on phone. React Native Expo already ready; estimate Effort: 3/5
2. [ ] **iOS support** — Extend React Native Expo builds to iOS via EAS Build.
   Effort: 2/5 (same codebase, new build target)
3. [ ] **Self-hosted ORS** — When community ORS rate limits or latency become
   problematic. Fly.io deployment of ORS Docker image. Effort: 2/5
4. [ ] **FieldEdge integration** — BackOfficeAdapter for FieldEdge.
5. [ ] **ServiceMax integration** — BackOfficeAdapter for ServiceMax.
6. [ ] **Real-time Route updates via WebSocket** — Upgrade from polling if Tenants
   report Route-update lag as an issue. Effort: 2/5
7. [ ] **Tenant-facing analytics dashboard** — Job completion rates, technician
   utilisation, route efficiency metrics.
