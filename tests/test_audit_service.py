"""Tests for AuditService — append-only audit event logging (Slice 4 / ADR 063).

Uses a mock AsyncSession so tests run without a real database.  We verify
the INSERT statement is executed with the correct parameters.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, call
from uuid import UUID, uuid4

import pytest

from office_hero.services.audit_service import AuditService


@pytest.fixture()
def service() -> AuditService:
    return AuditService()


@pytest.fixture()
def mock_session() -> AsyncMock:
    """AsyncMock that mimics an AsyncSession's execute() method."""
    session = AsyncMock()
    session.execute = AsyncMock()
    return session


def _get_params(mock_session: AsyncMock) -> dict:
    """Extract the params dict from the most recent session.execute() call."""
    # execute(stmt, params) → args[1] is the params dict
    return mock_session.execute.call_args.args[1]


class TestLogEventExecution:
    """Verify that log_event() calls session.execute() exactly once."""

    async def test_execute_called_once(self, service, mock_session):
        await service.log_event(
            event_type="auth.login",
            details={"email": "user@test.com"},
            tenant_id=uuid4(),
            session=mock_session,
        )
        mock_session.execute.assert_awaited_once()

    async def test_executes_an_insert_statement(self, service, mock_session):
        """The statement passed to execute must be an INSERT."""
        await service.log_event(
            event_type="auth.login",
            details={},
            tenant_id=uuid4(),
            session=mock_session,
        )
        stmt = mock_session.execute.call_args.args[0]
        # SQLAlchemy text() objects render to their SQL string
        assert "INSERT" in str(stmt).upper()
        assert "audit_events" in str(stmt).lower()


class TestLogEventParams:
    """Verify the correct parameters are passed to the INSERT."""

    async def test_event_type_passed_correctly(self, service, mock_session):
        await service.log_event(
            event_type="auth.login",
            details={},
            tenant_id=uuid4(),
            session=mock_session,
        )
        params = _get_params(mock_session)
        assert params["event_type"] == "auth.login"

    async def test_tenant_id_passed_as_string(self, service, mock_session):
        tid = uuid4()
        await service.log_event(
            event_type="data.access",
            details={},
            tenant_id=tid,
            session=mock_session,
        )
        params = _get_params(mock_session)
        assert params["tenant_id"] == str(tid)

    async def test_details_serialised_as_json_string(self, service, mock_session):
        details = {"email": "user@test.com", "attempts": 3}
        await service.log_event(
            event_type="auth.login",
            details=details,
            tenant_id=uuid4(),
            session=mock_session,
        )
        params = _get_params(mock_session)
        parsed = json.loads(params["details"])
        assert parsed == details

    async def test_user_id_passed_as_string_when_provided(self, service, mock_session):
        uid = uuid4()
        await service.log_event(
            event_type="auth.logout",
            details={},
            tenant_id=uuid4(),
            session=mock_session,
            user_id=uid,
        )
        params = _get_params(mock_session)
        assert params["user_id"] == str(uid)

    async def test_user_id_is_none_when_not_provided(self, service, mock_session):
        await service.log_event(
            event_type="auth.login",
            details={},
            tenant_id=uuid4(),
            session=mock_session,
        )
        params = _get_params(mock_session)
        assert params["user_id"] is None

    async def test_id_param_is_valid_uuid_string(self, service, mock_session):
        """Each event must be assigned a fresh UUID primary key."""
        await service.log_event(
            event_type="auth.login",
            details={},
            tenant_id=uuid4(),
            session=mock_session,
        )
        params = _get_params(mock_session)
        UUID(params["id"])  # raises ValueError if not a valid UUID


class TestRequestIdCorrelation:
    """Verify request_id correlation behaviour."""

    async def test_auto_generated_when_not_provided(self, service, mock_session):
        """A request_id must be generated automatically when caller omits it."""
        await service.log_event(
            event_type="auth.login",
            details={},
            tenant_id=uuid4(),
            session=mock_session,
        )
        params = _get_params(mock_session)
        assert params["request_id"] is not None
        UUID(params["request_id"])  # must be a valid UUID

    async def test_provided_request_id_is_used(self, service, mock_session):
        """When a request_id is supplied it must appear verbatim in the params."""
        rid = uuid4()
        await service.log_event(
            event_type="auth.login",
            details={},
            tenant_id=uuid4(),
            session=mock_session,
            request_id=rid,
        )
        params = _get_params(mock_session)
        assert params["request_id"] == str(rid)

    async def test_two_events_get_different_auto_ids(self, service, mock_session):
        """Two separate log_event() calls must produce different request_ids."""
        for _ in range(2):
            await service.log_event(
                event_type="auth.login",
                details={},
                tenant_id=uuid4(),
                session=mock_session,
            )

        calls = mock_session.execute.call_args_list
        rid1 = calls[0].args[1]["request_id"]
        rid2 = calls[1].args[1]["request_id"]
        assert rid1 != rid2


class TestEventTypes:
    """Smoke-test common event type strings."""

    @pytest.mark.parametrize(
        "event_type",
        [
            "auth.login",
            "auth.logout",
            "rbac.denial",
            "data.access",
        ],
    )
    async def test_known_event_types_are_accepted(self, service, mock_session, event_type):
        """AuditService must accept any string event type without error."""
        await service.log_event(
            event_type=event_type,
            details={},
            tenant_id=uuid4(),
            session=mock_session,
        )
        params = _get_params(mock_session)
        assert params["event_type"] == event_type
