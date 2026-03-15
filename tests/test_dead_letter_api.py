"""TDD tests for dead-letter retry — wiring JobsPage retry to POST /admin/dead-letters/{id}/retry.

Tests written FIRST per project TDD methodology.
These tests verify:
  - GET /admin/dead-letters returns list of dead-letter events
  - POST /admin/dead-letters/{event_id}/retry resets event to pending
  - Retried events disappear from dead-letter list
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from office_hero.api.app import create_app
from office_hero.repositories.mocks import MockOutboxRepository, MockSagaRepository
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


class TestListDeadLetters:
    """GET /admin/dead-letters — lists events in dead-letter state."""

    @pytest.mark.asyncio
    async def test_list_dead_letters_empty(self, client, outbox_repo):
        """Empty dead-letter list returns 200 with empty items."""
        response = client.get("/admin/dead-letters")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_dead_letters_with_events(self, client, outbox_repo):
        """Dead-letter events are returned in the list."""
        tenant_id = uuid4()
        event = await outbox_repo.create(
            tenant_id=tenant_id,
            event_type="dispatch_job",
            payload={"job_id": str(uuid4())},
            idem_key=uuid4(),
        )
        await outbox_repo.mark_dead_letter(event["id"], reason="max retries exceeded")

        response = client.get("/admin/dead-letters")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        event_ids = [item["id"] for item in data["items"]]
        assert str(event["id"]) in event_ids

    @pytest.mark.asyncio
    async def test_list_dead_letters_pagination(self, client, outbox_repo):
        """Dead-letter list respects limit and offset."""
        response = client.get("/admin/dead-letters?limit=5&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data


class TestRetryDeadLetter:
    """POST /admin/dead-letters/{event_id}/retry — resets dead-letter to pending."""

    @pytest.mark.asyncio
    async def test_retry_dead_letter_success(self, client, outbox_repo):
        """Retrying a dead-letter event returns 200 and resets status."""
        tenant_id = uuid4()
        event = await outbox_repo.create(
            tenant_id=tenant_id,
            event_type="dispatch_job",
            payload={"job_id": str(uuid4())},
            idem_key=uuid4(),
        )
        await outbox_repo.mark_dead_letter(event["id"], reason="step failed")

        response = client.post(f"/admin/dead-letters/{event['id']}/retry")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["id"] == str(event["id"])

    @pytest.mark.asyncio
    async def test_retry_dead_letter_not_found(self, client):
        """Retrying a non-existent event returns 404."""
        fake_id = uuid4()
        response = client.post(f"/admin/dead-letters/{fake_id}/retry")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_retried_event_removed_from_dead_letters(self, client, outbox_repo):
        """After retry, event no longer appears in dead-letter list."""
        tenant_id = uuid4()
        event = await outbox_repo.create(
            tenant_id=tenant_id,
            event_type="sync_customer",
            payload={"customer_id": str(uuid4())},
            idem_key=uuid4(),
        )
        await outbox_repo.mark_dead_letter(event["id"], reason="timeout")

        # Retry it
        client.post(f"/admin/dead-letters/{event['id']}/retry")

        # Verify it's gone from dead-letters
        response = client.get("/admin/dead-letters")
        data = response.json()
        dead_ids = [item["id"] for item in data["items"]]
        assert str(event["id"]) not in dead_ids


class TestSagaLogs:
    """GET /admin/sagas/{saga_id}/logs — returns saga execution history."""

    def test_get_saga_logs_after_dispatch(self, client):
        """After creating a saga, its logs are accessible."""
        payload = {
            "saga_type": "dispatch_job",
            "context": {"tenant_id": str(uuid4()), "job_id": str(uuid4())},
        }
        create_resp = client.post("/sagas", json=payload)
        saga_id = create_resp.json()["saga_id"]

        response = client.get(f"/admin/sagas/{saga_id}/logs")
        assert response.status_code == 200
        data = response.json()
        assert data["saga_id"] == saga_id
        assert "status" in data
        assert "context" in data

    def test_get_saga_logs_not_found(self, client):
        """Logs for non-existent saga returns 404."""
        fake_id = str(uuid4())
        response = client.get(f"/admin/sagas/{fake_id}/logs")
        assert response.status_code == 404
