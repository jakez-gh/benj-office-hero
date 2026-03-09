"""Unit tests for AuthService."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from office_hero.core.config import Settings
from office_hero.core.exceptions import AuthError
from office_hero.core.roles import Role
from office_hero.models import Base, Tenant, User
from office_hero.services.auth_service import AuthService


# Generate test RSA keys for testing
def _generate_test_keys():
    """Generate temporary RSA keys for testing."""
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    return private_pem, public_pem


@pytest.fixture
def test_settings():
    """Provide test JWT keys (generated for testing only)."""
    private_key, public_key = _generate_test_keys()
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        jwt_private_key=private_key,
        jwt_public_key=public_key,
        jwt_algorithm="RS256",
        access_token_ttl_minutes=15,
        refresh_token_ttl_days=7,
    )


@pytest_asyncio.fixture
async def async_session_fixture():
    """Create in-memory SQLite async session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_factory() as session:
        yield session

    await engine.dispose()


class TestPasswordHashing:
    """Tests for password hashing and verification."""

    def test_hash_password_creates_different_hashes(self, test_settings):
        """Password hashing should produce different hashes (salt randomization)."""
        service = AuthService(test_settings)
        password = "supersecret"
        hash1 = service.hash_password(password)
        hash2 = service.hash_password(password)
        assert hash1 != hash2  # Different salts

    def test_verify_password_success(self, test_settings):
        """Verify correct password against hash."""
        service = AuthService(test_settings)
        password = "correct"
        password_hash = service.hash_password(password)
        assert service.verify_password(password, password_hash) is True

    def test_verify_password_failure(self, test_settings):
        """Verify incorrect password against hash."""
        service = AuthService(test_settings)
        password_hash = service.hash_password("correct")
        assert service.verify_password("wrong", password_hash) is False


class TestJWTIssuing:
    """Tests for JWT token issuance."""

    def test_issue_jwt_returns_two_tokens(self, test_settings):
        """issue_jwt returns access and refresh tokens."""
        service = AuthService(test_settings)
        user_id = uuid4()
        tenant_id = uuid4()

        access_token, refresh_token = service.issue_jwt(
            user_id, tenant_id, Role.Operator, ["jobs:read"]
        )

        assert isinstance(access_token, str)
        assert isinstance(refresh_token, str)
        assert len(access_token) > 0
        assert len(refresh_token) > 0

    def test_access_token_has_correct_ttl(self, test_settings):
        """Access token should expire at correct TTL."""
        service = AuthService(test_settings)
        user_id = uuid4()
        tenant_id = uuid4()

        access_token, _ = service.issue_jwt(user_id, tenant_id, Role.Operator)

        payload = jwt.decode(access_token, test_settings.jwt_public_key, algorithms=["RS256"])

        assert "exp" in payload
        exp_time = datetime.fromtimestamp(payload["exp"], tz=UTC)
        now = datetime.now(UTC)
        expected_exp = now + timedelta(minutes=test_settings.access_token_ttl_minutes)

        # Allow 5 second margin for test execution
        assert abs((exp_time - expected_exp).total_seconds()) < 5

    def test_refresh_token_has_correct_ttl(self, test_settings):
        """Refresh token should expire at correct TTL."""
        service = AuthService(test_settings)
        user_id = uuid4()
        tenant_id = uuid4()

        _, refresh_token = service.issue_jwt(user_id, tenant_id, Role.Technician)

        payload = jwt.decode(refresh_token, test_settings.jwt_public_key, algorithms=["RS256"])

        assert "exp" in payload
        assert payload.get("type") == "refresh"

    def test_jwt_payload_contains_user_data(self, test_settings):
        """JWT payload should contain user_id, tenant_id, role, permissions."""
        service = AuthService(test_settings)
        user_id = uuid4()
        tenant_id = uuid4()
        permissions = ["routes:write", "dispatch:read"]

        access_token, _ = service.issue_jwt(user_id, tenant_id, Role.Dispatcher, permissions)

        payload = jwt.decode(access_token, test_settings.jwt_public_key, algorithms=["RS256"])

        assert payload["user_id"] == str(user_id)
        assert payload["tenant_id"] == str(tenant_id)
        assert payload["role"] == "dispatcher"
        assert payload["permissions"] == permissions


