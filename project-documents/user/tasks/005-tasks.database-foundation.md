---
slice: database-foundation
project: office-hero
lld: user/slices/005-slice.database-foundation.md
dependencies: [1, 1a]
projectState: Slices 1-1a complete (Python scaffold with pyproject.toml, Makefile, CLI tooling). Ready to add database infrastructure: async SQLAlchemy engine, session factory, Alembic migrations, and RLS helpers.
dateCreated: 20260308
dateUpdated: 20260308
status: not_started
---

## Context Summary

- Working on **Slice 2: Database Foundation** — implementing async SQLAlchemy engine, session factory with RLS enforcement, Alembic migration framework, and initial database tables (outbox_events, saga_log)
- Current state: Python project scaffold (Slice 1) ready; no database code yet
- Deliverable: Complete database infrastructure with async engine, tenant-scoped sessions (RLS), Alembic migrations, and test infrastructure
- Next: Slice 3 (Auth & RBAC) will create users/refresh_tokens tables and migrations

---

## Task Breakdown

### Phase 1: Dependencies & Environment Configuration

- [ ] **Database dependencies already in pyproject.toml (from Slice 1)**
  - [ ] Verify present: `sqlalchemy==2.0.23`, `sqlmodel==0.0.14`, `asyncpg==0.29.0`, `alembic==1.12.1`
  - [ ] If missing, add to pyproject.toml and run `poetry lock`
  - [ ] Success: `poetry install` installs all DB packages

- [ ] **Create core/db_config.py — database URL configuration**
  - [ ] Read `DATABASE_URL` environment variable (required)
  - [ ] Validate URL format: `postgresql+asyncpg://user:password@host:port/dbname`
  - [ ] Provide helper function: `get_database_url() -> str`
  - [ ] Success: Function exports without errors; config is readable from environment

- [ ] **Test database configuration**
  - [ ] Create `tests/test_db_config.py`:
    - Test `get_database_url()` reads from environment
    - Test validation rejects invalid URLs
  - [ ] Success: `pytest tests/test_db_config.py -v` passes

---

### Phase 2: Engine & Session Layer

- [ ] **Create db/engine.py — async SQLAlchemy engine factory**
  - [ ] Function `create_engine()`:
    - Creates async engine using `DATABASE_URL`
    - Options: `echo=False` (prod) or `echo=True` (dev), `pool_pre_ping=True` (connection validation)
    - Returns `AsyncEngine` instance
  - [ ] Function `async_session_maker()`:
    - Returns `sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)`
  - [ ] Global instance (singleton):
    - Lazily initialized engine + session maker
    - Reusable across application
  - [ ] Success: Engine and session maker initialize without errors

- [ ] **Create db/session.py — session context manager with RLS**
  - [ ] Async context manager `get_session(tenant_id: UUID | None)`:
    - Creates async session from engine
    - If `tenant_id` provided: executes `SET app.tenant_id = :tenant_id` on session
    - Yields session for use in request context
    - Automatically rolls back on error, commits on success
  - [ ] Function `get_session_context(tenant_id: UUID)`:
    - Similar to above, but as simple async context manager
  - [ ] Success: Context manager works; RLS variable set on session

- [ ] **Test engine & session (unit tests)**
  - [ ] Create `tests/test_engine.py`:
    - Test `create_engine()` returns AsyncEngine
    - Test engine configuration (echo, pool settings)
  - [ ] Create `tests/test_session.py`:
    - Test `get_session()` context manager works
    - Test session creation and cleanup
  - [ ] Success: `pytest tests/test_engine.py tests/test_session.py -v` passes

---

### Phase 3: RLS Helpers & Utilities

- [ ] **Create db/rls.py — RLS policy helper functions**
  - [ ] Function `enable_rls_on_table(table_name: str)`:
    - Returns SQL command: `ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;`
  - [ ] Function `create_rls_policy(table_name: str, scope: str = "tenant")`:
    - Returns SQL: creates policy `{table_name}_tenant_policy`
    - Policy logic: `(tenant_id = current_setting('app.tenant_id')::uuid) OR (current_user = 'postgres')`
    - Allows SELECT, INSERT, UPDATE, DELETE for matching tenant_id
  - [ ] Success: Functions return valid SQL strings; no import errors

