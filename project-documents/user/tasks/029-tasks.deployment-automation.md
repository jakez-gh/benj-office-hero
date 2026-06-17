---
slice: deployment-automation
project: office-hero
lld: user/slices/029-slice.deployment-automation.md
dependencies: [1]
projectState: >
  Fly.io deployment fully automated. Dockerfile.api (multi-stage Python/uvicorn),
  fly.api.toml (release_command runs alembic upgrade head before startup),
  fly.toml (frontend static build), .github/workflows/deploy.yml (test gate →
  deploy-api → deploy-web; workflow_dispatch with api|web|both selector).
  run.sh/run.bat for dev startup. deploy.sh/deploy.bat for interactive
  Fly.io walkthrough. README rewritten with full quick-start guide.
  Verified: all hooks pass, pushed to origin/main.
dateCreated: 20260616
dateUpdated: 20260617
status: complete
docType: tasks
---

## Context Summary

Slice 029 automates deployment to Fly.io and sets up local dev runner scripts.

## Completed Tasks

- [x] `Dockerfile.api` — multi-stage Python build (builder: gcc/libpq/Poetry → runtime:
  libpq5, non-root uid 1001, HEALTHCHECK, 2-worker uvicorn)
- [x] `fly.api.toml` — `[deploy] release_command = "alembic upgrade head"`, /health check,
  512MB VM; documents required secrets inline
- [x] `fly.toml` — corrected `dockerfile = "Dockerfile"`, proper duration strings, frontend
  static serving
- [x] `.github/workflows/deploy.yml` — test job (PostgreSQL 16 service, RSA key generation,
  pytest) → deploy-api → deploy-web; `workflow_dispatch` with `service: api|web|both`
- [x] `run.sh` — Unix dev runner: checks/installs Python + Node deps (stamp-file gating),
  loads .env, runs migrations, starts backend (port 8000, --reload) + Vite dev server
  (port 3000), cleans up on Ctrl+C
- [x] `run.bat` — Windows equivalent: separate terminal windows for each service
- [x] `deploy.sh` — Fly.io deployment walkthrough: flyctl auth check, app creation,
  secret prompts, API deploy + health check, web deploy
- [x] `deploy.bat` — Windows equivalent
- [x] `README.md` — complete rewrite: quick start, prerequisites, env vars, project
  structure, deployment guide, CI/CD instructions
- [x] `.env.example` — SENTRY_DSN + VITE_SENTRY_DSN documented

## Activation

To go live set these GitHub repo secrets:

- `FLY_API_TOKEN` — from `flyctl tokens create deploy`
- Fly.io app secrets: `DATABASE_URL`, `JWT_PRIVATE_KEY`, `JWT_PUBLIC_KEY`, `ORS_API_KEY`
- Optional: `SENTRY_DSN`, `VITE_SENTRY_DSN`, `PROD_ADMIN_TOKEN`, `PROD_API_URL`
