---
docType: slice-design
parent: ../project-guides/003-slices.office-hero.md
project: office-hero
dateCreated: 20260308
status: in_progress
---

# Slice Design 004: Python project scaffold & CLI tooling

This is the first *foundation* slice.  It establishes the repository
structure, build/test tooling, and a minimal CLI that will later be
expanded into the operator tools described in the concept and HLD.

It corresponds to slice 1 and 1a in the slice plan.

## Goals

* Create `src/office_hero/` package with empty modules for future code.
* Establish `pyproject.toml` with dependencies and development tools:
  * fastapi, sqlmodel, alembic, asyncpg, structlog, pydantic-settings, etc.
  * pytest + pytest-asyncio, httpx, ruff, black, bandit, pip-audit
* Add Makefile targets for common tasks (`make start`, `make test`,
  `make lint`, `make migrate`).
* Add Dockerfile with `python:3.11-slim` base, copying source and
  installing dependencies.
* Configure pre-commit hooks (already done globally,
  but ensure local `.pre-commit-config.yaml` exists).  Hooks will
  auto-format, lint, run bandit, and check for secrets.
* Set up basic `tools/` directory with a `cli.py` script that can
authenticate against the API and run a couple of placeholder
commands (health check, migrate).  It will import a small
`tools.client` helper for HTTP calls.
* Add `README.md` stub explaining how to bootstrap the environment.

## Structure

```text
project-root/
├── Makefile
├── Dockerfile
├── pyproject.toml
├── .pre-commit-config.yaml
├── tools/
│   ├── cli.py         # entry point for operator CLI
│   └── client.py      # httpx wrapper (auth helper, base URL)
├── src/
│   └── office_hero/
│       ├── __init__.py
│       ├── api/           # populated by later slices
│       ├── services/
│       ├── repositories/
│       ├── adapters/
│       ├── models/
│       ├── db/
│       └── core/
└── tests/
    ├── __init__.py
    └── test_smoke.py       # simple import / path test
```

## CLI design

`tools/cli.py` will use `click` to provide a simple command line
interface.  Initial commands:

```python
@click.group()
def cli():
    pass

@cli.command()
@click.option("--url", default=os.environ.get("API_BASE_URL"))
@click.option("--token", default=os.environ.get("API_TOKEN"))
def health(url, token):
    """Call GET /health and print result."""
    client = Client(base_url=url, token=token)
    print(client.get("/health"))

@cli.command()
def migrate():
    """Run alembic upgrade head."""
    subprocess.run(["alembic", "upgrade", "head"], check=True)
```

`tools/client.py` wraps `httpx.AsyncClient` with convenience
methods for auth and JSON handling.  It will be reused by future
operator commands and automated scripts.

## Testing

* `tests/test_smoke.py` simply imports `office_hero` and asserts
  `True`.  It serves to validate the Python environment and
  ensures `pytest` runs before other slices add real tests.
* The CLI has its own tests (using `click.testing.CliRunner`) in
  subsequent slices; no CLI tests here.

## Migration

No database schema yet.  This slice will create the Alembic
configuration (`alembic.ini`, `alembic/env.py`) and an initial
empty migration file.  The slice plan already noted that later
slices will add tables for `outbox_events`/`saga_log`; those can
be added to migrations once the models exist.

## Dependencies

This slice depends on nothing except the repository being
initialized.  It will create the initial Git commit on completion.

## Effort

Effort estimate: 1/5 for the project scaffold, another 1/5 for the
CLI tooling (combined, we allocate 1a+1 = 2/5 in the plan).

```text
Tasks:
- create pyproject, Makefile, Dockerfile
- set up pre-commit config
- implement minimal src package structure
- add tools/cli.py + client.py
- add tests/test_smoke.py
- initial git commit with this slice's work
```

Once this design is approved, execution is straightforward: run
`poetry install` (or pip via venv), apply pre-commit, and commit the
scaffold.  The next slice (DB foundation) will build on this
environment.
