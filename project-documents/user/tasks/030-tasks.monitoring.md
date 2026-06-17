---
slice: monitoring
project: office-hero
lld: user/slices/030-slice.monitoring.md
dependencies: [4, 29]
projectState: >
  Sentry integrated in both backend (sentry-sdk[fastapi], optional via SENTRY_DSN)
  and frontend (@sentry/react, optional via VITE_SENTRY_DSN). Hourly uptime cron
  pings /health; optional dead-letter count check via PROD_ADMIN_TOKEN repo secret
  (>10 dead letters → workflow error). All optional — app runs fine without these.
  Verified: pip-audit clean, hooks pass, pushed to origin/main.
dateCreated: 20260616
dateUpdated: 20260617
status: complete
docType: tasks
---

## Context Summary

Slice 030 adds error tracking, uptime monitoring, and dead-letter alerting.

## Completed Tasks

- [x] `sentry-sdk[fastapi]` added to `pyproject.toml`; `create_app()` in
  `src/office_hero/api/app.py` initialises Sentry when `SENTRY_DSN` is set
  (FastApiIntegration + StarletteIntegration, traces_sample_rate=0.1)
- [x] `@sentry/react` added to `apps/admin-web/package.json`; `main.tsx` initialises
  Sentry when `VITE_SENTRY_DSN` is set (browserTracingIntegration, tracesSampleRate=0.1)
- [x] `.github/workflows/uptime.yml` — hourly cron pings
  `https://office-hero-api.fly.dev/health`; optional dead-letter check via
  `PROD_ADMIN_TOKEN` + `PROD_API_URL` (>10 dead letters → error)
- [x] `.env.example` updated with `SENTRY_DSN` and `VITE_SENTRY_DSN` documentation

## Activation

1. Create a Sentry project at sentry.io (free tier)
2. Set `SENTRY_DSN` as a Fly.io secret on the API app
3. Set `VITE_SENTRY_DSN` as a Fly.io build arg on the web app
4. Optional: set `PROD_ADMIN_TOKEN` + `PROD_API_URL` as GitHub repo vars for
   dead-letter monitoring
