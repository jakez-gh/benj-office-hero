"""Unit tests for :class:`VehicleCrewService` (TDD-first, no DB)."""

from __future__ import annotations

from datetime import date, time
from typing import Any
from uuid import UUID, uuid4

import pytest

from office_hero.core.crew_role import CrewRole
from office_hero.core.exceptions import (
    CrewAssignmentConflictError,
    InvalidCrewMemberError,
    VehicleNotFoundError,
)
from office_hero.repositories.mocks import InMemoryAuditService
from office_hero.repositories.vehicle_crew_repository import (
    CrewMemberInput,
    InMemoryVehicleCrewRepository,
)
from office_hero.repositories.vehicle_repository import InMemoryVehicleRepository
from office_hero.services.vehicle_crew_service import VehicleCrewService
from office_hero.services.vehicle_service import VehicleService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeUser:
    def __init__(self, *, tenant_id, role="technician", active=True):
        self.id = uuid4()
        self.tenant_id = tenant_id
        self.role = role
        self.active = active


class _InMemoryUserRepo:
    """Minimal user repo for service-layer tests."""

    def __init__(self):
        self._users: dict[UUID, _FakeUser] = {}

    def add(self, user: _FakeUser) -> _FakeUser:
        self._users[user.id] = user
        return user

    async def get_by_id(self, user_id: UUID, tenant_id: UUID) -> Any | None:
        u = self._users.get(user_id)
        if u is None or u.tenant_id != tenant_id:
            return None
        return u


def make_member(user: _FakeUser, role: CrewRole = CrewRole.LEAD) -> CrewMemberInput:
    return CrewMemberInput(user_id=user.id, role_on_crew=role)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

WORK_DATE = date(2027, 8, 15)  # safely in the future


@pytest.fixture()
def tenant_a():
    return uuid4()


@pytest.fixture()
def tenant_b():
    return uuid4()


@pytest.fixture()
def user_repo():
    return _InMemoryUserRepo()


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
def vehicle_service(v_repo, vc_repo, audit):
    v_repo._crew_repo = vc_repo
    return VehicleService(repo=v_repo, audit=audit, crew_repo=vc_repo)


@pytest.fixture()
def crew_service(vc_repo, v_repo, user_repo, audit):
    return VehicleCrewService(
        crew_repo=vc_repo,
        vehicle_repo=v_repo,
        user_repo=user_repo,
        audit=audit,
    )


@pytest.fixture()
def dispatcher_user(tenant_a, user_repo):
    return user_repo.add(_FakeUser(tenant_id=tenant_a, role="dispatcher"))


@pytest.fixture()
def tech_a(tenant_a, user_repo):
    return user_repo.add(_FakeUser(tenant_id=tenant_a, role="technician"))


@pytest.fixture()
def tech_b(tenant_a, user_repo):
    return user_repo.add(_FakeUser(tenant_id=tenant_a, role="technician"))


@pytest.fixture()
async def vehicle(v_repo, tenant_a):
    return await v_repo.create(tenant_a, license_plate="TEST-001")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_create_crew_with_one_lead_succeeds(
    crew_service, vehicle, tech_a, tenant_a, dispatcher_user
):
    """Happy path: one lead member, valid date."""
    crew = await crew_service.create(
        tenant_a,
        dispatcher_user.id,
        vehicle_id=vehicle.id,
        work_date=WORK_DATE,
        shift_start=time(8, 0),
        shift_end=time(17, 0),
        notes=None,
        members=[make_member(tech_a, CrewRole.LEAD)],
    )
    assert crew.vehicle_id == vehicle.id
    assert len(crew.members) == 1
    assert crew.members[0].role_on_crew == str(CrewRole.LEAD)


async def test_create_crew_without_lead_raises(
    crew_service, vehicle, tech_a, tenant_a, dispatcher_user
):
    """A crew with no lead must be rejected."""
    with pytest.raises(ValueError, match="exactly one LEAD"):
        await crew_service.create(
            tenant_a,
            dispatcher_user.id,
            vehicle_id=vehicle.id,
            work_date=WORK_DATE,
            shift_start=time(8, 0),
            shift_end=time(17, 0),
            notes=None,
            members=[make_member(tech_a, CrewRole.HELPER)],
        )


