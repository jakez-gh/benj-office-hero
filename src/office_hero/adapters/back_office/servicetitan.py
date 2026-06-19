"""ServiceTitan BackOfficeAdapter — Slice 26.

Implements :class:`~office_hero.adapters.back_office.BackOfficeAdapter` against
the ServiceTitan v2 REST API.

Auth
----
4-credential ``client_credentials`` OAuth2 flow.  The token endpoint requires
``application/x-www-form-urlencoded`` (JSON returns 400).  Tokens last 900 s;
we reuse within 840 s to leave a 60 s margin.

Idempotency
-----------
ServiceTitan has no server-side idempotency key.  We use the ``externalData``
field on customers (applicationGuid=``office-hero``, key=``internal_id``,
value=<our UUID>) and the native ``externalId`` field on jobs.  Every mutating
method queries first and short-circuits if the record already exists.

Rate limits
-----------
60 req/s per tenant.  On HTTP 429 we retry up to 3 times with exponential
backoff (1 s, 2 s, 4 s).

Required env vars
-----------------
SERVICETITAN_CLIENT_ID
SERVICETITAN_CLIENT_SECRET
SERVICETITAN_APP_KEY
SERVICETITAN_TENANT_ID   (integer tenant id in the ST system)
SERVICETITAN_SANDBOX     (optional, "true" to use integration endpoints)
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

import httpx

from office_hero.adapters.back_office import BackOfficeAdapter, Customer, Job  # noqa: F401

APP_GUID = "office-hero"

_PROD_AUTH = "https://auth.servicetitan.io/connect/token"
_SANDBOX_AUTH = "https://auth-integration.servicetitan.io/connect/token"
_PROD_API = "https://api.servicetitan.io"
_SANDBOX_API = "https://api-integration.servicetitan.io"

_TOKEN_REUSE_WINDOW = 840  # seconds — 60 s margin before the 900 s lifetime


@dataclass
class ServiceTitanConfig:
    client_id: str
    client_secret: str
    app_key: str
    st_tenant_id: int
    sandbox: bool = False

    @property
    def auth_url(self) -> str:
        return _SANDBOX_AUTH if self.sandbox else _PROD_AUTH

    @property
    def api_base(self) -> str:
        return _SANDBOX_API if self.sandbox else _PROD_API

    @classmethod
    def from_env(cls) -> "ServiceTitanConfig":
        """Build config from environment variables; raises KeyError if any are missing."""
        return cls(
            client_id=os.environ["SERVICETITAN_CLIENT_ID"],
            client_secret=os.environ["SERVICETITAN_CLIENT_SECRET"],
            app_key=os.environ["SERVICETITAN_APP_KEY"],
            st_tenant_id=int(os.environ["SERVICETITAN_TENANT_ID"]),
            sandbox=os.environ.get("SERVICETITAN_SANDBOX", "false").lower() == "true",
        )


class ServiceTitanAdapter:
    """Async BackOfficeAdapter backed by the ServiceTitan v2 API."""

    name = "servicetitan"

    def __init__(self, config: ServiceTitanConfig, http: httpx.AsyncClient | None = None) -> None:
        self._cfg = config
        self._http = http or httpx.AsyncClient()
        self._token: str | None = None
        self._token_expiry: float = 0.0  # monotonic time

    # ------------------------------------------------------------------
    # Protocol classmethod — called by the registry
    # ------------------------------------------------------------------

    @classmethod
    def from_tenant(
        cls,
        tenant_id: UUID,  # noqa: ARG003  — reserved for per-tenant credential lookup
        customer_repo: Any,  # noqa: ARG003
        job_repo: Any,  # noqa: ARG003
    ) -> "ServiceTitanAdapter":
        """Factory matching the :data:`AdapterFactory` signature."""
        return cls(config=ServiceTitanConfig.from_env())

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    async def _get_token(self) -> str:
        """Return a valid bearer token, refreshing if needed."""
        now = time.monotonic()
        if self._token and now < self._token_expiry:
            return self._token

        resp = await self._http.post(
            self._cfg.auth_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self._cfg.client_id,
                "client_secret": self._cfg.client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        payload = resp.json()
        self._token = payload["access_token"]
        expires_in: int = payload.get("expires_in", 900)
        self._token_expiry = now + min(expires_in, _TOKEN_REUSE_WINDOW)
        return self._token  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Low-level API call with retry
    # ------------------------------------------------------------------

    async def _api(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Make an authenticated request; retry on 429 (up to 3 times)."""
        token = await self._get_token()
        url = f"{self._cfg.api_base}{path}"
        headers = {
            "Authorization": f"Bearer {token}",
            "ST-App-Key": self._cfg.app_key,
            **(kwargs.pop("headers", {})),
        }

        max_retries = 3
        backoff = 1.0
        for attempt in range(max_retries + 1):
            resp = await self._http.request(method, url, headers=headers, **kwargs)
            if resp.status_code == 429 and attempt < max_retries:
                await asyncio.sleep(backoff)
                backoff *= 2
                # Re-fetch token in case it changed between retries
                token = await self._get_token()
                headers["Authorization"] = f"Bearer {token}"
                continue
            resp.raise_for_status()
            return resp

        # Unreachable, but satisfies the type checker
        resp.raise_for_status()  # pragma: no cover
        return resp  # pragma: no cover

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _tid(self) -> int:
        return self._cfg.st_tenant_id

    async def _find_customer_by_external_id(self, internal_id: UUID) -> dict[str, Any] | None:
        """Query ST for a customer using our externalData UUID tag."""
        resp = await self._api(
            "GET",
            f"/crm/v2/tenant/{self._tid()}/customers",
            params={
                "externalData.applicationGuid": APP_GUID,
                "externalData.key": "internal_id",
                "externalData.value": str(internal_id),
                "pageSize": 1,
            },
        )
        data = resp.json()
        items = data.get("data") or []
        return items[0] if items else None

    async def _find_job_by_external_id(self, internal_id: UUID) -> dict[str, Any] | None:
        """Query ST for a job using our externalId field."""
        resp = await self._api(
            "GET",
            f"/jpm/v2/tenant/{self._tid()}/jobs",
            params={"externalId": str(internal_id), "pageSize": 1},
        )
        data = resp.json()
        items = data.get("data") or []
        return items[0] if items else None

    # ------------------------------------------------------------------
    # Protocol: BackOfficeAdapter
    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        try:
            await self._api(
                "GET",
                f"/crm/v2/tenant/{self._tid()}/customers",
                params={"pageSize": 1},
            )
            return True
        except Exception:
            return False

    # -- Customer ----------------------------------------------------------

    async def get_customer(self, id: UUID) -> Customer | None:
        row = await self._find_customer_by_external_id(id)
        if row is None:
            return None
        return Customer(id=id, name=row["name"])

    async def create_customer(self, customer: Customer) -> Customer:
        # Idempotency: return early if ST already has this customer
        existing = await self._find_customer_by_external_id(customer.id)
        if existing:
            return customer

        # Create the customer record
        resp = await self._api(
            "POST",
            f"/crm/v2/tenant/{self._tid()}/customers",
            json={
                "name": customer.name,
                "type": "Residential",
                "active": True,
                "externalData": [
                    {
                        "applicationGuid": APP_GUID,
                        "key": "internal_id",
                        "value": str(customer.id),
                    }
                ],
            },
        )
        st_customer_id: int = resp.json()["id"]

        # Every ST customer requires at least one location
        await self._api(
            "POST",
            f"/crm/v2/tenant/{self._tid()}/locations",
            json={
                "customerId": st_customer_id,
                "name": "Default",
                "address": {"zip": "00000"},
            },
        )

        return customer

    async def update_customer(self, customer: Customer) -> Customer:
        row = await self._find_customer_by_external_id(customer.id)
        if row is None:
            return await self.create_customer(customer)

        await self._api(
            "PATCH",
            f"/crm/v2/tenant/{self._tid()}/customers/{row['id']}",
            json={"name": customer.name},
        )
        return customer

    async def delete_customer(self, id: UUID) -> None:
        row = await self._find_customer_by_external_id(id)
        if row is None:
            return None  # idempotent

        await self._api(
            "PATCH",
            f"/crm/v2/tenant/{self._tid()}/customers/{row['id']}",
            json={"active": False},
        )
        return None

    # -- Job ---------------------------------------------------------------

    async def get_job(self, id: UUID) -> Job | None:
        row = await self._find_job_by_external_id(id)
        if row is None:
            return None
        # We can't easily map ST's integer customerId back to our UUID without
        # another externalData lookup — return a sentinel UUID so callers know
        # the job exists.  Customer linkage is a future enhancement (Slice 27+).
        return Job(id=id, customer_id=UUID(int=0))

    async def create_job(self, job: Job) -> Job:
        # Idempotency: return early if ST already has this job
        existing = await self._find_job_by_external_id(job.id)
        if existing:
            return job

        # We need the ST integer customerId to create a job
        customer_row = await self._find_customer_by_external_id(job.customer_id)
        if customer_row is None:
            raise ValueError(
                f"ServiceTitan customerId not found for customer {job.customer_id}. "
                "Ensure create_customer was called before create_job."
            )

        # Derive the location from the customer record (first location)
        locations_resp = await self._api(
            "GET",
            f"/crm/v2/tenant/{self._tid()}/locations",
            params={"customerId": customer_row["id"], "pageSize": 1},
        )
        locations = locations_resp.json().get("data") or []
        location_id: int | None = locations[0]["id"] if locations else None

        if location_id is None:
            raise ValueError(
                f"ServiceTitan location not found for customer {job.customer_id}. "
                "Cannot create job without a location."
            )

        await self._api(
            "POST",
            f"/jpm/v2/tenant/{self._tid()}/jobs",
            json={
                "customerId": customer_row["id"],
                "locationId": location_id,
                "externalId": str(job.id),
                "jobTypeId": 1,
                "priority": "Normal",
                "summary": "Synced from Office Hero",
            },
        )
        return job

    async def update_job(self, job: Job) -> Job:
        row = await self._find_job_by_external_id(job.id)
        if row is None:
            return await self.create_job(job)

        await self._api(
            "PATCH",
            f"/jpm/v2/tenant/{self._tid()}/jobs/{row['id']}",
            json={"priority": "Normal"},
        )
        return job

    async def delete_job(self, id: UUID) -> None:
        row = await self._find_job_by_external_id(id)
        if row is None:
            return None  # idempotent

        await self._api(
            "PATCH",
            f"/jpm/v2/tenant/{self._tid()}/jobs/{row['id']}",
            json={"summary": "Cancelled via Office Hero sync"},
        )
        return None
