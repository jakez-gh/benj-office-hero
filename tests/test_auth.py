from datetime import UTC, datetime
from uuid import UUID

import pytest

from office_hero.api.auth import InsufficientRoleError, require_role
from office_hero.core.roles import Role
from office_hero.services.auth_service import AuthService


class _TestSettings:
    """Minimal settings stub for unit tests — avoids pydantic-settings env-var loading."""

    jwt_private_key = "test-secret"
    jwt_public_key = "test-secret"
    jwt_algorithm = "HS256"
    access_token_ttl_minutes = 15
    refresh_token_ttl_days = 7
    database_url = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
def auth_service():
    return AuthService(_TestSettings())


def test_password_hashing(auth_service):
    pw = "s3cr3t"
    h = auth_service.hash_password(pw)
    assert auth_service.verify_password(pw, h)
    assert not auth_service.verify_password("wrong", h)


def test_access_token_roundtrip(auth_service):
    user_id = UUID("00000000-0000-0000-0000-000000000001")
    tenant_id = UUID("00000000-0000-0000-0000-000000000002")
    access_token, _ = auth_service.issue_jwt(user_id, tenant_id, Role.Technician)
    decoded = auth_service.validate_jwt(access_token)
    assert decoded["user_id"] == str(user_id)
    assert decoded["role"] == Role.Technician.value
    # exp should be present and in the future
    assert decoded["exp"] > int(datetime.now(UTC).timestamp())


def test_require_role_decorator():
    @require_role("TenantAdmin")
    def hi(claims):
        return "hello"

    assert hi({"role": "TenantAdmin"}) == "hello"
    assert hi({"role": "Operator"}) == "hello"  # higher role allowed

    with pytest.raises(InsufficientRoleError):
        hi({"role": "Technician"})

    with pytest.raises(InsufficientRoleError):
        hi({})  # missing role

    with pytest.raises(InsufficientRoleError):
        hi({"role": "Unknown"})
