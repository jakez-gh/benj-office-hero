"""VehicleLocation repository — protocol, SQLAlchemy impl, and in-memory impl."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from office_hero.models.vehicle_location import VehicleLocation


class VehicleLocationRepositoryProtocol(Protocol):
    async def create(
        self,
        tenant_id: UUID,
        vehicle_id: UUID,
        *,
        lat: Decimal,
        lng: Decimal,
        accuracy_m: Decimal | None,
        recorded_at: datetime,
    ) -> VehicleLocation: ...

    async def get_latest(self, tenant_id: UUID, vehicle_id: UUID) -> VehicleLocation | None: ...


class VehicleLocationRepository:
    """SQLAlchemy-backed concrete repository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        tenant_id: UUID,
        vehicle_id: UUID,
        *,
        lat: Decimal,
        lng: Decimal,
        accuracy_m: Decimal | None,
        recorded_at: datetime,
    ) -> VehicleLocation:
        row = VehicleLocation(
            tenant_id=tenant_id,
            vehicle_id=vehicle_id,
            lat=lat,
            lng=lng,
            accuracy_m=accuracy_m,
            recorded_at=recorded_at,
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def get_latest(self, tenant_id: UUID, vehicle_id: UUID) -> VehicleLocation | None:
        stmt = (
            select(VehicleLocation)
            .where(
                VehicleLocation.tenant_id == tenant_id,
                VehicleLocation.vehicle_id == vehicle_id,
            )
            .order_by(VehicleLocation.recorded_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class InMemoryVehicleLocationRepository:
    """In-memory implementation for tests."""

    def __init__(self) -> None:
        self._rows: list[VehicleLocation] = []

    async def create(
        self,
        tenant_id: UUID,
        vehicle_id: UUID,
        *,
        lat: Decimal,
        lng: Decimal,
        accuracy_m: Decimal | None,
        recorded_at: datetime,
    ) -> VehicleLocation:
        row = VehicleLocation(
            id=uuid4(),
            tenant_id=tenant_id,
            vehicle_id=vehicle_id,
            lat=lat,
            lng=lng,
            accuracy_m=accuracy_m,
            recorded_at=recorded_at,
            created_at=datetime.now(UTC),
        )
        self._rows.append(row)
        return row

    async def get_latest(self, tenant_id: UUID, vehicle_id: UUID) -> VehicleLocation | None:
        matches = [r for r in self._rows if r.tenant_id == tenant_id and r.vehicle_id == vehicle_id]
        if not matches:
            return None
        return max(matches, key=lambda r: r.recorded_at)
