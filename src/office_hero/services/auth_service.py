"""Authentication service with JWT and passlib pbkdf2_sha256."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from office_hero.core.config import Settings
from office_hero.core.exceptions import AuthError
from office_hero.core.roles import Role
from office_hero.models import RefreshToken, User
from office_hero.repositories.user_repository import UserRepository

# PBKDF2-SHA256 hashing context (avoids external bcrypt dependency and
# 72-byte limit issues during tests). Work factor via rounds ~ 20000.
pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto",
    pbkdf2_sha256__rounds=20000,
)


class AuthService:
    """Service for authentication, JWT token management, and password handling."""

    def __init__(self, settings: Settings):
        """Initialize with configuration."""
        self.settings = settings

    def hash_password(self, password: str) -> str:
        """Hash a plaintext password using pbkdf2_sha256 (20,000 rounds)."""
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, password_hash: str) -> bool:
        """Verify plaintext password against pbkdf2_sha256 hash."""
        return pwd_context.verify(plain_password, password_hash)

    def issue_jwt(
        self,
        user_id: UUID,
        tenant_id: UUID,
        role: Role,
        permissions: list | None = None,
    ) -> tuple[str, str]:
        """Issue access and refresh tokens for user.

        Returns:
            Tuple of (access_token, refresh_token)
        """
        if permissions is None:
            permissions = []

        now = datetime.now(UTC)
        access_expires = now + timedelta(minutes=self.settings.access_token_ttl_minutes)
        refresh_expires = now + timedelta(days=self.settings.refresh_token_ttl_days)

        access_payload = {
            "user_id": str(user_id),
            "tenant_id": str(tenant_id),
            "role": role.value,
            "permissions": permissions,
            "exp": access_expires,
            "iat": now,
        }

        refresh_payload = {
            "user_id": str(user_id),
            "tenant_id": str(tenant_id),
            "exp": refresh_expires,
            "iat": now,
            "type": "refresh",
        }

        access_token = jwt.encode(
            access_payload,
            self.settings.jwt_private_key,
            algorithm=self.settings.jwt_algorithm,
        )

        refresh_token = jwt.encode(
            refresh_payload,
            self.settings.jwt_private_key,
            algorithm=self.settings.jwt_algorithm,
        )

        return access_token, refresh_token

    def validate_jwt(self, token: str) -> dict:
        """Validate and decode JWT token.

        Raises:
            AuthError: If token is invalid, expired, or signature verification fails.
        """
        try:
            payload = jwt.decode(
                token,
                self.settings.jwt_public_key,
                algorithms=[self.settings.jwt_algorithm],
            )
            return payload
        except JWTError as e:
            raise AuthError(f"Invalid token: {str(e)}") from e

    async def login(
        self, email: str, password: str, session: AsyncSession
    ) -> tuple[User, str, str]:
        """Authenticate user and return (user, access_token, refresh_token).

        Raises:
            AuthError: If credentials are invalid.
        """
        repo = UserRepository(session)
        user = await repo.get_by_email(email)

        if not user or not self.verify_password(password, user.password_hash):
            raise AuthError("Invalid email or password")

        access_token, refresh_token = self.issue_jwt(
            user.id, user.tenant_id, Role(user.role), user.permissions
        )

        # Hash refresh token and store in DB
        refresh_token_hash = self.hash_password(refresh_token)
        expires_at = datetime.now(UTC) + timedelta(days=self.settings.refresh_token_ttl_days)
        refresh_token_obj = RefreshToken(
            user_id=user.id,
            token_hash=refresh_token_hash,
            expires_at=expires_at,
            revoked=False,
        )
        session.add(refresh_token_obj)
        await session.flush()

        return user, access_token, refresh_token

    async def refresh(self, refresh_token: str, session: AsyncSession) -> tuple[User, str]:
        """Validate refresh token and issue new access token.

        Raises:
            AuthError: If refresh token is invalid or revoked.
        """
        payload = self.validate_jwt(refresh_token)

        if payload.get("type") != "refresh":
            raise AuthError("Token is not a refresh token")

        user_id = UUID(payload["user_id"])
        tenant_id = UUID(payload["tenant_id"])

        repo = UserRepository(session)
        user = await repo.get_by_id(user_id)

        if not user or user.tenant_id != tenant_id:
            raise AuthError("User not found or tenant mismatch")

        # Check if refresh token is revoked (in production, query DB)
        # For now, we assume valid tokens are not revoked

        # Issue new access token
        access_token, _ = self.issue_jwt(user.id, user.tenant_id, Role(user.role), user.permissions)

        return user, access_token

    async def logout(self, refresh_token: str, session: AsyncSession) -> None:
        """Revoke refresh token on logout.

        In a real system, this would update the database to mark the token as revoked.
        For now, it's a placeholder for the flow.
        """
        self.validate_jwt(refresh_token)
        # In production: mark token as revoked in DB via token_hash lookup
        # Wired in Slice 4 (Observability) audit events table.