- [ ] **Create base SQLAlchemy models (models/**init**.py)**
  - [ ] Define declarative base:
    - `Base = declarative_base()` (or SQLAlchemy 2.0 style with `registry`)
  - [ ] Optionally mixin for common columns:
    - `id` (UUID, primary key)
    - `created_at` (DateTime, auto-set)
    - `updated_at` (DateTime, auto-set)
  - [ ] Success: Base exports without errors

- [ ] **Test RLS helpers (unit tests)**
  - [ ] Create `tests/test_rls.py`:
    - Test `enable_rls_on_table()` returns correct SQL
    - Test `create_rls_policy()` returns policy SQL with correct conditions
  - [ ] Success: `pytest tests/test_rls.py -v` passes

---

### Phase 4: Alembic Setup & Initial Migration

- [ ] **Initialize Alembic**
  - [ ] Command: `alembic init alembic` (if not already done)
  - [ ] Creates `alembic/` directory with `env.py`, `script.py.mako`, `versions/`
  - [ ] Success: Alembic directory structure exists

- [ ] **Configure alembic/env.py**
  - [ ] Import `create_engine` from `office_hero.db.engine`
  - [ ] Set `sqlalchemy.url` config section (can be empty; use env variable instead)
  - [ ] Set `target_metadata = Base.metadata` (from office_hero.models)
  - [ ] Configure async mode: `asyncio.run()` wrapper for async engine
  - [ ] Success: Alembic can load metadata from models; no import errors

- [ ] **Create initial migration: alembic/versions/0001_initial.py**
  - [ ] Creates tables:
    - `tenants` (id UUID PK, name VARCHAR, region VARCHAR, created_at, updated_at)
    - `outbox_events` (id UUID PK, tenant_id FK, event_type VARCHAR, payload JSON, created_at, processed_at)
    - `saga_log` (id UUID PK, tenant_id FK, saga_id UUID, step INT, status VARCHAR, data JSON, created_at, updated_at)
  - [ ] For each table:
    - Add RLS policy via SQL: execute `create_rls_policy(table_name)`
    - Execute `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`
  - [ ] Add indexes:
    - `outbox_events(tenant_id, created_at)`
    - `saga_log(tenant_id, saga_id, step)`
  - [ ] Success: Migration file is valid Python; can be parsed by Alembic

- [ ] **Test Alembic configuration**
  - [ ] Command: `alembic revision --autogenerate -m "test"` (creates dummy migration)
  - [ ] Command: `alembic history` (shows 0001_initial migration)
  - [ ] Success: Alembic recognizes migrations; can generate new ones

---

### Phase 5: Database Integration Testing (Requires Live DB)

- [ ] **Create tests/test_db_integration.py**
  - [ ] Fixture: `@pytest.fixture(scope="session")` providing test database URL
    - Skip test if `DATABASE_URL` not set or invalid
    - Or configure pytest to use Neon test branch (CI will do this)
  - [ ] Test `test_db_connection()`:
    - Create engine with live DATABASE_URL
    - Open session
    - Execute `SELECT 1`
    - Assert result == 1
  - [ ] Test `test_rls_session_variable()`:
    - Open session with tenant_id
    - Execute `SET app.tenant_id = ...` (done by get_session context manager)
    - Query `SELECT current_setting('app.tenant_id')`
    - Assert matches set value
  - [ ] Test `test_table_creation()`:
    - Run `alembic upgrade head` to create tables
    - Query `information_schema.tables` to verify tables exist
    - Verify RLS is enabled on each table
  - [ ] Success: Tests pass with live database (CI will run this)

- [ ] **Create conftest.py fixtures for database testing**
  - [ ] Fixture: `async_engine` — provides test engine with test DATABASE_URL
  - [ ] Fixture: `async_session` — provides test session context manager
  - [ ] Fixture: `reset_db` — drops and recreates schema before each test
  - [ ] Success: Fixtures can be imported by tests

---

### Phase 6: Documentation & Makefile Updates

- [ ] **Update Makefile with database targets**
  - [ ] `make db-migrate` → `alembic upgrade head`
  - [ ] `make db-rollback` → `alembic downgrade -1`
  - [ ] `make db-create-migration` → `alembic revision --autogenerate -m "..."`
  - [ ] `make db-shell` → `psql $DATABASE_URL` (if PostgreSQL installed)
  - [ ] `make db-test` → `pytest tests/test_db_*.py -v`
  - [ ] Success: `make db-migrate` can be run

- [ ] **Update README.md with database setup instructions**
  - [ ] Section: "Database Setup"
    - Required: PostgreSQL or Neon database
    - Set `DATABASE_URL` environment variable
    - Run `make db-migrate` to create tables
  - [ ] Section: "Local Development with Neon"
    - Link to Neon branch creation
    - How to use CI-provided ephemeral branches
  - [ ] Success: README documents database setup clearly

- [ ] **Create DB_SETUP.md documentation**
  - [ ] Section: RLS architecture
    - Explain tenant isolation via `app.tenant_id`
    - Document RLS policy logic
  - [ ] Section: Migration workflow
    - How to create new migrations
    - Best practices (reversible, no data loss if possible)
  - [ ] Section: Troubleshooting
    - Common errors (RLS policy conflicts, connection pooling)
  - [ ] Success: DB_SETUP.md is comprehensive

---

### Phase 7: Validation & Commit

- [ ] **Run full test suite (unit + integration)**
  - [ ] Command: `pytest tests/test_db_*.py -v --cov=src/office_hero/db`
  - [ ] Success: Unit tests pass; integration tests pass with live database (CI)

- [ ] **Verify Alembic workflow**
  - [ ] Run migrations: `alembic upgrade head`
  - [ ] Verify tables created: `\dt` in psql
  - [ ] Verify RLS enabled: `\d tenants` shows RLS policies
  - [ ] Test rollback: `alembic downgrade -1`, then `alembic upgrade head`
  - [ ] Success: All migrations work correctly

- [ ] **Verify engine/session functionality**
  - [ ] Script: create engine, open session, execute query, verify RLS variable
  - [ ] Success: Full flow works without errors

- [ ] **Documentation verification**
  - [ ] README includes database setup section
  - [ ] DB_SETUP.md explains RLS and migration workflow
  - [ ] All Makefile targets documented
  - [ ] Success: Documentation is clear and complete

- [ ] **Final commit & push**
  - [ ] Commit: "Implement Slice 2 (Database Foundation): async SQLAlchemy, Alembic migrations, RLS helpers, outbox/saga tables"
  - [ ] Push to feature branch (e.g., `phase-6/slice-2-implementation`)
  - [ ] Create PR with summary
  - [ ] Success: GitHub CI passes (unit tests, security checks)

---

## Success Criteria (Phase 6 Complete)

- ✅ async SQLAlchemy engine configured with DATABASE_URL
- ✅ Session factory provides async sessions with RLS enforcement
- ✅ Alembic configured and can auto-generate migrations
- ✅ Initial migration creates tenants, outbox_events, saga_log tables
- ✅ RLS policies enabled on all tables
- ✅ RLS session variable set via `app.tenant_id` context
- ✅ All unit tests passing (engine, session, RLS, Alembic)
- ✅ Integration tests passing with live database (CI)
- ✅ Makefile targets for db-migrate, db-shell, db-test added
- ✅ README and DB_SETUP.md documentation complete
- ✅ Migration workflow tested (upgrade, downgrade, autogenerate)
- ✅ All changes committed and pushed
- ✅ Ready for Slice 3 (Auth & RBAC) to add users/tokens tables
