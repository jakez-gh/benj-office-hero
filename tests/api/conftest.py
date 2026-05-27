"""Shared fixtures for the slice-9 API tests.

Bypasses the JWT middleware (which is not installed in test apps) by adding a
test-only middleware that pulls auth context from request headers. This keeps
the test request-construction simple while still exercising the real
permission/role dependencies.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from office_hero.adapters.geocoding.stub import StubGeocodingAdapter
from office_hero.api.app import create_app
from office_hero.api.limiter import limiter
from office_hero.repositories.customer_repository import (
    InMemoryCustomerRepository,
)
from office_hero.repositories.location_repository import (
    InMemoryLocationRepository,
)
from office_hero.repositories.mocks import InMemoryAuditService
from office_hero.services.customer_service import CustomerService
from office_hero.services.location_service import LocationService


class _TestAuthMiddleware(BaseHTTPMiddleware):
    """Populate ``request.state`` from ``X-Test-*`` headers (test only)."""

    async def dispatch(self, request: Request, call_next):
        request.state.tenant_id = request.headers.get("X-Test-Tenant-Id")
        request.state.user_id = request.headers.get("X-Test-User-Id")
        request.state.role = request.headers.get("X-Test-Role", "tenant_admin")
        perms = request.headers.get("X-Test-Permissions", "customers:read,customers:write")
        request.state.permissions = [p.strip() for p in perms.split(",") if p.strip()]
        return await call_next(request)


def _hard_reset_limiter() -> None:
    """Reset both the slowapi limiter and the underlying MemoryStorage.

    ``Limiter.reset`` only clears its in-Limiter caches; the bucket counts
    live in ``limiter.limiter.storage`` and need an explicit ``.reset()``
    to make per-IP/endpoint buckets forget across tests.

    The MemoryStorage's ``Counter`` keeps stale entries between tests
    despite ``reset()``, so we also nuke the events/locks dicts directly
    when the storage exposes them.
    """
    limiter.reset()
    storage = getattr(getattr(limiter, "limiter", None), "storage", None)
    if storage is None:
        return
    if hasattr(storage, "reset"):
        try:
            storage.reset()
        except Exception:  # noqa: BLE001 - best-effort reset
            pass
    # Belt-and-braces — clear the in-memory Counter/dicts the FixedWindow
    # ratelimiter actually queries.
    for attr in ("storage", "events", "locks", "expirations"):
        bucket = getattr(storage, attr, None)
        if hasattr(bucket, "clear"):
            try:
                bucket.clear()
            except Exception:  # noqa: BLE001
                pass


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> Iterator[None]:
    """Reset the slowapi limiter between tests so per-IP buckets don't leak.

    Some tests legitimately exercise the limiter (e.g. a future "exceeds
    write tier" test), but the default fixture clears state at both ends
    so a noisy neighbour can't fail the next test.
    """
    _hard_reset_limiter()
    yield
    _hard_reset_limiter()


@pytest.fixture()
def disabled_limiter() -> Iterator[None]:
    """Test override that turns the slowapi limiter off for the duration."""
    prior = limiter.enabled
    limiter.enabled = False
    try:
        yield
    finally:
        limiter.enabled = prior
        _hard_reset_limiter()


@pytest.fixture()
def tenant_a() -> UUID:
    return uuid4()


@pytest.fixture()
def tenant_b() -> UUID:
    return uuid4()


@pytest.fixture()
def user_a() -> UUID:
    return uuid4()


@pytest.fixture()
def auth() -> InMemoryAuditService:
    return InMemoryAuditService()


@pytest.fixture()
def cust_repo() -> InMemoryCustomerRepository:
    return InMemoryCustomerRepository()


@pytest.fixture()
def loc_repo() -> InMemoryLocationRepository:
    return InMemoryLocationRepository()


@pytest.fixture()
def geocoder() -> StubGeocodingAdapter:
    return StubGeocodingAdapter()


@pytest.fixture()
def customer_service(cust_repo, auth) -> CustomerService:
    return CustomerService(repo=cust_repo, audit=auth)


@pytest.fixture()
def location_service(loc_repo, cust_repo, auth, geocoder) -> LocationService:
    return LocationService(
        repo=loc_repo,
        customer_repo=cust_repo,
        audit=auth,
        geocoder=geocoder,
    )


def _build_app(customer_service, location_service) -> FastAPI:
    app = create_app(
        customer_service=customer_service,
        location_service=location_service,
    )
    app.add_middleware(_TestAuthMiddleware)
    return app


@pytest.fixture()
def app(customer_service, location_service) -> FastAPI:
    return _build_app(customer_service, location_service)


@pytest.fixture()
def client(app) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


def auth_headers(
    tenant_id: UUID,
    user_id: UUID,
    *,
    role: str = "tenant_admin",
    permissions: str = "customers:read,customers:write",
) -> dict[str, str]:
    """Build the X-Test-* header bag the test middleware reads."""
    return {
        "X-Test-Tenant-Id": str(tenant_id),
        "X-Test-User-Id": str(user_id),
        "X-Test-Role": role,
        "X-Test-Permissions": permissions,
    }


def technician_headers(tenant_id: UUID, user_id: UUID) -> dict[str, str]:
    """A Technician has read-only customers permission and a non-admin role."""
    return auth_headers(
        tenant_id,
        user_id,
        role="technician",
        permissions="customers:read",
    )


def sales_headers(tenant_id: UUID, user_id: UUID) -> dict[str, str]:
    """Sales role lacks ``customers:write``."""
    return auth_headers(
        tenant_id,
        user_id,
        role="sales",
        permissions="customers:read",
    )


def unauthenticated_headers() -> dict[str, Any]:
    """No auth headers — middleware will leave request.state empty."""
    return {}
