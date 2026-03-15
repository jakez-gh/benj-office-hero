"""Tests for admin API routes.

Updated to reflect implemented endpoints (no longer 501 stubs).
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from office_hero.api.app import create_app
from office_hero.repositories.mocks import MockOutboxRepository, MockSagaRepository
from office_hero.services.saga_service import SagaService


@pytest.fixture()
def outbox_repo():
    return MockOutboxRepository()


@pytest.fixture()
def client(outbox_repo):
    saga_repo = MockSagaRepository()
    saga_svc = SagaService(saga_repo=saga_repo)
    app = create_app(saga_service=saga_svc, outbox_repo=outbox_repo)
    return TestClient(app)


def test_list_dead_letters_empty(client):
    """Test GET /admin/dead-letters returns empty list."""
    response = client.get("/admin/dead-letters")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_list_dead_letters_with_pagination(client):
    """Test GET /admin/dead-letters respects limit and offset."""
    response = client.get("/admin/dead-letters?limit=10&offset=5")
    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 10
    assert data["offset"] == 5


def test_retry_dead_letter_not_found(client):
    """Test POST /admin/dead-letters/{event_id}/retry returns 404."""
    event_id = uuid4()
    response = client.post(f"/admin/dead-letters/{event_id}/retry")
    assert response.status_code == 404


def test_get_saga_logs_not_found(client):
    """Test GET /admin/sagas/{saga_id}/logs returns 404 for unknown saga."""
    saga_id = uuid4()
    response = client.get(f"/admin/sagas/{saga_id}/logs")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_retry_dead_letter_success(client, outbox_repo):
    """Test POST /admin/dead-letters/{event_id}/retry resets event to pending."""
    tenant_id = uuid4()
    event = await outbox_repo.create(
        tenant_id=tenant_id,
        event_type="dispatch_job",
        payload={"job_id": str(uuid4())},
        idem_key=uuid4(),
    )
    await outbox_repo.mark_dead_letter(event["id"], reason="max retries")
    response = client.post(f"/admin/dead-letters/{event['id']}/retry")
    assert response.status_code == 200
    assert response.json()["status"] == "pending"
