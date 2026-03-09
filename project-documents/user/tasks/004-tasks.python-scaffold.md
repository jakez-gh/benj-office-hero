---
slice: python-scaffold
project: office-hero
lld: user/slices/004-slice.python-scaffold.md
dependencies: []
projectState: Project initialized with Git repo. No Python code yet. Ready to establish repository structure, dependencies, tooling, and CLI foundation.
dateCreated: 20260308
dateUpdated: 20260308
status: not_started
---

## Context Summary

- Working on **Slices 1 + 1a: Python Project Scaffold & CLI Tooling** — establishing repository structure, build/test tooling, and minimal CLI for operator interactions
- Current state: Git repo initialized; ready for Python project setup
- Deliverable: Complete Python project structure with pyproject.toml, pre-commit hooks, Dockerfile, Makefile, CLI tooling, and test infrastructure
- Next: Slice 2 (Database Foundation) builds on this scaffold with SQLAlchemy models and Alembic migrations

---

## Task Breakdown

### Phase 1: Project Structure & Configuration

- [ ] **Create src/office_hero/ package directory structure**
  - [ ] Create directories:
    - `src/office_hero/` — main package
    - `src/office_hero/api/` — API routes (populated by later slices)
    - `src/office_hero/services/` — business logic
    - `src/office_hero/repositories/` — data access
    - `src/office_hero/adapters/` — external integrations (ORS, etc.)
    - `src/office_hero/models/` — SQLAlchemy ORM models
    - `src/office_hero/db/` — database utilities (engine, session, RLS)
    - `src/office_hero/core/` — shared utilities (config, exceptions, logging)
  - [ ] Create `src/office_hero/__init__.py` (empty or with version)
  - [ ] Create `__init__.py` files in each subdirectory
  - [ ] Success: All directories exist; Python treats each as package

- [ ] **Create tests/ directory structure**
  - [ ] Create `tests/` directory at project root
  - [ ] Create `tests/__init__.py`
  - [ ] Create `tests/conftest.py` (pytest fixtures; can be empty initially)
  - [ ] Create `tests/test_smoke.py` — simple import smoke test:
    - `test_office_hero_imports()`: `from office_hero import ...` succeeds
    - `test_package_structure()`: verify expected modules exist
  - [ ] Success: `pytest tests/test_smoke.py` passes

- [ ] **Create pyproject.toml with dependencies**
  - [ ] Initialize with:

    ```toml
    [project]
    name = "office-hero"
    version = "0.1.0"
    description = "Field service management platform"
    requires-python = ">=3.11"
    dependencies = [
      "fastapi==0.104.1",
      "uvicorn[standard]==0.24.0",
      "sqlalchemy==2.0.23",
      "sqlmodel==0.0.14",
      "asyncpg==0.29.0",
      "alembic==1.12.1",
      "pydantic==2.5.0",
      "pydantic-settings==2.1.0",
      "python-jose[cryptography]==3.3.0",
      "passlib[bcrypt]==1.7.4",
      "structlog==23.2.0",
      "slowapi==0.1.9",
      "click==8.1.7",
      "httpx==0.25.2"
    ]
    ```

  - [ ] Add dev dependencies:

    ```toml
    [project.optional-dependencies]
    dev = [
      "pytest==7.4.3",
      "pytest-asyncio==0.21.1",
      "pytest-cov==4.1.0",
      "black==23.12.0",
      "ruff==0.1.8",
      "bandit==1.7.5",
      "pip-audit==2.6.3",
      "pre-commit==3.5.0"
    ]
    ```

  - [ ] Add tool configurations: `[tool.pytest.ini_options]`, `[tool.black]`, `[tool.ruff]`
  - [ ] Success: `poetry lock` generates lock file; `poetry install` installs all deps

- [ ] **Test basic Python setup**
  - [ ] Run: `python -m office_hero --help` (will fail gracefully if no entrypoint yet)
  - [ ] Run: `pytest tests/test_smoke.py -v`
  - [ ] Success: Tests pass; packages are importable

---

### Phase 2: Build Tooling & Container Setup

