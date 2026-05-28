"""Vehicle repository — protocol, SQLAlchemy impl, and in-memory mock.

The protocol is what the service layer depends on (ADR 058). The concrete
SQLAlchemy implementation is the production binding. The in-memory mock is
used by unit tests so the service layer can be exercised without a database.
All implementations enforce tenant scoping defensively (ADR 053
defence-in-depth on top of RLS).
"""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, date, datetime
from typing import Any, Protocol, runtime_checkable
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from office_hero.core.exceptions import VehicleNotFoundError
from office_hero.models.vehicle import Vehicle
from office_hero.models.vehicle_crew import VehicleCrew


@runtime_checkable
class VehicleRepositoryProtocol(Protocol):
    """Repository contract for :class:`Vehicle` persistence."""

    async def create(
        self,
        tenant_id: UUID,
        *,
        license_plate: str,
        nickname: str | None = None,
        make: str | None = None,
        model: str | None = None,
        year: int | None = None,
        vin: str | None = None,
        gps_device_id: str | None = None,
        capacity_kg: int | None = None,
        home_base_lat: float | None = None,
        home_base_lng: float | None = None,
        notes: str | None = None,
    ) -> Vehicle: ...

    async def get_by_id(self, vehicle_id: UUID, tenant_id: UUID) -> Vehicle | None: ...

    async def list(
        self,
        tenant_id: UUID,
        *,
        archived: bool = False,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Vehicle], int]: ...

    async def update(self, vehicle_id: UUID, tenant_id: UUID, **patch: Any) -> Vehicle: ...

    async def archive(self, vehicle_id: UUID, tenant_id: UUID) -> Vehicle: ...

    async def restore(self, vehicle_id: UUID, tenant_id: UUID) -> Vehicle: ...

    async def list_active_for_date(self, tenant_id: UUID, work_date: date) -> list[Vehicle]: ...


