"""VehicleLocation model — time-series GPS positions posted by Technicians."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from office_hero.models import Base


class VehicleLocation(Base):
    """One GPS fix posted by a Technician for a Vehicle.

    Rows are append-only. The latest row per vehicle is used by the routing
    engine; older rows are available for auditing but not queried in hot paths.
    """

    __tablename__ = "vehicle_locations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    vehicle_id: Mapped[UUID] = mapped_column(ForeignKey("vehicles.id"), nullable=False)
    lat: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    lng: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    accuracy_m: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    __table_args__ = (
        Index(
            "idx_vehicle_locations_tenant_vehicle_recorded",
            "tenant_id",
            "vehicle_id",
            "recorded_at",
        ),
        Index("idx_vehicle_locations_tenant_id", "tenant_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<VehicleLocation(id={self.id}, vehicle_id={self.vehicle_id},"
            f" lat={self.lat}, lng={self.lng}, recorded_at={self.recorded_at})>"
        )
