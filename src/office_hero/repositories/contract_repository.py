"""Contract repository — protocol, SQLAlchemy impl, and in-memory mock (Slice 11).

The protocol is what the service layer depends on (ADR 058).  The concrete
SQLAlchemy implementation is the production binding.  The in-memory mock is
used by unit tests so the service layer can be exercised without a database.
All implementations enforce tenant scoping defensively (ADR 053
defence-in-depth on top of RLS).
"""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, date, datetime
from typing import Any, Protocol, runtime_checkable
from uuid import UUID, uuid4

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from office_hero.core.exceptions import ContractNotFoundError
from office_hero.models.contract import Contract


@runtime_checkable
class ContractRepositoryProtocol(Protocol):
    """Repository contract for :class:`Contract` persistence."""

    async def create(
        self,
        tenant_id: UUID,
        *,
        customer_id: UUID,
        location_id: UUID,
        industry: str,
        title: str,
        description: str | None,
        service_type: str | None,
        priority: int,
        estimated_duration_min: int,
        frequency: str,
        start_date: date,
        next_due: date,
        end_date: date | None,
        custom_fields: dict,
        created_by_user_id: UUID,
    ) -> Contract: ...

    async def get_by_id(self, contract_id: UUID, tenant_id: UUID) -> Contract | None: ...

    async def list(
        self,
        tenant_id: UUID,
        *,
        status: list[str] | None = None,
        customer_id: UUID | None = None,
        due_before: date | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Contract], int]: ...

    async def update_fields(self, contract_id: UUID, tenant_id: UUID, **patch: Any) -> Contract: ...

    async def update_status(
        self,
        contract_id: UUID,
        tenant_id: UUID,
        new_status: str,
        *,
        paused_at: datetime | None = None,
        ended_at: datetime | None = None,
        end_reason: str | None = None,
    ) -> Contract: ...

    async def list_due(self, tenant_id: UUID, as_of: date) -> list[Contract]: ...


