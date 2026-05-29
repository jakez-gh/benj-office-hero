"""HTTP-layer tests for POST /jobs/{job_id}/schedule-options."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from office_hero.adapters.routing.stub import StubRoutingAdapter
from office_hero.api.app import create_app
from office_hero.api.limiter import limiter
from office_hero.repositories.job_repository import InMemoryJobRepository
from office_hero.repositories.vehicle_repository import InMemoryVehicleRepository
from office_hero.services.schedule_suggestion_service import ScheduleSuggestionService


@dataclass
class _FakeLocation:
    """Minimal location stand-in so API tests stay off SQLAlchemy machinery."""

    lat: Decimal | None
    lng: Decimal | None
    geocode_status: str = "complete"


# ---------------------------------------------------------------------------
# Auth middleware
# ---------------------------------------------------------------------------


class _ScheduleTestAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.tenant_id = request.headers.get("X-Test-Tenant-Id")
        request.state.user_id = request.headers.get("X-Test-User-Id")
        request.state.role = request.headers.get("X-Test-Role", "tenant_admin")
        perms_raw = request.headers.get("X-Test-Permissions", "job:read,vehicle:read")
        request.state.permissions = [p.strip() for p in perms_raw.split(",") if p.strip()]
        return await call_next(request)


def _reset_limiter() -> None:
    import contextlib

    limiter.reset()
    storage = getattr(getattr(limiter, "limiter", None), "storage", None)
    if storage and hasattr(storage, "reset"):
        with contextlib.suppress(Exception):
            storage.reset()


def _auth_headers(tenant_id, user_id, *, perms="job:read,vehicle:read") -> dict[str, str]:
    return {
        "X-Test-Tenant-Id": str(tenant_id),
        "X-Test-User-Id": str(user_id),
        "X-Test-Role": "tenant_admin",
        "X-Test-Permissions": perms,
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Give each test its own rate-limit bucket (avoids 429s from shared IP)."""
    test_key = str(uuid4())
    saved: list[tuple] = []
    for limits in limiter._route_limits.values():
        for lim in limits:
            saved.append((lim, lim.key_func))
            lim.key_func = lambda *_a, **_k: test_key
    yield
    for lim, orig in saved:
        lim.key_func = orig


@pytest.fixture()
def tenant_id():
    return uuid4()


@pytest.fixture()
def user_id():
    return uuid4()


@pytest.fixture()
def j_repo():
    return InMemoryJobRepository()


@pytest.fixture()
def v_repo():
    return InMemoryVehicleRepository()


@pytest.fixture()
def schedule_service(j_repo, v_repo):
    return ScheduleSuggestionService(
        job_repo=j_repo,
        vehicle_repo=v_repo,
        routing_adapter=StubRoutingAdapter(),
    )


@pytest.fixture()
def app(schedule_service) -> FastAPI:
    saved = dict(limiter._route_limits)
    limiter._route_limits.clear()
    a = create_app(schedule_suggestion_service=schedule_service)
    a.add_middleware(_ScheduleTestAuthMiddleware)
    yield a
    limiter._route_limits.clear()
    limiter._route_limits.update(saved)


@pytest.fixture()
def client(app) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


def _make_geocoded_location(tenant_id) -> _FakeLocation:
    return _FakeLocation(lat=Decimal("41.8781"), lng=Decimal("-87.6298"))


def _make_ungeocode_location(tenant_id) -> _FakeLocation:
    return _FakeLocation(lat=None, lng=None, geocode_status="pending")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_missing_permissions_returns_403(client, tenant_id, user_id):
    """Request without required permissions gets 403."""
    resp = client.post(
        f"/jobs/{uuid4()}/schedule-options",
        json={
            "window_start": "2026-06-01T09:00:00Z",
            "window_end": "2026-06-01T17:00:00Z",
        },
        headers=_auth_headers(tenant_id, user_id, perms=""),
    )
    assert resp.status_code == 403


def test_missing_vehicle_read_returns_403(client, tenant_id, user_id):
    """Only job:read but not vehicle:read → 403."""
    resp = client.post(
        f"/jobs/{uuid4()}/schedule-options",
        json={
            "window_start": "2026-06-01T09:00:00Z",
            "window_end": "2026-06-01T17:00:00Z",
        },
        headers=_auth_headers(tenant_id, user_id, perms="job:read"),
    )
    assert resp.status_code == 403


def test_unknown_job_returns_404(client, tenant_id, user_id):
    """Non-existent job_id → 404."""
    resp = client.post(
        f"/jobs/{uuid4()}/schedule-options",
        json={
            "window_start": "2026-06-01T09:00:00Z",
            "window_end": "2026-06-01T17:00:00Z",
        },
        headers=_auth_headers(tenant_id, user_id),
    )
    assert resp.status_code == 404


