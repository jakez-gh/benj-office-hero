---
slice: e2e-test-suite
project: office-hero
lld: ../slices/029-slice.e2e-test-suite.md
dependencies: [17, 18, 19, 20, 21, 22]
projectState: >
  All feature slices (17-25) are complete. Playwright E2E (Chromium + Firefox
  + WebKit) is fully configured and running on main branch pushes. Remaining E2E
  work requires a live Fly.io test environment or hardware emulators.
dateCreated: 20260617
dateUpdated: 20260617
status: in_progress
docType: tasks
---

## Context Summary

Full E2E test suite. Playwright browser tests are already green. Remaining work
is API-level pytest against live Fly.io env, MCP integration tests, and
mobile Maestro tests (all require external resources).

---

## Task Breakdown

### Already complete

- [x] Playwright E2E — Chromium + Firefox + WebKit configured in `playwright.config.ts`
- [x] Playwright CI — all three browsers run on `push` to main (`.github/workflows/`)
- [x] Screenshot regression tests — pre-push hook regenerates on UI changes

### API pytest against live env (needs Fly.io test env)

- [ ] Provision a `office-hero-test` Fly.io app with dedicated test DB
- [ ] Add `LIVE_TEST_API_URL` + `LIVE_TEST_ADMIN_TOKEN` GitHub secrets
- [ ] `tests/e2e/test_live_api.py` — tenant lifecycle, job dispatch, route creation
- [ ] CI job that runs live-env tests on schedule (not on every push)

### MCP integration tests (needs live env)

- [ ] `tests/e2e/test_mcp_tools.py` — tool discovery, auth passthrough, JSON-Schema compliance
- [ ] Run as part of the scheduled live-env CI job

### Mobile Maestro tests (gated on hardware)

- [ ] DEV-01 complete (Android Studio + AVD — see `950-tasks.maintenance.md`)
- [ ] `maestro/flows/` — login, today view, job detail, new job flows for Android
- [ ] iOS Maestro flows (requires macOS + Xcode — deferred: DEV-02)

### Future Work

- [ ] Visual regression for admin-web (Percy or Chromatic)
- [ ] Load test with k6 or Locust against staging env
