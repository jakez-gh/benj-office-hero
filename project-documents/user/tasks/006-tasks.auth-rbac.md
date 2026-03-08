---
slice: auth-rbac
project: office-hero
lld: user/slices/006-slice.auth-rbac.md
dependencies: [1, 1a, 2]
projectState: Slices 1-2 complete (Python scaffold, database foundation with RLS). Alembic migrations running, PostgreSQL engine initialized. Ready to implement authentication layer.
dateCreated: 20260308
dateUpdated: 20260308
status: not_started
---

## Context Summary

- Working on **Slice 3: Auth & RBAC** — implementing JWT RS256 authentication with bcrypt password hashing, RBAC with 8 roles, and fine-grained permissions
- Current state: Python FastAPI skeleton (Slice 1), PostgreSQL with RLS (Slice 2) are in place; migrations working
- Deliverable: Complete auth stack with login/refresh/logout endpoints, JWT middleware, RBAC decorators, user/token models, and audit-ready permission system
- Next: Slice 4 (Observability) will add logging, health checks, and security headers to wrap auth endpoints with monitoring

---

## Task Breakdown

### Phase 1: Dependencies & Core Configuration (Setup)

- [ ] **Add auth dependencies to pyproject.toml**
  - [ ] Add: `fastapi`, `pydantic-settings`, `python-jose[cryptography]`, `passlib[bcrypt]`, `slowapi`
  - [ ] Run `poetry lock` to update lock file
  - [ ] Success: `poetry install` completes without errors; all packages importable in Python REPL

- [ ] **Create core/config.py — Settings (pydantic-settings)**
  - [ ] Environment variables: `DATABASE_URL`, `JWT_PRIVATE_KEY`, `JWT_PUBLIC_KEY`, `JWT_ALGORITHM=RS256` (pinned), `ACCESS_TOKEN_TTL_MINUTES=15`, `REFRESH_TOKEN_TTL_DAYS=7`
  - [ ] Settings class with validation (required, defaults where appropriate)
  - [ ] Success: `from office_hero.core.config import Settings; s = Settings()` loads from `.env` or environment

- [ ] **Create core/exceptions.py — Domain exceptions**
  - [ ] Classes: `AuthError`, `PermissionError`, `TenantError` (all inherit from Exception)
  - [ ] Each exception includes optional message + optional request_id field for tracing
  - [ ] Success: Exceptions instantiate and stringify correctly; no import errors

- [ ] **Create core/roles.py — Role enum**
  - [ ] Enum with all 8 roles: `Owner`, `Operator`, `OperatorStaff`, `TenantAdmin`, `Sales`, `Dispatcher`, `Technician`, `TechnicianHelper`
  - [ ] Success: `Role.Owner.value` returns string; all roles importable

---

### Phase 2: Database Layer (Models & Migrations)

- [ ] **Update Alembic alembic/env.py**
  - [ ] Set `target_metadata = Base.metadata` (where Base is SQLAlchemy declarative base from models)
  - [ ] Currently `target_metadata = None`; change to import models' Base
  - [ ] Success: `alembic revision --autogenerate -m "test"` recognizes models without errors

