# benj.office-hero

Office Hero web application.

## Development setup

```bash
# One-time setup (activates git hooks + installs deps)
bash scripts/setup-dev.sh        # Linux / macOS / Git Bash
.\scripts\setup-dev.ps1          # Windows PowerShell

# Run all quality gates locally
.\scripts\qa_gate.ps1            # Windows
pre-commit run --all-files       # any platform
```

## Quality gates

| Gate | Tool | When |
|------|------|------|
| Markdown lint | markdownlint | commit |
| Python format | black | commit |
| Python lint | ruff | commit |
| File hygiene | pre-commit-hooks | commit |
| Security scan | bandit | push |
| Unit tests | pytest | CI |
| Coverage | pytest-cov | CI |

## Database

Office Hero uses PostgreSQL with row-level security (RLS) for tenant
isolation.  A running database is required for most integration tests and for
local development migrations.

Before running any of the commands below you must export the
``DATABASE_URL`` environment variable, e.g.:

```bash
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost/dbname"
# Windows PowerShell
$Env:DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/dbname"
```

The following make targets are provided:

* ``make db-migrate`` – apply all outstanding Alembic migrations to the
  database pointed at by ``DATABASE_URL``.
* ``make db-shell`` – drop into a ``psql`` shell connected to that URL.

Integration tests will automatically skip when ``DATABASE_URL`` is not set.
CI provisions a temporary branch and configures this variable appropriately.

## CI

GitHub Actions runs on every push and PR:

* **Lint** — pre-commit (black, ruff, markdownlint, file checks)
* **Security** — bandit static analysis
* **Test** — pytest with coverage report