async def test_create_crew_with_two_leads_raises(
    crew_service, vehicle, tech_a, tech_b, tenant_a, dispatcher_user
):
    """A crew with two leads must be rejected."""
    with pytest.raises(ValueError, match="more than one LEAD"):
        await crew_service.create(
            tenant_a,
            dispatcher_user.id,
            vehicle_id=vehicle.id,
            work_date=WORK_DATE,
            shift_start=time(8, 0),
            shift_end=time(17, 0),
            notes=None,
            members=[
                make_member(tech_a, CrewRole.LEAD),
                make_member(tech_b, CrewRole.LEAD),
            ],
        )


async def test_create_crew_member_in_other_tenant_raises_invalid_member(
    crew_service, vehicle, user_repo, tenant_a, tenant_b, dispatcher_user
):
    """A user from a different tenant cannot be a crew member."""
    other_tenant_user = user_repo.add(_FakeUser(tenant_id=tenant_b, role="technician"))
    with pytest.raises(InvalidCrewMemberError) as exc:
        await crew_service.create(
            tenant_a,
            dispatcher_user.id,
            vehicle_id=vehicle.id,
            work_date=WORK_DATE,
            shift_start=time(8, 0),
            shift_end=time(17, 0),
            notes=None,
            members=[make_member(other_tenant_user, CrewRole.LEAD)],
        )
    assert exc.value.reason == "not_in_tenant"


async def test_create_crew_member_with_inactive_user_raises_invalid_member(
    crew_service, vehicle, user_repo, tenant_a, dispatcher_user
):
    """An inactive user cannot be a crew member."""
    inactive = user_repo.add(_FakeUser(tenant_id=tenant_a, role="technician", active=False))
    with pytest.raises(InvalidCrewMemberError) as exc:
        await crew_service.create(
            tenant_a,
            dispatcher_user.id,
            vehicle_id=vehicle.id,
            work_date=WORK_DATE,
            shift_start=time(8, 0),
            shift_end=time(17, 0),
            notes=None,
            members=[make_member(inactive, CrewRole.LEAD)],
        )
    assert exc.value.reason == "inactive"


async def test_create_crew_member_with_non_technician_role_raises_invalid_member(
    crew_service, vehicle, user_repo, tenant_a, dispatcher_user
):
    """A user with Dispatcher role cannot be a crew member."""
    disp = user_repo.add(_FakeUser(tenant_id=tenant_a, role="dispatcher"))
    with pytest.raises(InvalidCrewMemberError) as exc:
        await crew_service.create(
            tenant_a,
            dispatcher_user.id,
            vehicle_id=vehicle.id,
            work_date=WORK_DATE,
            shift_start=time(8, 0),
            shift_end=time(17, 0),
            notes=None,
            members=[make_member(disp, CrewRole.LEAD)],
        )
    assert exc.value.reason == "ineligible_role"


async def test_create_crew_duplicate_vehicle_date_raises_assignment_conflict(
    crew_service, vehicle, tech_a, tech_b, tenant_a, dispatcher_user
):
    """A second crew on the same (vehicle, date) is rejected."""
    await crew_service.create(
        tenant_a,
        dispatcher_user.id,
        vehicle_id=vehicle.id,
        work_date=WORK_DATE,
        shift_start=time(8, 0),
        shift_end=time(17, 0),
        notes=None,
        members=[make_member(tech_a, CrewRole.LEAD)],
    )
    with pytest.raises(CrewAssignmentConflictError) as exc:
        await crew_service.create(
            tenant_a,
            dispatcher_user.id,
            vehicle_id=vehicle.id,
            work_date=WORK_DATE,
            shift_start=time(9, 0),
            shift_end=time(18, 0),
            notes=None,
            members=[make_member(tech_b, CrewRole.LEAD)],
        )
    assert exc.value.existing_crew_id is not None


async def test_create_crew_archived_vehicle_raises_not_found(
    crew_service, v_repo, tech_a, tenant_a, dispatcher_user
):
    """Cannot assign a crew to an archived vehicle."""
    v = await v_repo.create(tenant_a, license_plate="ARCHIVED-1")
    await v_repo.archive(v.id, tenant_a)
    with pytest.raises(VehicleNotFoundError):
        await crew_service.create(
            tenant_a,
            dispatcher_user.id,
            vehicle_id=v.id,
            work_date=WORK_DATE,
            shift_start=time(8, 0),
            shift_end=time(17, 0),
            notes=None,
            members=[make_member(tech_a, CrewRole.LEAD)],
        )


