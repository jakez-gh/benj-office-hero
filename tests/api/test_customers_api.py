"""HTTP-layer tests for the /customers routes (RBAC + tenant isolation)."""

from __future__ import annotations

from uuid import uuid4

from tests.api.conftest import (
    auth_headers,
    sales_headers,
    unauthenticated_headers,
)


def test_post_customer_requires_auth(client):
    """No auth headers -> 401 Unauthorized."""
    resp = client.post(
        "/customers",
        json={"name": "Acme"},
        headers=unauthenticated_headers(),
    )
    # FastAPI dependencies first run permission checks (403) before tenant id is
    # read. Either 401 or 403 are acceptable "you may not" signals — we accept
    # both rather than encoding a specific order-of-evaluation here.
    assert resp.status_code in (401, 403)


def test_post_customer_wrong_permission_returns_403(client, tenant_a, user_a):
    """Sales role without ``customers:write`` is rejected."""
    resp = client.post(
        "/customers",
        json={"name": "Acme"},
        headers=sales_headers(tenant_a, user_a),
    )
    assert resp.status_code == 403


def test_post_customer_returns_201_and_id(client, tenant_a, user_a):
    """Successful create returns 201 with a UUID id."""
    resp = client.post(
        "/customers",
        json={"name": "Acme Plumbing", "email": "ops@acme.example"},
        headers=auth_headers(tenant_a, user_a),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Acme Plumbing"
    assert body["tenant_id"] == str(tenant_a)
    assert "id" in body


def test_get_customer_cross_tenant_returns_404(client, tenant_a, tenant_b, user_a):
    """Tenant B cannot see tenant A's customer; RLS-hide simulated as 404."""
    create = client.post(
        "/customers",
        json={"name": "Tenant A Co"},
        headers=auth_headers(tenant_a, user_a),
    )
    assert create.status_code == 201
    cid = create.json()["id"]

    resp = client.get(
        f"/customers/{cid}",
        headers=auth_headers(tenant_b, user_a),
    )
    assert resp.status_code == 404


def test_list_customers_pagination(client, tenant_a, user_a):
    """``limit`` and ``offset`` control the page."""
    for i in range(5):
        client.post(
            "/customers",
            json={"name": f"Cust {i}"},
            headers=auth_headers(tenant_a, user_a),
        )

    resp = client.get(
        "/customers?limit=2&offset=0",
        headers=auth_headers(tenant_a, user_a),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2
    assert body["limit"] == 2
    assert body["offset"] == 0


def test_list_customers_search(client, tenant_a, user_a):
    """``search`` filters by case-insensitive substring on name/email."""
    for name in ("Acme Plumbing", "Beta HVAC", "Acme Refrigeration"):
        client.post(
            "/customers",
            json={"name": name},
            headers=auth_headers(tenant_a, user_a),
        )

    resp = client.get(
        "/customers?search=acme",
        headers=auth_headers(tenant_a, user_a),
    )
    assert resp.status_code == 200
    names = sorted(item["name"] for item in resp.json()["items"])
    assert names == ["Acme Plumbing", "Acme Refrigeration"]


def test_archive_then_restore_roundtrip(client, tenant_a, user_a):
    """Archive then restore returns the customer to active state."""
    create = client.post(
        "/customers",
        json={"name": "Gamma"},
        headers=auth_headers(tenant_a, user_a),
    )
    cid = create.json()["id"]

    arch = client.post(
        f"/customers/{cid}/archive",
        headers=auth_headers(tenant_a, user_a),
    )
    assert arch.status_code == 200
    assert arch.json()["archived"] is True

    rest = client.post(
        f"/customers/{cid}/restore",
        headers=auth_headers(tenant_a, user_a),
    )
    assert rest.status_code == 200
    assert rest.json()["archived"] is False


def test_patch_customer_updates_fields(client, tenant_a, user_a):
    """PATCH applies the supplied fields and returns the new view."""
    create = client.post(
        "/customers",
        json={"name": "Original Name"},
        headers=auth_headers(tenant_a, user_a),
    )
    cid = create.json()["id"]

    patch = client.patch(
        f"/customers/{cid}",
        json={"name": "Renamed", "phone": "555-1234"},
        headers=auth_headers(tenant_a, user_a),
    )
    assert patch.status_code == 200
    body = patch.json()
    assert body["name"] == "Renamed"
    assert body["phone"] == "555-1234"


def test_patch_customer_empty_body_is_rejected(client, tenant_a, user_a):
    """Empty PATCH body must be rejected by the validator (422)."""
    create = client.post(
        "/customers",
        json={"name": "Original"},
        headers=auth_headers(tenant_a, user_a),
    )
    cid = create.json()["id"]
    resp = client.patch(
        f"/customers/{cid}",
        json={},
        headers=auth_headers(tenant_a, user_a),
    )
    assert resp.status_code == 422


def test_archive_unknown_customer_returns_404(client, tenant_a, user_a):
    """Archiving an unknown id surfaces 404."""
    resp = client.post(
        f"/customers/{uuid4()}/archive",
        headers=auth_headers(tenant_a, user_a),
    )
    assert resp.status_code == 404


def test_create_customer_duplicate_email_rejected(client, tenant_a, user_a):
    """Creating two active customers with the same email in the same tenant returns 409."""
    first = client.post(
        "/customers",
        json={"name": "Acme Plumbing", "email": "ops@acme.example"},
        headers=auth_headers(tenant_a, user_a),
    )
    assert first.status_code == 201

    second = client.post(
        "/customers",
        json={"name": "Acme Refrigeration", "email": "ops@acme.example"},
        headers=auth_headers(tenant_a, user_a),
    )
    assert second.status_code == 409
    assert "email" in second.json()["detail"].lower()
