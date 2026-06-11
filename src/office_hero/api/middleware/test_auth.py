"""Test/demo authentication middleware using X-Test-* headers.

SECURITY: this middleware bypasses JWT authentication entirely. It is only
installed by ``create_app`` when the ``OFFICE_HERO_TEST_AUTH`` environment
variable is set to ``1``/``true`` — never enable that in production.
"""

from __future__ import annotations

import os

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


def test_auth_enabled() -> bool:
    """Whether the X-Test-* header auth bypass is explicitly enabled."""
    return os.environ.get("OFFICE_HERO_TEST_AUTH", "").lower() in {"1", "true", "yes"}


class TestAuthMiddleware(BaseHTTPMiddleware):
    """Middleware for testing/demos that uses X-Test-* headers instead of JWT.

    ONLY FOR DEVELOPMENT AND TESTING — never enable in production.

    Headers:
    - X-Test-Tenant-Id: UUID of tenant
    - X-Test-User-Id: UUID of user
    - X-Test-Role: role string (e.g. "tenant_admin"); defaults to "test-user"
    - X-Test-Permissions: comma-separated permissions (e.g. "job:read,job:write")

    Requests without any X-Test-* identity headers pass through untouched so
    real JWT auth (or test fixtures' own middleware) still applies.
    """

    EXCLUDED_PATHS = {"/health", "/docs", "/openapi.json"}

    async def dispatch(self, request: Request, call_next):
        """Extract test auth headers and set request state."""
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        tenant_id = request.headers.get("X-Test-Tenant-Id")
        user_id = request.headers.get("X-Test-User-Id")

        # No test identity supplied — leave request state alone.
        if not tenant_id and not user_id:
            return await call_next(request)

        permissions_header = request.headers.get("X-Test-Permissions", "")
        permissions = [p.strip() for p in permissions_header.split(",") if p.strip()]

        request.state.tenant_id = tenant_id
        request.state.user_id = user_id
        request.state.permissions = permissions
        request.state.role = request.headers.get("X-Test-Role", "test-user")

        return await call_next(request)
