"""SQL-backed saga repository (ADR 056, Slice 24).

Implements :class:`office_hero.repositories.protocols.SagaRepository`
against the ``saga_log`` table.  String-36 ids are converted to/from
:class:`uuid.UUID` at the boundary so callers and the in-memory mock stay
interchangeable.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from office_hero.models.saga_log import SagaLog
from office_hero.sagas.core import SagaContext, SagaStatus


def _row_to_context(row: SagaLog) -> SagaContext:
    return SagaContext(
        saga_id=UUID(row.id),
        tenant_id=UUID(row.tenant_id),
        saga_type=row.saga_type,
        current_step=row.current_step,
        status=SagaStatus(row.status),
        context=dict(row.context or {}),
        last_error=row.last_error,
        created_at=row.created_at.isoformat() if row.created_at else None,
        updated_at=row.updated_at.isoformat() if row.updated_at else None,
    )


class SqlSagaRepository:
    """SQLAlchemy-backed concrete :class:`SagaRepository` (ADR 058)."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind to an async SQLAlchemy session."""
        self.session = session

    async def _get(self, saga_id: UUID) -> SagaLog:
        row = await self.session.get(SagaLog, str(saga_id))
        if row is None:
            raise KeyError(f"Saga {saga_id} not found")
        return row

    async def create(self, tenant_id: UUID, saga_type: str, context: dict[str, Any]) -> SagaContext:
        """Insert a running saga record; returns its SagaContext."""
        row = SagaLog(
            tenant_id=str(tenant_id),
            saga_type=saga_type,
            current_step=0,
            status=SagaStatus.RUNNING.value,
            context=context,
        )
        self.session.add(row)
        await self.session.flush()
        return _row_to_context(row)

    async def get_by_id(self, saga_id: UUID) -> SagaContext | None:
        row = await self.session.get(SagaLog, str(saga_id))
        return _row_to_context(row) if row else None

    async def get_by_type_and_context(
        self,
        tenant_id: UUID,
        saga_type: str,
        context_filter: dict[str, Any],
    ) -> list[SagaContext]:
        """Filter by type, then match context keys in Python.

        JSON containment is Postgres-specific; the candidate set per
        (tenant, type) is small, so in-process filtering keeps this portable
        across sqlite (tests) and Postgres.
        """
        stmt = select(SagaLog).where(
            SagaLog.tenant_id == str(tenant_id),
            SagaLog.saga_type == saga_type,
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        contexts = [_row_to_context(r) for r in rows]
        return [
            c for c in contexts if all(c.context.get(k) == v for k, v in context_filter.items())
        ]

    async def update_status(
        self,
        saga_id: UUID,
        new_status: SagaStatus,
        context_update: dict[str, Any] | None = None,
        error_msg: str | None = None,
    ) -> SagaContext:
        row = await self._get(saga_id)
        row.status = new_status.value
        if context_update:
            # Reassign (not mutate) so SQLAlchemy detects the JSON change.
            row.context = {**(row.context or {}), **context_update}
        if error_msg:
            row.last_error = error_msg
        await self.session.flush()
        # onupdate=func.now() expires updated_at on flush — refresh explicitly
        # so reading it doesn't trigger sync lazy-load IO (MissingGreenlet).
        await self.session.refresh(row)
        return _row_to_context(row)

    async def update_current_step(self, saga_id: UUID, step_number: int) -> SagaContext:
        row = await self._get(saga_id)
        row.current_step = step_number
        await self.session.flush()
        await self.session.refresh(row)
        return _row_to_context(row)