- [ ] **Create Makefile with common targets**
  - [ ] Targets:
    - `make install` → `poetry install`
    - `make test` → `pytest tests/ -v --cov=src/office_hero`
    - `make lint` → `black src/ tools/ tests/` + `ruff check src/ tools/ tests/`
    - `make fmt` → `black . && ruff check . --fix`
    - `make audit` → `bandit -r src/` + `pip-audit`
    - `make start` → `python -m uvicorn office_hero.api.app:app --reload` (when app exists)
    - `make migrate` → `alembic upgrade head` (when migrations exist)
    - `make docker-build` → `docker build -t office-hero:latest .`
    - `make docker-run` → `docker run --rm office-hero:latest`
  - [ ] Success: `make test` runs successfully; `make help` shows all targets

- [ ] **Create Dockerfile**
  - [ ] Multi-stage build:

    ```dockerfile
    FROM python:3.11-slim as builder
    WORKDIR /app
    COPY pyproject.toml poetry.lock ./
    RUN pip install poetry && poetry export -f requirements.txt -o requirements.txt

    FROM python:3.11-slim
    WORKDIR /app
    COPY --from=builder /app/requirements.txt .
    RUN pip install -r requirements.txt
    COPY src/ ./src/
    EXPOSE 8000
    CMD ["uvicorn", "office_hero.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
    ```

  - [ ] Success: `docker build -t office-hero:latest .` completes without errors

- [ ] **Test Docker setup**
  - [ ] Command: `docker build -t office-hero:test .`
  - [ ] Command: `docker run --rm office-hero:test python -m pytest --version`
  - [ ] Success: Docker image builds and runs tests

---

### Phase 3: Pre-Commit Hooks & Code Quality

- [ ] **Verify .pre-commit-config.yaml (already set up)**
  - [ ] Review existing hooks (should be from Slice setup):
    - `black` — code formatting
    - `ruff` — linting + sorting imports
    - `bandit` — security checks
    - `pip-audit` — dependency vulnerabilities
    - `trim-trailing-whitespace`, `end-of-file-fixer`, etc.
  - [ ] Install hooks: `pre-commit install`
  - [ ] Success: `git commit` triggers hooks automatically

- [ ] **Add linting/formatting configuration to pyproject.toml**
  - [ ] `[tool.black]`: line-length = 100
  - [ ] `[tool.ruff]`: select security/import/style rules, ignore unused code initially
  - [ ] `[tool.pytest.ini_options]`: testpaths, asyncio_mode, etc.
  - [ ] Success: `black`, `ruff`, `pytest` all respect configuration

- [ ] **Test pre-commit hooks**
  - [ ] Create a dummy Python file with poor formatting
  - [ ] Attempt `git add` + `git commit`
  - [ ] Verify hooks run and auto-fix code (if applicable)
  - [ ] Success: Hooks execute and enforce standards

---

### Phase 4: CLI Tooling (tools/ Directory)

- [ ] **Create tools/client.py — HTTP client wrapper**
  - [ ] Class `Client`:
    - Constructor: `__init__(base_url: str, token: str | None)`
    - Methods:
      - `get(path: str) -> dict` — make GET request, return JSON
      - `post(path: str, data: dict) -> dict` — make POST request
      - Error handling: raise exceptions on 401/403/500, return response body on success
  - [ ] Uses `httpx` library (async-capable)
  - [ ] Success: Client class imports and instantiates without errors

- [ ] **Create tools/cli.py — CLI entry point**
  - [ ] Use `click` library for command-line interface
  - [ ] Define root group: `@click.group() def cli():`
  - [ ] Implement commands:
    - `health`: call GET /health, print result
      - Options: `--url` (API base URL), `--token` (optional JWT)
    - `whoami`: call GET /me (if auth endpoint exists), print user info
    - Stub: `migrate` — placeholder for running alembic migrations
  - [ ] Entry point in pyproject.toml:

    ```toml
    [project.scripts]
    office-hero = "tools.cli:cli"
    ```

  - [ ] Success: `office-hero health --url http://localhost:8000` executes without errors

- [ ] **Test CLI tooling**
  - [ ] Create `tests/test_cli.py`:
    - Test Client class with mocked HTTP responses
    - Test CLI commands parse correctly
  - [ ] Command: `office-hero health --help` shows usage
  - [ ] Success: `pytest tests/test_cli.py -v` passes

