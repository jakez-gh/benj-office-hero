"""Location repository — protocol, SQLAlchemy impl, and in-memory mock."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from office_hero.core.exceptions import LocationNotFoundError
from office_hero.models.location import Location


@runtime_checkable
class LocationRepositoryProtocol(Protocol):
    """Repository contract for :class:`Location` persistence."""

    async def create(
        self,
        tenant_id: UUID,
        customer_id: UUID,
        *,
        street: str,
        city: str,
        state: str,
        postal_code: str,
        country: str = "US",
        street2: str | None = None,
        label: str | None = None,
    ) -> Location: ...

    async def get_by_id(self, location_id: UUID, tenant_id: UUID) -> Location | None: ...

    async def list_for_customer(
        self,
        customer_id: UUID,
        tenant_id: UUID,
        *,
        archived: bool = False,
    ) -> list[Location]: ...

    async def list_pending_geocode(
        self, tenant_id: UUID, limit: int = 50
    ) -> list[Location]: ...

    async def update(self, location_id: UUID, tenant_id: UUID, **patch: Any) -> Location: ...

    async def set_coordinates(
        self,
        location_id: UUID,
        tenant_id: UUID,
        lat: float,
        lng: float,
        source: str,
    ) -> Location: ...

    async def mark_geocode_failed(
        self, location_id: UUID, tenant_id: UUID, error: str
    ) -> Location: ...

    async def archive(self, location_id: UUID, tenant_id: UUID) -> Location: ...


class LocationRepository:
    """SQLAlchemy-backed concrete :class:`Location` repository."""

    def __init__(self, session: AsyncSession):
        """Bind to an async SQLAlchemy session."""
        self.session = session

    async def create(
        self,
        tenant_id: UUID,
        customer_id: UUID,
        *,
        street: str,
        city: str,
        state: str,
        postal_code: str,
        country: str = "US",
        street2: str | None = None,
        label: str | None = None,
    ) -> Location:
        """Insert a fresh location in ``pending`` geocode status."""
        loc = Location(
            tenant_id=tenant_id,
            customer_id=customer_id,
            street=street,
            street2=street2,
            city=city,
            state=state,
            postal_code=postal_code,
            country=country,
            label=label,
            geocode_status="pending",
            archived=False,
        )
        self.session.add(loc)
        await self.session.flush()
        return loc

    async def get_by_id(self, location_id: UUID, tenant_id: UUID) -> Location | None:
        """Tenant-scoped read."""
        stmt = select(Location).where(
            Location.id == location_id, Location.tenant_id == tenant_id
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_customer(
        self,
        customer_id: UUID,
        tenant_id: UUID,
        *,
        archived: bool = False,
    ) -> list[Location]:
        """List a customer's locations within the active tenant."""
        stmt = (
            select(Location)
            .where(
                Location.tenant_id == tenant_id,
                Location.customer_id == customer_id,
                Location.archived.is_(archived),
            )
            .order_by(Location.created_at.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_pending_geocode(
        self, tenant_id: UUID, limit: int = 50
    ) -> list[Location]:
        """Worker hook — fetch rows the geocoder still needs to resolve."""
        stmt = (
            select(Location)
            .where(
                Location.tenant_id == tenant_id,
                Location.geocode_status == "pending",
            )
            .order_by(Location.created_at.asc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def update(self, location_id: UUID, tenant_id: UUID, **patch: Any) -> Location:
        """Apply a partial update; raises :class:`LocationNotFoundError` if absent."""
        loc = await self.get_by_id(location_id, tenant_id)
        if loc is None:
            raise LocationNotFoundError(f"Location {location_id} not found")
        for key, value in patch.items():
            setattr(loc, key, value)
        await self.session.flush()
        return loc

    async def set_coordinates(
        self,
        location_id: UUID,
        tenant_id: UUID,
        lat: float,
        lng: float,
        source: str,
    ) -> Location:
        """Persist coordinates with status ``ok``."""
        return await self.update(
            location_id,
            tenant_id,
            lat=Decimal(str(lat)),
            lng=Decimal(str(lng)),
            geocode_source=source,
            geocode_status="ok",
            geocoded_at=datetime.now(UTC),
        )

    async def mark_geocode_failed(
        self, location_id: UUID, tenant_id: UUID, error: str
    ) -> Location:
        """Mark this location as having failed geocoding."""
        # ``error`` is logged at the service layer; we just store the status
        # transition here.
        del error
        return await self.update(
            location_id,
            tenant_id,
            geocode_status="failed",
            geocoded_at=datetime.now(UTC),
        )

    async def archive(self, location_id: UUID, tenant_id: UUID) -> Location:
        """Soft-delete a location."""
        return await self.update(location_id, tenant_id, archived=True)


class InMemoryLocationRepository:
    """In-memory mock implementing :class:`LocationRepositoryProtocol`."""

    def __init__(self) -> None:
        self._rows: dict[UUID, dict[str, Any]] = {}

    def _row_to_location(self, row: dict[str, Any]) -> Location:
        loc = Location(
            id=row["id"],
            tenant_id=row["tenant_id"],
            customer_id=row["customer_id"],
            label=row.get("label"),
            street=row["street"],
            street2=row.get("street2"),
            city=row["city"],
            state=row["state"],
            postal_code=row["postal_code"],
            country=row.get("country", "US"),
            lat=row.get("lat"),
            lng=row.get("lng"),
            geocode_source=row.get("geocode_source"),
            geocode_status=row.get("geocode_status", "pending"),
            geocoded_at=row.get("geocoded_at"),
            archived=row.get("archived", False),
        )
        loc.created_at = row["created_at"]
        loc.updated_at = row["updated_at"]
        return loc

    async def create(
        self,
        tenant_id: UUID,
        customer_id: UUID,
        *,
        street: str,
        city: str,
        state: str,
        postal_code: str,
        country: str = "US",
        street2: str | None = None,
        label: str | None = None,
    ) -> Location:
        """Insert a fresh location."""
        lid = uuid4()
        now = datetime.now(UTC)
        self._rows[lid] = {
            "id": lid,
            "tenant_id": tenant_id,
            "customer_id": customer_id,
            "label": label,
            "street": street,
            "street2": street2,
            "city": city,
            "state": state,
            "postal_code": postal_code,
            "country": country,
            "lat": None,
            "lng": None,
            "geocode_source": None,
            "geocode_status": "pending",
            "geocoded_at": None,
            "archived": False,
            "created_at": now,
            "updated_at": now,
        }
        return self._row_to_location(self._rows[lid])

    async def get_by_id(self, location_id: UUID, tenant_id: UUID) -> Location | None:
        """Tenant-scoped read."""
        row = self._rows.get(location_id)
        if row is None or row["tenant_id"] != tenant_id:
            return None
        return self._row_to_location(row)

    async def list_for_customer(
        self,
        customer_id: UUID,
        tenant_id: UUID,
        *,
        archived: bool = False,
    ) -> list[Location]:
        """List locations belonging to the customer."""
        rows = [
            r
            for r in self._rows.values()
            if r["tenant_id"] == tenant_id
            and r["customer_id"] == customer_id
            and r["archived"] == archived
        ]
        rows.sort(key=lambda r: r["created_at"])
        return [self._row_to_location(r) for r in rows]

    async def list_pending_geocode(
        self, tenant_id: UUID, limit: int = 50
    ) -> list[Location]:
        """Return up to ``limit`` rows still pending geocode."""
        rows = [
            r
            for r in self._rows.values()
            if r["tenant_id"] == tenant_id and r["geocode_status"] == "pending"
        ]
        rows.sort(key=lambda r: r["created_at"])
        return [self._row_to_location(r) for r in rows[:limit]]

    async def update(self, location_id: UUID, tenant_id: UUID, **patch: Any) -> Location:
        """Apply a partial update; raises if cross-tenant or absent."""
        row = self._rows.get(location_id)
        if row is None or row["tenant_id"] != tenant_id:
            raise LocationNotFoundError(f"Location {location_id} not found")
        for key, value in deepcopy(patch).items():
            row[key] = value
        row["updated_at"] = datetime.now(UTC)
        return self._row_to_location(row)

    async def set_coordinates(
        self,
        location_id: UUID,
        tenant_id: UUID,
        lat: float,
        lng: float,
        source: str,
    ) -> Location:
        """Persist coordinates and flip status to ``ok``."""
        return await self.update(
            location_id,
            tenant_id,
            lat=Decimal(str(lat)),
            lng=Decimal(str(lng)),
            geocode_source=source,
            geocode_status="ok",
            geocoded_at=datetime.now(UTC),
        )

    async def mark_geocode_failed(
        self, location_id: UUID, tenant_id: UUID, error: str
    ) -> Location:
        """Flip status to ``failed``; ``error`` is logged at the service layer."""
        del error
        return await self.update(
            location_id,
            tenant_id,
            geocode_status="failed",
            geocoded_at=datetime.now(UTC),
        )

    async def archive(self, location_id: UUID, tenant_id: UUID) -> Location:
        """Soft-delete a location."""
        return await self.update(location_id, tenant_id, archived=True)
