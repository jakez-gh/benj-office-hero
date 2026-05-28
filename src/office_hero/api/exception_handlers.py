"""Global exception handlers — convert domain exceptions to HTTP responses."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from office_hero.core.exceptions import (
    AuthError,
    CrewAssignmentConflictError,
    InvalidCrewMemberError,
    PermissionError,
    TenantError,
    VehicleCrewNotFoundError,
    VehicleNotFoundError,
)
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


async def rate_limit_error_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Convert slowapi RateLimitExceeded to 429 with Retry-After header.

    Returns a human-friendly message and the standard Retry-After header so
    clients (admin-web, tech-mobile) can display a meaningful toast.
    """
    request_id = getattr(request.state, "request_id", None)
    # Parse retry window from the exception detail (e.g. "Rate limit exceeded: 10 per 1 minute")
    retry_after_seconds = 60  # sensible default
    detail_str = str(exc.detail) if hasattr(exc, "detail") else str(exc)

    log.warning(
        "rate_limit.exceeded",
        request_id=request_id,
        detail=detail_str,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Too many requests. Please wait before trying again.",
            "retry_after": retry_after_seconds,
            "request_id": request_id,
        },
        headers={"Retry-After": str(retry_after_seconds)},
    )


async def vehicle_not_found_handler(request: Request, exc: VehicleNotFoundError) -> JSONResponse:
    """Convert VehicleNotFoundError to 404."""
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=404,
        content={"detail": exc.message, "request_id": request_id},
    )


async def vehicle_crew_not_found_handler(
    request: Request, exc: VehicleCrewNotFoundError
) -> JSONResponse:
    """Convert VehicleCrewNotFoundError to 404."""
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=404,
        content={"detail": exc.message, "request_id": request_id},
    )


async def crew_assignment_conflict_handler(
    request: Request, exc: CrewAssignmentConflictError
) -> JSONResponse:
    """Convert CrewAssignmentConflictError to 409 with existing_crew_id."""
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=409,
        content={
            "detail": exc.message,
            "existing_crew_id": str(exc.existing_crew_id) if exc.existing_crew_id else None,
            "request_id": request_id,
        },
    )


async def invalid_crew_member_handler(
    request: Request, exc: InvalidCrewMemberError
) -> JSONResponse:
    """Convert InvalidCrewMemberError to 422 with user_id and reason."""
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.message,
            "user_id": str(exc.user_id) if exc.user_id else None,
            "reason": exc.reason,
            "request_id": request_id,
        },
    )


def register_exception_handlers(app) -> None:
    """Register all global exception handlers on the FastAPI app."""
    app.add_exception_handler(AuthError, auth_error_handler)
    app.add_exception_handler(PermissionError, permission_error_handler)
    app.add_exception_handler(TenantError, tenant_error_handler)
    app.add_exception_handler(VehicleNotFoundError, vehicle_not_found_handler)
    app.add_exception_handler(VehicleCrewNotFoundError, vehicle_crew_not_found_handler)
    app.add_exception_handler(CrewAssignmentConflictError, crew_assignment_conflict_handler)
    app.add_exception_handler(InvalidCrewMemberError, invalid_crew_member_handler)
    app.add_exception_handler(RateLimitExceeded, rate_limit_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
