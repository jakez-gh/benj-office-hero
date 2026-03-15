"""Office Hero FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from office_hero.api.routes import admin, auth, health, sagas
from office_hero.api.state import set_auth_service, set_engine
from office_hero.core.config import get_settings
from office_hero.db.engine import create_engine
from office_hero.services.auth_service import AuthService


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize shared services for request handlers and clean up on shutdown."""
    engine = create_engine()
    settings = get_settings()
    auth_service = AuthService(settings)

    set_engine(engine)
    set_auth_service(auth_service)

    try:
        yield
    finally:
        await engine.dispose()


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title="Office Hero",
        description="Back-office management API for office services",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Include routers
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(sagas.router, prefix="/sagas", tags=["sagas"])
    app.include_router(admin.router, prefix="/admin", tags=["admin"])

    return app


app = create_app()
