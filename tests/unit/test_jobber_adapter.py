"""Unit tests for :class:`JobberAdapter` (Slice 28).

All network calls are intercepted via ``respx`` — no real HTTP traffic.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
import respx

from office_hero.adapters.back_office import BackOfficeAdapter, Customer, Job
from office_hero.adapters.back_office.jobber import (
    JobberAdapter,
    JobberConfig,
    JobberCredentials,
)

GRAPHQL_URL = "https://api.getjobber.com/api/graphql"
TOKEN_URL = "https://api.getjobber.com/api/oauth/token"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def config() -> JobberConfig:
    return JobberConfig(client_id="cid", client_secret="csec")


@pytest.fixture()
def creds() -> JobberCredentials:
    return JobberCredentials(
        tenant_id=uuid4(),
        access_token="test-token",
        refresh_token="refresh-tok",
        expires_at=datetime.now(tz=UTC) + timedelta(hours=1),
        custom_field_client_config_id="cf-client-123",
        custom_field_job_config_id="cf-job-456",
    )


@pytest.fixture()
def adapter(config: JobberConfig, creds: JobberCredentials) -> JobberAdapter:
    return JobberAdapter(config, creds, http=httpx.AsyncClient())


# ---------------------------------------------------------------------------
# Helper: build a minimal GraphQL success response
# ---------------------------------------------------------------------------


def _gql_response(data: dict, *, available: int | None = None) -> dict:
    body: dict = {"data": data}
    if available is not None:
        body["extensions"] = {"cost": {"throttleStatus": {"currentlyAvailable": available}}}
    return body


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_adapter_satisfies_protocol(adapter: JobberAdapter) -> None:
    assert isinstance(adapter, BackOfficeAdapter)


# --- health_check ---


@respx.mock
async def test_health_check_true(adapter: JobberAdapter) -> None:
    respx.post(GRAPHQL_URL).mock(
        return_value=httpx.Response(
            200,
            json=_gql_response({"account": {"id": "abc", "name": "Acme"}}),
        )
    )
    assert await adapter.health_check() is True


@respx.mock
async def test_health_check_false_on_graphql_error(adapter: JobberAdapter) -> None:
    respx.post(GRAPHQL_URL).mock(
        return_value=httpx.Response(
            200,
            json={"errors": [{"message": "Unauthorized"}]},
        )
    )
    assert await adapter.health_check() is False


# --- create_customer ---


@respx.mock
async def test_create_customer_posts_mutation(
    adapter: JobberAdapter, creds: JobberCredentials
) -> None:
    customer = Customer(id=uuid4(), name="Alice Wonderland")

    # First call: get_customer via custom field returns empty
    get_response = _gql_response({"clients": {"nodes": []}})
    # Second call: clientCreate mutation succeeds
    create_response = _gql_response(
        {"clientCreate": {"client": {"id": "jobber-c-001"}, "userErrors": []}}
    )

    calls = iter([get_response, create_response])

    def side_effect(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=next(calls))

    respx.post(GRAPHQL_URL).mock(side_effect=side_effect)

    result = await adapter.create_customer(customer)
    assert result == customer
    # Mapping stored in cache
    cached = await adapter._get_entity_map("client", customer.id)
    assert cached == "jobber-c-001"


@respx.mock
async def test_create_customer_idempotent_on_cache_hit(
    adapter: JobberAdapter,
) -> None:
    """If entity cache has a Jobber ID, create_customer delegates to update."""
    customer = Customer(id=uuid4(), name="Bob Builder")
    # Pre-seed the cache so create_customer routes to update_customer
    await adapter._set_entity_map("client", customer.id, "jobber-c-existing")

    update_response = _gql_response(
        {"clientEdit": {"client": {"id": "jobber-c-existing"}, "userErrors": []}}
    )
    respx.post(GRAPHQL_URL).mock(return_value=httpx.Response(200, json=update_response))

    result = await adapter.create_customer(customer)
    assert result == customer
    # Only one request made (no get_customer / clientCreate)
    assert respx.calls.call_count == 1


# --- create_job ---


async def test_create_job_raises_when_client_not_in_cache(
    adapter: JobberAdapter,
) -> None:
    job = Job(id=uuid4(), customer_id=uuid4())
    with pytest.raises(ValueError, match="Jobber client not found"):
        await adapter.create_job(job)


@respx.mock
async def test_create_job_success_with_client_in_cache(
    adapter: JobberAdapter,
) -> None:
    customer_id = uuid4()
    job = Job(id=uuid4(), customer_id=customer_id)

    # Pre-seed client mapping
    await adapter._set_entity_map("client", customer_id, "jobber-c-100")

    create_response = _gql_response(
        {"jobCreate": {"job": {"id": "jobber-j-001"}, "userErrors": []}}
    )
    respx.post(GRAPHQL_URL).mock(return_value=httpx.Response(200, json=create_response))

    result = await adapter.create_job(job)
    assert result == job
    cached = await adapter._get_entity_map("job", job.id)
    assert cached == "jobber-j-001"


# --- delete_customer ---


@respx.mock
async def test_delete_customer_archives_client(adapter: JobberAdapter) -> None:
    customer_id = uuid4()
    await adapter._set_entity_map("client", customer_id, "jobber-c-del")

    archive_response = _gql_response(
        {"clientArchive": {"client": {"id": "jobber-c-del"}, "userErrors": []}}
    )
    respx.post(GRAPHQL_URL).mock(return_value=httpx.Response(200, json=archive_response))

    result = await adapter.delete_customer(customer_id)
    assert result is None
    assert respx.calls.call_count == 1


async def test_delete_customer_noop_when_not_in_cache(adapter: JobberAdapter) -> None:
    """delete_customer returns None silently when there is no entity mapping."""
    result = await adapter.delete_customer(uuid4())
    assert result is None


# --- token refresh ---


@respx.mock
async def test_token_refresh_on_expiry(config: JobberConfig, creds: JobberCredentials) -> None:
    """If expires_at is in the past, the token endpoint is called before GraphQL."""
    # Expire the token
    creds.expires_at = datetime.now(tz=UTC) - timedelta(seconds=10)
    adapter = JobberAdapter(config, creds, http=httpx.AsyncClient())

    token_response = {
        "access_token": "new-access-token",
        "refresh_token": "new-refresh-token",
        "expires_in": 3600,
    }
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json=token_response))
    respx.post(GRAPHQL_URL).mock(
        return_value=httpx.Response(
            200,
            json=_gql_response({"account": {"id": "x", "name": "y"}}),
        )
    )

    await adapter.health_check()

    # Token endpoint was called
    token_calls = [c for c in respx.calls if str(c.request.url) == TOKEN_URL]
    assert len(token_calls) == 1
    # In-memory credentials were updated
    assert adapter._creds.access_token == "new-access-token"
    assert adapter._creds.refresh_token == "new-refresh-token"
