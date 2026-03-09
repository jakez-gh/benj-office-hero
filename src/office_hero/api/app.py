"""FastAPI application factory with middleware and configuration."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from office_hero.api.exception_handlers import register_exception_handlers
from office_hero.api.limiter import limiter
from office_hero.api.middleware.auth import JWTAuthMiddleware
from office_hero.api.middleware.logging import LoggingMiddleware
from office_hero.api.middleware.security_headers import SecurityHeadersMiddleware
from office_hero.api.middleware.tenant import TenantContextMiddleware
from office_hero.api.routes import auth as auth_routes
from office_hero.api.routes import health as health_routes
from office_hero.api.state import set_auth_service, set_engine
from office_hero.core.config import Settings, get_settings
from office_hero.core.logging import configure_logging
from office_hero.db.engine import create_async_engine
from office_hero.services.auth_service import AuthService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle: startup and shutdown."""
    configure_logging()

    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    auth_service = AuthService(settings)

    set_engine(engine)
    set_auth_service(auth_service)

    yield

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

    # Attach rate limiter to app state
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Register domain exception handlers (before middleware so they apply globally)
    register_exception_handlers(app)

    # Middleware stack — added in reverse execution order (last added = outermost)
    # Execution order: CORS → security headers → auth → logging → tenant → handler

    # Innermost: tenant RLS context (needs auth state set first)
    app.add_middleware(TenantContextMiddleware)

    # Logging middleware (needs request_id + tenant from auth)
    app.add_middleware(LoggingMiddleware)

    # JWT auth middleware (sets request.state.user_id/tenant_id/role)
    auth_service = AuthService(settings)
    app.add_middleware(JWTAuthMiddleware, auth_service=auth_service)

    # Security headers on all responses
    app.add_middleware(SecurityHeadersMiddleware)

    # CORS outermost
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # slowapi middleware
    app.add_middleware(SlowAPIMiddleware)

    # Routes
    app.include_router(health_routes.router)
    app.include_router(auth_routes.router)

    return app
