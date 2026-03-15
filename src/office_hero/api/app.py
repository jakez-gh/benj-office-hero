"""Office Hero FastAPI application factory with dependency injection."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from office_hero.repositories.mocks import MockOutboxRepository, MockSagaRepository
from office_hero.repositories.protocols import OutboxRepository
from office_hero.services.saga_service import SagaService


def create_app(
    *,
    saga_service: SagaService | None = None,
    outbox_repo: OutboxRepository | None = None,
) -> FastAPI:
    """Create FastAPI app with optional dependency injection for testability.

    Args:
        saga_service: SagaService instance (defaults to mock-backed for dev).
        outbox_repo: OutboxRepository instance (defaults to mock for dev).
    """
    if saga_service is None:
        saga_service = SagaService(saga_repo=MockSagaRepository())
    if outbox_repo is None:
        outbox_repo = MockOutboxRepository()

    from office_hero.api.routes.admin import create_admin_router
    from office_hero.api.routes.sagas import create_saga_router

    application = FastAPI(
        title="Office Hero",
        description="Back-office management API for office services",
        version="0.1.0",
    )

    @application.get("/health", tags=["health"])
    async def health_check():
        """Health check endpoint."""
        return JSONResponse({"status": "ok"})

    # Include routers with injected dependencies
    application.include_router(
        create_saga_router(saga_service=saga_service),
        prefix="/sagas",
        tags=["sagas"],
    )
    application.include_router(
        create_admin_router(saga_service=saga_service, outbox_repo=outbox_repo),
        prefix="/admin",
        tags=["admin"],
    )

    return application


# Module-level app for uvicorn / existing imports
app = create_app()
