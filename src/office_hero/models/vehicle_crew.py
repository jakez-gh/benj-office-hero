"""VehicleCrew and VehicleCrewMember ORM models.

A :class:`VehicleCrew` is date-scoped: one vehicle + one calendar date = one
crew record. The unique constraint ``(tenant_id, vehicle_id, work_date)`` is the
core invariant enforced at the database level (ADR 053 / migration 0006).

A :class:`VehicleCrewMember` links a :class:`~office_hero.models.user.User` to a
crew with a per-crew role (lead / helper / trainee). The unique ``(crew_id,
user_id)`` constraint prevents the same user appearing twice on the same crew.
"""

from __future__ import annotations

import time as _time
from datetime import date, datetime, time
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    String,
    Time,
    UniqueConstraint,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from office_hero.models import Base

if TYPE_CHECKING:
    from office_hero.models.vehicle import Vehicle
    from office_hero.models.user import User


class VehicleCrew(Base):
    """A crew assigned to a vehicle for a specific work date.

    Uniqueness is enforced on ``(tenant_id, vehicle_id, work_date)`` so that a
    vehicle cannot be double-booked. A Technician *can* appear on multiple crews
    on the same date (split-shift helper); those conflicts are surfaced via
    :meth:`~office_hero.repositories.vehicle_crew_repository.VehicleCrewRepository.find_user_crew_conflicts`
    rather than blocked by a constraint.
    """

    __tablename__ = "vehicle_crews"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    vehicle_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False
    )
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    shift_start: Mapped[time] = mapped_column(
        Time, nullable=False, default=lambda: time(8, 0)
    )
    shift_end: Mapped[time] = mapped_column(
        Time, nullable=False, default=lambda: time(17, 0)
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    vehicle: Mapped[Vehicle] = relationship("Vehicle", back_populates="crews")
    members: Mapped[list[VehicleCrewMember]] = relationship(
        "VehicleCrewMember",
        back_populates="crew",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "vehicle_id",
            "work_date",
            name="uq_vehicle_crew_vehicle_date",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<VehicleCrew(id={self.id}, vehicle_id={self.vehicle_id},"
            f" work_date={self.work_date})>"
        )


class VehicleCrewMember(Base):
    """A single user's assignment to a :class:`VehicleCrew` with their on-crew role.

    ``tenant_id`` is denormalised from the parent crew so RLS can apply without a
    join (ADR 053). The CHECK constraint ``role_on_crew IN ('lead','helper','trainee')``
    is enforced at the database level (migration 0006).
    """

    __tablename__ = "vehicle_crew_members"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    crew_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("vehicle_crews.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    role_on_crew: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    crew: Mapped[VehicleCrew] = relationship("VehicleCrew", back_populates="members")

    __table_args__ = (
        UniqueConstraint("crew_id", "user_id", name="uq_crew_member_user"),
    )

    def __repr__(self) -> str:
        return (
            f"<VehicleCrewMember(crew_id={self.crew_id}, user_id={self.user_id},"
            f" role={self.role_on_crew!r})>"
        )