async def test_create_crew_backdated_more_than_30_days_raises(
    crew_service, vehicle, tech_a, tenant_a, dispatcher_user
):
    """A work_date more than 30 days in the past must be rejected."""
    from datetime import timedelta

    old_date = date.today() - timedelta(days=31)
    with pytest.raises(ValueError, match="days in the past"):
        await crew_service.create(
            tenant_a,
            dispatcher_user.id,
            vehicle_id=vehicle.id,
            work_date=old_date,
            shift_start=time(8, 0),
            shift_end=time(17, 0),
            notes=None,
            members=[make_member(tech_a, CrewRole.LEAD)],
        )


async def test_create_crew_shift_end_before_start_raises(
    crew_service, vehicle, tech_a, tenant_a, dispatcher_user
):
    """shift_end <= shift_start must be rejected."""
    with pytest.raises(ValueError, match="shift_end must be after"):
        await crew_service.create(
            tenant_a,
            dispatcher_user.id,
            vehicle_id=vehicle.id,
            work_date=WORK_DATE,
            shift_start=time(17, 0),
            shift_end=time(8, 0),
            notes=None,
            members=[make_member(tech_a, CrewRole.LEAD)],
        )


async def test_replace_members_keeps_lead_invariant(
    crew_service, vehicle, tech_a, tech_b, tenant_a, dispatcher_user
):
    """replace_members must enforce the exactly-one-lead invariant."""
    crew = await crew_service.create(
        tenant_a,
        dispatcher_user.id,
        vehicle_id=vehicle.id,
        work_date=WORK_DATE,
        shift_start=time(8, 0),
        shift_end=time(17, 0),
        notes=None,
        members=[make_member(tech_a, CrewRole.LEAD)],
    )
    # Replace with two helpers — should raise
    with pytest.raises(ValueError, match="exactly one LEAD"):
        await crew_service.replace_members(
            tenant_a,
            dispatcher_user.id,
            crew.id,
            [
                make_member(tech_a, CrewRole.HELPER),
                make_member(tech_b, CrewRole.HELPER),
            ],
        )


async def test_remove_lead_member_without_replacement_refused(
    crew_service, vehicle, tech_a, tenant_a, dispatcher_user
):
    """Removing the only lead from a crew must be refused."""
    crew = await crew_service.create(
        tenant_a,
        dispatcher_user.id,
        vehicle_id=vehicle.id,
        work_date=WORK_DATE,
        shift_start=time(8, 0),
        shift_end=time(17, 0),
        notes=None,
        members=[make_member(tech_a, CrewRole.LEAD)],
    )
    with pytest.raises(ValueError, match="Cannot remove the LEAD"):
        await crew_service.remove_member(tenant_a, dispatcher_user.id, crew.id, tech_a.id)


async def test_conflicts_for_date_finds_double_booked_user(
    crew_service, v_repo, tech_a, user_repo, tenant_a, dispatcher_user
):
    """A user on two crews on the same date is surfaced as a conflict."""
    # Need two vehicles
    v1 = await v_repo.create(tenant_a, license_plate="C-TRUCK-1")
    v2 = await v_repo.create(tenant_a, license_plate="C-TRUCK-2")
    tech_b = user_repo.add(_FakeUser(tenant_id=tenant_a, role="technician"))

    await crew_service.create(
        tenant_a,
        dispatcher_user.id,
        vehicle_id=v1.id,
        work_date=WORK_DATE,
        shift_start=time(8, 0),
        shift_end=time(12, 0),
        notes=None,
        members=[make_member(tech_a, CrewRole.LEAD)],
    )
    await crew_service.create(
        tenant_a,
        dispatcher_user.id,
        vehicle_id=v2.id,
        work_date=WORK_DATE,
        shift_start=time(13, 0),
        shift_end=time(17, 0),
        notes=None,
        members=[
            make_member(tech_b, CrewRole.LEAD),
            make_member(tech_a, CrewRole.HELPER),
        ],
    )
    conflicts = await crew_service.conflicts_for_date(tenant_a, WORK_DATE)
    conflict_user_ids = {uid for uid, _ in conflicts}
    assert tech_a.id in conflict_user_ids


async def test_delete_crew_when_routed_refused_smoke(
    crew_service, vehicle, tech_a, tenant_a, dispatcher_user
):
    """Smoke: delete works today (route check is a no-op until Slice 14 lands)."""
    crew = await crew_service.create(
        tenant_a,
        dispatcher_user.id,
        vehicle_id=vehicle.id,
        work_date=WORK_DATE,
        shift_start=time(8, 0),
        shift_end=time(17, 0),
        notes=None,
        members=[make_member(tech_a, CrewRole.LEAD)],
    )
    # Should not raise — route check is deferred to Slice 14
    await crew_service.delete(tenant_a, dispatcher_user.id, crew.id)