---

### Phase 5: Documentation & README

- [ ] **Create README.md**
  - [ ] Sections:
    - Project overview
    - Setup: Python 3.11+, poetry, how to install
    - Development: how to run dev server, tests, linting
    - Docker: how to build and run container
    - CLI: how to use operator CLI
    - Contributing: coding standards, pre-commit hooks
  - [ ] Example (basic README structure):
    - Project overview section
    - Setup instructions (poetry install, pre-commit install)
    - Development commands (make test, make lint, make start)
    - CLI usage examples (office-hero health)
    - Contributing guidelines reference
  - [ ] Success: README is clear for developers

- [ ] **Create CONTRIBUTING.md**
  - [ ] Code standards (black, ruff, bandit)
  - [ ] Test coverage expectations
  - [ ] Pre-commit hook workflow
  - [ ] Commit message guidelines
  - [ ] Success: CONTRIBUTING.md guides developers

- [ ] **Create .env.example**
  - [ ] Template environment variables:

    ```bash
    # Backend API
    DATABASE_URL=postgresql://user:password@localhost:5432/office_hero
    API_BASE_URL=http://localhost:8000

    # JWT (see JWT setup in README)
    JWT_PRIVATE_KEY=(from environment or key file)
    JWT_PUBLIC_KEY=(from environment or key file)
    JWT_ALGORITHM=RS256

    # Logging
    LOG_LEVEL=INFO
    ```

  - [ ] Note in README to copy `.env.example` to `.env.local`
  - [ ] Document: JWT keys should be set via environment or loaded from secure key file (not committed)
  - [ ] Success: `.env.example` exists and is documented

---

### Phase 6: Validation & Testing

- [ ] **Run full test suite**
  - [ ] Command: `pytest tests/ -v --cov=src/office_hero`
  - [ ] Success: All tests pass; coverage ≥70%

- [ ] **Verify all imports**
  - [ ] Command: `python -c "import office_hero; print('Import OK')"`
  - [ ] Success: No import errors

- [ ] **Test CLI availability**
  - [ ] Command: `office-hero --version` (or `--help`)
  - [ ] Success: CLI is available and callable

- [ ] **Test Docker build**
  - [ ] Command: `docker build -t office-hero:latest .`
  - [ ] Success: Image builds without errors

- [ ] **Test code quality checks**
  - [ ] Command: `black --check src/ tools/ tests/`
  - [ ] Command: `ruff check src/ tools/ tests/`
  - [ ] Command: `bandit -r src/`
  - [ ] Success: All checks pass

- [ ] **Verify pre-commit hooks work**
  - [ ] Create a test file with formatting issues
  - [ ] Stage and commit: `git add` + `git commit`
  - [ ] Verify hooks run and auto-fix (or block commit if needed)
  - [ ] Success: Hooks execute in correct order

---

### Phase 7: Final Commit & Documentation

- [ ] **Final commit & push**
  - [ ] Commit: "Implement Slices 1+1a (Python Scaffold): project structure, dependencies, CLI, Docker, pre-commit hooks"
  - [ ] Push to feature branch (e.g., `phase-6/slices-1-1a-implementation`)
  - [ ] Create PR with summary
  - [ ] Success: GitHub CI passes (install, build, test, lint)

---

## Success Criteria (Phase 6 Complete)

- ✅ Repository structure created (src/office_hero/ with all subdirectories)
- ✅ pyproject.toml configured with all dependencies and tools
- ✅ poetry.lock generated; `poetry install` works
- ✅ tests/ directory created with conftest.py and smoke test
- ✅ Makefile with targets for common tasks
- ✅ Dockerfile creates buildable image
- ✅ .pre-commit-config.yaml installed and working
- ✅ tools/cli.py provides office-hero CLI command
- ✅ tools/client.py provides HTTP client wrapper
- ✅ README.md and CONTRIBUTING.md document project
- ✅ .env.example created with template variables
- ✅ All tests passing (pytest)
- ✅ Code passes linting (black, ruff, bandit)
- ✅ Docker image builds and runs tests successfully
- ✅ All changes committed and pushed
- ✅ Ready for Slice 2 (Database Foundation) implementation
