"""Repository for vehicle location tracking."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from office_hero.models.vehicle_location import VehicleLocation


class VehicleLocationRepositoryProtocol(Protocol):
    """Protocol for vehicle location data access."""

    async def create(
        self, tenant_id: UUID, location: VehicleLocation
    ) -> VehicleLocation:
        """Create a new location record."""
        ...

    async def get_latest(
        self, tenant_id: UUID, vehicle_id: UUID
    ) -> VehicleLocation | None:
        """Get the most recent location for a vehicle."""
        ...

    async def list_since(
        self,
        tenant_id: UUID,
        vehicle_id: UUID,
        since: datetime,
    ) -> list[VehicleLocation]:
        """Get all locations since a timestamp (for analytics)."""
        ...


class SQLAlchemyVehicleLocationRepository:
    """SQLAlchemy implementation of vehicle location repository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, tenant_id: UUID, location: VehicleLocation
    ) -> VehicleLocation:
        """Create a new location record."""
        location.tenant_id = tenant_id
        self.session.add(location)
        await self.session.flush()
        return location

    async def get_latest(
        self, tenant_id: UUID, vehicle_id: UUID
    ) -> VehicleLocation | None:
        """Get the most recent location for a vehicle."""
        stmt = (
            select(VehicleLocation)
            .where(
                and_(
                    VehicleLocation.tenant_id == tenant_id,
                    VehicleLocation.vehicle_id == vehicle_id,
                )
            )
            .order_by(desc(VehicleLocation.recorded_at))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_since(
        self,
        tenant_id: UUID,
        vehicle_id: UUID,
        since: datetime,
    ) -> list[VehicleLocation]:
        """Get all locations since a timestamp."""
        stmt = (
            select(VehicleLocation)
            .where(
                and_(
                    VehicleLocation.tenant_id == tenant_id,
                    VehicleLocation.vehicle_id == vehicle_id,
                    VehicleLocation.recorded_at >= since,
                )
            )
            .order_by(VehicleLocation.recorded_at)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()


class InMemoryVehicleLocationRepository:
    """In-memory implementation for testing."""

    def __init__(self):
        self._locations: dict[tuple[UUID, UUID], list[VehicleLocation]] = {}

    async def create(
        self, tenant_id: UUID, location: VehicleLocation
    ) -> VehicleLocation:
        """Create a new location record."""
        location.tenant_id = tenant_id
        key = (tenant_id, location.vehicle_id)
        if key not in self._locations:
            self._locations[key] = []
        self._locations[key].append(location)
        self._locations[key].sort(key=lambda l: l.recorded_at, reverse=True)
        return location

    async def get_latest(
        self, tenant_id: UUID, vehicle_id: UUID
    ) -> VehicleLocation | None:
        """Get the most recent location for a vehicle."""
        key = (tenant_id, vehicle_id)
        if key not in self._locations or not self._locations[key]:
            return None
        return self._locations[key][0]

    async def list_since(
        self,
        tenant_id: UUID,
        vehicle_id: UUID,
        since: datetime,
    ) -> list[VehicleLocation]:
        """Get all locations since a timestamp."""
        key = (tenant_id, vehicle_id)
        if key not in self._locations:
            return []
        return [l for l in self._locations[key] if l.recorded_at >= since]
