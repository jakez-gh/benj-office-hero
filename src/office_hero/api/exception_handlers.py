"""Global exception handlers — convert domain exceptions to HTTP responses."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from office_hero.core.exceptions import AuthError, PermissionError, TenantError
from office_hero.core.logging import get_logger

log = get_logger(__name__)


async def auth_error_handler(request: Request, exc: AuthError) -> JSONResponse:
    """Convert AuthError to 401 Unauthorized."""
    request_id = getattr(request.state, "request_id", None)
    log.warning("auth.error", message=exc.message, request_id=request_id)
    return JSONResponse(
        status_code=401,
        content={"detail": exc.message, "request_id": request_id},
    )


async def permission_error_handler(request: Request, exc: PermissionError) -> JSONResponse:
    """Convert PermissionError to 403 Forbidden."""
    request_id = getattr(request.state, "request_id", None)
    log.warning("permission.denied", message=exc.message, request_id=request_id)
    return JSONResponse(
        status_code=403,
        content={"detail": exc.message, "request_id": request_id},
    )


async def tenant_error_handler(request: Request, exc: TenantError) -> JSONResponse:
    """Convert TenantError to 400 Bad Request."""
    request_id = getattr(request.state, "request_id", None)
    log.warning("tenant.error", message=exc.message, request_id=request_id)
    return JSONResponse(
        status_code=400,
        content={"detail": exc.message, "request_id": request_id},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Convert unhandled exceptions to 500 — logs full traceback, never leaks it."""
    request_id = getattr(request.state, "request_id", None)
    log.exception("server.error", request_id=request_id)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred.",
            "request_id": request_id,
        },
    )


def register_exception_handlers(app) -> None:
    """Register all global exception handlers on the FastAPI app."""
    app.add_exception_handler(AuthError, auth_error_handler)
    app.add_exception_handler(PermissionError, permission_error_handler)
    app.add_exception_handler(TenantError, tenant_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
