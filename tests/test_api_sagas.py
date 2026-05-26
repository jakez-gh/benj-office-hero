"""Tests for saga API routes.

Updated to reflect implemented endpoints (no longer 501 stubs).
"""

from uuid import uuid4

from fastapi.testclient import TestClient

from office_hero.api.app import create_app
from office_hero.api.routes.sagas import require_operator as require_operator_saga
from office_hero.repositories.mocks import MockOutboxRepository, MockSagaRepository
from office_hero.services.saga_service import SagaService

# Use DI-aware app for tests
_saga_repo = MockSagaRepository()
_saga_service = SagaService(saga_repo=_saga_repo)
_outbox_repo = MockOutboxRepository()
app = create_app(saga_service=_saga_service, outbox_repo=_outbox_repo)
# Bypass Operator RBAC for these unit tests (auth is exercised in test_auth.py).
app.dependency_overrides[require_operator_saga] = lambda: "operator"
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


def test_get_saga_state_not_found():
    """Test GET /sagas/{saga_id}/state returns 404 for non-existent saga."""
    saga_id = uuid4()
    response = client.get(f"/sagas/{saga_id}/state")
    assert response.status_code == 404


def test_transition_saga_not_found():
    """Test POST /sagas/{saga_id}/transition returns 404 for non-existent saga."""
    saga_id = uuid4()
    response = client.post(f"/sagas/{saga_id}/transition")
    assert response.status_code == 404


def test_compensate_saga_not_found():
    """Test POST /sagas/{saga_id}/compensate returns 404 for non-existent saga."""
    saga_id = uuid4()
    response = client.post(f"/sagas/{saga_id}/compensate")
    assert response.status_code == 404


def test_create_saga_returns_201():
    """Test POST /sagas creates a new saga."""
    payload = {
        "saga_type": "dispatch_job",
        "context": {"tenant_id": str(uuid4()), "job_id": str(uuid4())},
    }
    response = client.post("/sagas", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["saga_type"] == "dispatch_job"
    assert data["status"] in ("running", "done")


def test_get_saga_state_after_creation():
    """Test GET /sagas/{saga_id}/state returns state of created saga."""
    payload = {
        "saga_type": "test_get_state",
        "context": {"tenant_id": str(uuid4())},
    }
    create_resp = client.post("/sagas", json=payload)
    saga_id = create_resp.json()["saga_id"]
    response = client.get(f"/sagas/{saga_id}/state")
    assert response.status_code == 200
    assert response.json()["saga_id"] == saga_id
