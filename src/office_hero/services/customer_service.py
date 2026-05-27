"""CustomerService — orchestrates customer CRUD and emits audit events.

The service depends on a :class:`CustomerRepositoryProtocol` and an audit
publisher with the ``log_event`` method shape established in slice 4. Audit
payloads must never carry raw PII unnecessarily — long free-text ``notes``
fields are truncated before being recorded.
"""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from office_hero.core.exceptions import CustomerNotFoundError, DuplicateEmailError
from office_hero.core.logging import get_logger
from office_hero.models.customer import Customer
from office_hero.repositories.customer_repository import (
    CustomerRepositoryProtocol,
)
# Type alias for the richer list-with-location-stats return
CustomerSummaryRow = tuple[Customer, int, str | None]

log = get_logger(__name__)


_NOTES_MAX_LEN_IN_AUDIT = 256


class AuditPublisher(Protocol):
    """Minimal audit-publisher contract the service depends on (ADR 063)."""

    async def log_event(
        self,
        event_type: str,
        details: dict,
        tenant_id: UUID,
        user_id: UUID | None = None,
        request_id: UUID | None = None,
    ) -> None: ...


def _truncate_notes_value(value: Any) -> Any:
    """Return ``value`` truncated if it's a long free-text notes string."""
    if isinstance(value, str) and len(value) > _NOTES_MAX_LEN_IN_AUDIT:
        return value[:_NOTES_MAX_LEN_IN_AUDIT] + "...[truncated]"
    return value


def _redact_notes(details: dict[str, Any]) -> dict[str, Any]:
    """Truncate any ``notes`` strings (top-level or inside before/after).

    Audit details may contain ``notes`` directly (create) or inside a diff
    bag (``before``/``after`` from update). Both shapes are handled here so
    PII can't sneak through one path.
    """
    if "notes" in details:
        details["notes"] = _truncate_notes_value(details["notes"])
    for bag_key in ("before", "after"):
        bag = details.get(bag_key)
        if isinstance(bag, dict) and "notes" in bag:
            bag["notes"] = _truncate_notes_value(bag["notes"])
    return details


def _customer_summary(cust: Customer) -> dict[str, Any]:
    """Audit-safe customer projection (no notes/email-detail)."""
    return {
        "customer_id": str(cust.id),
        "name": cust.name,
        "archived": cust.archived,
    }


class CustomerService:
    """Business orchestration for the :class:`Customer` aggregate."""

    def __init__(
        self,
        repo: CustomerRepositoryProtocol,
        audit: AuditPublisher,
    ):
        """Inject the repository and the audit publisher (DI)."""
        self.repo = repo
        self.audit = audit

    async def create(
        self,
        tenant_id: UUID,
        user_id: UUID,
        *,
        name: str,
        email: str | None = None,
        phone: str | None = None,
        notes: str | None = None,
        external_id: str | None = None,
    ) -> Customer:
        """Create a customer; emit ``customer.created``."""
        cust = await self.repo.create(
            tenant_id,
            name=name,
            email=email,
            phone=phone,
            notes=notes,
            external_id=external_id,
        )
        details = _redact_notes(
            {
                **_customer_summary(cust),
                "email": email,
                "phone": phone,
                "notes": notes,
            }
        )
        await self.audit.log_event(
            event_type="customer.created",
            details=details,
            tenant_id=tenant_id,
            user_id=user_id,
        )
        return cust

    async def get(self, tenant_id: UUID, customer_id: UUID) -> Customer:
        """Fetch a customer or raise :class:`CustomerNotFoundError`."""
        cust = await self.repo.get_by_id(customer_id, tenant_id)
        if cust is None:
            raise CustomerNotFoundError(f"Customer {customer_id} not found")
        return cust

    async def list(
        self,
        tenant_id: UUID,
        *,
        search: str | None = None,
        archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Customer], int]:
        """Return ``(rows, total)`` for a tenant, filtered."""
        return await self.repo.list(
            tenant_id, search=search, archived=archived, limit=limit, offset=offset
        )

    async def list_summaries(
        self,
        tenant_id: UUID,
        *,
        search: str | None = None,
        archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[CustomerSummaryRow], int]:
        """Return ``(rows, total)`` where each row includes location_count and primary_city."""
        return await self.repo.list_summaries(
            tenant_id, search=search, archived=archived, limit=limit, offset=offset
        )

    async def update(
        self,
        tenant_id: UUID,
        user_id: UUID,
        customer_id: UUID,
        patch: dict[str, Any],
    ) -> Customer:
        """Update a customer; emit ``customer.updated`` with the diff."""
        existing = await self.get(tenant_id, customer_id)

        before: dict[str, Any] = {}
        after: dict[str, Any] = {}
        for key, value in patch.items():
            current = getattr(existing, key, None)
            if current != value:
                before[key] = current
                after[key] = value

        updated = await self.repo.update(customer_id, tenant_id, **patch)
        details = _redact_notes(
            {
                "customer_id": str(updated.id),
                "before": before,
                "after": after,
            }
        )
        await self.audit.log_event(
            event_type="customer.updated",
            details=details,
            tenant_id=tenant_id,
            user_id=user_id,
        )
        return updated

    async def archive(self, tenant_id: UUID, user_id: UUID, customer_id: UUID) -> Customer:
        """Soft-delete; emit ``customer.archived``."""
        # Make sure it exists in this tenant first so we surface a clean
        # CustomerNotFoundError rather than a generic repo error.
        await self.get(tenant_id, customer_id)
        archived = await self.repo.archive(customer_id, tenant_id)
        await self.audit.log_event(
            event_type="customer.archived",
            details=_customer_summary(archived),
            tenant_id=tenant_id,
            user_id=user_id,
        )
        return archived

    async def restore(self, tenant_id: UUID, user_id: UUID, customer_id: UUID) -> Customer:
        """Clear archived; emit ``customer.restored``."""
        await self.get(tenant_id, customer_id)
        restored = await self.repo.restore(customer_id, tenant_id)
        await self.audit.log_event(
            event_type="customer.restored",
            details=_customer_summary(restored),
            tenant_id=tenant_id,
            user_id=user_id,
        )
        return restored
