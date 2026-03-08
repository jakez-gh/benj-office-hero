from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt


class AuthService:
    """Service responsible for authentication logic.

    Right now it handles password hashing/verification and access token
    issuance/validation.  In later slices it will also manage refresh tokens
    via a :class:`~office_hero.repositories.token_repository.TokenRepository`.
    """

    def __init__(
        self,
        private_key: str,
        public_key: str,
        algorithm: str = "RS256",
        access_token_expires: int = 15 * 60,
    ) -> None:
        self._private_key = private_key
        self._public_key = public_key
        self._algorithm = algorithm
        self._access_token_expires = access_token_expires

    def hash_password(self, plaintext: str) -> str:
        """Return a bcrypt hash of ``plaintext``."""

        hashed = bcrypt.hashpw(plaintext.encode("utf-8"), bcrypt.gensalt())
        return hashed.decode("utf-8")

    def verify_password(self, plaintext: str, hashed: str) -> bool:
        """Return ``True`` if ``plaintext`` matches the bcrypt ``hashed`` value."""

        try:
            return bcrypt.checkpw(plaintext.encode("utf-8"), hashed.encode("utf-8"))
        except ValueError:
            return False

    def issue_access_token(self, claims: dict[str, Any]) -> str:
        """Create a signed JWT access token containing ``claims``.

        The ``claims`` dict should already include standard fields such as
        ``sub`` (subject) and ``role``.  An ``exp`` field will be added
        automatically based on ``access_token_expires``.
        """

        payload = claims.copy()
        now = datetime.utcnow()
        payload.setdefault("iat", int(now.timestamp()))
        payload["exp"] = int((now + timedelta(seconds=self._access_token_expires)).timestamp())

        token = jwt.encode(payload, self._private_key, algorithm=self._algorithm)
        return token

    def verify_access_token(self, token: str) -> dict[str, Any]:
        """Decode and verify an access token, returning the claims.

        Raises :class:`jose.JWTError` on failure.
        """

        try:
            claims = jwt.decode(token, self._public_key, algorithms=[self._algorithm])
            return claims
        except JWTError:
            raise