class ContractRepository:
    """SQLAlchemy-backed concrete :class:`Contract` repository (ADR 058)."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind to an async SQLAlchemy session."""
        self.session = session

    async def create(
        self,
        tenant_id: UUID,
        *,
        customer_id: UUID,
        location_id: UUID,
        industry: str,
        title: str,
        description: str | None = None,
        service_type: str | None = None,
        priority: int = 50,
        estimated_duration_min: int = 60,
        frequency: str,
        start_date: date,
        next_due: date,
        end_date: date | None = None,
        custom_fields: dict | None = None,
        created_by_user_id: UUID,
    ) -> Contract:
        """Insert and flush a new :class:`Contract`."""
        contract = Contract(
            tenant_id=tenant_id,
            customer_id=customer_id,
            location_id=location_id,
            industry=industry,
            title=title,
            description=description,
            service_type=service_type,
            priority=priority,
            estimated_duration_min=estimated_duration_min,
            frequency=frequency,
            start_date=start_date,
            next_due=next_due,
            end_date=end_date,
            status="active",
            custom_fields=custom_fields or {},
            created_by_user_id=created_by_user_id,
        )
        self.session.add(contract)
        await self.session.flush()
        return contract

    async def get_by_id(self, contract_id: UUID, tenant_id: UUID) -> Contract | None:
        """Fetch a contract if it exists in ``tenant_id`` (defence-in-depth)."""
        stmt = select(Contract).where(Contract.id == contract_id, Contract.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list(
        self,
        tenant_id: UUID,
        *,
        status: list[str] | None = None,
        customer_id: UUID | None = None,
        due_before: date | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Contract], int]:
        """Return ``(rows, total)`` for a tenant with optional filters."""
        where_clauses = [Contract.tenant_id == tenant_id]

        if status:
            where_clauses.append(Contract.status.in_(status))
        if customer_id is not None:
            where_clauses.append(Contract.customer_id == customer_id)
        if due_before is not None:
            where_clauses.append(Contract.next_due <= due_before)
        if search:
            pattern = f"%{search}%"
            where_clauses.append(
                or_(Contract.title.ilike(pattern), Contract.description.ilike(pattern))
            )

        count_stmt = select(func.count(Contract.id)).where(and_(*where_clauses))
        total = int((await self.session.execute(count_stmt)).scalar_one())

        rows_stmt = (
            select(Contract)
            .where(and_(*where_clauses))
            .order_by(Contract.next_due.asc(), Contract.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = list((await self.session.execute(rows_stmt)).scalars().all())
        return rows, total

    async def update_fields(self, contract_id: UUID, tenant_id: UUID, **patch: Any) -> Contract:
        """Apply a partial update to non-status fields; raises if absent."""
        contract = await self.get_by_id(contract_id, tenant_id)
        if contract is None:
            raise ContractNotFoundError(f"Contract {contract_id} not found")
        for key, value in patch.items():
            setattr(contract, key, value)
        await self.session.flush()
        return contract

    async def update_status(
        self,
        contract_id: UUID,
        tenant_id: UUID,
        new_status: str,
        *,
        paused_at: datetime | None = None,
        ended_at: datetime | None = None,
        end_reason: str | None = None,
    ) -> Contract:
        """Set status + the matching lifecycle timestamp atomically."""
        contract = await self.get_by_id(contract_id, tenant_id)
        if contract is None:
            raise ContractNotFoundError(f"Contract {contract_id} not found")
        contract.status = new_status
        if paused_at is not None:
            contract.paused_at = paused_at
        if ended_at is not None:
            contract.ended_at = ended_at
        if end_reason is not None:
            contract.end_reason = end_reason
        await self.session.flush()
        return contract

    async def list_due(self, tenant_id: UUID, as_of: date) -> list[Contract]:
        """Return active contracts with ``next_due <= as_of`` (generation pass)."""
        stmt = (
            select(Contract)
            .where(
                Contract.tenant_id == tenant_id,
                Contract.status == "active",
                Contract.next_due <= as_of,
            )
            .order_by(Contract.next_due.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class InMemoryContractRepository:
    """In-memory mock implementing :class:`ContractRepositoryProtocol`.

    Used by unit tests so the service layer can be exercised without a DB.
    Tenant scope is honoured on every read/write so tests can assert the
    cross-tenant behaviour of the service layer.
    """

    def __init__(self) -> None:
        self._rows: dict[UUID, dict[str, Any]] = {}

    def _row_to_contract(self, row: dict[str, Any]) -> Contract:
        contract = Contract(
            id=row["id"],
            tenant_id=row["tenant_id"],
            customer_id=row["customer_id"],
            location_id=row["location_id"],
            industry=row["industry"],
            title=row["title"],
            description=row.get("description"),
            service_type=row.get("service_type"),
            priority=row["priority"],
            estimated_duration_min=row["estimated_duration_min"],
            frequency=row["frequency"],
            start_date=row["start_date"],
            next_due=row["next_due"],
            end_date=row.get("end_date"),
            status=row["status"],
            paused_at=row.get("paused_at"),
            ended_at=row.get("ended_at"),
            end_reason=row.get("end_reason"),
            custom_fields=deepcopy(row.get("custom_fields", {})),
            external_id=row.get("external_id"),
            created_by_user_id=row["created_by_user_id"],
        )
        contract.created_at = row["created_at"]
        contract.updated_at = row["updated_at"]
        return contract

    async def create(
        self,
        tenant_id: UUID,
        *,
        customer_id: UUID,
        location_id: UUID,
        industry: str,
        title: str,
        description: str | None = None,
        service_type: str | None = None,
        priority: int = 50,
        estimated_duration_min: int = 60,
        frequency: str,
        start_date: date,
        next_due: date,
        end_date: date | None = None,
        custom_fields: dict | None = None,
        created_by_user_id: UUID,
    ) -> Contract:
        """Insert and return a freshly minted :class:`Contract`."""
        cid = uuid4()
        now = datetime.now(UTC)
        self._rows[cid] = {
            "id": cid,
            "tenant_id": tenant_id,
            "customer_id": customer_id,
            "location_id": location_id,
            "industry": industry,
            "title": title,
            "description": description,
            "service_type": service_type,
            "priority": priority,
            "estimated_duration_min": estimated_duration_min,
            "frequency": frequency,
            "start_date": start_date,
            "next_due": next_due,
            "end_date": end_date,
            "status": "active",
            "paused_at": None,
            "ended_at": None,
            "end_reason": None,
            "custom_fields": deepcopy(custom_fields or {}),
            "external_id": None,
            "created_by_user_id": created_by_user_id,
            "created_at": now,
            "updated_at": now,
        }
        return self._row_to_contract(self._rows[cid])

    async def get_by_id(self, contract_id: UUID, tenant_id: UUID) -> Contract | None:
        """Return the contract if it exists in this tenant's scope."""
        row = self._rows.get(contract_id)
        if row is None or row["tenant_id"] != tenant_id:
            return None
        return self._row_to_contract(row)

    async def list(
        self,
        tenant_id: UUID,
        *,
        status: list[str] | None = None,
        customer_id: UUID | None = None,
        due_before: date | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Contract], int]:
        """Return ``(rows, total)`` matching the filter."""
        rows = [r for r in self._rows.values() if r["tenant_id"] == tenant_id]

        if status:
            rows = [r for r in rows if r["status"] in status]
        if customer_id is not None:
            rows = [r for r in rows if r["customer_id"] == customer_id]
        if due_before is not None:
            rows = [r for r in rows if r["next_due"] <= due_before]
        if search:
            needle = search.lower()
            rows = [
                r
                for r in rows
                if needle in (r["title"] or "").lower()
                or needle in ((r.get("description") or "").lower())
            ]

        rows.sort(key=lambda r: (r["next_due"], r["created_at"]))
        total = len(rows)
        page = rows[offset : offset + limit]
        return [self._row_to_contract(r) for r in page], total

    async def update_fields(self, contract_id: UUID, tenant_id: UUID, **patch: Any) -> Contract:
        """Apply a partial update; raises if cross-tenant or absent."""
        row = self._rows.get(contract_id)
        if row is None or row["tenant_id"] != tenant_id:
            raise ContractNotFoundError(f"Contract {contract_id} not found")
        for key, value in deepcopy(patch).items():
            row[key] = value
        row["updated_at"] = datetime.now(UTC)
        return self._row_to_contract(row)

    async def update_status(
        self,
        contract_id: UUID,
        tenant_id: UUID,
        new_status: str,
        *,
        paused_at: datetime | None = None,
        ended_at: datetime | None = None,
        end_reason: str | None = None,
    ) -> Contract:
        """Set status + lifecycle timestamp atomically."""
        row = self._rows.get(contract_id)
        if row is None or row["tenant_id"] != tenant_id:
            raise ContractNotFoundError(f"Contract {contract_id} not found")
        row["status"] = new_status
        if paused_at is not None:
            row["paused_at"] = paused_at
        if ended_at is not None:
            row["ended_at"] = ended_at
        if end_reason is not None:
            row["end_reason"] = end_reason
        row["updated_at"] = datetime.now(UTC)
        return self._row_to_contract(row)

    async def list_due(self, tenant_id: UUID, as_of: date) -> list[Contract]:
        """Return active contracts with ``next_due <= as_of`` (generation pass)."""
        rows = [
            r
            for r in self._rows.values()
            if r["tenant_id"] == tenant_id and r["status"] == "active" and r["next_due"] <= as_of
        ]
        rows.sort(key=lambda r: r["next_due"])
        return [self._row_to_contract(r) for r in rows]
