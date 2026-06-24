"""Tests for tenant CRUD and adapter management routes (Slice 29).

These tests run against the in-memory ``create_app()`` (no database engine),
so DB-dependent routes return 503.  We validate:
  - 503 shape for list/create (engine absent)
  - Request validation (422) for bad inputs
  - adapter PATCH validation (422) for unknown adapter
  - Require-operator gate (dependency override absent → 403)
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from office_hero.api.app import create_app
from office_hero.api.limiter import limiter
from tests.conftest import override_admin_auth


@pytest.fixture()
def app():
    saved = dict(limiter._route_limits)
    limiter._route_limits.clear()
    try:
        a = create_app()
        override_admin_auth(a)
        yield a
    finally:
        limiter._route_limits.clear()
        limiter._route_limits.update(saved)


@pytest.fixture()
def client(app):
    return TestClient(app)




@pytest.fixture()
def unauthed_client():
    """Client without operator auth override — tests the 403 gate."""
    return TestClient(create_app())


# ---------------------------------------------------------------------------
# GET /admin/tenants
# ---------------------------------------------------------------------------


def test_list_tenants_no_db_returns_503(client):
    resp = client.get("/admin/tenants")
    assert resp.status_code == 503


def test_list_tenants_requires_operator(unauthed_client):
    resp = unauthed_client.get("/admin/tenants")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /admin/tenants
# ---------------------------------------------------------------------------


def test_create_tenant_no_db_returns_503(client):
    resp = client.post("/admin/tenants", json={"name": "Acme", "industry": "generic"})
    assert resp.status_code == 503


def test_create_tenant_blank_name_422(client):
    resp = client.post("/admin/tenants", json={"name": "   ", "industry": "generic"})
    assert resp.status_code == 422


def test_create_tenant_invalid_industry_422(client):
    resp = client.post("/admin/tenants", json={"name": "Acme", "industry": "invalid_sector"})
    assert resp.status_code == 422


def test_create_tenant_extra_field_forbidden(client):
    resp = client.post(
        "/admin/tenants", json={"name": "Acme", "industry": "generic", "hack": "value"}
    )
    assert resp.status_code == 422


def test_create_tenant_requires_operator(unauthed_client):
    resp = unauthed_client.post("/admin/tenants", json={"name": "Acme", "industry": "generic"})
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /admin/tenants/{id}/adapter
# ---------------------------------------------------------------------------


def test_patch_adapter_unknown_adapter_422(client):
    resp = client.patch(
        f"/admin/tenants/{uuid4()}/adapter", json={"adapter": "unknown_crm"}
    )
    assert resp.status_code == 422


def test_patch_adapter_no_db_returns_503(client):
    resp = client.patch(
        f"/admin/tenants/{uuid4()}/adapter", json={"adapter": "jobber"}
    )
    assert resp.status_code == 503


def test_patch_adapter_requires_operator(unauthed_client):
    resp = unauthed_client.patch(
        f"/admin/tenants/{uuid4()}/adapter", json={"adapter": "jobber"}
    )
    assert resp.status_code == 403


def test_patch_adapter_all_valid_values_accepted(client):
    """All VALID_ADAPTERS values should pass validation (503 = DB absent, not 422)."""
    for adapter in ("native", "servicetitan", "pestpac", "jobber"):
        resp = client.patch(
            f"/admin/tenants/{uuid4()}/adapter", json={"adapter": adapter}
        )
        assert resp.status_code == 503, f"Expected 503 for adapter={adapter!r}, got {resp.status_code}"
