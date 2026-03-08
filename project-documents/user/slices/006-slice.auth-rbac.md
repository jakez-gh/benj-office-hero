---
docType: slice-design
parent: ../project-guides/003-slices.office-hero.md
project: office-hero
dateCreated: 20260308
status: not_started
---

# Slice Design 006: Auth & RBAC

This is the third foundation slice. It implements JWT RS256 authentication with bcrypt password hashing,
role-based access control (RBAC) with fine-grained permissions, and token refresh via refresh tokens.
It also integrates `slowapi` rate limiting on auth endpoints (10 req/min).

It corresponds to slice 3 in the slice plan.

## Goals

* Add dependencies to `pyproject.toml`: `fastapi`, `pydantic-settings`, `python-jose[cryptography]`,
  `passlib[bcrypt]`, `slowapi`.
* Create `src/office_hero/core/config.py` with `Settings` (pydantic-settings) reading environment:
  `DATABASE_URL`, `JWT_PRIVATE_KEY`, `JWT_PUBLIC_KEY`, `JWT_ALGORITHM=RS256` (pinned),
  `ACCESS_TOKEN_TTL_MINUTES=15`, `REFRESH_TOKEN_TTL_DAYS=7`.
* Create `src/office_hero/core/exceptions.py` with domain exceptions: `AuthError`, `PermissionError`,
  `TenantError`.
* Create `src/office_hero/core/roles.py` — `Role` enum with all 8 roles:
  `Owner, Operator, OperatorStaff, TenantAdmin, Sales, Dispatcher, Technician, TechnicianHelper`.
* Create FastAPI application in `src/office_hero/api/app.py` with CORS middleware and lifespan
  hook (startup/shutdown) for engine/session management.
* Create `src/office_hero/api/middleware/auth.py` — middleware that:
  * Validates JWT on every request (except `/health`, `/auth/login`, `/auth/refresh`)
  * Sets `request.state.user_id`, `.tenant_id`, `.role`, `.permissions` from JWT payload
  * Raises 401 on invalid/expired token
* Create `src/office_hero/api/middleware/tenant.py` — middleware that sets `app.tenant_id`
  on the DB session from `request.state.tenant_id` before each request (RLS enforcement).
* Create `src/office_hero/api/deps.py` with dependency factories:
  * `@require_role(roles: List[Role])` — FastAPI dependency; raises 403 if request.state.role not in roles
  * `@require_permission(perm: str)` — FastAPI dependency; raises 403 if perm not in request.state.permissions
* Create `src/office_hero/models/__init__.py` (empty; will be populated with SQLAlchemy models).
* Create `src/office_hero/models/user.py` — SQLAlchemy ORM model `User`:
  `id (UUID, PK)`, `tenant_id (UUID, FK, NOT NULL)`, `email (str, unique)`,
  `password_hash (str, bcrypt)`, `role (str, Enum)`, `permissions (JSON, default [])`, `active (bool, default True)`.
* Create `src/office_hero/models/token.py` — SQLAlchemy ORM model `RefreshToken`:
  `id (UUID, PK)`, `user_id (UUID, FK)`, `token_hash (str, NOT NULL)`,
  `expires_at (DateTime, NOT NULL)`, `revoked (bool, default False)`.
* Create `src/office_hero/repositories/__init__.py` (empty).
* Create `src/office_hero/repositories/user_repository.py` — async repository class:
  * `get_by_email(email) -> User | None`
  * `create(email, password_hash, tenant_id, role) -> User`
  * `get_by_id(id) -> User | None`
  * `update_role(id, role) -> User`
* Create `src/office_hero/services/auth_service.py` with business logic:
  * `hash_password(password: str) -> str` — uses `passlib.context.CryptContext` with bcrypt work factor 12
  * `verify_password(plain: str, hash: str) -> bool`
  * `issue_jwt(user_id, tenant_id, role, permissions) -> (access_token, refresh_token)` — RS256 with 15min/7day TTL
  * `validate_jwt(token) -> dict` — decodes and validates RS256; raises on expiry/invalid signature
  * `login(email, password, db_session) -> (user, access_token, refresh_token)` — validate creds, hash refresh token
  * `refresh(refresh_token, db_session) -> (user, new_access_token)` — validate refresh token, issue new access
  * `logout(refresh_token, db_session)` — mark refresh token as revoked
* Create `src/office_hero/api/routes/__init__.py` (empty).
* Create `src/office_hero/api/routes/auth.py` with three endpoints:
  * `POST /auth/login` — request: `{email, password}`, response: `{access_token, refresh_token, user: {id, email, role}}`; rate-limited 10 req/min
  * `POST /auth/refresh` — request: `{refresh_token}`, response: `{access_token, user: {id, email, role}}`; rate-limited 10 req/min
  * `POST /auth/logout` — requires valid JWT, request: empty, response: `{status: "ok"}`; revokes refresh token
