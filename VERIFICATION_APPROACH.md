# Office Hero Slice 14 - Verification Approach

**Document Type:** Verification Strategy  
**Scope:** Dispatch & Route Management (Slice 14)  
**Date:** June 2, 2026  
**Status:** In Progress

---

## Executive Summary

Slice 14 (Dispatch & Route Management) has been **code-complete and merged to main** with all identified issues fixed. This document outlines the verification strategy to validate the implementation from API contract through end-to-end UI flow.

**Key Artifacts:**
- Merged code: 9 commits with focused changes
- Comprehensive code review: 8 critical issues identified and fixed
- Ready for runtime verification

---

## Verification Phases

### Phase 1: Environment Setup ✅ Prerequisite
Before running tests, ensure:
- Poetry environment installed with dependencies
- PostgreSQL running with migrations applied
- FastAPI server running on localhost:8000
- Frontend dev servers running (admin-web, tech-web)

### Phase 2: API Contract Testing (Immediate)
Verify all 8 REST endpoints match their specification:
- Request validation (422 on invalid input)
- Response schema correctness
- HTTP status codes (200, 404, 409, 422, 403)
- RBAC enforcement (role-based access control)

**Tools:** pytest + httpx AsyncClient  
**Coverage:** Happy path + 3 error cases per endpoint  
**Est. Time:** 45 minutes

### Phase 3: Service Layer Testing (Immediate)
Unit test the DispatchService without database:
- Option mode: routing option selection and validation
- Manual mode: sequence validation and error handling
- Route lifecycle: state transitions and guards
- Stop lifecycle: status progression and auto-completion
- Idempotency: repeated requests return same result

**Tools:** pytest with in-memory repositories  
**Coverage:** All public methods + error paths  
**Est. Time:** 30 minutes

### Phase 4: UI/Frontend Testing (Depends on servers)
Integration test the admin and technician UIs:
- Admin dispatch interface: create job → select option → route created
- Route board: list routes, view details, manage stops
- Technician view: see assigned route, mark stops, auto-complete
- Error states: invalid input, concurrent conflicts, network failures

**Tools:** Playwright (Chrome/Firefox/Safari)  
**Coverage:** Happy path + 3 error cases per UI flow  
**Est. Time:** 45 minutes

### Phase 5: End-to-End Flow (Depends on full stack)
Test the complete MVP workflow:
1. Admin creates customer + location
2. Admin creates job
3. System shows 3 routing options
4. Admin selects option → route created
5. Technician views route
6. Technician marks all stops complete
7. Route auto-completes
8. Admin sees completed route

**Tools:** Playwright + API client  
**Acceptance:** All 8 steps succeed without errors  
**Est. Time:** 60 minutes

### Phase 6: Regression Testing (Immediate)
Verify existing slices still work:
- Job creation (Slice 10): create → view → edit
- Routing (Slice 13): get options → validate ranking
- Vehicles (Slice 12): list → edit crew → verify assignments
- Admin job entry (Slice 20): unchanged UI/UX
- Tech web view (Slice 22): unchanged UI/UX

**Tools:** Smoke tests via pytest  
**Coverage:** Happy path only  
**Est. Time:** 30 minutes

---

## Test Organization

```
tests/
├── api/
│   ├── test_dispatch_api.py          (existing - Slice 14 job dispatch)
│   └── test_routes_api.py            (NEW - Slice 14 route endpoints)
├── services/
│   └── test_dispatch_service.py      (NEW - DispatchService unit tests)
├── integration/
│   └── test_routes_e2e.py            (NEW - End-to-end flows)
└── ui/
    ├── test_admin_dispatch.py        (NEW - Admin UI flows)
    └── test_tech_route_view.py       (NEW - Technician UI flows)
```

---

## Success Criteria

### Code Coverage
- [ ] All route endpoints tested (happy + error paths)
- [ ] All service methods tested with in-memory repos
- [ ] Error responses validated for correctness
- [ ] RBAC enforced on all protected routes

### Functionality
- [ ] Route CRUD operations work correctly
- [ ] State transitions follow specification
- [ ] Atomic transactions hold on failure
- [ ] Idempotency prevents duplicate routes
- [ ] Audit trail captures all changes

### Integration
- [ ] Full MVP flow completes end-to-end
- [ ] UI renders without errors
- [ ] Frontend properly calls backend APIs
- [ ] Data persists across session boundaries

### Regression
- [ ] No breaking changes to existing API
- [ ] Existing UI flows unchanged
- [ ] Job creation still works
- [ ] Routing options unaffected

---

## Risk Factors

### High Risk
1. **API Contract Mismatch** — Endpoints return wrong status code or schema
   - Mitigation: Test 8 endpoints × 3 error cases = 24 test cases
   
2. **Frontend Integration** — UI doesn't call APIs correctly
   - Mitigation: Use Playwright to drive actual UI, inspect network tab

3. **Database Migrations** — Schema mismatch or missing constraints
   - Mitigation: Run migrations fresh, verify schema with SQL

### Medium Risk
1. **Async/Await Issues** — Race conditions in concurrent dispatch
   - Mitigation: Test concurrent dispatch with same sequence (idempotency)

2. **RLS Policy Gaps** — Technician can see other tenant's routes
   - Mitigation: Create 2 tenants, verify isolation in both

### Low Risk
1. **Documentation** — Swagger/OpenAPI spec mismatches
   - Mitigation: Run `sq review code` on changes

---

## Test Execution Order

1. **API Contract Tests** (Phase 2) — Immediate, validates endpoints work
2. **Service Unit Tests** (Phase 3) — Immediate, validates logic
3. **Regression Tests** (Phase 6) — Immediate, ensures no breakage
4. **UI Tests** (Phase 4) — Depends on servers, validates UX
5. **E2E Tests** (Phase 5) — Full stack only, validates integration

---

## Tools & Infrastructure

| Tool | Purpose | Status |
|------|---------|--------|
| pytest | Unit/integration tests | Ready (existing) |
| httpx | Async HTTP client | Ready (dependency) |
| Playwright | UI automation | Ready (dependency) |
| PostgreSQL | Database | External (pre-requisite) |
| FastAPI | Backend server | Built (pre-requisite) |
| React | Frontend | Built (pre-requisite) |

---

## Next Steps

1. **Immediate (Today):** Run API contract + service unit tests
2. **If servers running:** Run UI tests + regression tests
3. **If full stack up:** Run end-to-end tests
4. **Completion:** All phases green → mark Slice 14 complete → proceed to Slice 15

---

**Owner:** Mara  
**Last Updated:** 2026-06-02  
**Status:** Ready for execution
