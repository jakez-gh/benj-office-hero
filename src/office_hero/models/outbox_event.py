"""OutboxEvent ORM model — transactional outbox rows (ADR 056, Slice 24).

Maps the ``outbox_events`` table created in migration 0001.  Ids are
string-36 UUIDs (legacy table shape, preserved to avoid a type migration);
the repository converts at the boundary.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from office_hero.models import Base


class OutboxEvent(Base):
    """One reliably-deliverable event destined for a back-office adapter."""

    __tablename__ = "outbox_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    idem_key: Mapped[str] = mapped_column(String(36), nullable=False)
    # pending -> processing -> done | dead (dead can be retried back to pending)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    dead_letter_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<OutboxEvent(id={self.id}, type={self.event_type}, status={self.status})>"
