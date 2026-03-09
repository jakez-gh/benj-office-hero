"""JWT authentication middleware."""

from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from office_hero.core.exceptions import AuthError
from office_hero.services.auth_service import AuthService


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Middleware that validates JWT tokens and sets request state."""

    # Paths that skip JWT validation
    EXCLUDED_PATHS = {"/health", "/auth/login", "/auth/refresh", "/docs", "/openapi.json"}

    def __init__(self, app, auth_service: AuthService):
        """Initialize with FastAPI app and AuthService."""
        super().__init__(app)
        self.auth_service = auth_service

    async def dispatch(self, request: Request, call_next):
        """Process request and validate JWT if needed."""
        # Skip validation for excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        # Extract Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            request.state.user_id = None
            request.state.tenant_id = None
            request.state.role = None
            request.state.permissions = []
            # Continue anyway; endpoint auth decorators will enforce
            return await call_next(request)

        token = auth_header.split(" ", 1)[1]

        try:
            payload = self.auth_service.validate_jwt(token)
        except AuthError:
            # Set state to None values; let endpoint handle 401
            request.state.user_id = None
            request.state.tenant_id = None
            request.state.role = None
            request.state.permissions = []
            return await call_next(request)

        # Set request state from JWT payload
        request.state.user_id = payload.get("user_id")
        request.state.tenant_id = payload.get("tenant_id")
        request.state.role = payload.get("role")
        request.state.permissions = payload.get("permissions", [])

        response = await call_next(request)
        return response
