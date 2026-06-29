"""Jobber GraphQL back-office adapter (Slice 28).

Implements the :class:`~office_hero.adapters.back_office.BackOfficeAdapter`
protocol against Jobber's GraphQL API (2023-11-15).

Auth model
----------
OAuth2 authorization_code flow.  Per-tenant tokens are stored in the
``jobber_credentials`` table (migration 0015).  Access tokens expire after
3600 seconds; refresh tokens rotate on every use — the old refresh token is
invalidated the moment the new one is issued.  ``_refresh_token_if_needed``
handles this automatically; the updated credentials are written back in-memory
and **must** be persisted to the DB by the caller (``from_tenant`` handles this
in production; see the known limitations note below).

Entity mapping
--------------
Jobber has no native external-ID field.  We use app-configured custom fields:

* ``hero_client_id`` on Client (Text)
* ``hero_job_id`` on Job (Text)

The custom-field configuration IDs are stored in ``jobber_credentials`` after
the first connect (bootstrapped via ``customFieldConfigurationCreate``).

Jobber opaque IDs are stored in ``jobber_entity_map`` (production) or an
in-memory dict (scaffold — see ``_entity_cache``).

Known limitations / production TODOs
-------------------------------------
1. ``_refresh_token_if_needed`` updates credentials in memory only.  A
   ``CredentialsPersistCallback`` should be wired in to persist the rotated
   tokens to ``jobber_credentials`` before the next call.
2. ``_get_entity_map`` / ``_set_entity_map`` use ``self._entity_cache`` (dict).
   Production: query / upsert ``jobber_entity_map``.
3. ``from_tenant`` loads credentials from env vars (single-tenant bootstrap).
   Production: query ``jobber_credentials`` for the tenant row.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import httpx

from office_hero.adapters.back_office import BackOfficeAdapter, Customer, Job  # noqa: F401


class JobberGraphQLError(Exception):
    """Raised when the Jobber GraphQL response contains errors."""

    def __init__(self, errors: list[dict[str, Any]]) -> None:
        msgs = "; ".join(e.get("message", str(e)) for e in errors)
        super().__init__(f"Jobber GraphQL error: {msgs}")
        self.errors = errors


class JobberThrottleError(Exception):
    """Raised when Jobber's leaky-bucket throttle is exhausted."""


# ---------------------------------------------------------------------------
# Configuration / credentials
# ---------------------------------------------------------------------------


@dataclass
class JobberConfig:
    """App-level (not per-tenant) Jobber OAuth2 app configuration."""

    client_id: str
    client_secret: str
    graphql_version: str = "2023-11-15"

    @classmethod
    def from_env(cls) -> JobberConfig:
        return cls(
            client_id=os.environ["JOBBER_CLIENT_ID"],
            client_secret=os.environ["JOBBER_CLIENT_SECRET"],
        )


@dataclass
class JobberCredentials:
    """Per-tenant OAuth2 tokens loaded from ``jobber_credentials`` table."""

    tenant_id: UUID
    access_token: str
    refresh_token: str
    expires_at: datetime
    custom_field_client_config_id: str | None = None
    custom_field_job_config_id: str | None = None


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

_THROTTLE_LOW_WATERMARK = 100  # back off if available points fall below this


