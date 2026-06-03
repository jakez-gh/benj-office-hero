"""Test/demo authentication middleware using X-Test-* headers."""

from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class TestAuthMiddleware(BaseHTTPMiddleware):
    """Middleware for testing/demos that uses X-Test-* headers instead of JWT.

    ONLY FOR DEVELOPMENT AND TESTING — Do not use in production.

    Headers:
    - X-Test-Tenant-Id: UUID of tenant
    - X-Test-User-Id: UUID of user
    - X-Test-Permissions: comma-separated permissions (e.g. "job:read,job:write")
    """

    EXCLUDED_PATHS = {"/health", "/docs", "/openapi.json"}

    async def dispatch(self, request: Request, call_next):
        """Extract test auth headers and set request state."""
        # Skip validation for excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        # Check for test headers
        tenant_id = request.headers.get("X-Test-Tenant-Id")
        user_id = request.headers.get("X-Test-User-Id")
        permissions_header = request.headers.get("X-Test-Permissions", "")

        # Parse permissions (comma-separated)
        permissions = [p.strip() for p in permissions_header.split(",") if p.strip()]

        # Set request state
        request.state.tenant_id = tenant_id
        request.state.user_id = user_id
        request.state.permissions = permissions
        request.state.role = "test-user"

        response = await call_next(request)
        return response
