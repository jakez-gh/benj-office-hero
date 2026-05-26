"""Tests for saga API routes."""

from uuid import uuid4

from fastapi.testclient import TestClient

from office_hero.api.app import app

client = TestClient(app)


def test_health_check():
    """``GET /health`` is a lightweight liveness probe (no DB/ORS I/O).

    ADR 050 splits the legacy ``/health`` endpoint into liveness vs readiness;
    this test pins the liveness contract used by Fly.io and the server-manager
    hook.
    """
    response = client.get("/health")
    body = response.json()
    assert response.status_code == 200
    assert body == {"status": "ok"}


def test_health_ready_returns_structured_response():
    """``GET /health/ready`` probes DB + ORS and returns the full shape.

    In the test environment neither a DB nor an ORS instance is running, so
    the probes fail and the endpoint should report ``unhealthy`` with a 503
    status. We assert response shape and that the status code is one of the
    two expected values so this test does not break in environments where the
    real backing services happen to be up.
    """
    response = client.get("/health/ready")
    body = response.json()
    assert "status" in body
    assert "db" in body
    assert "ors" in body
    assert response.status_code in (200, 503)


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
