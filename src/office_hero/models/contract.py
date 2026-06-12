"""Contract ORM model — recurring service agreements (Slice 11).

A Contract belongs to a :class:`~office_hero.models.customer.Customer` and a
:class:`~office_hero.models.location.Location` and generates Jobs on a schedule
driven by ``frequency`` / ``next_due``.  ``industry`` is copied from the Tenant
at creation time (same rationale as Job).  ``status`` follows the lifecycle in
:mod:`office_hero.core.contract_status`; all transitions must go through
:class:`~office_hero.services.contract_service.ContractService._transition`.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from office_hero.models import Base

if TYPE_CHECKING:
    from office_hero.models.customer import Customer
    from office_hero.models.location import Location


class Contract(Base):
    """Tenant-scoped recurring service agreement."""

    __tablename__ = "contracts"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    customer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False
    )
    location_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("locations.id"), nullable=False
    )

    # Copied from Tenant.industry at create time (immutable per ADR).
    industry: Mapped[str] = mapped_column(String(50), nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    service_type: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Copied onto generated Jobs (routing-compatible scale: 0 highest, 100 lowest).
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    estimated_duration_min: Mapped[int] = mapped_column(Integer, nullable=False, default=60)

    # Recurrence — see core/contract_frequency.py.
    frequency: Mapped[str] = mapped_column(String(20), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    next_due: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Status is a plain varchar; domain rules are enforced exclusively by
    # ContractService._transition() (see core/contract_status.py).
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Industry-specific metadata validated by the CustomFieldTemplate registry;
    # copied onto generated Jobs.
    custom_fields: Mapped[dict] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=False, server_default="{}"
    )

    # Back-office integration identifier (ADR 056).
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

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

    customer: Mapped[Customer] = relationship("Customer")
    location: Mapped[Location] = relationship("Location")

    __table_args__ = (
        # Contracts list: filter by status within a tenant.
        Index("idx_contracts_tenant_status", "tenant_id", "status"),
        # Generation pass: active contracts due on/before a date.
        Index("idx_contracts_tenant_next_due", "tenant_id", "next_due"),
        # Customer detail view: all contracts for a customer.
        Index("idx_contracts_tenant_customer", "tenant_id", "customer_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<Contract(id={self.id}, title={self.title!r}, "
            f"status={self.status}, next_due={self.next_due}, tenant_id={self.tenant_id})>"
        )
