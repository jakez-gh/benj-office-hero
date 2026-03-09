"""Tests for ORM models: User, RefreshToken, Tenant."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from office_hero.models import RefreshToken, Tenant, User


class TestTenantModel:
    """Tests for Tenant ORM model."""

    def test_tenant_creation(self):
        """Tenant model instantiates with required fields."""
        tenant_id = uuid4()
        tenant = Tenant(id=tenant_id, name="Acme Corp")
        assert tenant.id == tenant_id
        assert tenant.name == "Acme Corp"

    def test_tenant_repr(self):
        """Tenant model has readable repr."""
        tenant = Tenant(id=uuid4(), name="Test Tenant")
        assert "Test Tenant" in repr(tenant)


class TestUserModel:
    """Tests for User ORM model."""

    def test_user_creation(self):
        """User model instantiates with required fields."""
        user_id = uuid4()
        tenant_id = uuid4()
        user = User(
            id=user_id,
            tenant_id=tenant_id,
            email="test@example.com",
            password_hash="hashed_password",
            role="operator",
            permissions=["jobs:read", "routes:write"],
            active=True,
        )
        assert user.id == user_id
        assert user.tenant_id == tenant_id
        assert user.email == "test@example.com"
        assert user.password_hash == "hashed_password"
        assert user.role == "operator"
        assert user.permissions == ["jobs:read", "routes:write"]
        assert user.active is True

    def test_user_columns_accessible(self):
        """User model columns are accessible."""
        user_id = uuid4()
        tenant_id = uuid4()
        user = User(
            id=user_id,
            tenant_id=tenant_id,
            email="user@test.com",
            password_hash="hash",
            role="technician",
            active=True,
            permissions=[],
        )
        assert user.id == user_id
        assert user.tenant_id == tenant_id
        assert user.email == "user@test.com"
        assert user.password_hash == "hash"
        assert user.role == "technician"
        assert user.active is True
        assert user.permissions == []

    def test_user_repr(self):
        """User model has readable repr."""
        user = User(
            tenant_id=uuid4(),
            email="test@example.com",
            password_hash="hash",
            role="operator",
        )
        assert "test@example.com" in repr(user)
        assert "operator" in repr(user)


class TestRefreshTokenModel:
    """Tests for RefreshToken ORM model."""

    def test_refresh_token_creation(self):
        """RefreshToken model instantiates with required fields."""
        token_id = uuid4()
        user_id = uuid4()
        expires_at = datetime.now(UTC) + timedelta(days=7)

        token = RefreshToken(
            id=token_id,
            user_id=user_id,
            token_hash="hashed_token",
            expires_at=expires_at,
            revoked=False,
        )
        assert token.id == token_id
        assert token.user_id == user_id
        assert token.token_hash == "hashed_token"
        assert token.expires_at == expires_at
        assert token.revoked is False

    def test_refresh_token_columns_accessible(self):
        """RefreshToken model columns are accessible."""
        token_id = uuid4()
        user_id = uuid4()
        expires_at = datetime.now(UTC) + timedelta(days=7)
        token = RefreshToken(
            id=token_id,
            user_id=user_id,
            token_hash="hash",
            expires_at=expires_at,
            revoked=False,
        )
        assert token.id == token_id
        assert token.user_id == user_id
        assert token.token_hash == "hash"
        assert token.expires_at == expires_at
        assert token.revoked is False

    def test_refresh_token_repr(self):
        """RefreshToken model has readable repr."""
        user_id = uuid4()
        token = RefreshToken(
            user_id=user_id,
            token_hash="hash",
            expires_at=datetime.now(UTC) + timedelta(days=7),
            revoked=False,
        )
        assert str(user_id) in repr(token)
        assert "False" in repr(token)  # revoked=False
