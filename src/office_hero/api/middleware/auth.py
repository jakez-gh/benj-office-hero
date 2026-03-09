"""Authentication middleware placeholder.

Actual web framework integration will happen in later slices; for now the
module exposes utility functions that can be imported by tests.
"""

from typing import Any

from jose import jwt


def decode_jwt(token: str, public_key: str, algorithms: list[str]) -> dict[str, Any]:
    """Decode and validate a JWT token, returning its claims.

    A real middleware would extract the token from headers, call this helper,
    and attach the resulting claims to the request/context.
    """
    return jwt.decode(token, public_key, algorithms=algorithms)
