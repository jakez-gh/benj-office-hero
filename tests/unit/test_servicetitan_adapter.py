"""Unit tests for the ServiceTitan BackOfficeAdapter (Slice 26).

Uses ``respx`` to mock the httpx transport so no real HTTP calls are made.
The sandbox endpoints are used because the fixture config sets sandbox=True.

Auth endpoint (sandbox): https://auth-integration.servicetitan.io/connect/token
API base (sandbox):      https://api-integration.servicetitan.io
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
import pytest
import respx

from office_hero.adapters.back_office import BackOfficeAdapter, Customer, Job
from office_hero.adapters.back_office.servicetitan import ServiceTitanAdapter, ServiceTitanConfig

# ── Fixtures ─────────────────────────────────────────────────────────────────

ST_TID = 12345
AUTH_URL = "https://auth-integration.servicetitan.io/connect/token"
API_BASE = "https://api-integration.servicetitan.io"


@pytest.fixture()
def config() -> ServiceTitanConfig:
    return ServiceTitanConfig(
        client_id="cid",
        client_secret="csec",
        app_key="appkey",
        st_tenant_id=ST_TID,
        sandbox=True,
    )


@pytest.fixture()
def adapter(config: ServiceTitanConfig) -> ServiceTitanAdapter:
    client = httpx.AsyncClient()
    return ServiceTitanAdapter(config, http=client)


def _token_response() -> httpx.Response:
    return httpx.Response(200, json={"access_token": "tok", "expires_in": 900})


def _empty_page() -> httpx.Response:
    return httpx.Response(200, json={"data": [], "totalCount": 0})


def _page_with(item: dict) -> httpx.Response:
    return httpx.Response(200, json={"data": [item], "totalCount": 1})


# ── Auth tests ────────────────────────────────────────────────────────────────


async def test_get_token_posts_form_urlencoded(adapter: ServiceTitanAdapter) -> None:
    """Token request must use form-urlencoded, not JSON."""
    with respx.mock:
        route = respx.post(AUTH_URL).mock(return_value=_token_response())
        token = await adapter._get_token()

    assert token == "tok"
    assert route.called
    request = route.calls.last.request
    assert request.headers["content-type"] == "application/x-www-form-urlencoded"
    body = request.content.decode()
    assert "grant_type=client_credentials" in body
    assert "client_id=cid" in body
    assert "client_secret=csec" in body


async def test_get_token_caches_within_840s(adapter: ServiceTitanAdapter) -> None:
    """Second call within 840 s must reuse the cached token (1 HTTP request total)."""
    with respx.mock:
        route = respx.post(AUTH_URL).mock(return_value=_token_response())
        t1 = await adapter._get_token()
        t2 = await adapter._get_token()

    assert t1 == t2 == "tok"
    assert route.call_count == 1


async def test_get_token_refreshes_after_expiry(adapter: ServiceTitanAdapter) -> None:
    """Token is refreshed when monotonic time passes the reuse window."""
    with respx.mock:
        route = respx.post(AUTH_URL).mock(return_value=_token_response())
        await adapter._get_token()
        # Simulate expiry
        adapter._token_expiry = time.monotonic() - 1
        await adapter._get_token()

    assert route.call_count == 2


# ── Health check ──────────────────────────────────────────────────────────────


async def test_health_check_true_on_200(adapter: ServiceTitanAdapter) -> None:
    with respx.mock:
        respx.post(AUTH_URL).mock(return_value=_token_response())
        respx.get(f"{API_BASE}/crm/v2/tenant/{ST_TID}/customers").mock(return_value=_empty_page())
        result = await adapter.health_check()

    assert result is True


async def test_health_check_false_on_exception(adapter: ServiceTitanAdapter) -> None:
    with respx.mock:
        respx.post(AUTH_URL).mock(return_value=_token_response())
        respx.get(f"{API_BASE}/crm/v2/tenant/{ST_TID}/customers").mock(
            return_value=httpx.Response(500)
        )
        result = await adapter.health_check()

    assert result is False


# ── Customer tests ────────────────────────────────────────────────────────────


async def test_create_customer_posts_with_external_data(adapter: ServiceTitanAdapter) -> None:
    """Creating a new customer: GET (empty) → POST /customers → POST /locations."""
    customer = Customer(id=uuid4(), name="Acme Plumbing")
    st_customer_id = 99

    with respx.mock:
        respx.post(AUTH_URL).mock(return_value=_token_response())
        # Idempotency check — not found
        respx.get(f"{API_BASE}/crm/v2/tenant/{ST_TID}/customers").mock(return_value=_empty_page())
        # Create customer
        create_customer = respx.post(f"{API_BASE}/crm/v2/tenant/{ST_TID}/customers").mock(
            return_value=httpx.Response(200, json={"id": st_customer_id})
        )
        # Create location
        create_location = respx.post(f"{API_BASE}/crm/v2/tenant/{ST_TID}/locations").mock(
            return_value=httpx.Response(200, json={"id": 1})
        )

        result = await adapter.create_customer(customer)

    assert result == customer
    assert create_customer.called
    req_body = create_customer.calls.last.request.read()
    import json

    body = json.loads(req_body)
    assert body["name"] == "Acme Plumbing"
    assert body["externalData"][0]["applicationGuid"] == "office-hero"
    assert body["externalData"][0]["value"] == str(customer.id)
    assert create_location.called
    loc_body = json.loads(create_location.calls.last.request.read())
    assert loc_body["customerId"] == st_customer_id


async def test_create_customer_idempotent_when_exists(adapter: ServiceTitanAdapter) -> None:
    """If externalData query finds existing customer, skip POST."""
    customer = Customer(id=uuid4(), name="Existing Corp")
    st_row = {"id": 42, "name": "Existing Corp"}

    with respx.mock:
        respx.post(AUTH_URL).mock(return_value=_token_response())
        get_route = respx.get(f"{API_BASE}/crm/v2/tenant/{ST_TID}/customers").mock(
            return_value=_page_with(st_row)
        )
        post_route = respx.post(f"{API_BASE}/crm/v2/tenant/{ST_TID}/customers").mock(
            return_value=httpx.Response(200, json={"id": 43})
        )

        result = await adapter.create_customer(customer)

    assert result == customer
    assert get_route.call_count == 1
    assert not post_route.called


async def test_get_customer_returns_none_when_not_found(adapter: ServiceTitanAdapter) -> None:
    with respx.mock:
        respx.post(AUTH_URL).mock(return_value=_token_response())
        respx.get(f"{API_BASE}/crm/v2/tenant/{ST_TID}/customers").mock(return_value=_empty_page())
        result = await adapter.get_customer(uuid4())

    assert result is None


async def test_get_customer_returns_customer_when_found(adapter: ServiceTitanAdapter) -> None:
    cid = uuid4()
    st_row = {"id": 55, "name": "Found Co"}

    with respx.mock:
        respx.post(AUTH_URL).mock(return_value=_token_response())
        respx.get(f"{API_BASE}/crm/v2/tenant/{ST_TID}/customers").mock(
            return_value=_page_with(st_row)
        )
        result = await adapter.get_customer(cid)

    assert result == Customer(id=cid, name="Found Co")


# ── Job tests ─────────────────────────────────────────────────────────────────


async def test_create_job_idempotent_when_exists(adapter: ServiceTitanAdapter) -> None:
    """If job found by externalId, skip all POSTs."""
    job = Job(id=uuid4(), customer_id=uuid4())
    st_job = {"id": 77, "externalId": str(job.id)}

    with respx.mock:
        respx.post(AUTH_URL).mock(return_value=_token_response())
        get_jobs = respx.get(f"{API_BASE}/jpm/v2/tenant/{ST_TID}/jobs").mock(
            return_value=_page_with(st_job)
        )
        post_jobs = respx.post(f"{API_BASE}/jpm/v2/tenant/{ST_TID}/jobs").mock(
            return_value=httpx.Response(200, json={"id": 78})
        )

        result = await adapter.create_job(job)

    assert result == job
    assert get_jobs.call_count == 1
    assert not post_jobs.called


async def test_create_job_raises_on_missing_customer_in_st(adapter: ServiceTitanAdapter) -> None:
    """ValueError raised when the linked customer isn't in ST yet."""
    job = Job(id=uuid4(), customer_id=uuid4())

    with respx.mock:
        respx.post(AUTH_URL).mock(return_value=_token_response())
        # Job not found (first GET)
        respx.get(f"{API_BASE}/jpm/v2/tenant/{ST_TID}/jobs").mock(return_value=_empty_page())
        # Customer not found either
        respx.get(f"{API_BASE}/crm/v2/tenant/{ST_TID}/customers").mock(return_value=_empty_page())

        with pytest.raises(ValueError, match="ServiceTitan customerId not found"):
            await adapter.create_job(job)


