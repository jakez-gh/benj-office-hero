# Office Hero

Field service management platform — dispatch, routing, and technician coordination
for home-service businesses (pest control, HVAC, plumbing, and similar trades).

## Quick Start

```bash
# 1. Clone
git clone <url> office-hero && cd office-hero

# 2. Copy and fill in environment variables
cp .env.example .env
# Edit .env — set DATABASE_URL, JWT_PRIVATE_KEY, JWT_PUBLIC_KEY (see below)

# 3. Start (installs dependencies automatically on first run)
./run.sh          # Linux / macOS / Git Bash
run.bat           # Windows
```

Open <http://127.0.0.1:3000> in your browser. API docs are at <http://127.0.0.1:8000/docs>.

## Prerequisites

| Tool | Version | Install |
| --- | --- | --- |
| Python | 3.11+ | <https://www.python.org> |
| Poetry | 1.8+ | `curl -sSL https://install.python-poetry.org \| python3 -` |
| Node.js | 18+ | <https://nodejs.org> |
| pnpm | 8+ | `npm install -g pnpm` |
| PostgreSQL | 14+ | [Neon](https://neon.tech) (free tier works) or local |

## Environment Variables

Copy `.env.example` to `.env` and fill in these required values:

```bash
# PostgreSQL connection string (Neon free tier works)
DATABASE_URL=postgresql+asyncpg://user:password@host/dbname?sslmode=require

# RSA key pair for JWT auth (generate with: openssl genrsa -out key.pem 2048)
# Paste the PEM contents with literal \n replacing newlines:
JWT_PRIVATE_KEY=<paste RSA private key PEM here, \n-escaped>
JWT_PUBLIC_KEY=<paste RSA public key PEM here, \n-escaped>

# OpenRouteService API key (free at https://openrouteservice.org)
ORS_API_KEY=your_ors_key_here
```

To generate an RSA key pair:

```bash
openssl genrsa -out private.pem 2048
openssl rsa -in private.pem -pubout -out public.pem
# Then paste the contents into .env with \n replacing newlines
```

## Running the Stack

### `run.sh` / `run.bat` — recommended

```bash
./run.sh               # both services (hot-reload dev mode)
./run.sh --backend     # backend only
./run.sh --frontend    # frontend only
./run.sh --prod        # build frontend, serve production preview
./run.sh --port 9000   # backend on a different port
./run.sh --help
```

The script handles dependency installation automatically:

- Python deps: runs `poetry install` when `.venv` is missing or `poetry.lock` is newer
- Node deps: runs `pnpm install` when `node_modules` is missing or `pnpm-lock.yaml` is newer
- Database migrations: runs `alembic upgrade head` on startup

### Manual startup

```bash
# Backend
poetry install --with dev
poetry run alembic upgrade head
OFFICE_HERO_TEST_AUTH=1 poetry run uvicorn office_hero.main:app \
    --reload --host 127.0.0.1 --port 8000

# Frontend (separate terminal)
pnpm install
VITE_API_BASE_URL=http://127.0.0.1:8000 pnpm --filter admin-web dev
```

### Make targets

```bash
make dev          # same as ./run.sh
make db-migrate   # run alembic upgrade head
```

## Development Workflow

```bash
# Run tests
poetry run pytest                        # all tests
poetry run pytest tests/test_routes.py  # specific file
poetry run pytest -x -q                  # stop on first failure

# Type checking and linting
pnpm --filter admin-web exec tsc --noEmit
pnpm --filter admin-web exec eslint src

# Format check (runs automatically on commit)
poetry run black --check src/ tests/
poetry run ruff check src/ tests/

# CLI tools
poetry run hero db status        # current migration revision
poetry run hero db migrate       # apply pending migrations
poetry run hero db rollback      # undo last migration
poetry run hero health           # ping /health endpoint
poetry run hero jwt generate --tenant-id <uuid>  # mint a test JWT
```

## Project Structure

```
office-hero/
├── src/office_hero/          FastAPI backend
│   ├── api/                  Routes, schemas, middleware, exception handlers
│   ├── core/                 Domain exceptions, enums, logging
│   ├── models/               SQLAlchemy ORM models
│   ├── repositories/         DB + in-memory implementations
│   ├── services/             Business logic (one service per slice boundary)
│   └── adapters/             External adapters (geocoding, routing)
├── apps/
│   └── admin-web/            React + TypeScript + Vite + Tailwind (dispatcher UI)
│       └── src/
│           ├── api.ts         All API client functions and types
│           ├── pages/         Page components
│           └── components/    Shared UI components
├── tools/
│   ├── cli.py                hero CLI (db, health, jwt, run-server)
│   └── client.py             HTTP client for CLI commands
├── migrations/               Alembic migration files
├── tests/                    pytest test suite
├── .github/workflows/        CI (test.yml), deploy (deploy.yml), uptime (uptime.yml)
├── Dockerfile.api            Multi-stage Python build for API
├── fly.api.toml              Fly.io config for API
├── fly.toml                  Fly.io config for web
├── run.sh / run.bat          Dev runner (this file!)
└── deploy.sh / deploy.bat    Deployment scripts
```

## Deploying to Fly.io

```bash
./deploy.sh          # Linux / macOS
deploy.bat           # Windows
```

The deploy script walks you through every step interactively:

1. Checks `flyctl` is installed (links to installer if missing)
2. Verifies you are logged in (`flyctl auth login`)
3. Creates apps on Fly.io if they don't exist
4. Prompts for any missing secrets (DATABASE_URL, JWT keys, ORS key)
5. Deploys API — runs `alembic upgrade head` via `release_command` before starting
6. Deploys web frontend
7. Runs a health check against the live API

### Manual deployment

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh   # Linux/macOS
# iwr https://fly.io/install.ps1 -useb | iex   # Windows PowerShell

flyctl auth login

# Set required secrets (once)
flyctl secrets set DATABASE_URL="..." --app office-hero-api
flyctl secrets set JWT_PRIVATE_KEY="..." --app office-hero-api
flyctl secrets set JWT_PUBLIC_KEY="..." --app office-hero-api
flyctl secrets set ORS_API_KEY="..." --app office-hero-api

# Deploy
flyctl deploy --config fly.api.toml --remote-only
flyctl deploy --config fly.toml --remote-only
```

### CI/CD (GitHub Actions)

Automated deploys on push to `main`:

1. Add `FLY_API_TOKEN` to your GitHub repo secrets (`flyctl tokens create deploy`)
2. Push to `main` — `.github/workflows/deploy.yml` runs tests then deploys both apps

Manual deploys via GitHub Actions:

```
Actions → Deploy to Fly.io → Run workflow → choose api | web | both
```

### Production URLs

| Service | URL |
| --- | --- |
| API | <https://office-hero-api.fly.dev> |
| API docs | <https://office-hero-api.fly.dev/docs> |
| Health | <https://office-hero-api.fly.dev/health> |
| Web admin | <https://office-hero-admin-web.fly.dev> |

## Architecture

- **Backend:** FastAPI (Python 3.11), SQLAlchemy async, Alembic, PostgreSQL (Neon)
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS v3
- **Auth:** RS256 JWT (15-minute access tokens, 7-day refresh tokens), bcrypt passwords
- **Routing:** OpenRouteService (ORS) adapter — nearest / earliest-completion / balanced-load options
- **Dispatch:** Route + RouteStop FSM; drag-and-drop resequencing; live GPS polling (30s)
- **Monitoring:** Sentry (optional, via `SENTRY_DSN` / `VITE_SENTRY_DSN`), hourly uptime check
- **RBAC:** Six roles (operator, tenant\_admin, dispatcher, technician, billing, read\_only)
- **Multi-tenant:** All data scoped by `tenant_id`; RLS policy helpers on all models

## Quality Gates

| Check | Tool | When |
| --- | --- | --- |
| Type check | mypy / tsc | CI |
| Lint | ruff + eslint | commit |
| Format | black + prettier | commit |
| Security | bandit + pip-audit | pre-push |
| Tests | pytest | CI + pre-push |
| Screenshots | Playwright | pre-push |

Run all checks locally:

```bash
pre-commit run --all-files   # fast checks (lint, format, markdown)
poetry run pytest            # full test suite
```