* Update Alembic `alembic/env.py`: set `target_metadata = Base.metadata` (currently `None`)
  where `Base` is the SQLAlchemy declarative base from `models`.
* Create migration `alembic/versions/0002_users_and_tokens.py`:
  * Creates `users` table with `tenant_id` column and RLS policy
  * Creates `refresh_tokens` table with `user_id` FK + RLS policy
  * Adds unique constraint on `users(tenant_id, email)` (email unique per tenant)
  * No default admin user; that comes in later slices
* Create `tests/test_auth.py` with failing TDD tests:
  * `test_login_returns_tokens` — POST /auth/login 200, response contains access + refresh tokens
  * `test_login_wrong_password_401` — POST /auth/login with wrong password returns 401
  * `test_protected_endpoint_rejects_no_token` — GET /operator/tenants without JWT returns 401
  * `test_protected_endpoint_rejects_expired_token` — JWT past expiry returns 401
  * `test_wrong_role_rejected` — user with Technician role tries GET /operator/tenants returns 403
  * `test_permission_denial_rejected` — user with Sales role but `!dispatch:write` tries dispatch, returns 403
  * `test_require_role_decorator` — unit test @require_role decorator; test both granted and denied
  * `test_jwt_middleware_sets_state` — request through middleware has request.state.user_id, .role, .permissions set
  * `test_refresh_token_flow` — POST /auth/refresh with valid refresh token returns new access token
  * `test_logout_revokes_token` — POST /auth/logout marks refresh token as revoked; next refresh fails

## Structure

```text
src/office_hero/
├── core/
│   ├── config.py        # Settings + environment
│   ├── exceptions.py     # Domain exceptions
│   └── roles.py          # Role enum (8 roles)
├── models/
│   ├── __init__.py
│   ├── user.py           # User ORM model
│   └── token.py          # RefreshToken ORM model
├── repositories/
│   ├── __init__.py
│   └── user_repository.py # User CRUD
├── services/
│   └── auth_service.py    # Auth business logic (hash, JWT, login, refresh, logout)
├── api/
│   ├── app.py            # FastAPI application + CORS + lifespan
│   ├── deps.py           # @require_role, @require_permission dependencies
│   ├── middleware/
│   │   ├── auth.py       # JWT validation middleware
│   │   └── tenant.py     # Tenant RLS context middleware
│   └── routes/
│       ├── __init__.py
│       └── auth.py       # /auth/login, /auth/refresh, /auth/logout

alembic/
└── versions/
    └── 0002_users_and_tokens.py

tests/
└── test_auth.py          # Auth endpoint + decorator tests
```

## Failing Test Outline

```python
import pytest
from fastapi.testclient import TestClient
from office_hero.api.app import app
from office_hero.db.session import get_session

client = TestClient(app)


def test_login_returns_tokens():
    """Successful login returns access and refresh tokens."""
    # Precondition: user with email "admin@t1.com" exists in DB
    resp = client.post("/auth/login", json={"email": "admin@t1.com", "password": "secret"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "admin@t1.com"


def test_login_wrong_password_401():
    """Login with wrong password returns 401."""
    resp = client.post("/auth/login", json={"email": "admin@t1.com", "password": "wrong"})
    assert resp.status_code == 401


def test_protected_endpoint_requires_jwt():
    """GET /operator/tenants without JWT returns 401."""
    resp = client.get("/operator/tenants")
    assert resp.status_code == 401


def test_wrong_role_returns_403():
    """User with Technician role cannot access /operator/tenants (requires Operator+)."""
    # Precondition: technician_token from user with role=Technician
    resp = client.get(
        "/operator/tenants",
        headers={"Authorization": f"Bearer {technician_token}"}
    )
    assert resp.status_code == 403


def test_require_role_decorator():
    """Test @require_role(Owner, Operator) accepts those roles, rejects others."""
    # Unit test: call dependency factory directly
    from office_hero.api.deps import require_role
    req_Owner = require_role(Operator)
    # Mock request.state with role=Technician
    # Should raise 403
```

## Dependencies

Depends on slices 1 (Python scaffold) and 2 (Database foundation).

Slice 2 provides the SQLAlchemy engine and session context; slice 1 provides the
package structure and pyproject.toml.

## Effort

Estimate: 2/5. The JWT logic is well-known (use `python-jose`); bcrypt password hashing
is standard via `passlib`. The main work is: (a) setting up the FastAPI app with middleware
in the right order, (b) writing the repository + service layer, (c) writing the three auth
endpoints, and (d) comprehensive TDD tests covering token refresh, expiry, and permission denials.

---

Once this design is approved, implementation will proceed with the failing `test_auth.py` tests
and corresponding code files. Key concern: JWT RS256 keys must be generated and stored as
environment variables or loaded from a secure location before the app starts. For development,
test keys can be auto-generated or loaded from a fixture.
