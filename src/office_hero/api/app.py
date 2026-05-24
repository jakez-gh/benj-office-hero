"""Office Hero FastAPI application factory (SOLID: SRP, DIP)."""

from fastapi import FastAPI

from office_hero.api.exception_handlers import register_exception_handlers
from office_hero.api.limiter import limiter
from office_hero.api.middleware.logging import LoggingMiddleware
from office_hero.api.middleware.security_headers import SecurityHeadersMiddleware
from office_hero.api.routes import admin, health, sagas


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Wires middleware (order matters — outermost first), exception handlers,
    the slowapi rate limiter, and all route routers.
    """
    application = FastAPI(
        title="Office Hero",
        description="Back-office management API for office services",
        version="0.1.0",
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
