"""Authentication service with JWT and passlib pbkdf2_sha256."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

# PBKDF2-SHA256 hashing context (avoids external bcrypt dependency and
# 72-byte limit issues). Work factor via rounds ~ 20000.
_pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto",
    pbkdf2_sha256__rounds=20000,
)


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
        """Return a pbkdf2_sha256 hash of ``plaintext`` (20,000 rounds)."""
        return _pwd_context.hash(plaintext)

    def verify_password(self, plaintext: str, hashed: str) -> bool:
        """Return ``True`` if ``plaintext`` matches the pbkdf2_sha256 ``hashed`` value."""
        try:
            return _pwd_context.verify(plaintext, hashed)
        except ValueError:
            return False

    def issue_access_token(self, claims: dict[str, Any]) -> str:
        """Create a signed JWT access token containing ``claims``.

        The ``claims`` dict should already include standard fields such as
        ``sub`` (subject) and ``role``.  An ``exp`` field will be added
        automatically based on ``access_token_expires``.
        """

        payload = claims.copy()
        now = datetime.now(UTC)
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
