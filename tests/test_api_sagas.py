"""Tests for saga API routes."""

from uuid import uuid4

from fastapi.testclient import TestClient

from office_hero.api.app import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_saga_state_not_implemented():
    """Test GET /sagas/{saga_id}/state returns 501."""
    saga_id = uuid4()
    response = client.get(f"/sagas/{saga_id}/state")
    assert response.status_code == 501
    assert "Not implemented" in response.json()["detail"]


def test_transition_saga_not_implemented():
    """Test POST /sagas/{saga_id}/transition returns 501."""
    saga_id = uuid4()
    response = client.post(f"/sagas/{saga_id}/transition")
    assert response.status_code == 501
    assert "Not implemented" in response.json()["detail"]


def test_compensate_saga_not_implemented():
    """Test POST /sagas/{saga_id}/compensate returns 501."""
    saga_id = uuid4()
    response = client.post(f"/sagas/{saga_id}/compensate")
    assert response.status_code == 501
    assert "Not implemented" in response.json()["detail"]
