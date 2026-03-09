"""Global app state for engine and auth service."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine

from office_hero.services.auth_service import AuthService

# Global variables for app lifecycle
_engine: AsyncEngine | None = None
_auth_service: AuthService | None = None


def get_engine() -> AsyncEngine:
    """Get the global engine instance."""
    global _engine
    if _engine is None:
        raise RuntimeError("Engine not initialized. Ensure app has been created with create_app()")
    return _engine


def get_auth_service() -> AuthService:
    """Get the global auth service instance."""
    global _auth_service
    if _auth_service is None:
        raise RuntimeError(
            "AuthService not initialized. Ensure app has been created with create_app()"
        )
    return _auth_service


def set_engine(engine: AsyncEngine) -> None:
    """Set the global engine instance."""
    global _engine
    _engine = engine


def set_auth_service(auth_service: AuthService) -> None:
    """Set the global auth service instance."""
    global _auth_service
    _auth_service = auth_service
