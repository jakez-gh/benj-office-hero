"""Location ORM model — one Customer has many service Locations (1:N)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from office_hero.models import Base

if TYPE_CHECKING:
    from office_hero.models.customer import Customer


class Location(Base):
    """A physical service site belonging to a :class:`Customer`.

    Coordinates (``lat``/``lng``) are populated asynchronously by the
    geocoding adapter; ``geocode_status`` tracks the lifecycle so a worker
    can pick up ``"pending"`` rows in bulk.
    """

    __tablename__ = "locations"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    customer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    street: Mapped[str] = mapped_column(String(255), nullable=False)
    street2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    state: Mapped[str] = mapped_column(String(60), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False, default="US")
    lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    lng: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    geocode_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    geocode_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    geocoded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    customer: Mapped[Customer] = relationship("Customer", back_populates="locations")

    __table_args__ = (
        Index("idx_location_tenant_customer", "tenant_id", "customer_id"),
        Index("idx_location_tenant_status", "tenant_id", "geocode_status"),
    )

    def __repr__(self) -> str:
        return (
            f"<Location(id={self.id}, customer_id={self.customer_id}, "
            f"street={self.street!r}, status={self.geocode_status})>"
        )