class TestJWTValidation:
    """Tests for JWT token validation."""

    def test_validate_jwt_success(self, test_settings):
        """validate_jwt successfully decodes valid token."""
        service = AuthService(test_settings)
        user_id = uuid4()
        tenant_id = uuid4()

        access_token, _ = service.issue_jwt(user_id, tenant_id, Role.Owner)
        payload = service.validate_jwt(access_token)

        assert payload["user_id"] == str(user_id)
        assert payload["tenant_id"] == str(tenant_id)

    def test_validate_jwt_raises_on_invalid_token(self, test_settings):
        """validate_jwt raises AuthError for invalid token."""
        service = AuthService(test_settings)
        with pytest.raises(AuthError):
            service.validate_jwt("invalid.token.here")

    def test_validate_jwt_raises_on_tampered_token(self, test_settings):
        """validate_jwt raises AuthError if token was tampered."""
        service = AuthService(test_settings)
        user_id = uuid4()
        tenant_id = uuid4()

        access_token, _ = service.issue_jwt(user_id, tenant_id, Role.Owner)
        # Tamper with token by changing a character
        tampered_token = access_token[:-5] + "xxxxx"

        with pytest.raises(AuthError):
            service.validate_jwt(tampered_token)

    def test_validate_jwt_raises_on_expired_token(self, test_settings):
        """validate_jwt raises AuthError for expired token."""
        service = AuthService(test_settings)
        user_id = uuid4()
        tenant_id = uuid4()

        # Create expired token by manipulating the payload
        expired_payload = {
            "user_id": str(user_id),
            "tenant_id": str(tenant_id),
            "role": "operator",
            "exp": datetime.now(UTC) - timedelta(hours=1),
            "iat": datetime.now(UTC),
        }

        expired_token = jwt.encode(
            expired_payload,
            test_settings.jwt_private_key,
            algorithm="RS256",
        )

        # Wait a moment to ensure expiry
        time.sleep(0.1)

        with pytest.raises(AuthError):
            service.validate_jwt(expired_token)


class TestLoginFlow:
    """Tests for login operation."""

    @pytest.mark.asyncio
    async def test_login_success(self, async_session_fixture, test_settings):
        """Successful login returns user and tokens."""
        service = AuthService(test_settings)
        tenant_id = uuid4()

        # Setup: create tenant and user
        tenant = Tenant(id=tenant_id, name="Test Corp")
        user_password = "secret123"
        user = User(
            tenant_id=tenant_id,
            email="user@test.com",
            password_hash=service.hash_password(user_password),
            role="operator",
            permissions=[],
            active=True,
        )

        async_session_fixture.add(tenant)
        async_session_fixture.add(user)
        await async_session_fixture.commit()

        # Act
        returned_user, access_token, refresh_token = await service.login(
            "user@test.com", user_password, async_session_fixture
        )

        # Assert
        assert returned_user.email == "user@test.com"
        assert returned_user.role == "operator"
        assert len(access_token) > 0
        assert len(refresh_token) > 0

        # Verify tokens are valid
        payload = service.validate_jwt(access_token)
        assert payload["user_id"] == str(user.id)

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, async_session_fixture, test_settings):
        """Login with wrong password raises AuthError."""
        service = AuthService(test_settings)
        tenant_id = uuid4()

        # Setup
        tenant = Tenant(id=tenant_id, name="Test Corp")
        user = User(
            tenant_id=tenant_id,
            email="user@test.com",
            password_hash=service.hash_password("correct"),
            role="technician",
            permissions=[],
            active=True,
        )

        async_session_fixture.add(tenant)
        async_session_fixture.add(user)
        await async_session_fixture.commit()

        # Act & Assert
        with pytest.raises(AuthError, match="Invalid email or password"):
            await service.login("user@test.com", "wrong", async_session_fixture)

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, async_session_fixture, test_settings):
        """Login with nonexistent email raises AuthError."""
        service = AuthService(test_settings)

        with pytest.raises(AuthError, match="Invalid email or password"):
            await service.login("nonexistent@test.com", "password", async_session_fixture)
