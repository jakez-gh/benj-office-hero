"""Tenant ORM model for multi-tenant isolation."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from office_hero.models import Base


class Tenant(Base):
    """Tenant representing a single organization/customer."""

    __tablename__ = "tenants"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Industry vertical — copied onto Job rows at creation time so historical
    # Jobs are unaffected by future industry changes (ADR 056 / design doc 012).
    industry: Mapped[str] = mapped_column(String(50), nullable=False, server_default="generic")
    # Which back-office system this tenant syncs with (ADR 056 / design doc 024).
    # 'native' = Office Hero is the system of record. Slices 25-27 add
    # 'servicetitan' / 'pestpac' / 'jobber' via adapters.back_office.registry.
    back_office_adapter: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="native"
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

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name={self.name})>"
