"""Office Hero FastAPI application factory (SOLID: SRP, DIP).

The app is constructed via ``create_app`` so saga / outbox dependencies can be
injected at startup (tests pass mocks; production wires the real repositories).
A module-level ``app`` instance is created at import time using the in-memory
mock repositories so legacy tests that do ``from office_hero.api.app import app``
continue to work.
"""

from __future__ import annotations

from fastapi import FastAPI

from office_hero.api.exception_handlers import register_exception_handlers
from office_hero.api.limiter import limiter
from office_hero.api.middleware.logging import LoggingMiddleware
from office_hero.api.middleware.security_headers import SecurityHeadersMiddleware
from office_hero.api.routes import health
from office_hero.api.routes.admin import audit_router, create_admin_router
from office_hero.api.routes.sagas import create_saga_router
from office_hero.repositories.mocks import MockOutboxRepository, MockSagaRepository
from office_hero.repositories.protocols import OutboxRepository
from office_hero.services.saga_service import SagaService


def create_app(
    *,
    saga_service: SagaService | None = None,
    outbox_repo: OutboxRepository | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Wires middleware (order matters - outermost first), exception handlers,
    the slowapi rate limiter, and all route routers.

    Args:
        saga_service: Saga orchestrator. Defaults to an in-memory mock-backed
            instance so the module-level ``app`` boots without a database.
        outbox_repo: Outbox repository for dead-letter routes. Defaults to an
            in-memory mock.

    The factory invokes ``create_saga_router`` / ``create_admin_router`` once
    at startup, not per-request.
    """
    if saga_service is None:
        saga_service = SagaService(saga_repo=MockSagaRepository())
    if outbox_repo is None:
        outbox_repo = MockOutboxRepository()

    application = FastAPI(
        title="Office Hero",
        description="Back-office management API for office services",
        version="0.1.0",
    )

    # --- Middleware (outermost -> innermost) ---
    # Security headers must wrap everything so every response gets them.
    application.add_middleware(SecurityHeadersMiddleware)
    # Logging after security so request_id is available for error responses.
    application.add_middleware(LoggingMiddleware)

    # --- Exception handlers ---
    register_exception_handlers(application)

    # --- slowapi rate limiter state ---
    application.state.limiter = limiter

    # --- Routers ---
    application.include_router(health.router, tags=["health"])

    saga_router = create_saga_router(saga_service=saga_service)
    application.include_router(saga_router, prefix="/sagas", tags=["sagas"])

    admin_router = create_admin_router(
        saga_service=saga_service,
        outbox_repo=outbox_repo,
    )
    application.include_router(admin_router, prefix="/admin", tags=["admin"])
    application.include_router(audit_router, prefix="/admin", tags=["admin"])

    return application


# Module-level instance used by TestClient and uvicorn. Uses in-memory mocks
# so the import succeeds without a live database; production callers should
# build their own app via ``create_app(saga_service=..., outbox_repo=...)``.
app = create_app()
