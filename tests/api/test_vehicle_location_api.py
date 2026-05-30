"""HTTP-layer tests for PUT /vehicles/{vehicle_id}/location (Slice 15)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from office_hero.api.app import create_app
from office_hero.api.limiter import limiter
from office_hero.repositories.vehicle_location_repository import (
    InMemoryVehicleLocationRepository,
)
from office_hero.repositories.vehicle_repository import InMemoryVehicleRepository
from office_hero.services.vehicle_location_service import VehicleLocationService


class _LocTestAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.tenant_id = request.headers.get("X-Test-Tenant-Id")
        request.state.user_id = request.headers.get("X-Test-User-Id")
        request.state.role = request.headers.get("X-Test-Role", "technician")
        perms_raw = request.headers.get("X-Test-Permissions", "vehicle:write")
        request.state.permissions = [p.strip() for p in perms_raw.split(",") if p.strip()]
        return await call_next(request)


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    test_key = str(uuid4())
    saved: list[tuple] = []
    for limits in limiter._route_limits.values():
        for lim in limits:
            saved.append((lim, lim.key_func))
            lim.key_func = lambda *_a, **_k: test_key
    yield
    for lim, orig in saved:
        lim.key_func = orig


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture()
def tenant_id() -> UUID:
    return uuid4()


@pytest.fixture()
def user_id() -> UUID:
    return uuid4()


@pytest.fixture()
def v_repo() -> InMemoryVehicleRepository:
    return InMemoryVehicleRepository()


@pytest.fixture()
def loc_repo() -> InMemoryVehicleLocationRepository:
    return InMemoryVehicleLocationRepository()


@pytest.fixture()
def location_service(v_repo, loc_repo) -> VehicleLocationService:
    return VehicleLocationService(location_repo=loc_repo, vehicle_repo=v_repo)


@pytest.fixture()
def app(location_service) -> FastAPI:
    saved = dict(limiter._route_limits)
    limiter._route_limits.clear()
    a = create_app(vehicle_location_service=location_service)
    a.add_middleware(_LocTestAuthMiddleware)
    yield a
    limiter._route_limits.clear()
    limiter._route_limits.update(saved)


@pytest.fixture()
def client(app) -> TestClient:
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def vehicle(v_repo, tenant_id):
    async def _create():
        return await v_repo.create(
            tenant_id,
            license_plate="TRK-LOC",
            nickname="Location Van",
            make="Ford",
            model="Transit",
            year=2023,
        )

    return _run(_create())


def _headers(tenant_id, user_id, *, perms: str = "vehicle:write") -> dict[str, str]:
    return {
        "X-Test-Tenant-Id": str(tenant_id),
        "X-Test-User-Id": str(user_id),
        "X-Test-Role": "technician",
        "X-Test-Permissions": perms,
    }


RECORDED_AT = datetime(2026, 5, 30, 14, 0, 0, tzinfo=UTC)


def test_record_location_success(client, tenant_id, user_id, vehicle):
    resp = client.put(
        f"/vehicles/{vehicle.id}/location",
        json={
            "lat": "37.7749",
            "lng": "-122.4194",
            "accuracy_m": "5.0",
            "recorded_at": RECORDED_AT.isoformat(),
        },
        headers=_headers(tenant_id, user_id),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["vehicle_id"] == str(vehicle.id)
    assert float(data["lat"]) == pytest.approx(37.7749)
    assert float(data["lng"]) == pytest.approx(-122.4194)
    assert float(data["accuracy_m"]) == pytest.approx(5.0)


def test_record_location_no_accuracy(client, tenant_id, user_id, vehicle):
    resp = client.put(
        f"/vehicles/{vehicle.id}/location",
        json={
            "lat": "51.5074",
            "lng": "-0.1278",
            "recorded_at": RECORDED_AT.isoformat(),
        },
        headers=_headers(tenant_id, user_id),
    )
    assert resp.status_code == 200
    assert resp.json()["accuracy_m"] is None


def test_record_location_vehicle_not_found(client, tenant_id, user_id):
    resp = client.put(
        f"/vehicles/{uuid4()}/location",
        json={"lat": "0.0", "lng": "0.0", "recorded_at": RECORDED_AT.isoformat()},
        headers=_headers(tenant_id, user_id),
    )
    assert resp.status_code == 404


def test_record_location_missing_permission(client, tenant_id, user_id, vehicle):
    resp = client.put(
        f"/vehicles/{vehicle.id}/location",
        json={"lat": "0.0", "lng": "0.0", "recorded_at": RECORDED_AT.isoformat()},
        headers=_headers(tenant_id, user_id, perms="vehicle:read"),
    )
    assert resp.status_code == 403


def test_record_location_naive_datetime_422(client, tenant_id, user_id, vehicle):
    resp = client.put(
        f"/vehicles/{vehicle.id}/location",
        json={"lat": "0.0", "lng": "0.0", "recorded_at": "2026-05-30T14:00:00"},
        headers=_headers(tenant_id, user_id),
    )
    assert resp.status_code == 422


def test_record_location_lat_out_of_range(client, tenant_id, user_id, vehicle):
    resp = client.put(
        f"/vehicles/{vehicle.id}/location",
        json={"lat": "91.0", "lng": "0.0", "recorded_at": RECORDED_AT.isoformat()},
        headers=_headers(tenant_id, user_id),
    )
    assert resp.status_code == 422


def test_record_location_cross_tenant_404(client, tenant_id, user_id, v_repo):
    other_vehicle = _run(
        v_repo.create(
            uuid4(),
            license_plate="OTH-999",
            nickname="Other Van",
            make="Ford",
            model="Transit",
            year=2022,
        )
    )
    resp = client.put(
        f"/vehicles/{other_vehicle.id}/location",
        json={"lat": "0.0", "lng": "0.0", "recorded_at": RECORDED_AT.isoformat()},
        headers=_headers(tenant_id, user_id),
    )
    assert resp.status_code == 404