async def test_create_job_posts_with_correct_fields(adapter: ServiceTitanAdapter) -> None:
    """Full create_job path: no existing job, customer found, location found → POST."""
    import json

    job = Job(id=uuid4(), customer_id=uuid4())
    st_customer_id = 11
    st_location_id = 22

    with respx.mock:
        respx.post(AUTH_URL).mock(return_value=_token_response())
        # Job not found
        respx.get(f"{API_BASE}/jpm/v2/tenant/{ST_TID}/jobs").mock(return_value=_empty_page())
        # Customer found
        respx.get(f"{API_BASE}/crm/v2/tenant/{ST_TID}/customers").mock(
            return_value=_page_with({"id": st_customer_id, "name": "Test Co"})
        )
        # Location found
        respx.get(f"{API_BASE}/crm/v2/tenant/{ST_TID}/locations").mock(
            return_value=_page_with({"id": st_location_id})
        )
        post_job = respx.post(f"{API_BASE}/jpm/v2/tenant/{ST_TID}/jobs").mock(
            return_value=httpx.Response(200, json={"id": 99})
        )

        result = await adapter.create_job(job)

    assert result == job
    assert post_job.called
    body = json.loads(post_job.calls.last.request.read())
    assert body["externalId"] == str(job.id)
    assert body["customerId"] == st_customer_id
    assert body["locationId"] == st_location_id


# ── Protocol satisfaction ─────────────────────────────────────────────────────


def test_adapter_satisfies_protocol(adapter: ServiceTitanAdapter) -> None:
    """ServiceTitanAdapter must satisfy the BackOfficeAdapter runtime-checkable protocol."""
    assert isinstance(adapter, BackOfficeAdapter)


# ── Retry on 429 ─────────────────────────────────────────────────────────────


async def test_api_retries_on_429(adapter: ServiceTitanAdapter) -> None:
    """First response 429, second 200 — exactly 2 requests should be made."""
    with respx.mock:
        respx.post(AUTH_URL).mock(return_value=_token_response())
        get_route = respx.get(f"{API_BASE}/crm/v2/tenant/{ST_TID}/customers").mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "1"}),
                _empty_page(),
            ]
        )

        # Patch asyncio.sleep so the test doesn't actually wait 1 second
        with patch("office_hero.adapters.back_office.servicetitan.asyncio.sleep", new=AsyncMock()):
            result = await adapter._api(
                "GET",
                f"/crm/v2/tenant/{ST_TID}/customers",
                params={"pageSize": 1},
            )

    assert result.status_code == 200
    assert get_route.call_count == 2
