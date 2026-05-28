"""Unit tests for :class:`VehicleService` (TDD-first, no DB)."""

from __future__ import annotations

from datetime import date, time
from uuid import uuid4

import pytest

from office_hero.core.crew_role import CrewRole
from office_hero.core.exceptions import CrewAssignmentConflictError
from office_hero.repositories.mocks import InMemoryAuditService
from office_hero.repositories.vehicle_crew_repository import (
    CrewMemberInput,
    InMemoryVehicleCrewRepository,
)
from office_hero.repositories.vehicle_repository import InMemoryVehicleRepository
from office_hero.services.vehicle_service import VehicleService


@pytest.fixture()
def audit():
    return InMemoryAuditService()


@pytest.fixture()
def v_repo():
    return InMemoryVehicleRepository()


@pytest.fixture()
def vc_repo():
    return InMemoryVehicleCrewRepository()


@pytest.fixture()
def service(v_repo, vc_repo, audit):
    v_repo._crew_repo = vc_repo
    return VehicleService(repo=v_repo, audit=audit, crew_repo=vc_repo)


@pytest.fixture()
def tenant_a():
    return uuid4()


@pytest.fixture()
def user_a():
    return uuid4()


async def test_create_vehicle_returns_vehicle_and_audits(service, audit, tenant_a, user_a):
    """Creating a vehicle must emit ``vehicle.created`` with the plate."""
    v = await service.create(
        tenant_a,
        user_a,
        license_plate="ABC-1234",
        make="Ford",
        model="Transit",
        year=2022,
    )
    assert v.license_plate == "ABC-1234"
    assert v.tenant_id == tenant_a
    assert len(audit.events) == 1
    evt = audit.events[0]
    assert evt.event_type == "vehicle.created"
    assert evt.details["license_plate"] == "ABC-1234"


async def test_create_vehicle_duplicate_plate_raises_conflict(service, tenant_a, user_a):
    """Duplicate active license plate within a tenant raises ValueError."""
    await service.create(tenant_a, user_a, license_plate="DUP-0001")
    with pytest.raises(ValueError, match="already exists"):
        await service.create(tenant_a, user_a, license_plate="DUP-0001")


async def test_archive_vehicle_with_active_crew_today_refused(
    service, v_repo, vc_repo, audit, tenant_a, user_a
):
    """Archiving a vehicle with a crew for today (or future) must raise 409-equivalent."""
    v = await service.create(tenant_a, user_a, license_plate="TRUCK-1")
    tech_id = uuid4()
    today = date.today()
    await vc_repo.create(
        tenant_a,
        vehicle_id=v.id,
        work_date=today,
        shift_start=time(8, 0),
        shift_end=time(17, 0),
        notes=None,
        created_by_user_id=user_a,
        members=[CrewMemberInput(user_id=tech_id, role_on_crew=CrewRole.LEAD)],
    )
    with pytest.raises(CrewAssignmentConflictError):
        await service.archive(tenant_a, user_a, v.id)


async def test_archive_vehicle_with_only_past_crews_succeeds(
    service, v_repo, vc_repo, audit, tenant_a, user_a
):
    """A vehicle with only past crews can be archived."""
    v = await service.create(tenant_a, user_a, license_plate="TRUCK-2")
    tech_id = uuid4()
    past_date = date(2020, 1, 1)
    await vc_repo.create(
        tenant_a,
        vehicle_id=v.id,
        work_date=past_date,
        shift_start=time(8, 0),
        shift_end=time(17, 0),
        notes=None,
        created_by_user_id=user_a,
        members=[CrewMemberInput(user_id=tech_id, role_on_crew=CrewRole.LEAD)],
    )
    archived = await service.archive(tenant_a, user_a, v.id)
    assert archived.archived is True


async def test_update_vehicle_partial_patch_emits_diff_audit(service, audit, tenant_a, user_a):
    """Partial patch emits ``vehicle.updated`` with before/after diff."""
    v = await service.create(tenant_a, user_a, license_plate="PATCH-ME", make="Ford")
    audit.events.clear()

    updated = await service.update(tenant_a, user_a, v.id, {"make": "Sprinter"})
    assert updated.make == "Sprinter"
    assert len(audit.events) == 1
    evt = audit.events[0]
    assert evt.event_type == "vehicle.updated"
    assert evt.details["before"]["make"] == "Ford"
    assert evt.details["after"]["make"] == "Sprinter"
