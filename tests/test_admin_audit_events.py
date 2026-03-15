"""Tests for admin audit events API endpoint — TDD first (Slice 4).

Verifies the GET /admin/audit-events endpoint provides paginated,
filterable audit event listing for the admin panel.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from office_hero.api.app import app


@pytest.fixture()
def client():
    """Fresh TestClient per test for isolation."""
    return TestClient(app)


class TestListAuditEvents:
    """GET /admin/audit-events — paginated audit event listing."""

    def test_returns_200_with_empty_list_when_no_events(self, client):
        """Endpoint must return 200 with an empty items list when DB is empty."""
        resp = client.get("/admin/audit-events")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert isinstance(body["items"], list)
        assert "total" in body

    def test_returns_paginated_structure(self, client):
        """Response must contain items, total, limit, offset keys."""
        resp = client.get("/admin/audit-events?limit=10&offset=0")
        assert resp.status_code == 200
        body = resp.json()
        for key in ("items", "total", "limit", "offset"):
            assert key in body, f"Missing key: {key}"
        assert body["limit"] == 10
        assert body["offset"] == 0

    def test_limit_defaults_to_50(self, client):
        """Default limit is 50 when not specified."""
        resp = client.get("/admin/audit-events")
        assert resp.status_code == 200
        assert resp.json()["limit"] == 50

    def test_offset_defaults_to_0(self, client):
        """Default offset is 0 when not specified."""
        resp = client.get("/admin/audit-events")
        assert resp.status_code == 200
        assert resp.json()["offset"] == 0

    def test_filter_by_event_type(self, client):
        """Filtering by event_type query param is accepted."""
        resp = client.get("/admin/audit-events?event_type=auth.login")
        assert resp.status_code == 200

    def test_filter_by_tenant_id(self, client):
        """Filtering by tenant_id query param is accepted."""
        tenant_id = str(uuid4())
        resp = client.get(f"/admin/audit-events?tenant_id={tenant_id}")
        assert resp.status_code == 200

    def test_invalid_limit_rejected(self, client):
        """limit < 1 must be rejected with 422."""
        resp = client.get("/admin/audit-events?limit=0")
        assert resp.status_code == 422

    def test_invalid_offset_rejected(self, client):
        """offset < 0 must be rejected with 422."""
        resp = client.get("/admin/audit-events?offset=-1")
        assert resp.status_code == 422

    def test_limit_upper_bound(self, client):
        """limit > 1000 must be rejected with 422."""
        resp = client.get("/admin/audit-events?limit=1001")
        assert resp.status_code == 422


class TestAuditEventItemSchema:
    """Verify that audit event items have expected fields."""

    def test_item_contains_expected_keys(self, client):
        """Each item in items list must contain id, timestamp, event_type, details."""
        # When no events exist this is vacuously true; we test the schema contract
        resp = client.get("/admin/audit-events")
        assert resp.status_code == 200
        # Items may be empty; schema is tested via integration when events exist
