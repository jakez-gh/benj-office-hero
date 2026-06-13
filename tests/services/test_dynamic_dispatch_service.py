"""Unit tests for DynamicDispatchService — day-of re-routing (Slice 16)."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from office_hero.adapters.routing.stub import StubRoutingAdapter
from office_hero.core.crew_role import CrewRole
from office_hero.core.exceptions import (
    RouteCommitConflictError,
    RouteNotFoundError,
    VehicleNotFoundError,
)
from office_hero.core.route_status import RouteStatus, RouteStopStatus
from office_hero.repositories.job_repository import InMemoryJobRepository
from office_hero.repositories.mocks import InMemoryAuditService
from office_hero.repositories.route_repository import InMemoryRouteRepository, RouteCreateRow
from office_hero.repositories.route_stop_repository import InMemoryRouteStopRepository, StopRow
from office_hero.repositories.vehicle_crew_repository import (
    CrewMemberInput,
    InMemoryVehicleCrewRepository,
)
from office_hero.repositories.vehicle_repository import InMemoryVehicleRepository
from office_hero.services.dynamic_dispatch_service import DynamicDispatchService
from office_hero.services.schedule_suggestion_service import ScheduleSuggestionService

TENANT_A = uuid4()
TENANT_B = uuid4()
USER_A = uuid4()
WORK_DATE = date(2026, 6, 15)


@pytest.fixture
def ctx():
    job_repo = InMemoryJobRepository()
    vehicle_repo = InMemoryVehicleRepository()
    vc_repo = InMemoryVehicleCrewRepository()
    route_repo = InMemoryRouteRepository()
    stop_repo = InMemoryRouteStopRepository()
    audit = InMemoryAuditService()
    schedule_svc = ScheduleSuggestionService(
        job_repo=job_repo,
        vehicle_repo=vehicle_repo,
        routing_adapter=StubRoutingAdapter(),
        vehicle_location_repo=None,
    )
    svc = DynamicDispatchService(
        route_repo=route_repo,
        stop_repo=stop_repo,
        job_repo=job_repo,
        vehicle_repo=vehicle_repo,
        vehicle_crew_repo=vc_repo,
        schedule_service=schedule_svc,
        audit=audit,
    )
    return SimpleNamespace(
        svc=svc,
        job_repo=job_repo,
        vehicle_repo=vehicle_repo,
        vc_repo=vc_repo,
        route_repo=route_repo,
        stop_repo=stop_repo,
        audit=audit,
    )


async def _vehicle_with_crew(ctx, *, tenant_id=TENANT_A, plate="ABC-1", work_date=WORK_DATE):
    v = await ctx.vehicle_repo.create(
        tenant_id, license_plate=plate, nickname=plate, make="Ford", model="Transit", year=2022
    )
    await ctx.vc_repo.create(
        tenant_id,
        vehicle_id=v.id,
        work_date=work_date,
        shift_start=time(8, 0),
        shift_end=time(17, 0),
        notes=None,
        created_by_user_id=USER_A,
        members=[CrewMemberInput(user_id=USER_A, role_on_crew=CrewRole.LEAD)],
    )
    return v


async def _job(ctx, *, tenant_id=TENANT_A, title="Job", geocoded=False):
    loc_id = uuid4()
    job = await ctx.job_repo.create(
        tenant_id,
        customer_id=uuid4(),
        location_id=loc_id,
        industry="generic",
        title=title,
        created_by_user_id=USER_A,
    )
    if geocoded:
        # Attach a geocoded location so the schedule service can rank the job.
        orig = ctx.job_repo.get_by_id

        async def patched(jid, tid, _orig=orig):
            j = await _orig(jid, tid)
            if j is not None and j.location_id == loc_id:
                j.location = SimpleNamespace(lat=Decimal("34.05"), lng=Decimal("-118.24"))
            return j

        ctx.job_repo.get_by_id = patched
    return job


async def _committed_route(ctx, vehicle, jobs, *, tenant_id=TENANT_A, work_date=WORK_DATE):
    route = await ctx.route_repo.create(
        tenant_id,
        row=RouteCreateRow(
            vehicle_id=vehicle.id,
            vehicle_crew_id=uuid4(),
            work_date=work_date,
            committed_by_user_id=USER_A,
            option_kind_applied="manual",
            notes=None,
            total_distance_m=1000 * len(jobs),
            total_duration_s=600 * len(jobs),
        ),
    )
    stops = await ctx.stop_repo.bulk_insert(
        tenant_id,
        route.id,
        [
            StopRow(
                job_id=j.id,
                sequence_index=i,
                planned_distance_from_prev_m=1000,
                planned_duration_from_prev_s=600,
            )
            for i, j in enumerate(jobs)
        ],
    )
    route.stops = stops
    return route, stops


# ---------------------------------------------------------------------------
# reassign_route
# ---------------------------------------------------------------------------


async def test_reassign_moves_pending_stops_to_target(ctx):
    va = await _vehicle_with_crew(ctx, plate="A")
    vb = await _vehicle_with_crew(ctx, plate="B")
    j1 = await _job(ctx, title="J1")
    j2 = await _job(ctx, title="J2")
    src, _ = await _committed_route(ctx, va, [j1, j2])

    result = await ctx.svc.reassign_route(TENANT_A, USER_A, src.id, target_vehicle_id=vb.id)

    assert result["moved_count"] == 2
    # Source is finalised (cancelled — it never started).
    assert RouteStatus(result["source_route"].status) == RouteStatus.CANCELLED
    # Target now carries both jobs.
    target_stops = await ctx.stop_repo.get_for_route(TENANT_A, result["target_route"].id)
    assert [s.job_id for s in target_stops] == [j1.id, j2.id]
    assert [s.sequence_index for s in target_stops] == [0, 1]
    # Source pending stops are skipped.
    src_stops = await ctx.stop_repo.get_for_route(TENANT_A, src.id)
    assert all(RouteStopStatus(s.status) == RouteStopStatus.SKIPPED for s in src_stops)
    assert any(e.event_type == "route.reassigned" for e in ctx.audit.events)


async def test_reassign_keeps_completed_stops_on_source_and_completes_it(ctx):
    va = await _vehicle_with_crew(ctx, plate="A")
    vb = await _vehicle_with_crew(ctx, plate="B")
    j1 = await _job(ctx, title="done")
    j2 = await _job(ctx, title="pending")
    src, stops = await _committed_route(ctx, va, [j1, j2])
    # Start the route and complete the first stop.
    await ctx.route_repo.update_status(src.id, TENANT_A, RouteStatus.IN_PROGRESS)
    await ctx.stop_repo.update_status(stops[0].id, TENANT_A, RouteStopStatus.COMPLETE)

    result = await ctx.svc.reassign_route(TENANT_A, USER_A, src.id, target_vehicle_id=vb.id)

    assert result["moved_count"] == 1
    # Source had a completed stop and was in-progress → completes (not cancelled).
    assert RouteStatus(result["source_route"].status) == RouteStatus.COMPLETE
    target_stops = await ctx.stop_repo.get_for_route(TENANT_A, result["target_route"].id)
    assert [s.job_id for s in target_stops] == [j2.id]


async def test_reassign_appends_to_existing_target_route(ctx):
    va = await _vehicle_with_crew(ctx, plate="A")
    vb = await _vehicle_with_crew(ctx, plate="B")
    j1 = await _job(ctx, title="src")
    jb = await _job(ctx, title="already-on-b")
    src, _ = await _committed_route(ctx, va, [j1])
    await _committed_route(ctx, vb, [jb])

    result = await ctx.svc.reassign_route(TENANT_A, USER_A, src.id, target_vehicle_id=vb.id)

    target_stops = await ctx.stop_repo.get_for_route(TENANT_A, result["target_route"].id)
    assert [s.job_id for s in target_stops] == [jb.id, j1.id]
    assert [s.sequence_index for s in target_stops] == [0, 1]


async def test_reassign_target_without_crew_409(ctx):
    va = await _vehicle_with_crew(ctx, plate="A")
    vb = await ctx.vehicle_repo.create(
        TENANT_A, license_plate="NOCREW", nickname="NoCrew", make="F", model="T", year=2022
    )
    j1 = await _job(ctx)
    src, _ = await _committed_route(ctx, va, [j1])

    with pytest.raises(RouteCommitConflictError) as exc:
        await ctx.svc.reassign_route(TENANT_A, USER_A, src.id, target_vehicle_id=vb.id)
    assert exc.value.reason == "no_crew"


async def test_reassign_same_vehicle_409(ctx):
    va = await _vehicle_with_crew(ctx, plate="A")
    j1 = await _job(ctx)
    src, _ = await _committed_route(ctx, va, [j1])
    with pytest.raises(RouteCommitConflictError) as exc:
        await ctx.svc.reassign_route(TENANT_A, USER_A, src.id, target_vehicle_id=va.id)
    assert exc.value.reason == "same_vehicle"


async def test_reassign_terminal_source_409(ctx):
    va = await _vehicle_with_crew(ctx, plate="A")
    vb = await _vehicle_with_crew(ctx, plate="B")
    j1 = await _job(ctx)
    src, _ = await _committed_route(ctx, va, [j1])
    await ctx.route_repo.update_status(src.id, TENANT_A, RouteStatus.CANCELLED)
    with pytest.raises(RouteCommitConflictError):
        await ctx.svc.reassign_route(TENANT_A, USER_A, src.id, target_vehicle_id=vb.id)


async def test_reassign_nothing_pending_409(ctx):
    va = await _vehicle_with_crew(ctx, plate="A")
    vb = await _vehicle_with_crew(ctx, plate="B")
    j1 = await _job(ctx)
    src, stops = await _committed_route(ctx, va, [j1])
    await ctx.route_repo.update_status(src.id, TENANT_A, RouteStatus.IN_PROGRESS)
    await ctx.stop_repo.update_status(stops[0].id, TENANT_A, RouteStopStatus.COMPLETE)
    with pytest.raises(RouteCommitConflictError) as exc:
        await ctx.svc.reassign_route(TENANT_A, USER_A, src.id, target_vehicle_id=vb.id)
    assert exc.value.reason == "nothing_to_reassign"


async def test_reassign_unknown_route_404(ctx):
    await _vehicle_with_crew(ctx, plate="B")
    with pytest.raises(RouteNotFoundError):
        await ctx.svc.reassign_route(TENANT_A, USER_A, uuid4(), target_vehicle_id=uuid4())


# ---------------------------------------------------------------------------
# add_emergency_job
# ---------------------------------------------------------------------------


def _window():
    start = datetime.combine(WORK_DATE, time(9, 0), tzinfo=UTC)
    return start, start + timedelta(hours=8)


async def test_emergency_auto_picks_vehicle_and_creates_route(ctx):
    await _vehicle_with_crew(ctx, plate="A")
    job = await _job(ctx, title="Emergency leak", geocoded=True)
    start, end = _window()

    route = await ctx.svc.add_emergency_job(
        TENANT_A, USER_A, job.id, window_start=start, window_end=end
    )

    assert route.option_kind_applied == "emergency"
    stops = await ctx.stop_repo.get_for_route(TENANT_A, route.id)
    assert [s.job_id for s in stops] == [job.id]
    refreshed = await ctx.job_repo.get_by_id(job.id, TENANT_A)
    assert refreshed.status == "scheduled"
    assert refreshed.assigned_vehicle_id == route.vehicle_id
    assert any(e.event_type == "job.emergency_dispatched" for e in ctx.audit.events)


async def test_emergency_jumps_the_pending_queue(ctx):
    va = await _vehicle_with_crew(ctx, plate="A")
    existing = await _job(ctx, title="routine")
    route, _ = await _committed_route(ctx, va, [existing])
    emergency = await _job(ctx, title="emergency")
    start, end = _window()

    await ctx.svc.add_emergency_job(
        TENANT_A,
        USER_A,
        emergency.id,
        window_start=start,
        window_end=end,
        target_vehicle_id=va.id,
    )

    stops = await ctx.stop_repo.get_for_route(TENANT_A, route.id)
    assert [s.job_id for s in stops] == [emergency.id, existing.id]
    assert [s.sequence_index for s in stops] == [0, 1]


async def test_emergency_preserves_completed_stop_and_inserts_after_it(ctx):
    va = await _vehicle_with_crew(ctx, plate="A")
    done = await _job(ctx, title="done")
    pending = await _job(ctx, title="pending")
    route, stops = await _committed_route(ctx, va, [done, pending])
    await ctx.route_repo.update_status(route.id, TENANT_A, RouteStatus.IN_PROGRESS)
    await ctx.stop_repo.update_status(stops[0].id, TENANT_A, RouteStopStatus.COMPLETE)
    emergency = await _job(ctx, title="emergency")
    start, end = _window()

    await ctx.svc.add_emergency_job(
        TENANT_A,
        USER_A,
        emergency.id,
        window_start=start,
        window_end=end,
        target_vehicle_id=va.id,
    )

    result = await ctx.stop_repo.get_for_route(TENANT_A, route.id)
    # Completed stop stays first; emergency jumps ahead of the remaining pending one.
    assert [s.job_id for s in result] == [done.id, emergency.id, pending.id]
    completed = next(s for s in result if s.job_id == done.id)
    assert RouteStopStatus(completed.status) == RouteStopStatus.COMPLETE


async def test_emergency_no_vehicle_available_409(ctx):
    # A geocoded job but no active vehicles → schedule service returns no options.
    job = await _job(ctx, title="nobody", geocoded=True)
    start, end = _window()
    with pytest.raises(RouteCommitConflictError) as exc:
        await ctx.svc.add_emergency_job(
            TENANT_A, USER_A, job.id, window_start=start, window_end=end
        )
    assert exc.value.reason == "no_options"


async def test_emergency_job_not_pending_409(ctx):
    va = await _vehicle_with_crew(ctx, plate="A")
    job = await _job(ctx)
    await ctx.job_repo.update_fields(job.id, TENANT_A, status="complete")
    start, end = _window()
    with pytest.raises(RouteCommitConflictError) as exc:
        await ctx.svc.add_emergency_job(
            TENANT_A,
            USER_A,
            job.id,
            window_start=start,
            window_end=end,
            target_vehicle_id=va.id,
        )
    assert exc.value.reason == "job_not_pending"


async def test_emergency_cross_tenant_vehicle_not_found(ctx):
    vb = await _vehicle_with_crew(ctx, tenant_id=TENANT_B, plate="B")
    job = await _job(ctx, title="a")
    start, end = _window()
    with pytest.raises(VehicleNotFoundError):
        await ctx.svc.add_emergency_job(
            TENANT_A,
            USER_A,
            job.id,
            window_start=start,
            window_end=end,
            target_vehicle_id=vb.id,
        )