def test_ungeocoded_job_returns_422(client, j_repo, tenant_id, user_id):
    """Job with no geocoords → 422."""
    jid = uuid4()
    now = datetime.now(UTC)
    j_repo._rows[jid] = {
        "id": jid,
        "tenant_id": tenant_id,
        "customer_id": uuid4(),
        "location_id": uuid4(),
        "industry": "plumbing",
        "title": "Fix leak",
        "description": None,
        "status": "pending",
        "priority": 50,
        "service_type": None,
        "requested_at": None,
        "requested_until": None,
        "estimated_duration_min": 60,
        "scheduled_for": None,
        "started_at": None,
        "completed_at": None,
        "cancelled_at": None,
        "cancel_reason": None,
        "custom_fields": {},
        "external_id": None,
        "assigned_vehicle_id": None,
        "created_by_user_id": user_id,
        "created_at": now,
        "updated_at": now,
    }
    raw_job = j_repo._row_to_job(j_repo._rows[jid])
    raw_job.location = _make_ungeocode_location(tenant_id)
    j_repo._rows[jid]["_job_obj"] = raw_job

    # Monkey-patch get_by_id to return our job with ungeocode location
    original_get = j_repo.get_by_id

    async def _patched_get(job_id, t_id):
        if job_id == jid and t_id == tenant_id:
            return raw_job
        return await original_get(job_id, t_id)

    j_repo.get_by_id = _patched_get

    resp = client.post(
        f"/jobs/{jid}/schedule-options",
        json={
            "window_start": "2026-06-01T09:00:00Z",
            "window_end": "2026-06-01T17:00:00Z",
        },
        headers=_auth_headers(tenant_id, user_id),
    )
    assert resp.status_code == 422
    assert "geocoded" in resp.json()["detail"].lower()


def test_happy_path_returns_options(client, j_repo, v_repo, tenant_id, user_id):
    """Happy path: 1 vehicle + geocoded job → 1 option with expected shape."""

    async def _setup():
        await v_repo.create(
            tenant_id,
            license_plate="HAPPY-001",
            nickname="Blue Van",
            home_base_lat=41.8,
            home_base_lng=-87.6,
        )

        jid = uuid4()
        now = datetime.now(UTC)
        j_repo._rows[jid] = {
            "id": jid,
            "tenant_id": tenant_id,
            "customer_id": uuid4(),
            "location_id": uuid4(),
            "industry": "plumbing",
            "title": "Fix leak",
            "description": None,
            "status": "pending",
            "priority": 50,
            "service_type": None,
            "requested_at": None,
            "requested_until": None,
            "estimated_duration_min": 60,
            "scheduled_for": None,
            "started_at": None,
            "completed_at": None,
            "cancelled_at": None,
            "cancel_reason": None,
            "custom_fields": {},
            "external_id": None,
            "assigned_vehicle_id": None,
            "created_by_user_id": user_id,
            "created_at": now,
            "updated_at": now,
        }
        raw_job = j_repo._row_to_job(j_repo._rows[jid])
        raw_job.location = _make_geocoded_location(tenant_id)

        original_get = j_repo.get_by_id

        async def _patched_get(job_id, t_id):
            if job_id == jid and t_id == tenant_id:
                return raw_job
            return await original_get(job_id, t_id)

        j_repo.get_by_id = _patched_get
        return jid

    jid = asyncio.get_event_loop().run_until_complete(_setup())

    resp = client.post(
        f"/jobs/{jid}/schedule-options",
        json={
            "window_start": "2026-06-01T09:00:00Z",
            "window_end": "2026-06-01T17:00:00Z",
        },
        headers=_auth_headers(tenant_id, user_id),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"] == str(jid)
    assert len(body["options"]) == 1
    opt = body["options"][0]
    assert opt["rank"] == 1
    assert opt["vehicle_display"] == "Blue Van (HAPPY-001)"
    assert opt["travel_seconds"] == 900
    assert opt["distance_meters"] == 12_000


def test_no_vehicles_returns_empty_options(client, j_repo, tenant_id, user_id):
    """No vehicles → empty options list, still 200."""

    async def _setup():
        jid = uuid4()
        now = datetime.now(UTC)
        j_repo._rows[jid] = {
            "id": jid,
            "tenant_id": tenant_id,
            "customer_id": uuid4(),
            "location_id": uuid4(),
            "industry": "plumbing",
            "title": "No vehicles",
            "description": None,
            "status": "pending",
            "priority": 50,
            "service_type": None,
            "requested_at": None,
            "requested_until": None,
            "estimated_duration_min": 60,
            "scheduled_for": None,
            "started_at": None,
            "completed_at": None,
            "cancelled_at": None,
            "cancel_reason": None,
            "custom_fields": {},
            "external_id": None,
            "assigned_vehicle_id": None,
            "created_by_user_id": user_id,
            "created_at": now,
            "updated_at": now,
        }
        raw_job = j_repo._row_to_job(j_repo._rows[jid])
        raw_job.location = _make_geocoded_location(tenant_id)

        original_get = j_repo.get_by_id

        async def _patched_get(job_id, t_id):
            if job_id == jid and t_id == tenant_id:
                return raw_job
            return await original_get(job_id, t_id)

        j_repo.get_by_id = _patched_get
        return jid

    jid = asyncio.get_event_loop().run_until_complete(_setup())

    resp = client.post(
        f"/jobs/{jid}/schedule-options",
        json={
            "window_start": "2026-06-01T09:00:00Z",
            "window_end": "2026-06-01T17:00:00Z",
        },
        headers=_auth_headers(tenant_id, user_id),
    )
    assert resp.status_code == 200
    assert resp.json()["options"] == []


def test_invalid_request_body_returns_422(client, tenant_id, user_id):
    """Missing window_start field → 422 from Pydantic."""
    resp = client.post(
        f"/jobs/{uuid4()}/schedule-options",
        json={"window_end": "2026-06-01T17:00:00Z"},
        headers=_auth_headers(tenant_id, user_id),
    )
    assert resp.status_code == 422


def test_extra_fields_in_body_rejected(client, tenant_id, user_id):
    """extra='forbid' means unknown request body fields → 422."""
    resp = client.post(
        f"/jobs/{uuid4()}/schedule-options",
        json={
            "window_start": "2026-06-01T09:00:00Z",
            "window_end": "2026-06-01T17:00:00Z",
            "unknown_field": "oops",
        },
        headers=_auth_headers(tenant_id, user_id),
    )
    assert resp.status_code == 422
