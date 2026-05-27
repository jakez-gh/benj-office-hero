"""Customer repository — protocol, SQLAlchemy impl, and in-memory mock.

The protocol is what the service layer depends on (ADR 058). The concrete
SQLAlchemy implementation is the production binding. The in-memory mock is
used by unit tests so the service layer can be exercised without a database.
All implementations enforce tenant scoping defensively (ADR 053
defence-in-depth on top of RLS).
"""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from office_hero.core.exceptions import CustomerNotFoundError
from office_hero.models.customer import Customer


@runtime_checkable
class CustomerRepositoryProtocol(Protocol):
    """Repository contract for :class:`Customer` persistence."""

    async def create(
        self,
        tenant_id: UUID,
        *,
        name: str,
        email: str | None = None,
        phone: str | None = None,
        notes: str | None = None,
        external_id: str | None = None,
    ) -> Customer: ...

    async def get_by_id(self, customer_id: UUID, tenant_id: UUID) -> Customer | None: ...

    async def list(
        self,
        tenant_id: UUID,
        *,
        search: str | None = None,
        archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Customer], int]: ...

    async def update(self, customer_id: UUID, tenant_id: UUID, **patch: Any) -> Customer: ...

    async def archive(self, customer_id: UUID, tenant_id: UUID) -> Customer: ...

    async def restore(self, customer_id: UUID, tenant_id: UUID) -> Customer: ...


class CustomerRepository:
    """SQLAlchemy-backed concrete :class:`Customer` repository (ADR 058)."""

    def __init__(self, session: AsyncSession):
        """Bind to an async SQLAlchemy session."""
        self.session = session

    async def create(
        self,
        tenant_id: UUID,
        *,
        name: str,
        email: str | None = None,
        phone: str | None = None,
        notes: str | None = None,
        external_id: str | None = None,
    ) -> Customer:
        """Insert and flush a new :class:`Customer`."""
        cust = Customer(
            tenant_id=tenant_id,
            name=name,
            email=email,
            phone=phone,
            notes=notes,
            external_id=external_id,
            archived=False,
        )
        self.session.add(cust)
        await self.session.flush()
        return cust

    async def get_by_id(self, customer_id: UUID, tenant_id: UUID) -> Customer | None:
        """Fetch a customer if it exists in ``tenant_id`` (defence-in-depth)."""
        stmt = select(Customer).where(Customer.id == customer_id, Customer.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list(
        self,
        tenant_id: UUID,
        *,
        search: str | None = None,
        archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Customer], int]:
        """Return ``(rows, total)`` for a tenant, optionally substring-filtered."""
        where_clauses = [Customer.tenant_id == tenant_id, Customer.archived.is_(archived)]
        if search:
            pattern = f"%{search}%"
            where_clauses.append(or_(Customer.name.ilike(pattern), Customer.email.ilike(pattern)))

        count_stmt = select(func.count(Customer.id)).where(*where_clauses)
        total = int((await self.session.execute(count_stmt)).scalar_one())

        rows_stmt = (
            select(Customer)
            .where(*where_clauses)
            .order_by(Customer.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = list((await self.session.execute(rows_stmt)).scalars().all())
        return rows, total

    async def update(self, customer_id: UUID, tenant_id: UUID, **patch: Any) -> Customer:
        """Apply a partial update; raises :class:`CustomerNotFoundError` if absent."""
        cust = await self.get_by_id(customer_id, tenant_id)
        if cust is None:
            raise CustomerNotFoundError(f"Customer {customer_id} not found")
        for key, value in patch.items():
            if value is None and key in {"name"}:
                # Don't allow setting required columns to NULL.
                continue
            setattr(cust, key, value)
        await self.session.flush()
        return cust

    async def archive(self, customer_id: UUID, tenant_id: UUID) -> Customer:
        """Mark a customer archived (soft delete)."""
        return await self.update(customer_id, tenant_id, archived=True)

    async def restore(self, customer_id: UUID, tenant_id: UUID) -> Customer:
        """Clear the archived flag."""
        return await self.update(customer_id, tenant_id, archived=False)


class InMemoryCustomerRepository:
    """In-memory mock implementing :class:`CustomerRepositoryProtocol`.

    Used by unit tests so the service layer can be exercised without a DB.
    Tenant scope is honoured on every read/write so tests can assert the
    cross-tenant behaviour of the service layer.
    """

    def __init__(self) -> None:
        # Snapshot dict {customer_id -> dict}. We store dicts (not the ORM
        # object) and rebuild Customer instances on each read so callers
        # can mutate freely without corrupting the store.
        self._rows: dict[UUID, dict[str, Any]] = {}

    def _row_to_customer(self, row: dict[str, Any]) -> Customer:
        cust = Customer(
            id=row["id"],
            tenant_id=row["tenant_id"],
            name=row["name"],
            email=row.get("email"),
            phone=row.get("phone"),
            notes=row.get("notes"),
            archived=row.get("archived", False),
            external_id=row.get("external_id"),
        )
        cust.created_at = row["created_at"]
        cust.updated_at = row["updated_at"]
        return cust

    async def create(
        self,
        tenant_id: UUID,
        *,
        name: str,
        email: str | None = None,
        phone: str | None = None,
        notes: str | None = None,
        external_id: str | None = None,
    ) -> Customer:
        """Insert and return a freshly minted :class:`Customer`."""
        cid = uuid4()
        now = datetime.now(UTC)
        self._rows[cid] = {
            "id": cid,
            "tenant_id": tenant_id,
            "name": name,
            "email": email,
            "phone": phone,
            "notes": notes,
            "external_id": external_id,
            "archived": False,
            "created_at": now,
            "updated_at": now,
        }
        return self._row_to_customer(self._rows[cid])

    async def get_by_id(self, customer_id: UUID, tenant_id: UUID) -> Customer | None:
        """Return the customer if it exists in this tenant's scope."""
        row = self._rows.get(customer_id)
        if row is None or row["tenant_id"] != tenant_id:
            return None
        return self._row_to_customer(row)

    async def list(
        self,
        tenant_id: UUID,
        *,
        search: str | None = None,
        archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Customer], int]:
        """Return ``(rows, total)`` matching the filter."""
        needle = search.lower() if search else None
        rows = [
            r
            for r in self._rows.values()
            if r["tenant_id"] == tenant_id and r["archived"] == archived
        ]
        if needle is not None:
            rows = [
                r
                for r in rows
                if needle in (r["name"] or "").lower() or needle in ((r.get("email") or "").lower())
            ]
        rows.sort(key=lambda r: r["created_at"], reverse=True)
        total = len(rows)
        page = rows[offset : offset + limit]
        return [self._row_to_customer(r) for r in page], total

    async def update(self, customer_id: UUID, tenant_id: UUID, **patch: Any) -> Customer:
        """Apply a partial update; raises if cross-tenant or absent."""
        row = self._rows.get(customer_id)
        if row is None or row["tenant_id"] != tenant_id:
            raise CustomerNotFoundError(f"Customer {customer_id} not found")
        # Avoid mutating the caller's patch dict accidentally.
        for key, value in deepcopy(patch).items():
            if key == "name" and value is None:
                continue
            row[key] = value
        row["updated_at"] = datetime.now(UTC)
        return self._row_to_customer(row)

    async def archive(self, customer_id: UUID, tenant_id: UUID) -> Customer:
        """Mark the customer archived."""
        return await self.update(customer_id, tenant_id, archived=True)

    async def restore(self, customer_id: UUID, tenant_id: UUID) -> Customer:
        """Clear the archived flag."""
        return await self.update(customer_id, tenant_id, archived=False)
