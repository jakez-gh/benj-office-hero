"""Shared pytest fixtures for the Office Hero test suite.

Provides helpers to:
  - Inject a test tenant_id into ``request.state`` so admin routes can
    enforce tenant isolation without a real JWT auth middleware.
  - Bypass the Operator RBAC dependency in unit tests.
  - Make the ``mcp-server`` package importable during tests so MCP tests
    can locate ``office_hero_mcp`` without an install step.

Tests that need the tenant/auth behaviours should either use the
``configure_admin_app`` fixture or call :func:`override_admin_auth`
directly on their own ``app``.
"""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from office_hero.api.routes.admin import require_operator

# Make ``office_hero_mcp`` (lives under ``mcp-server/src``) importable.
_root = Path(__file__).parent.parent
_mcp_src = _root / "mcp-server" / "src"
if str(_mcp_src) not in sys.path:
    sys.path.insert(0, str(_mcp_src))


class _TestTenantMiddleware(BaseHTTPMiddleware):
    """Test-only middleware that populates ``request.state.tenant_id``.

    Reads either the ``X-Test-Tenant-ID`` header (if a test wants per-request
    control) or falls back to a single default tenant set on the app state.
    """

    async def dispatch(self, request: Request, call_next):
        header = request.headers.get("X-Test-Tenant-ID")
        default = getattr(request.app.state, "test_default_tenant_id", None)

        if header:
            request.state.tenant_id = header
        elif default is not None:
            request.state.tenant_id = str(default)
        else:
            request.state.tenant_id = None

        request.state.role = "operator"
        return await call_next(request)


def override_admin_auth(app: FastAPI, *, tenant_id: UUID | str | None = None) -> UUID:
    """Configure ``app`` so admin/saga routes work in unit tests.

    - Adds a middleware that sets ``request.state.tenant_id`` and ``role``.
    - Overrides the ``require_operator`` dependency to a no-op.

    Returns the tenant_id used (a freshly-generated one if none was supplied)
    so tests can refer to it when seeding repository state.
    """
    if tenant_id is None:
        tenant_id = uuid4()

    app.state.test_default_tenant_id = tenant_id
    app.add_middleware(_TestTenantMiddleware)
    app.dependency_overrides[require_operator] = lambda: "operator"

    return tenant_id if isinstance(tenant_id, UUID) else UUID(str(tenant_id))


@pytest.fixture()
def default_tenant_id() -> UUID:
    """A stable tenant_id for tests that don't care which one they use."""
    return uuid4()
