"""Shared request-context helpers for route handlers.

Every ``api/routes/*.py`` module previously defined identical local
``_tenant_id`` / ``_user_id`` helpers that read auth context off
``request.state`` (populated by the JWT / test-auth middleware).  These are
the single source of truth so the auth-extraction logic lives in one place.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Request, status
from fastapi.exceptions import HTTPException


def _coerce_uuid(raw: object) -> UUID:
    return raw if isinstance(raw, UUID) else UUID(str(raw))


def require_tenant_id(request: Request) -> UUID:
    """Return the request's tenant_id, or raise 401 if unauthenticated."""
    raw = getattr(request.state, "tenant_id", None)
    if not raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return _coerce_uuid(raw)


def require_user_id(request: Request) -> UUID:
    """Return the request's user_id (for audit attribution), or raise 401."""
    raw = getattr(request.state, "user_id", None)
    if not raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return _coerce_uuid(raw)


def optional_user_id(request: Request) -> UUID | None:
    """Return the request's user_id or None when absent (no raise).

    Used where user attribution is best-effort (e.g. the dispatch route, which
    passes the id through to services that tolerate ``None``).
    """
    raw = getattr(request.state, "user_id", None)
    if not raw:
        return None
    return _coerce_uuid(raw)
