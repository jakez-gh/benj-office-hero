---
docType: slice-plan
parent: ../project-guides/002-spec.office-hero.md
project: office-hero
dateCreated: 20260308
dateUpdated: 20260308
status: not_started
---

# Slice Plan: Office Hero

## Parent Document

[002-spec.office-hero.md](../project-guides/002-spec.office-hero.md)
HLD: [050-arch.hld-office-hero.md](050-arch.hld-office-hero.md)

---

## Foundation Work

Must be complete before any feature slices begin.
Each foundation slice leaves the system in a runnable, tested state.

1. [ ] **Python project scaffold** — Package structure (`src/office_hero/`), pyproject.toml,
   Dockerfile, Fly.io config, environment config via pydantic-settings, Makefile targets.
   Dependencies: none. Effort: 1/5

2. [ ] **Database foundation** — Neon connection, SQLAlchemy async session factory,
   Alembic migration workflow, base `tenant_id` column pattern, RLS policy helpers,
   per-request session context. Integration test infrastructure (Neon branch per CI run).
   Dependencies: Slice 1. Effort: 2/5

3. [ ] **Auth & RBAC** — JWT issue/validate, bcrypt password hashing, `@require_role`
   / `@require_permission` decorators, Tenant context middleware (sets `app.tenant_id`
   from JWT), all six roles defined. Dependencies: Slices 1–2. Effort: 2/5

4. [ ] **Observability foundation** — structlog structured logging (JSON, request-id),
   `GET /health` endpoint (DB + ORS reachability), global FastAPI exception handler,
   request-id middleware. Dependencies: Slices 1–2. Effort: 1/5

5. [ ] **Frontend scaffold** — pnpm monorepo (`packages/api-client`, `packages/types`,
   `apps/admin-web`, `apps/tech-web`, `apps/tech-mobile`), TypeScript config, ESLint,
   Prettier, shared API client skeleton. Dependencies: Slice 1. Effort: 2/5

6. [ ] **Mobile app scaffold** — React Native Expo project (`apps/tech-mobile`),
   Android build config, `expo-location` background permission setup (tested on device
   early — known to require OS-level configuration). Dependencies: Slice 5. Effort: 2/5

---

## Feature Slices

Ordered by dependency and value. Each slice is independently demonstrable.

### Platform / Operator

7. [ ] **Tenant management** — Operator CRUD for Tenants; Tenant provisioning creates
   DB schema, sets back\_office\_adapter. Dependencies: Slices 1–4. Risk: Low. Effort: 2/5

8. [ ] **User management** — TenantAdmin CRUD for Users within their Tenant (all roles
   except Operator). Self-registration disabled by default (Operator or TenantAdmin
   invites). Dependencies: Slices 3, 7. Risk: Low. Effort: 2/5

### Core FSM

9. [ ] **Customer & Location management** — CRUD for Customers and their Locations
   (geocoded lat/lng via ORS or Nominatim). RLS enforced. Dependencies: Slices 2–3, 7.
   Risk: Low. Effort: 2/5

10. [ ] **Job management (core CRUD)** — Create/read/update/cancel Jobs; industry-specific
    `custom_fields` JSONB with per-industry templates; Job status lifecycle (pending →
    scheduled → in\_progress → complete / cancelled). Dependencies: Slices 3, 7, 9.
    Risk: Low. Effort: 3/5

11. [ ] **Contract management** — Recurring service agreements; scheduled Job generation
    (cron-style); links to Customer + service type + frequency. Dependencies: Slice 10.
    Risk: Medium. Effort: 3/5

12. [ ] **Vehicle & VehicleCrew management** — CRUD for Vehicles; daily crew assignment
    (VehicleCrew: Vehicle + Technicians + date + roles). Dependencies: Slices 3, 7–8.
    Risk: Low. Effort: 2/5

### Dispatch & Routing

13. [ ] **Routing engine integration** — ORS adapter (`RoutingAdapter` protocol + ORS
    HTTP client); `POST /jobs/{id}/routing-options` returns three ranked options
    (nearest, earliest-completion, balanced-load). Unit tests mock adapter.
    Dependencies: Slices 4, 10, 12. Risk: High. Effort: 3/5

14. [ ] **Dispatch & Route management** — Commit dispatch (creates/updates Route +
    RouteStops); Route status lifecycle; TenantAdmin selects option or enters custom
    fourth; `GET /routes` for daily view. Dependencies: Slice 13. Risk: Medium. Effort: 3/5

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
    Dependencies: Slices 5, 9–10, 13–14. Risk: Medium. Effort: 3/5

21. [ ] **Tenant Admin web — Dispatch dashboard** — Route board view (all Vehicles + their
    Routes for the day), drag-and-drop resequencing, live Vehicle positions (polling),
    day-of exception handling UI. Dependencies: Slices 12–16, 20. Risk: High. Effort: 4/5

22. [ ] **Technician web view** — Lighter React view: own Route for the day, Job details,
    basic Job entry. Separate from Technician Android app; useful for desktop/laptop use.
    Dependencies: Slices 5, 14. Risk: Low. Effort: 2/5

### AI Integration

23. [ ] **MCP server** — Python MCP server wrapping the REST API as MCP tools.
    Auto-generated from FastAPI's OpenAPI spec where possible; manual tools for
    complex operations (dispatch, routing). Same auth/RBAC as API.
    Dependencies: Slices 3, 10, 14. Risk: Medium. Effort: 3/5

---

## Back-Office Integration Slices

Each integration is a separate slice. All implement the `BackOfficeAdapter` protocol.

24. [ ] **BackOfficeAdapter protocol** — Define the full protocol ABC; refactor all
    existing code to call the NativeAdapter through it (NativeAdapter is already
    the default; this slice makes the seam explicit and tested).
    Dependencies: Slices 10–12. Risk: Medium. Effort: 2/5

25. [ ] **ServiceTitan integration** — Adapter implementing BackOfficeAdapter against
    the ServiceTitan API. Field mapping, auth, error handling.
    Dependencies: Slice 24. Risk: High. Effort: 4/5

26. [ ] **PestPac integration** — Adapter for PestPac API.
    Dependencies: Slice 24. Risk: High. Effort: 4/5

27. [ ] **Jobber integration** — Adapter for Jobber API.
    Dependencies: Slice 24. Risk: High. Effort: 4/5

*(Additional integrations added as future work entries below.)*

---

## Integration Work

28. [ ] **E2E test suite** — Playwright (web) + Detox or Maestro (mobile) covering
    core flows: Job entry → dispatch → Technician receives Route → location update.
    Dependencies: Slices 17–22. Effort: 3/5

29. [ ] **Deployment automation** — Fly.io deployment pipeline (GitHub Actions);
    Neon branch promotion (dev → production); zero-downtime deploys via Fly.io
    rolling restart. Dependencies: Slice 1. Effort: 2/5

30. [ ] **Monitoring & alerting** — Sentry error tracking (free tier); Fly.io metrics
    dashboard; uptime check against `GET /health`; SLO reporting (99.5% target).
    Dependencies: Slices 4, 29. Effort: 2/5

---

## Notes

- Slices 1–6 (Foundation) must be done in order. All others can proceed in
  parallel once their listed dependencies are met.
- Back-office integration slices (24–27) are gated on Slice 24 (protocol),
  which itself is gated on the core FSM slices being stable.
- Dynamic re-routing (Slice 16) is the highest-effort single feature slice
  and should be prototyped early to surface complexity.
- Mobile location tracking (Slice 18) is marked High risk because background
  location on Android requires OS-level permissions that can vary by device/OS
  version — test on real hardware as early as possible.

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
