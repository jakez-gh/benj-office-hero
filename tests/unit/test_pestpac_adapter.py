"""Unit tests for PestPacAdapter scaffold (Slice 27).

These tests cover the parts of the adapter that are already implemented:
- Protocol satisfaction
- Config construction
- Entity cache helpers (health check, idempotency guards)
- NotImplementedError raised by the HTTP-blocked methods

When RES-026 open question #1 (sync vs async response model) is resolved and
the HTTP call layer is added, replace the NotImplementedError assertions here
with respx mock tests matching the real Odyssey API shape.
"""

from __future__ import annotations

from uuid import uuid4

import httpx
import pytest

from office_hero.adapters.back_office import BackOfficeAdapter, Customer, Job
from office_hero.adapters.back_office.pestpac import PestPacAdapter, PestPacConfig

TENANT_ID = uuid4()


@pytest.fixture()
def config() -> PestPacConfig:
    return PestPacConfig(
        api_key="test-key",
        company_key="123456",
        sandbox=True,
    )


@pytest.fixture()
def adapter(config: PestPacConfig) -> PestPacAdapter:
    return PestPacAdapter(config, http=httpx.AsyncClient())


# ---------------------------------------------------------------------------
# Protocol and config
# ---------------------------------------------------------------------------


async def test_adapter_satisfies_protocol(adapter: PestPacAdapter) -> None:
    assert isinstance(adapter, BackOfficeAdapter)


def test_config_sandbox_url() -> None:
    cfg = PestPacConfig(api_key="k", company_key="123456", sandbox=True)
    assert "sandbox" in cfg.base_url


def test_config_prod_url() -> None:
    cfg = PestPacConfig(api_key="k", company_key="123456", sandbox=False)
    assert "prod" in cfg.base_url


def test_from_tenant_factory_satisfies_protocol(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PESTPAC_API_KEY", "k")
    monkeypatch.setenv("PESTPAC_COMPANY_KEY", "999999")
    adapter = PestPacAdapter.from_tenant(uuid4(), None, None)
    assert isinstance(adapter, BackOfficeAdapter)


# ---------------------------------------------------------------------------
# Entity cache helpers
# ---------------------------------------------------------------------------


async def test_get_customer_returns_none_when_not_in_cache(adapter: PestPacAdapter) -> None:
    result = await adapter.get_customer(uuid4())
    assert result is None


async def test_get_job_returns_none_when_not_in_cache(adapter: PestPacAdapter) -> None:
    result = await adapter.get_job(uuid4())
    assert result is None


async def test_delete_customer_noop_when_not_in_cache(adapter: PestPacAdapter) -> None:
    # Should return None without raising — idempotent
    result = await adapter.delete_customer(uuid4())
    assert result is None


async def test_delete_job_noop_when_not_in_cache(adapter: PestPacAdapter) -> None:
    result = await adapter.delete_job(uuid4())
    assert result is None


# ---------------------------------------------------------------------------
# Blocked methods raise NotImplementedError (until HTTP layer is completed)
# ---------------------------------------------------------------------------


async def test_create_customer_raises_not_implemented(adapter: PestPacAdapter) -> None:
    with pytest.raises(NotImplementedError, match="RES-026"):
        await adapter.create_customer(Customer(id=uuid4(), name="Acme"))


async def test_create_job_raises_value_error_when_customer_not_in_cache(
    adapter: PestPacAdapter,
) -> None:
    job = Job(id=uuid4(), customer_id=uuid4())
    with pytest.raises(ValueError, match="PestPac LocationCode not found"):
        await adapter.create_job(job)


async def test_create_job_raises_not_implemented_when_customer_in_cache(
    adapter: PestPacAdapter,
) -> None:
    """Once the customer is in cache, the job creation itself is blocked."""
    customer_id = uuid4()
    adapter._cache_set("location", customer_id, "99001")  # simulate prior create
    job = Job(id=uuid4(), customer_id=customer_id)
    with pytest.raises(NotImplementedError, match="not yet implemented"):
        await adapter.create_job(job)


async def test_create_customer_idempotent_in_cache(adapter: PestPacAdapter) -> None:
    """If we already have the PestPac ID in cache, create_customer returns early."""
    cust = Customer(id=uuid4(), name="Acme")
    adapter._cache_set("location", cust.id, "77001")
    # Should return the customer without hitting NotImplementedError
    result = await adapter.create_customer(cust)
    assert result == cust


async def test_create_job_idempotent_in_cache(adapter: PestPacAdapter) -> None:
    """If we already have the work order ID in cache, create_job returns early."""
    customer_id = uuid4()
    job = Job(id=uuid4(), customer_id=customer_id)
    adapter._cache_set("workorder", job.id, "55001")
    result = await adapter.create_job(job)
    assert result == job
