"""TDD tests for POST /sagas (dispatch action) — wiring DispatchPage to saga creation.

Tests written FIRST per project TDD methodology (Erik Corkran Phase 7).
These tests verify:
  - POST /sagas creates a new saga and returns its state
  - GET /sagas/{saga_id}/state returns saga status
  - Saga status transitions are reflected (pending → running → done/failed)
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from office_hero.api.app import create_app
from office_hero.repositories.mocks import MockOutboxRepository, MockSagaRepository
from office_hero.sagas.core import SagaStatus
from office_hero.services.saga_service import SagaService


@pytest.fixture()
def saga_repo():
    return MockSagaRepository()


@pytest.fixture()
def outbox_repo():
    return MockOutboxRepository()


@pytest.fixture()
def saga_service(saga_repo):
    return SagaService(saga_repo=saga_repo)


@pytest.fixture()
def client(saga_service, outbox_repo):
    app = create_app(saga_service=saga_service, outbox_repo=outbox_repo)
    return TestClient(app)


class TestDispatchSagaCreation:
    """POST /sagas — creates a dispatch saga and returns state."""

    def test_create_saga_returns_201(self, client):
        """Dispatching a job creates a saga and returns 201 with saga state."""
        payload = {
            "saga_type": "dispatch_job",
            "context": {
                "tenant_id": str(uuid4()),
                "job_id": str(uuid4()),
                "technician_id": str(uuid4()),
            },
        }
        response = client.post("/sagas", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert "saga_id" in data
        assert data["status"] in ("running", "done")
        assert data["saga_type"] == "dispatch_job"

    def test_create_saga_requires_saga_type(self, client):
        """POST /sagas without saga_type returns 422."""
        response = client.post("/sagas", json={"context": {}})
        assert response.status_code == 422

    def test_create_saga_requires_context(self, client):
        """POST /sagas without context returns 422."""
        response = client.post("/sagas", json={"saga_type": "dispatch_job"})
        assert response.status_code == 422


class TestGetSagaState:
    """GET /sagas/{saga_id}/state — returns current saga state."""

    def test_get_saga_state_after_creation(self, client):
        """Created saga is retrievable via GET endpoint."""
        payload = {
            "saga_type": "dispatch_job",
            "context": {
                "tenant_id": str(uuid4()),
                "job_id": str(uuid4()),
            },
        }
        create_resp = client.post("/sagas", json=payload)
        saga_id = create_resp.json()["saga_id"]

        response = client.get(f"/sagas/{saga_id}/state")
        assert response.status_code == 200
        data = response.json()
        assert data["saga_id"] == saga_id
        assert "status" in data
        assert "context" in data

    def test_get_saga_state_not_found(self, client):
        """GET for non-existent saga returns 404."""
        fake_id = str(uuid4())
        response = client.get(f"/sagas/{fake_id}/state")
        assert response.status_code == 404

    def test_saga_status_values(self, client):
        """Saga status is one of the valid SagaStatus values."""
        payload = {
            "saga_type": "dispatch_job",
            "context": {"tenant_id": str(uuid4())},
        }
        create_resp = client.post("/sagas", json=payload)
        saga_id = create_resp.json()["saga_id"]

        response = client.get(f"/sagas/{saga_id}/state")
        data = response.json()
        valid_statuses = {s.value for s in SagaStatus}
        assert data["status"] in valid_statuses
