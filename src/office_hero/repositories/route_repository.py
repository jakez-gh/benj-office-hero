"""RouteRepository — protocol, SQLAlchemy impl, and in-memory impl (Slice 14)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from office_hero.models.route import Route


@dataclass
class RouteCreateRow:
    vehicle_id: UUID
    vehicle_crew_id: UUID
    work_date: date
    committed_by_user_id: UUID | None
    option_kind_applied: str | None
    notes: str | None
    total_distance_m: int
    total_duration_s: int


class RouteRepositoryProtocol(Protocol):
    async def get_by_id(self, route_id: UUID, tenant_id: UUID) -> Route | None: ...

    async def get_for_vehicle_date(
        self, tenant_id: UUID, vehicle_id: UUID, work_date: date
    ) -> Route | None: ...

    async def list_for_date(
        self,
        tenant_id: UUID,
        work_date: date,
        *,
        vehicle_id: UUID | None = None,
        status: list[str] | None = None,
    ) -> list[Route]: ...

    async def create(self, tenant_id: UUID, *, row: RouteCreateRow) -> Route: ...

    async def update_status(
        self,
        route_id: UUID,
        tenant_id: UUID,
        new_status: str,
        *,
        committed_at: datetime | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        cancelled_at: datetime | None = None,
        cancel_reason: str | None = None,
    ) -> Route: ...

    async def update_totals(
        self,
        route_id: UUID,
        tenant_id: UUID,
        *,
        total_distance_m: int,
        total_duration_s: int,
    ) -> Route: ...


class RouteRepository:
    """SQLAlchemy-backed concrete repository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, route_id: UUID, tenant_id: UUID) -> Route | None:
        stmt = select(Route).where(Route.id == route_id, Route.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_for_vehicle_date(
        self, tenant_id: UUID, vehicle_id: UUID, work_date: date
    ) -> Route | None:
        stmt = select(Route).where(
            Route.tenant_id == tenant_id,
            Route.vehicle_id == vehicle_id,
            Route.work_date == work_date,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_date(
        self,
        tenant_id: UUID,
        work_date: date,
        *,
        vehicle_id: UUID | None = None,
        status: list[str] | None = None,
    ) -> list[Route]:
        stmt = select(Route).where(Route.tenant_id == tenant_id, Route.work_date == work_date)
        if vehicle_id is not None:
            stmt = stmt.where(Route.vehicle_id == vehicle_id)
        if status:
            stmt = stmt.where(Route.status.in_(status))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, tenant_id: UUID, *, row: RouteCreateRow) -> Route:
        now = datetime.now(UTC)
        route = Route(
            tenant_id=tenant_id,
            vehicle_id=row.vehicle_id,
            vehicle_crew_id=row.vehicle_crew_id,
            work_date=row.work_date,
            status="committed",
            committed_at=now,
            committed_by_user_id=row.committed_by_user_id,
            option_kind_applied=row.option_kind_applied,
            notes=row.notes,
            total_distance_m=row.total_distance_m,
            total_duration_s=row.total_duration_s,
        )
        self.session.add(route)
        await self.session.flush()
        await self.session.refresh(route)
        return route

    async def update_status(
        self,
        route_id: UUID,
        tenant_id: UUID,
        new_status: str,
        *,
        committed_at: datetime | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        cancelled_at: datetime | None = None,
        cancel_reason: str | None = None,
    ) -> Route:
        route = await self.get_by_id(route_id, tenant_id)
        if route is None:
            from office_hero.core.exceptions import RouteNotFoundError

            raise RouteNotFoundError(f"Route {route_id} not found")
        route.status = new_status
        if committed_at is not None:
            route.committed_at = committed_at
        if started_at is not None:
            route.started_at = started_at
        if completed_at is not None:
            route.completed_at = completed_at
        if cancelled_at is not None:
            route.cancelled_at = cancelled_at
        if cancel_reason is not None:
            route.cancel_reason = cancel_reason
        route.updated_at = datetime.now(UTC)
        await self.session.flush()
        return route

    async def update_totals(
        self,
        route_id: UUID,
        tenant_id: UUID,
        *,
        total_distance_m: int,
        total_duration_s: int,
    ) -> Route:
        route = await self.get_by_id(route_id, tenant_id)
        if route is None:
            from office_hero.core.exceptions import RouteNotFoundError

            raise RouteNotFoundError(f"Route {route_id} not found")
        route.total_distance_m = total_distance_m
        route.total_duration_s = total_duration_s
        route.updated_at = datetime.now(UTC)
        await self.session.flush()
        return route


class InMemoryRouteRepository:
    """In-memory implementation for tests."""

    def __init__(self) -> None:
        self._rows: dict[UUID, Route] = {}

    def _clone(self, r: Route) -> Route:
        return r

    async def get_by_id(self, route_id: UUID, tenant_id: UUID) -> Route | None:
        r = self._rows.get(route_id)
        return r if (r is not None and r.tenant_id == tenant_id) else None

    async def get_for_vehicle_date(
        self, tenant_id: UUID, vehicle_id: UUID, work_date: date
    ) -> Route | None:
        for r in self._rows.values():
            if r.tenant_id == tenant_id and r.vehicle_id == vehicle_id and r.work_date == work_date:
                return r
        return None

    async def list_for_date(
        self,
        tenant_id: UUID,
        work_date: date,
        *,
        vehicle_id: UUID | None = None,
        status: list[str] | None = None,
    ) -> list[Route]:
        rows = [
            r for r in self._rows.values() if r.tenant_id == tenant_id and r.work_date == work_date
        ]
        if vehicle_id is not None:
            rows = [r for r in rows if r.vehicle_id == vehicle_id]
        if status:
            rows = [r for r in rows if r.status in status]
        return rows

    async def create(self, tenant_id: UUID, *, row: RouteCreateRow) -> Route:
        now = datetime.now(UTC)
        route = Route(
            id=uuid4(),
            tenant_id=tenant_id,
            vehicle_id=row.vehicle_id,
            vehicle_crew_id=row.vehicle_crew_id,
            work_date=row.work_date,
            status="committed",
            committed_at=now,
            committed_by_user_id=row.committed_by_user_id,
            option_kind_applied=row.option_kind_applied,
            notes=row.notes,
            total_distance_m=row.total_distance_m,
            total_duration_s=row.total_duration_s,
            created_at=now,
            updated_at=now,
        )
        route.stops = []
        self._rows[route.id] = route
        return route

    async def update_status(
        self,
        route_id: UUID,
        tenant_id: UUID,
        new_status: str,
        *,
        committed_at: datetime | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        cancelled_at: datetime | None = None,
        cancel_reason: str | None = None,
    ) -> Route:
        from office_hero.core.exceptions import RouteNotFoundError

        route = await self.get_by_id(route_id, tenant_id)
        if route is None:
            raise RouteNotFoundError(f"Route {route_id} not found")
        route.status = new_status
        route.updated_at = datetime.now(UTC)
        if committed_at is not None:
            route.committed_at = committed_at
        if started_at is not None:
            route.started_at = started_at
        if completed_at is not None:
            route.completed_at = completed_at
        if cancelled_at is not None:
            route.cancelled_at = cancelled_at
        if cancel_reason is not None:
            route.cancel_reason = cancel_reason
        return route

    async def update_totals(
        self,
        route_id: UUID,
        tenant_id: UUID,
        *,
        total_distance_m: int,
        total_duration_s: int,
    ) -> Route:
        from office_hero.core.exceptions import RouteNotFoundError

        route = await self.get_by_id(route_id, tenant_id)
        if route is None:
            raise RouteNotFoundError(f"Route {route_id} not found")
        route.total_distance_m = total_distance_m
        route.total_duration_s = total_duration_s
        route.updated_at = datetime.now(UTC)
        return route