class JobberAdapter:
    """Jobber GraphQL back-office adapter.

    Satisfies :class:`~office_hero.adapters.back_office.BackOfficeAdapter`.
    """

    name = "jobber"
    GRAPHQL_URL = "https://api.getjobber.com/api/graphql"
    TOKEN_URL = "https://api.getjobber.com/api/oauth/token"  # noqa: S105 (not a secret)

    def __init__(
        self,
        config: JobberConfig,
        creds: JobberCredentials,
        http: httpx.AsyncClient | None = None,
        *,
        db_init_pending: bool = False,
    ) -> None:
        self._cfg = config
        self._creds = creds
        self._http = http or httpx.AsyncClient(timeout=30.0)
        # When True, _refresh_token_if_needed loads creds from DB before first call.
        self._db_init_pending = db_init_pending
        # Scaffold entity cache: (entity_type, internal_id) -> jobber_id
        # Production: replace with jobber_entity_map table queries.
        self._entity_cache: dict[tuple[str, UUID], str] = {}

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    async def _load_creds_from_db(self) -> None:
        """Load real OAuth2 credentials from the ``jobber_credentials`` table.

        Called on first use when ``from_tenant`` was constructed without env-var
        tokens (production path — tokens come from the Jobber OAuth2 callback).
        """
        from sqlalchemy import select  # noqa: PLC0415

        from office_hero.api.state import get_engine  # noqa: PLC0415
        from office_hero.db.session import get_session  # noqa: PLC0415
        from office_hero.models.jobber_credentials import (  # noqa: PLC0415
            JobberCredentials as JCModel,
        )

        engine = get_engine()
        async with get_session(engine) as session:
            result = await session.execute(
                select(JCModel).where(JCModel.tenant_id == self._creds.tenant_id)
            )
            row = result.scalars().first()
        if row is None:
            raise RuntimeError(
                f"No Jobber credentials found for tenant {self._creds.tenant_id}. "
                "Complete the OAuth2 flow at /admin/integrations/jobber/connect first."
            )
        self._creds.access_token = row.access_token
        self._creds.refresh_token = row.refresh_token
        self._creds.expires_at = row.expires_at
        self._creds.custom_field_client_config_id = row.custom_field_client_config_id
        self._creds.custom_field_job_config_id = row.custom_field_job_config_id
        self._db_init_pending = False

    async def _persist_creds_to_db(self) -> None:
        """Persist refreshed tokens back to ``jobber_credentials``.

        Called after every token refresh so rotated refresh tokens are not lost.
        """
        from sqlalchemy import text  # noqa: PLC0415

        from office_hero.api.state import get_engine  # noqa: PLC0415
        from office_hero.db.session import get_session  # noqa: PLC0415

        try:
            engine = get_engine()
            async with get_session(engine) as session:
                await session.execute(
                    text(
                        "UPDATE jobber_credentials "
                        "SET access_token = :at, refresh_token = :rt, "
                        "    expires_at = :ea, updated_at = NOW() "
                        "WHERE tenant_id = :tid"
                    ),
                    {
                        "at": self._creds.access_token,
                        "rt": self._creds.refresh_token,
                        "ea": self._creds.expires_at,
                        "tid": self._creds.tenant_id,
                    },
                )
                await session.commit()
        except Exception:  # noqa: BLE001 - non-fatal; next process will refresh again
            pass

    async def _refresh_token_if_needed(self) -> None:
        """Refresh the access token if it expires within 5 minutes."""
        if self._db_init_pending:
            await self._load_creds_from_db()

        threshold = datetime.now(tz=UTC) + timedelta(minutes=5)
        if self._creds.expires_at > threshold:
            return

        resp = await self._http.post(
            self.TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": self._creds.refresh_token,
                "client_id": self._cfg.client_id,
                "client_secret": self._cfg.client_secret,
            },
        )
        resp.raise_for_status()
        payload = resp.json()

        self._creds.access_token = payload["access_token"]
        self._creds.refresh_token = payload["refresh_token"]
        self._creds.expires_at = datetime.now(tz=UTC) + timedelta(
            seconds=payload.get("expires_in", 3600)
        )
        await self._persist_creds_to_db()

    # ------------------------------------------------------------------
    # GraphQL transport
    # ------------------------------------------------------------------

    async def _graphql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a GraphQL request and return the ``data`` portion.

        Handles token refresh, throttle back-off, and error unwrapping.
        """
        await self._refresh_token_if_needed()

        resp = await self._http.post(
            self.GRAPHQL_URL,
            json={"query": query, "variables": variables or {}},
            headers={
                "Authorization": f"Bearer {self._creds.access_token}",
                "X-JOBBER-GRAPHQL-VERSION": self._cfg.graphql_version,
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        body = resp.json()

        # Throttle backoff
        try:
            available = body["extensions"]["cost"]["throttleStatus"]["currentlyAvailable"]
            if available < _THROTTLE_LOW_WATERMARK:
                await asyncio.sleep(1)
        except (KeyError, TypeError):
            pass  # throttle info not present on all responses

        if errors := body.get("errors"):
            raise JobberGraphQLError(errors)

        return body.get("data", {})

    # ------------------------------------------------------------------
    # Entity cache (scaffold → production: jobber_entity_map table)
    # ------------------------------------------------------------------

    async def _get_entity_map(self, entity_type: str, internal_id: UUID) -> str | None:
        """Return the Jobber opaque ID for an internal UUID, or None."""
        return self._entity_cache.get((entity_type, internal_id))

    async def _set_entity_map(self, entity_type: str, internal_id: UUID, jobber_id: str) -> None:
        """Store the internal → Jobber ID mapping."""
        self._entity_cache[(entity_type, internal_id)] = jobber_id

    # ------------------------------------------------------------------
    # BackOfficeAdapter protocol — health
    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        """Return True if Jobber's API is reachable and tokens are valid."""
        try:
            await self._graphql("{ account { id name } }")
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Customer operations
    # ------------------------------------------------------------------

    async def get_customer(self, id: UUID) -> Customer | None:
        """Look up a Jobber client via the hero_client_id custom field."""
        cfg_id = self._creds.custom_field_client_config_id
        if not cfg_id:
            return None

        query = """
            query GetClientByCustomField($cfgId: ID!, $val: String!) {
                clients(filter: {customFieldFilter: {configurationId: $cfgId, value: $val}}) {
                    nodes {
                        id
                        firstName
                        lastName
                        companyName
                    }
                }
            }
        """
        data = await self._graphql(query, {"cfgId": cfg_id, "val": str(id)})
        nodes = data.get("clients", {}).get("nodes", [])
        if not nodes:
            return None

        node = nodes[0]
        jobber_id = node["id"]
        await self._set_entity_map("client", id, jobber_id)

        name = _client_display_name(node)
        return Customer(id=id, name=name)

    async def create_customer(self, customer: Customer) -> Customer:
        """Create a Jobber client, or update if already mapped."""
        existing_jobber_id = await self._get_entity_map("client", customer.id)
        if existing_jobber_id:
            return await self.update_customer(customer)

        # Check Jobber via custom field before creating a duplicate.
        cfg_id = self._creds.custom_field_client_config_id
        if cfg_id:
            remote = await self.get_customer(customer.id)
            if remote is not None:
                return await self.update_customer(customer)

        mutation = """
            mutation CreateClient($input: ClientCreateInput!) {
                clientCreate(input: $input) {
                    client { id }
                    userErrors { message }
                }
            }
        """
        input_payload: dict[str, Any] = {**_name_fields(customer.name)}
        if cfg_id:
            input_payload["customFields"] = [{"configurationId": cfg_id, "value": str(customer.id)}]

        data = await self._graphql(mutation, {"input": input_payload})
        result = data["clientCreate"]
        _raise_user_errors(result.get("userErrors", []))

        jobber_id = result["client"]["id"]
        await self._set_entity_map("client", customer.id, jobber_id)
        return customer

    async def update_customer(self, customer: Customer) -> Customer:
        """Edit a Jobber client in place, or create if not yet mapped."""
        jobber_id = await self._get_entity_map("client", customer.id)
        if not jobber_id:
            return await self.create_customer(customer)

        mutation = """
            mutation EditClient($id: ID!, $input: ClientEditInput!) {
                clientEdit(clientId: $id, input: $input) {
                    client { id }
                    userErrors { message }
                }
            }
        """
        data = await self._graphql(
            mutation, {"id": jobber_id, "input": _name_fields(customer.name)}
        )
        result = data["clientEdit"]
        _raise_user_errors(result.get("userErrors", []))
        return customer

    async def delete_customer(self, id: UUID) -> None:
        """Archive a Jobber client (Jobber has no hard-delete API)."""
        jobber_id = await self._get_entity_map("client", id)
        if not jobber_id:
            return None

        mutation = """
            mutation ArchiveClient($id: ID!) {
                clientArchive(clientId: $id) {
                    client { id }
                    userErrors { message }
                }
            }
        """
        data = await self._graphql(mutation, {"id": jobber_id})
        result = data["clientArchive"]
        _raise_user_errors(result.get("userErrors", []))
        return None

    # ------------------------------------------------------------------
    # Job operations
    # ------------------------------------------------------------------

    async def get_job(self, id: UUID) -> Job | None:
        """Look up a Jobber job via the hero_job_id custom field."""
        cfg_id = self._creds.custom_field_job_config_id
        if not cfg_id:
            return None

        query = """
            query GetJobByCustomField($cfgId: ID!, $val: String!) {
                jobs(filter: {customFieldFilter: {configurationId: $cfgId, value: $val}}) {
                    nodes {
                        id
                        client { id }
                    }
                }
            }
        """
        data = await self._graphql(query, {"cfgId": cfg_id, "val": str(id)})
        nodes = data.get("jobs", {}).get("nodes", [])
        if not nodes:
            return None

        node = nodes[0]
        jobber_id = node["id"]
        await self._set_entity_map("job", id, jobber_id)

        # Resolve the customer_id from the entity cache (reverse lookup not trivial).
        # Use UUID(int=0) as sentinel when we cannot recover it from cache.
        customer_id = _find_internal_id_for_jobber(
            self._entity_cache, "client", node["client"]["id"]
        )
        return Job(id=id, customer_id=customer_id or UUID(int=0))

    async def create_job(self, job: Job) -> Job:
        """Create a Jobber job, or update if already mapped."""
        existing = await self._get_entity_map("job", job.id)
        if existing:
            return await self.update_job(job)

        # We need the Jobber Client ID to create a job.
        jobber_client_id = await self._get_entity_map("client", job.customer_id)
        if not jobber_client_id:
            raise ValueError(
                f"Jobber client not found for customer {job.customer_id}. "
                "Call create_customer first."
            )

        cfg_id = self._creds.custom_field_job_config_id
        mutation = """
            mutation CreateJob($input: JobCreateInput!) {
                jobCreate(input: $input) {
                    job { id }
                    userErrors { message }
                }
            }
        """
        input_payload: dict[str, Any] = {
            "clientId": jobber_client_id,
            "title": "Office Hero Job",
        }
        if cfg_id:
            input_payload["customFields"] = [{"configurationId": cfg_id, "value": str(job.id)}]

        data = await self._graphql(mutation, {"input": input_payload})
        result = data["jobCreate"]
        _raise_user_errors(result.get("userErrors", []))

        jobber_job_id = result["job"]["id"]
        await self._set_entity_map("job", job.id, jobber_job_id)
        return job

    async def update_job(self, job: Job) -> Job:
        """Edit a Jobber job in place, or create if not yet mapped."""
        jobber_id = await self._get_entity_map("job", job.id)
        if not jobber_id:
            return await self.create_job(job)

        mutation = """
            mutation EditJob($id: ID!, $input: JobEditInput!) {
                jobEdit(jobId: $id, input: $input) {
                    job { id }
                    userErrors { message }
                }
            }
        """
        data = await self._graphql(
            mutation, {"id": jobber_id, "input": {"title": "Office Hero Job"}}
        )
        result = data["jobEdit"]
        _raise_user_errors(result.get("userErrors", []))
        return job

    async def delete_job(self, id: UUID) -> None:
        """Archive a Jobber job (Jobber has no hard-delete API)."""
        jobber_id = await self._get_entity_map("job", id)
        if not jobber_id:
            return None

        mutation = """
            mutation ArchiveJob($id: ID!) {
                jobArchive(jobId: $id) {
                    job { id }
                    userErrors { message }
                }
            }
        """
        data = await self._graphql(mutation, {"id": jobber_id})
        result = data["jobArchive"]
        _raise_user_errors(result.get("userErrors", []))
        return None

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_tenant(cls, tenant_id: UUID, customer_repo: Any, job_repo: Any) -> JobberAdapter:
        """Construct a JobberAdapter for ``tenant_id``.

        Production path: tokens are loaded lazily from the ``jobber_credentials``
        table on first API call (set ``db_init_pending=True``).  This avoids
        running a DB query inside a synchronous factory while still supporting
        the async FastAPI event loop used by ``process_pending``.

        Env-var fallback (single-tenant testing): if ``JOBBER_ACCESS_TOKEN`` is
        set, use it directly instead of the DB lookup.
        """
        cfg = JobberConfig.from_env()
        # Env-var shortcut for local testing / staging with a single Jobber account
        if os.environ.get("JOBBER_ACCESS_TOKEN"):
            creds = JobberCredentials(
                tenant_id=tenant_id,
                access_token=os.environ["JOBBER_ACCESS_TOKEN"],
                refresh_token=os.environ.get("JOBBER_REFRESH_TOKEN", ""),
                expires_at=datetime.now(tz=UTC) + timedelta(hours=1),
                custom_field_client_config_id=os.environ.get("JOBBER_CF_CLIENT_ID"),
                custom_field_job_config_id=os.environ.get("JOBBER_CF_JOB_ID"),
            )
            return cls(cfg, creds, db_init_pending=False)

        # Production: placeholder creds — real tokens loaded from DB on first call.
        placeholder = JobberCredentials(
            tenant_id=tenant_id,
            access_token="__pending__",
            refresh_token="__pending__",
            expires_at=datetime.min.replace(tzinfo=UTC),
        )
        return cls(cfg, placeholder, db_init_pending=True)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _client_display_name(node: dict[str, Any]) -> str:
    """Build a display name from a Jobber client node."""
    first = (node.get("firstName") or "").strip()
    last = (node.get("lastName") or "").strip()
    company = (node.get("companyName") or "").strip()
    if first or last:
        return f"{first} {last}".strip()
    return company or "Unknown"


def _name_fields(name: str) -> dict[str, Any]:
    """Split a display name into Jobber firstName/lastName or companyName."""
    parts = name.strip().split(" ", 1)
    if len(parts) == 2:
        return {"firstName": parts[0], "lastName": parts[1]}
    return {"companyName": parts[0]}


def _raise_user_errors(user_errors: list[dict[str, Any]]) -> None:
    """Raise :class:`JobberGraphQLError` if the mutation returned userErrors."""
    if user_errors:
        raise JobberGraphQLError(user_errors)


def _find_internal_id_for_jobber(
    cache: dict[tuple[str, UUID], str], entity_type: str, jobber_id: str
) -> UUID | None:
    """Reverse-look up an internal UUID from the entity cache by Jobber ID."""
    for (et, internal_id), jid in cache.items():
        if et == entity_type and jid == jobber_id:
            return internal_id
    return None
