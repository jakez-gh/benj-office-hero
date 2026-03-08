---
docType: slice-design
parent: ../project-guides/003-slices.office-hero.md
project: office-hero
dateCreated: 20260308
status: in_progress
---

# Slice Design 006: Authentication & RBAC

This slice implements the core authentication stack described in the ADR
(060-auth) and introduces a minimal role-based access control helper used by
later API endpoints.

## Goals

* Add `AuthService` with password hashing (bcrypt) and JWT issuance/verification.
  * Access tokens are RS256 by default; tests use HS256 symmetric key for
    simplicity.  Private/public keys will be provided via environment or
    secrets in production.
* Provide a `require_role` decorator that clients can apply to functions.  It
  uses a simple in-memory hierarchy (User &lt; Technician &lt; TenantAdmin &lt;
  Operator) for now.
* Stub out a refresh-token repository class so that later slices can store
  refresh tokens without breaking imports.
* Add authentication middleware helper with a trivial ``decode_jwt`` function.
* Write unit tests verifying:
  1. Password hashing/verification works.
  2. An access token can be issued and round-tripped.
  3. The `@require_role` decorator allows/denies based on roles and handles
     missing/unknown roles.
* Update `pyproject.toml` with new dependencies: `bcrypt` and
  `python-jose[cryptography]`.

## Structure additions

```text
src/office_hero/
├── api/
│   ├── auth.py            # RBAC decorator + related error
│   └── middleware/auth.py # JWT decode helper (placeholder)
├── repositories/
│   └── token_repository.py # stub for refresh tokens
└── services/
    └── auth_service.py    # password+token logic

tests/
└── test_auth.py          # unit tests for auth slice
```

## Implementation notes

* The auth service uses ``python-jose`` for JWT handling; tests override the
  algorithm to HS256 to avoid needing a real keypair at this stage.  Later
  slices will load keys from configuration.
* The ``require_role`` decorator is intentionally simple and does not yet
  interact with any database.  Auth middleware will supply the ``claims``
  dict in actual API handlers.

## Failing tests outline

See ``tests/test_auth.py``; they drive development of the auth modules and
initialize the dependencies.

## Consequences

Completing this slice enables subsequent slices that need user login,
permissions checks, and token revocation support.  The code is purposely
minimal yet structured so that replacing the JWT strategy or expanding the
role hierarchy is straightforward.
