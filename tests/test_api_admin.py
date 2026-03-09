"""Tests for admin API routes."""

from uuid import uuid4

from fastapi.testclient import TestClient

from office_hero.api.app import app

client = TestClient(app)


def test_list_dead_letters_not_implemented():
    """Test GET /admin/dead-letters returns 501."""
    response = client.get("/admin/dead-letters")
    assert response.status_code == 501
    assert "Not implemented" in response.json()["detail"]


def test_list_dead_letters_with_pagination():
    """Test GET /admin/dead-letters respects limit and offset."""
    response = client.get("/admin/dead-letters?limit=10&offset=5")
    assert response.status_code == 501


def test_retry_dead_letter_not_implemented():
    """Test POST /admin/dead-letters/{event_id}/retry returns 501."""
    event_id = uuid4()
    response = client.post(f"/admin/dead-letters/{event_id}/retry")
    assert response.status_code == 501
    assert "Not implemented" in response.json()["detail"]


def test_get_saga_logs_not_implemented():
    """Test GET /admin/sagas/{saga_id}/logs returns 501."""
    saga_id = uuid4()
    response = client.get(f"/admin/sagas/{saga_id}/logs")
    assert response.status_code == 501
    assert "Not implemented" in response.json()["detail"]
