"""Office Hero Development Setup Guide

This document explains how to rehydrate the Office Hero project from the GitHub repository.
All dependencies, configurations, and entry points are defined in version control.
"""

# Development Setup (macOS, Linux, Windows)

## Prerequisites

- Python 3.11+ (required by pyproject.toml)
- git
- pip (comes with Python)

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/jakez-gh/benj-office-hero.git
cd benj-office-hero
```

### 2. Create Virtual Environment

```bash
# macOS / Linux
python3.11 -m venv .venv
source .venv/bin/activate

# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

The `pyproject.toml` file declares all dependencies:

```bash
# Install project + all dev dependencies
pip install -e ".[dev]"

# Or just production dependencies:
pip install -e .
```

## Running the Application

### Via CLI

```bash
# Show help
python -m tools.cli --help

# Start API server (auto-reload on code changes)
python -m tools.cli run_server --reload

# Start API server (production)
python -m tools.cli run_server --host 0.0.0.0 --port 8000
```

### Direct Module Run

```bash
python -m office_hero.api
```

Starts server on <http://127.0.0.1:8000> with OpenAPI docs at `/docs`

## Running Tests

```bash
# All tests
pytest

# With verbose output
pytest -v

# Specific test file
pytest tests/test_api_sagas.py

# With coverage
pytest --cov=src
```

## Dependencies (from pyproject.toml)

**Production:**

- fastapi>=0.104 — Web framework with async support
- uvicorn[standard]>=0.24 — ASGI server
- httpx>=0.24 — HTTP client
- click>=8.0 — CLI framework

**Development:**

- pytest>=7.4 — Testing framework
- pytest-asyncio>=0.24 — Async test support
- pytest-cov>=4.1 — Coverage reporting
- pre-commit>=4.0 — Git hooks
- ruff>=0.8, black>=24.0 — Code formatting
- bandit>=1.8 — Security scanning

## Project Structure

```text
src/office_hero/
├── api/                        # FastAPI application layer
│   ├── __init__.py            # Exports app
│   ├── __main__.py            # CLI entry point for direct run
│   ├── app.py                 # FastAPI initialization, routes
│   └── routes/
│       ├── sagas.py           # GET /sagas/{saga_id}/state, POST transition
│       └── admin.py           # GET /admin/dead-letters, POST retry/logs
├── sagas/                      # Saga orchestration pattern
├── repositories/               # Data layer protocols & mocks
├── services/                   # Business logic services
└── adapters/                   # External system integrations

tests/
├── test_api_sagas.py          # API route tests
├── test_api_admin.py          # Admin route tests
├── test_saga_*.py             # Saga component tests
└── ...

tools/
└── cli.py                      # Operator CLI (run_server, health, migrate)

pyproject.toml                  # All config in one file (dependencies, pytest, ruff, black, etc.)
```

## Key Entry Points

1. **API Server**: `python -m tools.cli run_server`
2. **Health Check**: `python -m tools.cli health`
3. **Tests**: `pytest`
4. **Pre-commit Hooks**: Automatic on git commit (black, ruff, security scan)

## API Endpoints

All endpoints are defined in `src/office_hero/api/routes/` and currently return 501 (Not Implemented)
with implementation notes:

- **GET /health** — Health check
- **GET /sagas/{saga_id}/state** — Retrieve saga state and context
- **POST /sagas/{saga_id}/transition** — Resume saga execution
- **POST /sagas/{saga_id}/compensate** — Manually trigger compensation
- **GET /admin/dead-letters** — List failed events
- **POST /admin/dead-letters/{event_id}/retry** — Retry failed event
- **GET /admin/sagas/{saga_id}/logs** — Saga execution history

## Pre-commit Hooks

All commits run automated checks (defined in `.pre-commit-config.yaml`):

```bash
# View all configured hooks
cat .pre-commit-config.yaml

# Run hooks manually
pre-commit run --all-files

# Skip hooks (not recommended)
git commit --no-verify
```

## Coverage

Current coverage: **89.25%** (47 tests, 1 skipped)

View HTML report after running tests:

```text
htmlcov/index.html
```

## Troubleshooting

**ModuleNotFoundError: No module named 'office_hero'**

- Ensure venv is activated and `pip install -e .[dev]` was run

**pytest not found**

- Install dev dependencies: `pip install -e ".[dev]"`

**Port 8000 already in use**

- Use different port: `python -m tools.cli run_server --port 8001`

**Pre-commit hook failures**

- Automatically fixes: `black` formatting, `ruff` import sorting
- Manual review: Security issues from `bandit`

## Notes for Future Developers

1. **All production config** lives in `pyproject.toml` (no setup.py, no requirements.txt)
2. **All API routes** are discoverable from `src/office_hero/api/routes/`
3. **All tests** auto-discover from `tests/test_*.py`
4. **Protocol-based architecture**: Swap implementations without changing interfaces
5. **Async throughout**: All services use `async/await` and `pytest-asyncio`
