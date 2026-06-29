"""PestPac (WorkWave Service / Odyssey API) BackOfficeAdapter (Slice 27).

DESIGN BLOCKER — do not complete this adapter until the following question
is resolved via sandbox access (see RES-026, open question #1):

    Does the Odyssey API return the created entity synchronously, or does it
    return a ``requestId`` immediately (asynchronous pattern, like the WWRM
    sibling API)?

If the Odyssey API is asynchronous, the ``BackOfficeAdapter`` protocol's
synchronous return contract (``create_customer`` returns ``Customer``) cannot
be satisfied without a polling loop.  That may require a protocol amendment
(ADR update) before this file can be completed.

Everything up to and including the HTTP call layer is scaffolded here and can
be finished the same session sandbox credentials arrive.

Auth: ``X-API-Key`` header (``PESTPAC_API_KEY`` env var).
Sandbox base URL: ``https://sandbox-api.service.workwave.com/api/public/v1``
Production base URL: ``https://prod-api.service.workwave.com/api/public/v1``
Company key (6-digit tenant ID): ``PESTPAC_COMPANY_KEY`` env var.

See ``project-documents/user/research/026-research.pestpac-api.md`` for full
findings and open questions.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from uuid import UUID

import httpx

from office_hero.adapters.back_office import Customer, Job


@dataclass
class PestPacConfig:
    """Configuration for one PestPac (WorkWave) tenant."""

    api_key: str
    company_key: str  # 6-digit PestPac CompanyKey (tenant identifier)
    sandbox: bool = False

    # Required fields for Location (Customer) creation; sensible defaults may
    # be overridden per tenant in the future.  PestPac requires Division,
    # Source, and Type on every Location create.
    default_division: str = "1"
    default_source: str = "Office Hero"
    default_type: str = "Residential"

    @property
    def base_url(self) -> str:
        if self.sandbox:
            return "https://sandbox-api.service.workwave.com/api/public/v1"
        return "https://prod-api.service.workwave.com/api/public/v1"

    @classmethod
    def from_env(cls) -> PestPacConfig:
        return cls(
            api_key=os.environ["PESTPAC_API_KEY"],
            company_key=os.environ["PESTPAC_COMPANY_KEY"],
            sandbox=os.environ.get("PESTPAC_SANDBOX", "false").lower() == "true",
            default_division=os.environ.get("PESTPAC_DEFAULT_DIVISION", "1"),
            default_source=os.environ.get("PESTPAC_DEFAULT_SOURCE", "Office Hero"),
            default_type=os.environ.get("PESTPAC_DEFAULT_TYPE", "Residential"),
        )


class PestPacAdapter:
    """BackOfficeAdapter for PestPac (WorkWave Odyssey API).

    PARTIALLY IMPLEMENTED — see module docstring for the design blocker.
    All methods raise ``NotImplementedError`` with a descriptive message until
    the sync/async response model is confirmed and the HTTP call layer is
    completed.
    """

    name = "pestpac"

    def __init__(self, config: PestPacConfig, http: httpx.AsyncClient | None = None) -> None:
        self._cfg = config
        self._http = http or httpx.AsyncClient(timeout=30.0)
        # In-memory entity cache: (entity_type, internal_id) → pestpac_id (str)
        # Production: replace with pestpac_entity_map table queries.
        self._entity_cache: dict[tuple[str, UUID], str] = {}

    @classmethod
    def from_tenant(
        cls, tenant_id: UUID, customer_repo: object, job_repo: object
    ) -> PestPacAdapter:
        return cls(PestPacConfig.from_env())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self._cfg.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _request(self, method: str, path: str, **kwargs: object) -> httpx.Response:
        """Issue a single API request with basic 429 backoff."""
        url = f"{self._cfg.base_url}{path}"
        for attempt in range(3):
            resp = await self._http.request(
                method, url, headers=self._headers(), **kwargs  # type: ignore[arg-type]
            )
            if resp.status_code == 429:
                await asyncio.sleep(2**attempt)
                continue
            resp.raise_for_status()
            return resp
        resp.raise_for_status()
        return resp  # unreachable; satisfies type checker

    def _cache_get(self, entity_type: str, internal_id: UUID) -> str | None:
        return self._entity_cache.get((entity_type, internal_id))

    def _cache_set(self, entity_type: str, internal_id: UUID, pestpac_id: str) -> None:
        self._entity_cache[(entity_type, internal_id)] = pestpac_id

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        """Probe the Odyssey API with a minimal list request."""
        try:
            # GET workorders with a very small limit as a connectivity probe.
            await self._request(
                "GET",
                "/workorders",
                params={"companyKey": self._cfg.company_key, "pageSize": 1},
            )
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Customer / Location operations
    # ------------------------------------------------------------------

    async def get_customer(self, id: UUID) -> Customer | None:
        """Look up a PestPac Location by our internal UUID.

        Uses the in-memory entity cache (seeded by ``create_customer``).
        Production: query ``pestpac_entity_map`` table.
        """
        pestpac_id = self._cache_get("location", id)
        if pestpac_id is None:
            return None
        # TODO(slice-27): GET /locations/{pestpac_id} and map to Customer.
        # Blocked on confirming the exact Odyssey endpoint path.
        raise NotImplementedError(
            "PestPacAdapter.get_customer: HTTP call layer not yet implemented. "
            "Resolve RES-026 open question #1 (sync vs. async response) and confirm "
            "the /locations/{id} endpoint path before completing this method."
        )

    async def create_customer(self, customer: Customer) -> Customer:
        """Create a PestPac BillTo Location for this Customer.

        BLOCKED — see module-level docstring.  Returns the customer unchanged
        for now so the Outbox can be tested end-to-end with a mock adapter;
        the real implementation is the first thing to complete when sandbox
        access is available.
        """
        # Idempotency check
        if self._cache_get("location", customer.id) is not None:
            return customer  # already created

        # TODO(slice-27): POST /locations with:
        # {
        #   "companyKey": self._cfg.company_key,
        #   "name": customer.name,
        #   "division": self._cfg.default_division,
        #   "source": self._cfg.default_source,
        #   "type": self._cfg.default_type,
        #   "phone": "0000000000",  # placeholder; extend Customer dataclass later
        # }
        # Then: self._cache_set("location", customer.id, str(response["locationCode"]))
        #
        # Design blocker: confirm Odyssey API returns entity synchronously
        # (not just a requestId).
        raise NotImplementedError(
            "PestPacAdapter.create_customer: HTTP call layer not yet implemented. "
            "Resolve RES-026 open question #1 before completing."
        )

    async def update_customer(self, customer: Customer) -> Customer:
        """Update a PestPac Location name."""
        pestpac_id = self._cache_get("location", customer.id)
        if pestpac_id is None:
            return await self.create_customer(customer)
        # TODO(slice-27): PATCH /locations/{pestpac_id}
        raise NotImplementedError("PestPacAdapter.update_customer: not yet implemented.")

    async def delete_customer(self, id: UUID) -> None:
        """Deactivate a PestPac Location (no hard-delete in PestPac)."""
        pestpac_id = self._cache_get("location", id)
        if pestpac_id is None:
            return
        # TODO(slice-27): PATCH /locations/{pestpac_id} with {"active": false}
        raise NotImplementedError("PestPacAdapter.delete_customer: not yet implemented.")

    # ------------------------------------------------------------------
    # Job / Work Order operations
    # ------------------------------------------------------------------

    async def get_job(self, id: UUID) -> Job | None:
        """Look up a PestPac Work Order by our internal UUID."""
        pestpac_id = self._cache_get("workorder", id)
        if pestpac_id is None:
            return None
        # TODO(slice-27): GET /workorders/{pestpac_id}
        raise NotImplementedError("PestPacAdapter.get_job: not yet implemented.")

    async def create_job(self, job: Job) -> Job:
        """Create a PestPac Work Order for this Job.

        Requires the PestPac LocationCode for ``job.customer_id`` to be in the
        entity cache (i.e. ``create_customer`` must have been called first for
        the same tenant session).
        """
        if self._cache_get("workorder", job.id) is not None:
            return job  # idempotent

        customer_pestpac_id = self._cache_get("location", job.customer_id)
        if customer_pestpac_id is None:
            raise ValueError(
                f"PestPac LocationCode not found for customer {job.customer_id}. "
                "create_customer must succeed before create_job."
            )

        # TODO(slice-27): POST /workorders with:
        # {
        #   "companyKey": self._cfg.company_key,
        #   "locationCode": customer_pestpac_id,
        #   "serviceType": "General",  # placeholder
        # }
        # Then: self._cache_set("workorder", job.id, str(response["workOrderId"]))
        raise NotImplementedError("PestPacAdapter.create_job: not yet implemented.")

    async def update_job(self, job: Job) -> Job:
        """Update a PestPac Work Order."""
        pestpac_id = self._cache_get("workorder", job.id)
        if pestpac_id is None:
            return await self.create_job(job)
        # TODO(slice-27): PATCH /workorders/{pestpac_id}
        raise NotImplementedError("PestPacAdapter.update_job: not yet implemented.")

    async def delete_job(self, id: UUID) -> None:
        """Cancel a PestPac Work Order."""
        pestpac_id = self._cache_get("workorder", id)
        if pestpac_id is None:
            return
        # TODO(slice-27): PATCH /workorders/{pestpac_id} with {"status": "Cancelled"}
        raise NotImplementedError("PestPacAdapter.delete_job: not yet implemented.")
