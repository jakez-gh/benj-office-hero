"""Per-request structured logging middleware."""

from __future__ import annotations

import time
from uuid import UUID, uuid4

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from office_hero.core.logging import get_logger

log = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that binds request context and logs request/response lifecycle."""

    async def dispatch(self, request: Request, call_next):
        # Generate or read request ID
        raw_request_id = request.headers.get("X-Request-ID")
        try:
            request_id = str(UUID(raw_request_id)) if raw_request_id else str(uuid4())
        except ValueError:
            request_id = str(uuid4())

        tenant_id = getattr(request.state, "tenant_id", None)

        # Bind context for all log statements in this request
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            tenant_id=tenant_id,
            method=request.method,
            path=request.url.path,
        )

        # Store request_id on request.state for downstream use
        request.state.request_id = request_id

        start = time.monotonic()
        log.info("request.received")

        try:
            response = await call_next(request)
            duration_ms = round((time.monotonic() - start) * 1000, 1)
            log.info(
                "request.completed",
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception:
            duration_ms = round((time.monotonic() - start) * 1000, 1)
            log.exception("request.failed", duration_ms=duration_ms)
            raise
