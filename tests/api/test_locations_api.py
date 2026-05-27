"""HTTP-layer tests for /customers/{cid}/locations and /locations/{lid}.

The stub geocoder is the default in ``create_app`` so no live network calls
happen. Rate-limit assertions are kept light — slowapi may not block in the
test client without explicit configuration, so we test the limiter is wired
rather than enforce the exact ceiling.
"""

from __future__ import annotations

from uuid import uuid4

from tests.api.conftest import (
    auth_headers,
    technician_headers,
)

_VALID_ADDR = {
    "street": "123 Main St",
    "city": "Philadelphia",
    "state": "PA",
    "postal_code": "19103",
    "country": "US",
}


def _create_customer(client, tenant_a, user_a, name: str = "Acme") -> str:
    resp = client.post(
        "/customers",
        json={"name": name},
        headers=auth_headers(tenant_a, user_a),
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_post_location_geocodes_and_returns_lat_lng(client, tenant_a, user_a):
    """Posting a location with the stub geocoder returns ok status + coords."""
    cid = _create_customer(client, tenant_a, user_a)
    resp = client.post(
        f"/customers/{cid}/locations",
        json={**_VALID_ADDR, "label": "Main"},
        headers=auth_headers(tenant_a, user_a),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["geocode_status"] == "ok"
    assert body["geocode_source"] == "stub"
    assert body["lat"] is not None
    assert body["lng"] is not None


def test_post_location_geocode_failure_still_returns_201(client, tenant_a, user_a):
    """A geocoder miss returns 201 with status=failed (the location persists)."""
    cid = _create_customer(client, tenant_a, user_a)
    # The stub geocoder returns None when the street contains "FAIL".
    resp = client.post(
        f"/customers/{cid}/locations",
        json={**_VALID_ADDR, "street": "FAIL Lane", "label": "x"},
        headers=auth_headers(tenant_a, user_a),
    )
    assert resp.status_code == 201
    assert resp.json()["geocode_status"] == "failed"


def test_get_locations_for_customer_other_tenant_returns_404(client, tenant_a, tenant_b, user_a):
    """Cross-tenant list returns 404 (silent RLS-style isolation)."""
    cid = _create_customer(client, tenant_a, user_a)
    resp = client.get(
        f"/customers/{cid}/locations",
        headers=auth_headers(tenant_b, user_a),
    )
    assert resp.status_code == 404


def test_manual_coordinates_requires_dispatcher_or_admin(client, tenant_a, user_a):
    """Technician (non-admin/non-dispatcher) cannot manually override coordinates."""
    cid = _create_customer(client, tenant_a, user_a)
    create = client.post(
        f"/customers/{cid}/locations",
        json={**_VALID_ADDR, "label": "x"},
        headers=auth_headers(tenant_a, user_a),
    )
    lid = create.json()["id"]

    resp = client.post(
        f"/locations/{lid}/coordinates",
        json={"lat": 40.0, "lng": -75.0},
        headers=technician_headers(tenant_a, user_a),
    )
    assert resp.status_code == 403


def test_manual_coordinates_admin_succeeds(client, tenant_a, user_a):
    """A tenant admin can override coordinates manually."""
    cid = _create_customer(client, tenant_a, user_a)
    create = client.post(
        f"/customers/{cid}/locations",
        json={**_VALID_ADDR, "label": "x"},
        headers=auth_headers(tenant_a, user_a),
    )
    lid = create.json()["id"]

    resp = client.post(
        f"/locations/{lid}/coordinates",
        json={"lat": 40.0, "lng": -75.0},
        headers=auth_headers(tenant_a, user_a),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["geocode_source"] == "manual"
    assert body["geocode_status"] == "manual"


def test_patch_location_address_triggers_regeocode(client, tenant_a, user_a):
    """PATCH with an address change updates lat/lng via the stub geocoder."""
    cid = _create_customer(client, tenant_a, user_a)
    create = client.post(
        f"/customers/{cid}/locations",
        json={**_VALID_ADDR, "label": "x"},
        headers=auth_headers(tenant_a, user_a),
    )
    body0 = create.json()
    lid = body0["id"]
    lat0 = body0["lat"]

    patch = client.patch(
        f"/locations/{lid}",
        json={"street": "999 Different Ave"},
        headers=auth_headers(tenant_a, user_a),
    )
    assert patch.status_code == 200
    body1 = patch.json()
    assert body1["geocode_status"] == "ok"
    # The stub is deterministic on ``street``, so the coords MUST differ.
    assert body1["lat"] != lat0


def test_regeocode_endpoint_returns_200(client, tenant_a, user_a, disabled_limiter):
    """Force-regeocode is exposed at POST /locations/{id}/regeocode.

    The endpoint carries a 5/minute rate limit (see slice design); the
    ``disabled_limiter`` fixture turns slowapi off for this test so we can
    assert the happy-path response shape without colliding with the bucket
    that other location tests may have already used inside the same
    pytest process.
    """
    cid = _create_customer(client, tenant_a, user_a)
    create = client.post(
        f"/customers/{cid}/locations",
        json={**_VALID_ADDR, "label": "x"},
        headers=auth_headers(tenant_a, user_a),
    )
    lid = create.json()["id"]

    resp = client.post(
        f"/locations/{lid}/regeocode",
        headers=auth_headers(tenant_a, user_a),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["geocode_status"] in {"ok", "failed"}


def test_regeocode_endpoint_is_rate_limited(client, tenant_a, user_a):
    """The endpoint enforces a 5/minute rate limit (Nominatim quota protection).

    Sending 6 consecutive POSTs from the same client identity should see the
    last one rejected with 429.
    """
    cid = _create_customer(client, tenant_a, user_a)
    create = client.post(
        f"/customers/{cid}/locations",
        json={**_VALID_ADDR, "label": "x"},
        headers=auth_headers(tenant_a, user_a),
    )
    lid = create.json()["id"]

    statuses = []
    for _ in range(6):
        statuses.append(
            client.post(
                f"/locations/{lid}/regeocode",
                headers=auth_headers(tenant_a, user_a),
            ).status_code
        )
    # At least one of the 6 must be 429 — slowapi may permit fewer than the
    # advertised count due to window boundaries.
    assert 429 in statuses, f"expected a 429 in {statuses!r}"


def test_post_location_unknown_customer_returns_404(client, tenant_a, user_a):
    """Posting against a missing customer id returns 404."""
    resp = client.post(
        f"/customers/{uuid4()}/locations",
        json={**_VALID_ADDR, "label": "x"},
        headers=auth_headers(tenant_a, user_a),
    )
    assert resp.status_code == 404


def test_get_location_cross_tenant_returns_404(client, tenant_a, tenant_b, user_a):
    """Reading a location from another tenant must return 404."""
    cid = _create_customer(client, tenant_a, user_a)
    create = client.post(
        f"/customers/{cid}/locations",
        json={**_VALID_ADDR, "label": "x"},
        headers=auth_headers(tenant_a, user_a),
    )
    lid = create.json()["id"]

    resp = client.get(
        f"/locations/{lid}",
        headers=auth_headers(tenant_b, user_a),
    )
    assert resp.status_code == 404


def test_archive_location_admin_succeeds(client, tenant_a, user_a):
    """Admins can archive a location."""
    cid = _create_customer(client, tenant_a, user_a)
    create = client.post(
        f"/customers/{cid}/locations",
        json={**_VALID_ADDR, "label": "x"},
        headers=auth_headers(tenant_a, user_a),
    )
    lid = create.json()["id"]
    resp = client.post(
        f"/locations/{lid}/archive",
        headers=auth_headers(tenant_a, user_a),
    )
    assert resp.status_code == 200
    assert resp.json()["archived"] is True
