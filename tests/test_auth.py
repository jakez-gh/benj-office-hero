from datetime import UTC, datetime

import pytest

from office_hero.api.auth import InsufficientRoleError, require_role
from office_hero.services.auth_service import AuthService

# for tests we'll use a simple symmetric secret and HS256 algorithm.
# this avoids dealing with RSA key encoding and keeps the tests fast.
SECRET = "test-secret"


@pytest.fixture
def auth_service():
    return AuthService(private_key=SECRET, public_key=SECRET, algorithm="HS256")


def test_password_hashing(auth_service):
    pw = "s3cr3t"
    h = auth_service.hash_password(pw)
    assert auth_service.verify_password(pw, h)
    assert not auth_service.verify_password("wrong", h)


def test_access_token_roundtrip(auth_service):
    claims = {"sub": "user1", "role": "User"}
    token = auth_service.issue_access_token(claims)
    decoded = auth_service.verify_access_token(token)
    assert decoded["sub"] == "user1"
    assert decoded["role"] == "User"
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
