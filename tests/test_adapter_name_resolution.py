"""Unit tests for BackOfficeSyncService._adapter_name (WS-04).

Covers the two resolution paths:
  1. tenant_repo is provided — uses repo.get_by_id() synchronously.
  2. tenant_repo is None — falls back to lazy DB lookup via get_engine();
     if the engine is absent (test env) it must return "native" without raising.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from office_hero.services.back_office_sync_service import BackOfficeSyncService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service(tenant_repo=None) -> BackOfficeSyncService:
    return BackOfficeSyncService(
        outbox=MagicMock(),
        customer_repo=MagicMock(),
        job_repo=MagicMock(),
        tenant_repo=tenant_repo,
    )


# ---------------------------------------------------------------------------
# Path 1: tenant_repo provided
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_adapter_name_uses_tenant_repo_when_provided():
    tenant_id = uuid4()
    mock_tenant = MagicMock()
    mock_tenant.back_office_adapter = "jobber"

    mock_repo = AsyncMock()
    mock_repo.get_by_id.return_value = mock_tenant

    svc = _make_service(tenant_repo=mock_repo)
    name = await svc._adapter_name(tenant_id)

    assert name == "jobber"
    mock_repo.get_by_id.assert_awaited_once_with(tenant_id)


@pytest.mark.asyncio
async def test_adapter_name_falls_back_to_native_when_repo_returns_none_adapter():
    tenant_id = uuid4()
    mock_tenant = MagicMock()
    mock_tenant.back_office_adapter = None

    mock_repo = AsyncMock()
    mock_repo.get_by_id.return_value = mock_tenant

    svc = _make_service(tenant_repo=mock_repo)
    name = await svc._adapter_name(tenant_id)

    assert name == "native"


@pytest.mark.asyncio
async def test_adapter_name_falls_back_to_native_when_repo_returns_empty_string():
    tenant_id = uuid4()
    mock_tenant = MagicMock()
    mock_tenant.back_office_adapter = ""

    mock_repo = AsyncMock()
    mock_repo.get_by_id.return_value = mock_tenant

    svc = _make_service(tenant_repo=mock_repo)
    name = await svc._adapter_name(tenant_id)

    assert name == "native"


# ---------------------------------------------------------------------------
# Path 2: tenant_repo is None → lazy DB lookup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_adapter_name_returns_native_when_no_repo_and_no_engine():
    """Engine absent in test env — must not raise, must return 'native'."""
    tenant_id = uuid4()
    svc = _make_service(tenant_repo=None)

    # get_engine() raises RuntimeError when the engine has not been set
    with patch("office_hero.api.state.get_engine", side_effect=RuntimeError("no engine")):
        name = await svc._adapter_name(tenant_id)

    assert name == "native"


@pytest.mark.asyncio
async def test_adapter_name_reads_db_when_engine_available():
    """When the engine IS available, _adapter_name queries it."""
    tenant_id = uuid4()
    svc = _make_service(tenant_repo=None)

    mock_tenant = MagicMock()
    mock_tenant.back_office_adapter = "servicetitan"

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_tenant

    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_engine = MagicMock()

    with (
        patch("office_hero.api.state.get_engine", return_value=mock_engine),
        patch("office_hero.db.session.get_session", return_value=mock_session),
    ):
        name = await svc._adapter_name(tenant_id)

    assert name == "servicetitan"


@pytest.mark.asyncio
async def test_adapter_name_returns_native_when_tenant_not_in_db():
    """DB available but tenant row absent → 'native'."""
    tenant_id = uuid4()
    svc = _make_service(tenant_repo=None)

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None

    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_engine = MagicMock()

    with (
        patch("office_hero.api.state.get_engine", return_value=mock_engine),
        patch("office_hero.db.session.get_session", return_value=mock_session),
    ):
        name = await svc._adapter_name(tenant_id)

    assert name == "native"
