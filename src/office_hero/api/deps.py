"""FastAPI dependency factories for RBAC and authentication."""

from __future__ import annotations

from fastapi import Request, status
from fastapi.exceptions import HTTPException

from office_hero.core.roles import Role


def require_role(roles: list[Role]):
    """Dependency factory that checks if user has one of the required roles.

    Args:
        roles: List of Role enums that are allowed.

    Returns:
        Dependency function to be used with FastAPI Depends.

    Raises:
        HTTPException: 403 if user doesn't have required role.
    """

    async def _require_role(request: Request):
        user_role = getattr(request.state, "role", None)
        allowed_roles = [r.value if isinstance(r, Role) else r for r in roles]

        if user_role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

        return user_role

    return _require_role


def require_permission(permission: str):
    """Dependency factory that checks if user has a specific permission.

    Args:
        permission: Permission string (e.g., "jobs:write", "routes:read").

    Returns:
        Dependency function to be used with FastAPI Depends.

    Raises:
        HTTPException: 403 if user doesn't have required permission.
    """

    async def _require_permission(request: Request):
        permissions = getattr(request.state, "permissions", [])

        # Check for permission or deny-permission prefix
        has_permission = permission in permissions
        denied_permission = f"!{permission}" in permissions

        if not has_permission or denied_permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

        return permission

    return _require_permission


async def require_auth(request: Request):
    """Dependency that requires valid authentication.

    Raises:
        HTTPException: 401 if user is not authenticated.
    """
    user_id = getattr(request.state, "user_id", None)

    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    return user_id
