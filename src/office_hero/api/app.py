"""FastAPI application factory with middleware and configuration."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from office_hero.api.middleware.auth import JWTAuthMiddleware
from office_hero.api.middleware.tenant import TenantContextMiddleware
from office_hero.api.routes import auth as auth_routes
from office_hero.api.state import set_auth_service, set_engine
from office_hero.core.config import Settings, get_settings
from office_hero.db.engine import create_async_engine
from office_hero.services.auth_service import AuthService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle: startup and shutdown."""
    # Startup
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    auth_service = AuthService(settings)

    set_engine(engine)
    set_auth_service(auth_service)

    yield

    # Shutdown
    if engine:
        await engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure FastAPI application.

    Args:
        settings: Optional Settings instance. If None, loads from environment.

    Returns:
        Configured FastAPI app instance.
    """
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title="Office Hero API",
        description="Multi-tenant field service management platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, restrict to specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add tenant RLS context middleware
    app.add_middleware(TenantContextMiddleware)

    # Add JWT auth middleware
    auth_service = AuthService(settings)
    app.add_middleware(JWTAuthMiddleware, auth_service=auth_service)

    # Add health check endpoint
    @app.get("/health")
    async def health_check():
        """Simple health check endpoint."""
        return {"status": "ok"}

    # Include auth routes
    app.include_router(auth_routes.router)

    return app
