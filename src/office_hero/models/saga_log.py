"""SagaLog ORM model — persisted saga execution state (ADR 056, Slice 24).

Maps the ``saga_log`` table created in migration 0001.  Ids are string-36
UUIDs (legacy table shape, preserved); the repository converts at the
boundary.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from office_hero.models import Base


class SagaLog(Base):
    """Execution record for one saga instance."""

    __tablename__ = "saga_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    saga_type: Mapped[str] = mapped_column(Text, nullable=False)
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # running | done | compensating | failed (see sagas.core.SagaStatus)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    context: Mapped[dict] = mapped_column(JSON, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<SagaLog(id={self.id}, type={self.saga_type}, status={self.status})>"
