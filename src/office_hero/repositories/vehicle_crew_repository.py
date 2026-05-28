"""VehicleCrew repository — protocol, SQLAlchemy impl, and in-memory mock.

The date-scoped crew model enforces a unique ``(tenant_id, vehicle_id, work_date)``
invariant at the database level. The in-memory mock mirrors that invariant so unit
tests exercise the same conflict-detection path as production.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time
from typing import Any, Protocol, runtime_checkable
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from office_hero.core.crew_role import CrewRole
from office_hero.core.exceptions import (
    CrewAssignmentConflictError,
    VehicleCrewNotFoundError,
)
from office_hero.models.vehicle_crew import VehicleCrew, VehicleCrewMember


@dataclass
class CrewMemberInput:
    """Value object used to specify a member when creating/replacing a crew."""

    user_id: UUID
    role_on_crew: CrewRole


@runtime_checkable
class VehicleCrewRepositoryProtocol(Protocol):
    """Repository contract for :class:`VehicleCrew` persistence."""

    async def create(
        self,
        tenant_id: UUID,
        *,
        vehicle_id: UUID,
        work_date: date,
        shift_start: time,
        shift_end: time,
        notes: str | None,
        created_by_user_id: UUID,
        members: list[CrewMemberInput],
    ) -> VehicleCrew: ...

    async def get_by_id(self, crew_id: UUID, tenant_id: UUID) -> VehicleCrew | None: ...

    async def get_for_vehicle_date(
        self, tenant_id: UUID, vehicle_id: UUID, work_date: date
    ) -> VehicleCrew | None: ...

    async def list_for_date(
        self, tenant_id: UUID, work_date: date
    ) -> list[VehicleCrew]: ...

    async def list_for_user_date(
        self, tenant_id: UUID, user_id: UUID, work_date: date
    ) -> list[VehicleCrew]: ...

    async def update(
        self,
        crew_id: UUID,
        tenant_id: UUID,
        *,
        shift_start: time | None = None,
        shift_end: time | None = None,
        notes: str | None = None,
    ) -> VehicleCrew: ...

    async def replace_members(
        self,
        crew_id: UUID,
        tenant_id: UUID,
        members: list[CrewMemberInput],
    ) -> VehicleCrew: ...

    async def add_member(
        self,
        crew_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        role_on_crew: CrewRole,
    ) -> VehicleCrewMember: ...

    async def remove_member(
        self, crew_id: UUID, tenant_id: UUID, user_id: UUID
    ) -> None: ...

    async def delete(self, crew_id: UUID, tenant_id: UUID) -> None: ...

    async def find_user_crew_conflicts(
        self, tenant_id: UUID, work_date: date
    ) -> list[tuple[UUID, list[UUID]]]: ...


class VehicleCrewRepository:
    """SQLAlchemy-backed concrete :class:`VehicleCrew` repository (ADR 058)."""

    def __init__(self, session: AsyncSession):
        """Bind to an async SQLAlchemy session."""
        self.session = session

    async def create(
        self,
        tenant_id: UUID,
        *,
        vehicle_id: UUID,
        work_date: date,
        shift_start: time,
        shift_end: time,
        notes: str | None,
        created_by_user_id: UUID,
        members: list[CrewMemberInput],
    ) -> VehicleCrew:
        """Insert a crew + members in one transaction.

        Raises :class:`~office_hero.core.exceptions.CrewAssignmentConflictError`
        on duplicate ``(vehicle_id, work_date)`` (caught IntegrityError → typed error).
        """
        from sqlalchemy.exc import IntegrityError

        crew = VehicleCrew(
            tenant_id=tenant_id,
            vehicle_id=vehicle_id,
            work_date=work_date,
            shift_start=shift_start,
            shift_end=shift_end,
            notes=notes,
            created_by_user_id=created_by_user_id,
        )
        self.session.add(crew)
        try:
            await self.session.flush()
        except IntegrityError:
            await self.session.rollback()
            # Look up the conflicting crew to surface its ID.
            existing = await self.get_for_vehicle_date(tenant_id, vehicle_id, work_date)
            raise CrewAssignmentConflictError(
                existing_crew_id=existing.id if existing else None
            )

        for m in members:
            member = VehicleCrewMember(
                tenant_id=tenant_id,
                crew_id=crew.id,
                user_id=m.user_id,
                role_on_crew=str(m.role_on_crew),
            )
            self.session.add(member)
        await self.session.flush()
        return crew

    async def get_by_id(self, crew_id: UUID, tenant_id: UUID) -> VehicleCrew | None:
        """Fetch a crew if it exists in ``tenant_id``."""
        stmt = select(VehicleCrew).where(
            VehicleCrew.id == crew_id, VehicleCrew.tenant_id == tenant_id
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_for_vehicle_date(
        self, tenant_id: UUID, vehicle_id: UUID, work_date: date
    ) -> VehicleCrew | None:
        """Return the crew for a vehicle on a given date, or None."""
        stmt = select(VehicleCrew).where(
            VehicleCrew.tenant_id == tenant_id,
            VehicleCrew.vehicle_id == vehicle_id,
            VehicleCrew.work_date == work_date,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_for_date(
        self, tenant_id: UUID, work_date: date
    ) -> list[VehicleCrew]:
        """Return all crews for a tenant on ``work_date`` (daily dispatch view)."""
        stmt = (
            select(VehicleCrew)
            .where(
                VehicleCrew.tenant_id == tenant_id,
                VehicleCrew.work_date == work_date,
            )
            .order_by(VehicleCrew.shift_start)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_for_user_date(
        self, tenant_id: UUID, user_id: UUID, work_date: date
    ) -> list[VehicleCrew]:
        """Return crews where ``user_id`` is a member on ``work_date``."""
        stmt = (
            select(VehicleCrew)
            .join(VehicleCrewMember, VehicleCrewMember.crew_id == VehicleCrew.id)
            .where(
                VehicleCrew.tenant_id == tenant_id,
                VehicleCrew.work_date == work_date,
                VehicleCrewMember.user_id == user_id,
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(
        self,
        crew_id: UUID,
        tenant_id: UUID,
        *,
        shift_start: time | None = None,
        shift_end: time | None = None,
        notes: str | None = None,
    ) -> VehicleCrew:
        """Update crew shift/notes fields; raises if not found."""
        crew = await self.get_by_id(crew_id, tenant_id)
        if crew is None:
            raise VehicleCrewNotFoundError(f"VehicleCrew {crew_id} not found")
        if shift_start is not None:
            crew.shift_start = shift_start
        if shift_end is not None:
            crew.shift_end = shift_end
        if notes is not None:
            crew.notes = notes
        await self.session.flush()
        return crew

    async def replace_members(
        self,
        crew_id: UUID,
        tenant_id: UUID,
        members: list[CrewMemberInput],
    ) -> VehicleCrew:
        """Atomically replace the crew roster (delete-then-insert)."""
        from sqlalchemy import delete

        crew = await self.get_by_id(crew_id, tenant_id)
        if crew is None:
            raise VehicleCrewNotFoundError(f"VehicleCrew {crew_id} not found")

        await self.session.execute(
            delete(VehicleCrewMember).where(VehicleCrewMember.crew_id == crew_id)
        )
        for m in members:
            self.session.add(
                VehicleCrewMember(
                    tenant_id=tenant_id,
                    crew_id=crew_id,
                    user_id=m.user_id,
                    role_on_crew=str(m.role_on_crew),
                )
            )
        await self.session.flush()
        return crew

    async def add_member(
        self,
        crew_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        role_on_crew: CrewRole,
    ) -> VehicleCrewMember:
        """Add one member to an existing crew."""
        crew = await self.get_by_id(crew_id, tenant_id)
        if crew is None:
            raise VehicleCrewNotFoundError(f"VehicleCrew {crew_id} not found")
        m = VehicleCrewMember(
            tenant_id=tenant_id,
            crew_id=crew_id,
            user_id=user_id,
            role_on_crew=str(role_on_crew),
        )
        self.session.add(m)
        await self.session.flush()
        return m

    async def remove_member(
        self, crew_id: UUID, tenant_id: UUID, user_id: UUID
    ) -> None:
        """Remove a member from the crew; raises if crew not found."""
        from sqlalchemy import delete

        crew = await self.get_by_id(crew_id, tenant_id)
        if crew is None:
            raise VehicleCrewNotFoundError(f"VehicleCrew {crew_id} not found")
        await self.session.execute(
            delete(VehicleCrewMember).where(
                VehicleCrewMember.crew_id == crew_id,
                VehicleCrewMember.user_id == user_id,
            )
        )
        await self.session.flush()

    async def delete(self, crew_id: UUID, tenant_id: UUID) -> None:
        """Delete the crew (cascades to members via DB FK)."""
        from sqlalchemy import delete

        crew = await self.get_by_id(crew_id, tenant_id)
        if crew is None:
            raise VehicleCrewNotFoundError(f"VehicleCrew {crew_id} not found")
        await self.session.execute(
            delete(VehicleCrew).where(VehicleCrew.id == crew_id)
        )
        await self.session.flush()

    async def find_user_crew_conflicts(
        self, tenant_id: UUID, work_date: date
    ) -> list[tuple[UUID, list[UUID]]]:
        """Return ``[(user_id, [crew_id, ...]), ...]`` for double-booked users."""
        from sqlalchemy import func

        stmt = (
            select(
                VehicleCrewMember.user_id,
                func.array_agg(VehicleCrewMember.crew_id).label("crew_ids"),
            )
            .join(VehicleCrew, VehicleCrew.id == VehicleCrewMember.crew_id)
            .where(
                VehicleCrewMember.tenant_id == tenant_id,
                VehicleCrew.work_date == work_date,
            )
            .group_by(VehicleCrewMember.user_id)
            .having(func.count(VehicleCrewMember.crew_id) > 1)
        )
        result = await self.session.execute(stmt)
        return [(row.user_id, row.crew_ids) for row in result]


# ---------------------------------------------------------------------------
# In-memory mock
# ---------------------------------------------------------------------------


class InMemoryVehicleCrewRepository:
    """In-memory mock implementing :class:`VehicleCrewRepositoryProtocol`."""

    def __init__(self) -> None:
        # crew_id -> dict snapshot
        self._rows: dict[UUID, dict[str, Any]] = {}
        # member_id -> dict snapshot
        self._member_rows: dict[UUID, dict[str, Any]] = {}

    def _row_to_crew(self, row: dict[str, Any]) -> VehicleCrew:
        crew = VehicleCrew(
            id=row["id"],
            tenant_id=row["tenant_id"],
            vehicle_id=row["vehicle_id"],
            work_date=row["work_date"],
            shift_start=row["shift_start"],
            shift_end=row["shift_end"],
            notes=row.get("notes"),
            created_by_user_id=row["created_by_user_id"],
        )
        crew.created_at = row["created_at"]
        crew.updated_at = row["updated_at"]
        # Attach member objects
        crew.members = [
            self._row_to_member(mr)
            for mr in self._member_rows.values()
            if mr["crew_id"] == row["id"]
        ]
        return crew

    def _row_to_member(self, row: dict[str, Any]) -> VehicleCrewMember:
        m = VehicleCrewMember(
            id=row["id"],
            tenant_id=row["tenant_id"],
            crew_id=row["crew_id"],
            user_id=row["user_id"],
            role_on_crew=row["role_on_crew"],
        )
        m.created_at = row["created_at"]
        return m

    async def create(
        self,
        tenant_id: UUID,
        *,
        vehicle_id: UUID,
        work_date: date,
        shift_start: time,
        shift_end: time,
        notes: str | None,
        created_by_user_id: UUID,
        members: list[CrewMemberInput],
    ) -> VehicleCrew:
        """Raise :class:`CrewAssignmentConflictError` on duplicate (vehicle, date)."""
        existing = await self.get_for_vehicle_date(tenant_id, vehicle_id, work_date)
        if existing is not None:
            raise CrewAssignmentConflictError(existing_crew_id=existing.id)

        cid = uuid4()
        now = datetime.now(UTC)
        self._rows[cid] = {
            "id": cid,
            "tenant_id": tenant_id,
            "vehicle_id": vehicle_id,
            "work_date": work_date,
            "shift_start": shift_start,
            "shift_end": shift_end,
            "notes": notes,
            "created_by_user_id": created_by_user_id,
            "created_at": now,
            "updated_at": now,
        }
        for m in members:
            mid = uuid4()
            self._member_rows[mid] = {
                "id": mid,
                "tenant_id": tenant_id,
                "crew_id": cid,
                "user_id": m.user_id,
                "role_on_crew": str(m.role_on_crew),
                "created_at": now,
            }
        return self._row_to_crew(self._rows[cid])

    async def get_by_id(self, crew_id: UUID, tenant_id: UUID) -> VehicleCrew | None:
        """Return the crew if it exists in this tenant's scope."""
        row = self._rows.get(crew_id)
        if row is None or row["tenant_id"] != tenant_id:
            return None
        return self._row_to_crew(row)

    async def get_for_vehicle_date(
        self, tenant_id: UUID, vehicle_id: UUID, work_date: date
    ) -> VehicleCrew | None:
        """Return the crew for a vehicle on a given date, or None."""
        for row in self._rows.values():
            if (
                row["tenant_id"] == tenant_id
                and row["vehicle_id"] == vehicle_id
                and row["work_date"] == work_date
            ):
                return self._row_to_crew(row)
        return None

    async def list_for_date(
        self, tenant_id: UUID, work_date: date
    ) -> list[VehicleCrew]:
        """Return all crews for the date."""
        rows = [
            r
            for r in self._rows.values()
            if r["tenant_id"] == tenant_id and r["work_date"] == work_date
        ]
        rows.sort(key=lambda r: r["shift_start"])
        return [self._row_to_crew(r) for r in rows]

    async def list_for_user_date(
        self, tenant_id: UUID, user_id: UUID, work_date: date
    ) -> list[VehicleCrew]:
        """Return crews where user is a member on the date."""
        crew_ids = {
            mr["crew_id"]
            for mr in self._member_rows.values()
            if mr["user_id"] == user_id
        }
        return [
            self._row_to_crew(r)
            for r in self._rows.values()
            if r["tenant_id"] == tenant_id
            and r["work_date"] == work_date
            and r["id"] in crew_ids
        ]

    async def update(
        self,
        crew_id: UUID,
        tenant_id: UUID,
        *,
        shift_start: time | None = None,
        shift_end: time | None = None,
        notes: str | None = None,
    ) -> VehicleCrew:
        """Update shift/notes fields."""
        row = self._rows.get(crew_id)
        if row is None or row["tenant_id"] != tenant_id:
            raise VehicleCrewNotFoundError(f"VehicleCrew {crew_id} not found")
        if shift_start is not None:
            row["shift_start"] = shift_start
        if shift_end is not None:
            row["shift_end"] = shift_end
        if notes is not None:
            row["notes"] = notes
        row["updated_at"] = datetime.now(UTC)
        return self._row_to_crew(row)

    async def replace_members(
        self,
        crew_id: UUID,
        tenant_id: UUID,
        members: list[CrewMemberInput],
    ) -> VehicleCrew:
        """Atomically replace the roster."""
        row = self._rows.get(crew_id)
        if row is None or row["tenant_id"] != tenant_id:
            raise VehicleCrewNotFoundError(f"VehicleCrew {crew_id} not found")
        # Remove all existing members
        to_remove = [mid for mid, mr in self._member_rows.items() if mr["crew_id"] == crew_id]
        for mid in to_remove:
            del self._member_rows[mid]
        # Add new members
        now = datetime.now(UTC)
        for m in members:
            mid = uuid4()
            self._member_rows[mid] = {
                "id": mid,
                "tenant_id": tenant_id,
                "crew_id": crew_id,
                "user_id": m.user_id,
                "role_on_crew": str(m.role_on_crew),
                "created_at": now,
            }
        return self._row_to_crew(row)

    async def add_member(
        self,
        crew_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        role_on_crew: CrewRole,
    ) -> VehicleCrewMember:
        """Add one member to a crew."""
        row = self._rows.get(crew_id)
        if row is None or row["tenant_id"] != tenant_id:
            raise VehicleCrewNotFoundError(f"VehicleCrew {crew_id} not found")
        mid = uuid4()
        now = datetime.now(UTC)
        self._member_rows[mid] = {
            "id": mid,
            "tenant_id": tenant_id,
            "crew_id": crew_id,
            "user_id": user_id,
            "role_on_crew": str(role_on_crew),
            "created_at": now,
        }
        return self._row_to_member(self._member_rows[mid])

    async def remove_member(
        self, crew_id: UUID, tenant_id: UUID, user_id: UUID
    ) -> None:
        """Remove a member."""
        row = self._rows.get(crew_id)
        if row is None or row["tenant_id"] != tenant_id:
            raise VehicleCrewNotFoundError(f"VehicleCrew {crew_id} not found")
        to_remove = [
            mid
            for mid, mr in self._member_rows.items()
            if mr["crew_id"] == crew_id and mr["user_id"] == user_id
        ]
        for mid in to_remove:
            del self._member_rows[mid]

    async def delete(self, crew_id: UUID, tenant_id: UUID) -> None:
        """Delete the crew and all its members."""
        row = self._rows.get(crew_id)
        if row is None or row["tenant_id"] != tenant_id:
            raise VehicleCrewNotFoundError(f"VehicleCrew {crew_id} not found")
        to_remove = [mid for mid, mr in self._member_rows.items() if mr["crew_id"] == crew_id]
        for mid in to_remove:
            del self._member_rows[mid]
        del self._rows[crew_id]

    async def find_user_crew_conflicts(
        self, tenant_id: UUID, work_date: date
    ) -> list[tuple[UUID, list[UUID]]]:
        """Return double-booked users for ``work_date``."""
        from collections import defaultdict

        crew_ids_on_date = {
            r["id"]
            for r in self._rows.values()
            if r["tenant_id"] == tenant_id and r["work_date"] == work_date
        }
        user_to_crews: dict[UUID, list[UUID]] = defaultdict(list)
        for mr in self._member_rows.values():
            if mr["crew_id"] in crew_ids_on_date:
                user_to_crews[mr["user_id"]].append(mr["crew_id"])
        return [
            (uid, crew_ids)
            for uid, crew_ids in user_to_crews.items()
            if len(crew_ids) > 1
        ]
