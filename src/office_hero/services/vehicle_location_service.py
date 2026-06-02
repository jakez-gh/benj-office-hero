"""Service for vehicle location tracking (Slice 15)."""

from __future__ import annotations

from datetime import datetime, UTC
from uuid import UUID

from office_hero.models.vehicle_location import VehicleLocation
from office_hero.repositories.vehicle_location_repository import VehicleLocationRepositoryProtocol


class VehicleLocationService:
    """Service for recording and querying vehicle GPS locations."""

    def __init__(self, location_repo: VehicleLocationRepositoryProtocol):
        self._location_repo = location_repo

    async def record_location(
        self,
        tenant_id: UUID,
        vehicle_id: UUID,
        latitude: float,
        longitude: float,
        accuracy_meters: int | None = None,
        recorded_at: datetime | None = None,
    ) -> VehicleLocation:
        """Record a vehicle's current GPS location."""
        recorded_at = recorded_at or datetime.now(UTC)

        location = VehicleLocation(
            id=UUID(int=0),  # DB generates
            tenant_id=tenant_id,
            vehicle_id=vehicle_id,
            latitude=latitude,
            longitude=longitude,
            accuracy_meters=accuracy_meters,
            recorded_at=recorded_at,
            created_at=datetime.now(UTC),
        )

        return await self._location_repo.create(tenant_id, location)

    async def get_latest_location(
        self, tenant_id: UUID, vehicle_id: UUID
    ) -> VehicleLocation | None:
        """Get the most recent location for a vehicle."""
        return await self._location_repo.get_latest(tenant_id, vehicle_id)

    async def get_location_history(
        self,
        tenant_id: UUID,
        vehicle_id: UUID,
        since: datetime,
    ) -> list[VehicleLocation]:
        """Get all locations since a timestamp (for analytics/replay)."""
        return await self._location_repo.list_since(tenant_id, vehicle_id, since)