class VehicleRepository:
    """SQLAlchemy-backed concrete :class:`Vehicle` repository (ADR 058)."""

    def __init__(self, session: AsyncSession):
        """Bind to an async SQLAlchemy session."""
        self.session = session

    async def create(
        self,
        tenant_id: UUID,
        *,
        license_plate: str,
        nickname: str | None = None,
        make: str | None = None,
        model: str | None = None,
        year: int | None = None,
        vin: str | None = None,
        gps_device_id: str | None = None,
        capacity_kg: int | None = None,
        home_base_lat: float | None = None,
        home_base_lng: float | None = None,
        notes: str | None = None,
    ) -> Vehicle:
        """Insert and flush a new :class:`Vehicle`."""
        v = Vehicle(
            tenant_id=tenant_id,
            license_plate=license_plate,
            nickname=nickname,
            make=make,
            model=model,
            year=year,
            vin=vin,
            gps_device_id=gps_device_id,
            capacity_kg=capacity_kg,
            home_base_lat=home_base_lat,
            home_base_lng=home_base_lng,
            notes=notes,
            archived=False,
        )
        self.session.add(v)
        await self.session.flush()
        return v

    async def get_by_id(self, vehicle_id: UUID, tenant_id: UUID) -> Vehicle | None:
        """Fetch a vehicle if it exists in ``tenant_id`` (defence-in-depth)."""
        stmt = select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list(
        self,
        tenant_id: UUID,
        *,
        archived: bool = False,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Vehicle], int]:
        """Return ``(rows, total)`` for a tenant, optionally filtered."""
        where_clauses = [Vehicle.tenant_id == tenant_id, Vehicle.archived.is_(archived)]
        if search:
            pattern = f"%{search}%"
            where_clauses.append(
                or_(
                    Vehicle.license_plate.ilike(pattern),
                    Vehicle.nickname.ilike(pattern),
                    Vehicle.vin.ilike(pattern),
                )
            )

        count_stmt = select(func.count(Vehicle.id)).where(*where_clauses)
        total = int((await self.session.execute(count_stmt)).scalar_one())

        rows_stmt = (
            select(Vehicle)
            .where(*where_clauses)
            .order_by(Vehicle.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = list((await self.session.execute(rows_stmt)).scalars().all())
        return rows, total

    async def update(self, vehicle_id: UUID, tenant_id: UUID, **patch: Any) -> Vehicle:
        """Apply a partial update; raises :class:`VehicleNotFoundError` if absent."""
        v = await self.get_by_id(vehicle_id, tenant_id)
        if v is None:
            raise VehicleNotFoundError(f"Vehicle {vehicle_id} not found")
        for key, value in patch.items():
            setattr(v, key, value)
        await self.session.flush()
        return v

    async def archive(self, vehicle_id: UUID, tenant_id: UUID) -> Vehicle:
        """Mark a vehicle archived (soft delete)."""
        return await self.update(vehicle_id, tenant_id, archived=True)

    async def restore(self, vehicle_id: UUID, tenant_id: UUID) -> Vehicle:
        """Clear the archived flag."""
        return await self.update(vehicle_id, tenant_id, archived=False)

    async def list_active_for_date(self, tenant_id: UUID, work_date: date) -> list[Vehicle]:
        """Return non-archived vehicles that have a crew for ``work_date``.

        Used by the routing engine (Slice 14) to enumerate dispatch candidates.
        """
        stmt = (
            select(Vehicle)
            .join(VehicleCrew, VehicleCrew.vehicle_id == Vehicle.id)
            .where(
                Vehicle.tenant_id == tenant_id,
                Vehicle.archived.is_(False),
                VehicleCrew.tenant_id == tenant_id,
                VehicleCrew.work_date == work_date,
            )
            .distinct()
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class InMemoryVehicleRepository:
    """In-memory mock implementing :class:`VehicleRepositoryProtocol`.

    Used by unit tests so the service layer can be exercised without a DB.
    """

    def __init__(self) -> None:
        self._rows: dict[UUID, dict[str, Any]] = {}
        # Reference to InMemoryVehicleCrewRepository for list_active_for_date.
        self._crew_repo: Any = None

    def _row_to_vehicle(self, row: dict[str, Any]) -> Vehicle:
        v = Vehicle(
            id=row["id"],
            tenant_id=row["tenant_id"],
            license_plate=row["license_plate"],
            nickname=row.get("nickname"),
            make=row.get("make"),
            model=row.get("model"),
            year=row.get("year"),
            vin=row.get("vin"),
            gps_device_id=row.get("gps_device_id"),
            capacity_kg=row.get("capacity_kg"),
            home_base_lat=row.get("home_base_lat"),
            home_base_lng=row.get("home_base_lng"),
            notes=row.get("notes"),
            archived=row.get("archived", False),
        )
        v.created_at = row["created_at"]
        v.updated_at = row["updated_at"]
        return v

    async def create(
        self,
        tenant_id: UUID,
        *,
        license_plate: str,
        nickname: str | None = None,
        make: str | None = None,
        model: str | None = None,
        year: int | None = None,
        vin: str | None = None,
        gps_device_id: str | None = None,
        capacity_kg: int | None = None,
        home_base_lat: float | None = None,
        home_base_lng: float | None = None,
        notes: str | None = None,
    ) -> Vehicle:
        """Insert and return a freshly minted :class:`Vehicle`.

        Raises :class:`~office_hero.core.exceptions.CrewAssignmentConflictError`-equivalent
        on duplicate active license plate — mirrors the partial unique index on the DB.
        """
        # Check duplicate active license plate within tenant
        for row in self._rows.values():
            if (
                row["tenant_id"] == tenant_id
                and row["license_plate"] == license_plate
                and not row.get("archived", False)
            ):

                raise ValueError(
                    f"Vehicle with license plate {license_plate!r} already exists in tenant"
                )
        vid = uuid4()
        now = datetime.now(UTC)
        self._rows[vid] = {
            "id": vid,
            "tenant_id": tenant_id,
            "license_plate": license_plate,
            "nickname": nickname,
            "make": make,
            "model": model,
            "year": year,
            "vin": vin,
            "gps_device_id": gps_device_id,
            "capacity_kg": capacity_kg,
            "home_base_lat": home_base_lat,
            "home_base_lng": home_base_lng,
            "notes": notes,
            "archived": False,
            "created_at": now,
            "updated_at": now,
        }
        return self._row_to_vehicle(self._rows[vid])

    async def get_by_id(self, vehicle_id: UUID, tenant_id: UUID) -> Vehicle | None:
        """Return the vehicle if it exists in this tenant's scope."""
        row = self._rows.get(vehicle_id)
        if row is None or row["tenant_id"] != tenant_id:
            return None
        return self._row_to_vehicle(row)

    async def list(
        self,
        tenant_id: UUID,
        *,
        archived: bool = False,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Vehicle], int]:
        """Return ``(rows, total)`` matching the filter."""
        needle = search.lower() if search else None
        rows = [
            r
            for r in self._rows.values()
            if r["tenant_id"] == tenant_id and r["archived"] == archived
        ]
        if needle is not None:
            rows = [
                r
                for r in rows
                if (
                    needle in (r["license_plate"] or "").lower()
                    or needle in ((r.get("nickname") or "").lower())
                    or needle in ((r.get("vin") or "").lower())
                )
            ]
        rows.sort(key=lambda r: r["created_at"], reverse=True)
        total = len(rows)
        page = rows[offset : offset + limit]
        return [self._row_to_vehicle(r) for r in page], total

    async def update(self, vehicle_id: UUID, tenant_id: UUID, **patch: Any) -> Vehicle:
        """Apply a partial update; raises if cross-tenant or absent."""
        row = self._rows.get(vehicle_id)
        if row is None or row["tenant_id"] != tenant_id:
            raise VehicleNotFoundError(f"Vehicle {vehicle_id} not found")
        for key, value in deepcopy(patch).items():
            row[key] = value
        row["updated_at"] = datetime.now(UTC)
        return self._row_to_vehicle(row)

    async def archive(self, vehicle_id: UUID, tenant_id: UUID) -> Vehicle:
        """Mark the vehicle archived."""
        return await self.update(vehicle_id, tenant_id, archived=True)

    async def restore(self, vehicle_id: UUID, tenant_id: UUID) -> Vehicle:
        """Clear the archived flag."""
        return await self.update(vehicle_id, tenant_id, archived=False)

    async def list_active_for_date(self, tenant_id: UUID, work_date: date) -> list[Vehicle]:
        """Return non-archived vehicles that have a crew for ``work_date``."""
        if self._crew_repo is None:
            return []
        crew_vehicle_ids = {
            cr["vehicle_id"]
            for cr in self._crew_repo._rows.values()
            if cr["tenant_id"] == tenant_id and cr["work_date"] == work_date
        }
        return [
            self._row_to_vehicle(r)
            for r in self._rows.values()
            if r["tenant_id"] == tenant_id
            and not r.get("archived", False)
            and r["id"] in crew_vehicle_ids
        ]
