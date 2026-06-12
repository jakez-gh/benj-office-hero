"""HTTP-layer tests for POST /admin/outbox/process (Slice 24)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from office_hero.api.app import create_app
from tests.api.conftest import _TestAuthMiddleware


def _operator_headers(tenant_id, user_id) -> dict[str, str]:
    return {
        "X-Test-Tenant-Id": str(tenant_id),
        "X-Test-User-Id": str(user_id),
        "X-Test-Role": "operator",
        "X-Test-Permissions": "*",
    }


def _admin_headers(tenant_id, user_id) -> dict[str, str]:
    """TenantAdmin — must NOT be able to trigger outbox processing."""
    return {
        "X-Test-Tenant-Id": str(tenant_id),
        "X-Test-User-Id": str(user_id),
        "X-Test-Role": "tenant_admin",
        "X-Test-Permissions": "*",
    }


@pytest.fixture()
def app():
    application = create_app()
    application.add_middleware(_TestAuthMiddleware)
    return application


@pytest.fixture()
def client(app):
    with TestClient(app) as c:
        yield c


def test_process_outbox_requires_operator_role(client):
    resp = client.post(
        "/admin/outbox/process",
        headers=_admin_headers(uuid4(), uuid4()),
    )
    assert resp.status_code == 403


def test_process_outbox_empty_returns_zero_counters(client):
    resp = client.post(
        "/admin/outbox/process",
        headers=_operator_headers(uuid4(), uuid4()),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"processed": 0, "failed": 0, "dead_lettered": 0}


def test_contract_creation_feeds_outbox_then_processing_drains_it(client):
    """End-to-end seam: create customer+location+contract -> process -> done."""
    tenant_id = uuid4()
    user_id = uuid4()
    headers = {
        "X-Test-Tenant-Id": str(tenant_id),
        "X-Test-User-Id": str(user_id),
        "X-Test-Role": "operator",
        "X-Test-Permissions": "*",
    }

    cust = client.post("/customers", json={"name": "Acme"}, headers=headers).json()
    loc = client.post(
        f"/customers/{cust['id']}/locations",
        json={
            "street": "1 Main St",
            "city": "Austin",
            "state": "TX",
            "postal_code": "78701",
        },
        headers=headers,
    ).json()

    created = client.post(
        "/contracts",
        json={
            "customer_id": cust["id"],
            "location_id": loc["id"],
            "title": "Quarterly pest plan",
            "frequency": "quarterly",
            "start_date": "2026-06-01",
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text

    resp = client.post("/admin/outbox/process", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["processed"] == 1

    # Idempotent: the event is done; a second run drains nothing.
    again = client.post("/admin/outbox/process", headers=headers)
    assert again.json()["processed"] == 0
