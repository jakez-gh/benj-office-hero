from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any


class InsufficientRoleError(Exception):
    """Raised when a caller lacks the required role."""


# define a simple hierarchical ordering for roles; later slices will make this
# configurable or data-driven.  Lower index = lower privilege.
_ROLE_HIERARCHY = [
    "User",
    "Technician",
    "TenantAdmin",
    "Operator",
]


def require_role(minimum_role: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator that asserts the supplied claims meet ``minimum_role``.

    The decorated function is expected to accept a ``claims`` dict as its
    first argument.  This keeps the decorator framework-agnostic for now; later
    middleware will inject the claims extracted from the JWT.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapper(claims: dict, *args, **kwargs):
            role = claims.get("role")
            if role is None:
                raise InsufficientRoleError("no role present in claims")
            try:
                role_index = _ROLE_HIERARCHY.index(role)
                min_index = _ROLE_HIERARCHY.index(minimum_role)
            except ValueError:
                # either the current role or the minimum role is unrecognized
                raise InsufficientRoleError(f"unknown role: {role}") from None
            if role_index < min_index:
                raise InsufficientRoleError(f"requires role {minimum_role}, got {role}")
            return fn(claims, *args, **kwargs)

        return wrapper

    return decorator
