from __future__ import annotations

from uuid import UUID

from office_hero.adapters.back_office import BackOfficeAdapter, Customer, Job


class BackOfficeService:
    """Thin service layer that delegates to a BackOfficeAdapter.

    Keeping the logic here will make it easier to unit-test business rules
    without needing a concrete adapter implementation.
    """

    def __init__(self, adapter: BackOfficeAdapter):
        self._adapter = adapter

    async def upsert_customer(self, customer: Customer) -> Customer:
        """Create or update a customer in the back-office system."""
        existing = await self._adapter.get_customer(customer.id)
        if existing is None:
            return await self._adapter.create_customer(customer)
        return await self._adapter.update_customer(customer)

    async def get_job(self, job_id: UUID) -> Job | None:
        return await self._adapter.get_job(job_id)

    # further business operations will be added as slices evolve
