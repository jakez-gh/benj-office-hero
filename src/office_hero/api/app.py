"""Office Hero FastAPI application factory (SOLID: SRP, DIP)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from office_hero.api.exception_handlers import register_exception_handlers
from office_hero.api.limiter import limiter
from office_hero.api.middleware.logging import LoggingMiddleware
from office_hero.api.middleware.security_headers import SecurityHeadersMiddleware
from office_hero.api.routes import admin, health, sagas
from office_hero.api.state import set_auth_service, set_engine
from office_hero.core.logging import get_logger

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: bring up shared resources, then dispose them.

    Startup:
        * Build the async SQLAlchemy engine from ``DATABASE_URL`` (if set) and
          register it in module-level state so request handlers can resolve it
          via ``office_hero.api.state.get_engine``.
        * Build the ``AuthService`` from environment-derived ``Settings`` (if
          ``JWT_PRIVATE_KEY``/``JWT_PUBLIC_KEY`` are present) and register it
          in module-level state.

    Shutdown:
        * Dispose the engine pool so connections are released cleanly.

    Missing config is treated as non-fatal at startup — individual routes
    will surface a ``RuntimeError`` if they try to use an uninitialized
    dependency. This keeps the test environment (which never has Postgres
    available) working while still wiring real lifecycle in production.
    """
    engine = None
    try:
        try:
            from office_hero.core.config import get_settings
            from office_hero.db.engine import create_engine
            from office_hero.services.auth_service import AuthService

            settings = get_settings()
            engine = create_engine(settings.database_url)
            set_engine(engine)
            set_auth_service(AuthService(settings))
            log.info("app.lifespan.startup", db="ready", auth="ready")
        except Exception as exc:  # noqa: BLE001 - intentional broad catch
            log.warning("app.lifespan.startup_skipped", error=str(exc))

        yield
    finally:
        if engine is not None:
            try:
                await engine.dispose()
                log.info("app.lifespan.shutdown", db="disposed")
            except Exception as exc:  # noqa: BLE001 - intentional broad catch
                log.warning("app.lifespan.shutdown_failed", error=str(exc))


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Wires middleware (order matters — outermost first), exception handlers,
    the slowapi rate limiter, and all route routers.
    """
    application = FastAPI(
        title="Office Hero",
        description="Back-office management API for office services",
        version="0.1.0",
        lifespan=lifespan,
    )

    # --- Middleware (outermost ➜ innermost) ---
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
    application.include_router(sagas.router, prefix="/sagas", tags=["sagas"])
    application.include_router(admin.router, prefix="/admin", tags=["admin"])

    return application


# Module-level instance used by TestClient and uvicorn
app = create_app()
