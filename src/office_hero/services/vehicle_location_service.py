"""VehicleLocationService — records GPS positions posted by Technicians."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from office_hero.core.exceptions import VehicleNotFoundError
from office_hero.core.logging import get_logger
from office_hero.models.vehicle_location import VehicleLocation
from office_hero.repositories.vehicle_location_repository import (
    VehicleLocationRepositoryProtocol,
)
from office_hero.repositories.vehicle_repository import VehicleRepositoryProtocol

log = get_logger(__name__)


class VehicleLocationService:
    def __init__(
        self,
        location_repo: VehicleLocationRepositoryProtocol,
        vehicle_repo: VehicleRepositoryProtocol,
    ) -> None:
        self._location_repo = location_repo
        self._vehicle_repo = vehicle_repo

    async def record(
        self,
        tenant_id: UUID,
        vehicle_id: UUID,
        *,
        lat: Decimal,
        lng: Decimal,
        accuracy_m: Decimal | None,
        recorded_at: datetime,
    ) -> VehicleLocation:
        """Persist a GPS fix for a vehicle.

        Raises VehicleNotFoundError if the vehicle doesn't exist in the tenant.
        """
        vehicle = await self._vehicle_repo.get_by_id(vehicle_id, tenant_id)
        if vehicle is None:
            raise VehicleNotFoundError(f"Vehicle {vehicle_id} not found")

        fix = await self._location_repo.create(
            tenant_id,
            vehicle_id,
            lat=lat,
            lng=lng,
            accuracy_m=accuracy_m,
            recorded_at=recorded_at,
        )
        log.info(
            "vehicle.location.recorded",
            vehicle_id=str(vehicle_id),
            lat=str(lat),
            lng=str(lng),
            recorded_at=recorded_at.isoformat(),
            tenant_id=str(tenant_id),
        )
        return fix

    async def get_latest(
        self, tenant_id: UUID, vehicle_id: UUID
    ) -> VehicleLocation | None:
        """Return the most recent GPS fix for a vehicle, or None."""
        return await self._location_repo.get_latest(tenant_id, vehicle_id)
