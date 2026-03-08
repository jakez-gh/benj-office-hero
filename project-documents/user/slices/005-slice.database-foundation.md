---
docType: slice-design
parent: ../project-guides/003-slices.office-hero.md
project: office-hero
dateCreated: 20260308
status: in_progress
---

# Slice Design 005: Database foundation

This slice implements the database infrastructure described in the HLD and
slice plan (slice 2). It sets up the async SQLAlchemy engine/session, Neon
connection, Alembic migrations, and RLS helpers. It also creates the
`outbox_events` and `saga_log` tables required by later back-office slices.

A failing integration test kicks off this slice: connecting to a live database
(branch) and verifying that a simple query executes and that the RLS session
variable can be set.

## Goals

* Configure `src/office_hero/db/engine.py` with `create_async_engine()` using
  `DATABASE_URL` environment variable.
* Provide a `get_session()` async context manager in `src/office_hero/db/session.py`
  that sets `app.tenant_id` on each connection.
* Add `alembic/` config: `alembic.ini`, `env.py` referencing the async engine and
  using SQLAlchemy `MetaData` from `models/`.
* Create initial migration that creates `outbox_events` and `saga_log` tables with
  `tenant_id` columns and RLS policy helpers (see ADRs 053 & 056).  This migration
  will also install `gen_random_uuid()` extension if needed.
* Provide a simple `tests/test_db.py` that requires a running Neon database (CI
  will provision a branch) and asserts that:
    1. A session can be opened.
    2. Executing `SELECT 1` returns 1.
    3. Setting the session variable and querying `current_setting('app.tenant_id')`
       returns the value.
* Update `Makefile` with `make db-migrate`, `make db-shell` targets.
* Document in README how to configure `DATABASE_URL` and run migrations locally.

## Structure additions

```text
src/office_hero/db/
├── engine.py        # async engine factory
├── session.py       # session context manager
└── rls.py           # helper functions for RLS policy generation

alembic/
├── env.py
├── script.py.mako
└── versions/
    └── 0001_initial.py
```

## Failing Test Outline

```python
import pytest
from office_hero.db.engine import create_engine
from office_hero.db.session import get_session


def test_db_connection_and_rls(monkeypatch):
    # require DATABASE_URL env var pointing to test branch
    pytest.skip("needs live database", allow_module_level=True)

    async def run():
        engine = create_engine()
        async with get_session(engine) as session:
            result = await session.execute("SELECT 1")
            assert result.scalar() == 1
            await session.execute("SET LOCAL app.tenant_id = '00000000-0000-0000-0000-000000000000'")
            r = await session.execute("SELECT current_setting('app.tenant_id')")
            assert r.scalar() == '00000000-0000-0000-0000-000000000000'

    import asyncio
    asyncio.run(run())
```

The test is marked to skip unless a real database is configured; CI will
set `DATABASE_URL` accordingly.

## Dependencies

Depends on slice 1 (scaffold) only.  Alembic and SQLAlchemy are already
listed in `pyproject.toml` dev dependencies; add `sqlmodel` when models are
introduced in later slices.

## Effort

Estimate: 2/5. The engine/session code is straightforward but the Alembic
configuration and migration creation require attention.  Writing the integration
test early keeps TDD discipline.  The first migration also establishes the
RLS pattern used by every table thereafter.

---

Once this design is approved, implementation will proceed with the failing
`test_db.py` and corresponding code files.  Commit early and push often as the
hook configuration is in place.
