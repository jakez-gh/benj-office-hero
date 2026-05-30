"""RouteStopRepository — protocol, SQLAlchemy impl, and in-memory impl (Slice 14)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from office_hero.models.route import RouteStop


@dataclass
class StopRow:
    job_id: UUID
    sequence_index: int
    planned_eta: datetime | None = None
    planned_distance_from_prev_m: int = 0
    planned_duration_from_prev_s: int = 0


class RouteStopRepositoryProtocol(Protocol):
    async def bulk_insert(
        self, tenant_id: UUID, route_id: UUID, stops: list[StopRow]
    ) -> list[RouteStop]: ...

    async def delete_for_route(self, tenant_id: UUID, route_id: UUID) -> int: ...

    async def replace_all(
        self, tenant_id: UUID, route_id: UUID, stops: list[StopRow]
    ) -> list[RouteStop]: ...

    async def update_status(
        self,
        stop_id: UUID,
        tenant_id: UUID,
        new_status: str,
        *,
        arrived_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> RouteStop: ...

    async def get_for_route(self, tenant_id: UUID, route_id: UUID) -> list[RouteStop]: ...


class RouteStopRepository:
    """SQLAlchemy-backed concrete repository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def bulk_insert(
        self, tenant_id: UUID, route_id: UUID, stops: list[StopRow]
    ) -> list[RouteStop]:
        rows = [
            RouteStop(
                tenant_id=tenant_id,
                route_id=route_id,
                job_id=s.job_id,
                sequence_index=s.sequence_index,
                planned_eta=s.planned_eta,
                planned_distance_from_prev_m=s.planned_distance_from_prev_m,
                planned_duration_from_prev_s=s.planned_duration_from_prev_s,
            )
            for s in stops
        ]
        self.session.add_all(rows)
        await self.session.flush()
        for r in rows:
            await self.session.refresh(r)
        return rows

    async def delete_for_route(self, tenant_id: UUID, route_id: UUID) -> int:
        existing = await self.get_for_route(tenant_id, route_id)
        for row in existing:
            await self.session.delete(row)
        await self.session.flush()
        return len(existing)

    async def replace_all(
        self, tenant_id: UUID, route_id: UUID, stops: list[StopRow]
    ) -> list[RouteStop]:
        await self.delete_for_route(tenant_id, route_id)
        return await self.bulk_insert(tenant_id, route_id, stops)

    async def update_status(
        self,
        stop_id: UUID,
        tenant_id: UUID,
        new_status: str,
        *,
        arrived_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> RouteStop:
        stmt = select(RouteStop).where(RouteStop.id == stop_id, RouteStop.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        stop = result.scalar_one_or_none()
        if stop is None:
            from office_hero.core.exceptions import RouteNotFoundError

            raise RouteNotFoundError(f"RouteStop {stop_id} not found")
        stop.status = new_status
        stop.updated_at = datetime.now(UTC)
        if arrived_at is not None:
            stop.actual_arrived_at = arrived_at
        if completed_at is not None:
            stop.actual_completed_at = completed_at
        await self.session.flush()
        return stop

    async def get_for_route(self, tenant_id: UUID, route_id: UUID) -> list[RouteStop]:
        stmt = (
            select(RouteStop)
            .where(RouteStop.tenant_id == tenant_id, RouteStop.route_id == route_id)
            .order_by(RouteStop.sequence_index)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class InMemoryRouteStopRepository:
    """In-memory implementation for tests."""

    def __init__(self) -> None:
        self._rows: dict[UUID, RouteStop] = {}

    async def bulk_insert(
        self, tenant_id: UUID, route_id: UUID, stops: list[StopRow]
    ) -> list[RouteStop]:
        now = datetime.now(UTC)
        result = []
        for s in stops:
            row = RouteStop(
                id=uuid4(),
                tenant_id=tenant_id,
                route_id=route_id,
                job_id=s.job_id,
                sequence_index=s.sequence_index,
                status="pending",
                planned_eta=s.planned_eta,
                planned_distance_from_prev_m=s.planned_distance_from_prev_m,
                planned_duration_from_prev_s=s.planned_duration_from_prev_s,
                created_at=now,
                updated_at=now,
            )
            self._rows[row.id] = row
            result.append(row)
        return result

    async def delete_for_route(self, tenant_id: UUID, route_id: UUID) -> int:
        to_del = [
            k for k, r in self._rows.items() if r.tenant_id == tenant_id and r.route_id == route_id
        ]
        for k in to_del:
            del self._rows[k]
        return len(to_del)

    async def replace_all(
        self, tenant_id: UUID, route_id: UUID, stops: list[StopRow]
    ) -> list[RouteStop]:
        await self.delete_for_route(tenant_id, route_id)
        return await self.bulk_insert(tenant_id, route_id, stops)

    async def update_status(
        self,
        stop_id: UUID,
        tenant_id: UUID,
        new_status: str,
        *,
        arrived_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> RouteStop:
        from office_hero.core.exceptions import RouteNotFoundError

        stop = self._rows.get(stop_id)
        if stop is None or stop.tenant_id != tenant_id:
            raise RouteNotFoundError(f"RouteStop {stop_id} not found")
        stop.status = new_status
        stop.updated_at = datetime.now(UTC)
        if arrived_at is not None:
            stop.actual_arrived_at = arrived_at
        if completed_at is not None:
            stop.actual_completed_at = completed_at
        return stop

    async def get_for_route(self, tenant_id: UUID, route_id: UUID) -> list[RouteStop]:
        rows = [
            r for r in self._rows.values() if r.tenant_id == tenant_id and r.route_id == route_id
        ]
        return sorted(rows, key=lambda r: r.sequence_index)
