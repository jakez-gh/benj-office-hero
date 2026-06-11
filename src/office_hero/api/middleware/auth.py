"""JWT authentication middleware."""

from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from office_hero.core.exceptions import AuthError


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Middleware that validates Bearer JWTs and sets request state.

    The AuthService is resolved lazily from app state on each request because
    it is only registered during application lifespan startup (and may be
    absent entirely in test environments without JWT keys). Requests without
    an ``Authorization: Bearer`` header pass through untouched so endpoint
    dependencies (``require_auth``/``require_permission``/``require_role``)
    can reject them — and so test fixtures that set request state via their
    own middleware are not clobbered.
    """

    # Paths that skip JWT validation
    EXCLUDED_PATHS = {"/health", "/auth/login", "/auth/refresh", "/docs", "/openapi.json"}

    async def dispatch(self, request: Request, call_next):
        """Process request and validate JWT if present."""
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return await call_next(request)

        from office_hero.api.state import get_auth_service

        try:
            auth_service = get_auth_service()
        except RuntimeError:
            # Auth service not configured (e.g. unit tests without JWT keys).
            return await call_next(request)

        token = auth_header.split(" ", 1)[1]

        try:
            payload = auth_service.validate_jwt(token)
        except AuthError:
            # Invalid/expired token: explicitly clear identity so endpoint
            # dependencies reject the request.
            request.state.user_id = None
            request.state.tenant_id = None
            request.state.role = None
            request.state.permissions = []
            return await call_next(request)

        request.state.user_id = payload.get("user_id")
        request.state.tenant_id = payload.get("tenant_id")
        request.state.role = payload.get("role")
        request.state.permissions = payload.get("permissions", [])

        return await call_next(request)
