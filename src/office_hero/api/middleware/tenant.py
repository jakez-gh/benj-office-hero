"""Tenant RLS context middleware."""

from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

try:
    from starlette_context import context
except ImportError:
    context = None


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Middleware that sets tenant_id in starlette_context for RLS filtering."""

    async def dispatch(self, request: Request, call_next):
        """Set tenant_id from request.state in starlette_context for get_session to use."""
        # Get tenant_id from JWT auth middleware
        tenant_id = getattr(request.state, "tenant_id", None)

        # If starlette_context is available, set it for get_session to use
        if context is not None and tenant_id:
            context["tenant_id"] = tenant_id

        response = await call_next(request)
        return response