- [ ] **Create models/**init**.py**
  - [ ] Empty file declaring module (will be populated with SQLAlchemy Base)
  - [ ] Success: `from office_hero.models import Base` imports without error (after step 4 below creates Base)

- [ ] **Create models/user.py — User ORM model**
  - [ ] SQLAlchemy model User with columns:
    - `id` (UUID, primary key)
    - `tenant_id` (UUID, foreign key to tenants.id, NOT NULL)
    - `email` (String, unique per tenant via composite unique constraint tenant_id+email)
    - `password_hash` (String, bcrypt hash)
    - `role` (String, Enum-like field storing role name)
    - `permissions` (JSON, default empty list)
    - `active` (Boolean, default True)
    - `created_at`, `updated_at` (DateTime, auto-managed)
  - [ ] Add RLS policy: Users can only read/write their own tenant's rows
  - [ ] Success: `from office_hero.models.user import User; u = User(...)` instantiates; introspection shows all columns

- [ ] **Create models/token.py — RefreshToken ORM model**
  - [ ] SQLAlchemy model RefreshToken with columns:
    - `id` (UUID, primary key)
    - `user_id` (UUID, foreign key to users.id, NOT NULL)
    - `token_hash` (String, bcrypt hash of refresh token)
    - `expires_at` (DateTime, NOT NULL)
    - `revoked` (Boolean, default False)
    - `created_at` (DateTime, auto-managed)
  - [ ] Add RLS policy: Tokens visible only within the user's tenant
  - [ ] Success: Model instantiates and columns are correct

- [ ] **Create migration alembic/versions/0002_users_and_tokens.py**
  - [ ] Create `users` table (columns per step 3 above)
  - [ ] Create unique constraint on (tenant_id, email)
  - [ ] Create RLS policy on users: `SET app.tenant_id` filtering
  - [ ] Create `refresh_tokens` table (columns per step 4 above)
  - [ ] Create RLS policy on refresh_tokens (via user's tenant)
  - [ ] Create foreign key constraints
  - [ ] Success: `alembic upgrade head` creates tables; `\d users` shows all columns in psql; RLS policies exist

- [ ] **Test database models and migrations**
  - [ ] Write test `tests/test_models.py`: instantiate User and RefreshToken, verify fields
  - [ ] Write test `tests/test_migrations.py`: run migration, verify tables exist in DB with correct columns, RLS enabled
  - [ ] Success: `pytest tests/test_models.py tests/test_migrations.py -v` passes

---

### Phase 3: Service Layer (Auth Business Logic)

- [ ] **Create repositories/user_repository.py — User data access**
  - [ ] Class UserRepository with async methods:
    - `get_by_email(email: str) -> User | None` — query users table by email (single tenant RLS applied by DB)
    - `create(email: str, password_hash: str, tenant_id: UUID, role: Role) -> User` — insert and return
    - `get_by_id(id: UUID) -> User | None` — fetch by ID (RLS applied)
    - `update_role(id: UUID, role: Role) -> User` — update role field
  - [ ] All methods use async SQLAlchemy session (from Slice 2 foundation)
  - [ ] Success: Methods execute without import/type errors; queries are async-safe

- [ ] **Create services/auth_service.py — Auth business logic**
  - [ ] Class AuthService with methods:
    - `hash_password(password: str) -> str` — bcrypt hash with work factor 12 via `passlib.context.CryptContext`
    - `verify_password(plain: str, hash: str) -> bool` — bcrypt verify
    - `issue_jwt(user_id: UUID, tenant_id: UUID, role: Role, permissions: list) -> tuple[str, str]` — returns (access_token, refresh_token)
      - access_token: RS256, 15min TTL
      - refresh_token: RS256, 7day TTL, includes token_jti for revocation tracking
    - `validate_jwt(token: str) -> dict` — decode, validate RS256 signature, check expiry, return payload; raise AuthError on failure
    - `login(email: str, password: str, session) -> tuple[User, str, str]` — fetch user by email, verify password, hash refresh token, return (user, access_token, refresh_token)
    - `refresh(refresh_token: str, session) -> tuple[User, str]` — validate refresh token, check if revoked, issue new access_token
    - `logout(refresh_token: str, session)` — mark refresh token as revoked in DB
  - [ ] Use Settings from core/config.py for JWT keys and TTL
  - [ ] Success: All methods execute without errors; JWTs can be issued and validated; bcrypt hashing works

- [ ] **Test auth service (unit tests)**
  - [ ] Create `tests/test_auth_service.py`:
    - Test hash_password produces different hash each time (salt randomization)
    - Test verify_password success/failure
    - Test issue_jwt creates valid RS256 tokens with correct TTL
    - Test validate_jwt decodes and validates correctly
    - Test validate_jwt raises AuthError on expired/invalid/tampered token
    - Test login success/failure (wrong password)
    - Test refresh with valid/expired/revoked token
    - Test logout marks token revoked
  - [ ] Success: `pytest tests/test_auth_service.py -v` passes all 8+ tests

---

### Phase 4: API Layer (FastAPI App, Middleware)

- [ ] **Create api/app.py — FastAPI application**
  - [ ] Instantiate FastAPI app with title "Office Hero API"
  - [ ] Add CORS middleware (origins: `*` in dev, env-configured in prod)
  - [ ] Add lifespan hook for startup/shutdown:
    - Startup: Initialize engine, session factory (from Slice 2)
    - Shutdown: Dispose engine
  - [ ] Success: App instantiates without error; `app.openapi()` returns valid OpenAPI schema

- [ ] **Create api/middleware/auth.py — JWT middleware**
  - [ ] Middleware that:
    - Validates JWT on all requests EXCEPT `/health`, `/auth/login`, `/auth/refresh`
    - Extracts Authorization header, validates token, decodes payload
    - Sets `request.state.user_id`, `request.state.tenant_id`, `request.state.role`, `request.state.permissions` from JWT
    - Raises 401 Unauthorized on invalid/expired/missing token
  - [ ] Success: Valid JWT sets request.state fields; invalid JWT raises 401

- [ ] **Create api/middleware/tenant.py — RLS tenant enforcement**
  - [ ] Middleware that:
    - Reads `request.state.tenant_id` (set by auth middleware)
    - Calls `session.execute(text("SET app.tenant_id = :tenant_id"), {"tenant_id": str(tenant_id)})` on the DB session
    - Ensures all subsequent DB queries in that request use RLS filtering
  - [ ] Success: All DB queries within request context are filtered by RLS

- [ ] **Test middleware (integration tests)**
  - [ ] Create `tests/test_middleware.py`:
    - Test auth middleware sets request.state on valid JWT
    - Test auth middleware rejects invalid/expired JWT with 401
    - Test auth middleware skips validation for `/health`, `/auth/login`, `/auth/refresh`
    - Test tenant middleware sets RLS context on session
  - [ ] Success: `pytest tests/test_middleware.py -v` passes

- [ ] **Wire middleware into app**
  - [ ] Add auth middleware and tenant middleware to app in `api/app.py`
  - [ ] Middleware order: auth first (sets state), then tenant (uses state)
  - [ ] Success: App starts without error; middleware chain executes

---

### Phase 5: Route Dependencies & Endpoints

- [ ] **Create api/deps.py — FastAPI dependency factories**
  - [ ] Function `require_role(roles: list[Role])` — FastAPI Depends-compatible function that:
    - Checks `request.state.role in roles`
    - Raises 403 Forbidden if not
    - Returns nothing (dependency used for side-effects)
  - [ ] Function `require_permission(perm: str)` — checks `perm in request.state.permissions`, raises 403 if not
  - [ ] Success: Both functions can be used as FastAPI dependency annotations

- [ ] **Create api/routes/auth.py — Auth endpoints**
  - [ ] Endpoint `POST /auth/login`:
    - Request: `{email: str, password: str}`
    - Calls AuthService.login(email, password, session)
    - Returns: `{access_token: str, refresh_token: str, user: {id, email, role}}`
    - Rate-limited: 10 req/min (via slowapi; will be wired in Slice 4)
    - On auth failure: 401 Unauthorized
  - [ ] Endpoint `POST /auth/refresh`:
    - Request: `{refresh_token: str}`
    - Calls AuthService.refresh(refresh_token, session)
    - Returns: `{access_token: str, user: {id, email, role}}`
    - Rate-limited: 10 req/min
    - On failure: 401
  - [ ] Endpoint `POST /auth/logout`:
    - Requires valid JWT (auth middleware enforces)
    - Request: empty body
    - Calls AuthService.logout(refresh_token_from_request, session)
    - Returns: `{status: "ok"}`
  - [ ] Use APIRouter to modularize; include in app in `api/app.py`
  - [ ] Success: All 3 endpoints respond with correct status codes and payloads

- [ ] **Test auth endpoints (E2E tests)**
  - [ ] Create `tests/test_auth_endpoints.py`:
    - Test `POST /auth/login` with valid creds → 200, tokens in response
    - Test `POST /auth/login` with wrong password → 401
    - Test `POST /auth/refresh` with valid refresh token → 200, new access token
    - Test `POST /auth/refresh` with expired/revoked token → 401
    - Test `POST /auth/logout` with valid JWT → 200
    - Test protected endpoint (e.g., `GET /operator/tenants`) without JWT → 401
    - Test protected endpoint with valid JWT → 200 (or 403 if role denied, tested in role/permission tests below)
  - [ ] Success: `pytest tests/test_auth_endpoints.py -v` passes all scenarios

- [ ] **Test RBAC (@require_role, @require_permission)**
  - [ ] Create `tests/test_rbac.py`:
    - Create test endpoint that requires `@require_role([Role.Operator])`
    - Test request with Technician role → 403
    - Test request with Operator role → 200
    - Similar for `@require_permission` decorator
  - [ ] Success: RBAC decorators enforce correctly

---

### Phase 6: Validation & Commit

- [ ] **Run full test suite**
  - [ ] Command: `pytest tests/ -v --cov=src/office_hero`
  - [ ] Success: All tests pass (test_models, test_migrations, test_auth_service, test_middleware, test_auth_endpoints, test_rbac)
  - [ ] Coverage: ≥85% for auth module

- [ ] **Verify app starts**
  - [ ] Command: `python -m uvicorn office_hero.api.app:app --reload` from repo root
  - [ ] Verify: `GET http://localhost:8000/health` returns 200 (even though health isn't implemented yet, should not 500)
  - [ ] Verify: `GET http://localhost:8000/docs` shows Swagger UI with login, refresh, logout endpoints

- [ ] **Final commit & push**
  - [ ] Commit: "Implement Slice 3 (Auth & RBAC): JWT RS256, bcrypt, RBAC decorators, user/token models, auth endpoints"
  - [ ] Push to origin/main
  - [ ] Success: GitHub CI passes (lint, tests, security checks)

---

## Success Criteria (Phase 5 Complete)

- ✅ All 6 test files created and passing
- ✅ All 12 implementation files created and imported without errors
- ✅ 3 auth endpoints functional (login, refresh, logout)
- ✅ JWT RS256 validates and rejects correctly
- ✅ RBAC decorators enforce role/permission checks
- ✅ App starts without errors
- ✅ All changes committed and pushed
- ✅ Ready for Phase 6 (Implementation) of Slice 4 (Observability)
