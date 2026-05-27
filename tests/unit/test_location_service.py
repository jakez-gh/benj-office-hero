"""Unit tests for :class:`LocationService` (TDD-first, no DB or live network)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from office_hero.adapters.geocoding.protocol import (
    AddressInput,
    Coordinates,
    GeocodingAdapter,
)
from office_hero.adapters.geocoding.stub import StubGeocodingAdapter
from office_hero.core.exceptions import (
    CustomerNotFoundError,
    GeocodingError,
)
from office_hero.repositories.customer_repository import (
    InMemoryCustomerRepository,
)
from office_hero.repositories.location_repository import (
    InMemoryLocationRepository,
)
from office_hero.repositories.mocks import InMemoryAuditService
from office_hero.services.location_service import LocationService


class _FailingGeocoder(GeocodingAdapter):
    """Geocoder that always raises :class:`GeocodingError` — for tests."""

    async def geocode(self, address: AddressInput) -> Coordinates | None:
        raise GeocodingError("simulated network error")


class _MissGeocoder(GeocodingAdapter):
    """Geocoder that always returns ``None`` (no match found)."""

    async def geocode(self, address: AddressInput) -> Coordinates | None:
        return None


@pytest.fixture()
def cust_repo() -> InMemoryCustomerRepository:
    return InMemoryCustomerRepository()


@pytest.fixture()
def loc_repo() -> InMemoryLocationRepository:
    return InMemoryLocationRepository()


@pytest.fixture()
def audit() -> InMemoryAuditService:
    return InMemoryAuditService()


@pytest.fixture()
def stub_geocoder() -> StubGeocodingAdapter:
    return StubGeocodingAdapter()


@pytest.fixture()
def service(loc_repo, cust_repo, audit, stub_geocoder) -> LocationService:
    return LocationService(
        repo=loc_repo,
        customer_repo=cust_repo,
        audit=audit,
        geocoder=stub_geocoder,
    )


@pytest.fixture()
def tenant_a():
    return uuid4()


@pytest.fixture()
def tenant_b():
    return uuid4()


@pytest.fixture()
def user_a():
    return uuid4()


_VALID_ADDRESS = {
    "street": "123 Main St",
    "city": "Philadelphia",
    "state": "PA",
    "postal_code": "19103",
    "country": "US",
}


async def test_create_location_calls_geocoder_and_sets_coordinates(
    service, cust_repo, audit, tenant_a, user_a
):
    """``create`` geocodes the address and persists lat/lng + status=ok."""
    cust = await cust_repo.create(tenant_a, name="Acme Plumbing")
    loc = await service.create(
        tenant_id=tenant_a,
        user_id=user_a,
        customer_id=cust.id,
        address_fields=dict(_VALID_ADDRESS),
        label="Main Office",
    )

    assert loc.lat is not None and loc.lng is not None
    assert loc.geocode_status == "ok"
    assert loc.geocode_source == "stub"
    assert any(e.event_type == "location.created" for e in audit.events)


async def test_create_location_geocoder_failure_marks_failed_but_returns_location(
    loc_repo, cust_repo, audit, tenant_a, user_a
):
    """When the geocoder raises we still return the location with status=failed."""
    svc = LocationService(
        repo=loc_repo,
        customer_repo=cust_repo,
        audit=audit,
        geocoder=_FailingGeocoder(),
    )
    cust = await cust_repo.create(tenant_a, name="Acme")
    loc = await svc.create(
        tenant_id=tenant_a,
        user_id=user_a,
        customer_id=cust.id,
        address_fields=dict(_VALID_ADDRESS),
        label="x",
    )

    assert loc.geocode_status == "failed"
    assert loc.lat is None
    assert any(e.event_type == "location.created" for e in audit.events)


async def test_create_location_geocoder_miss_marks_failed(
    loc_repo, cust_repo, audit, tenant_a, user_a
):
    """Geocoder returning ``None`` also flips status to ``failed``."""
    svc = LocationService(
        repo=loc_repo,
        customer_repo=cust_repo,
        audit=audit,
        geocoder=_MissGeocoder(),
    )
    cust = await cust_repo.create(tenant_a, name="Acme")
    loc = await svc.create(
        tenant_id=tenant_a,
        user_id=user_a,
        customer_id=cust.id,
        address_fields=dict(_VALID_ADDRESS),
        label="x",
    )

    assert loc.geocode_status == "failed"


async def test_create_location_geocode_false_skips_geocoder(service, cust_repo, tenant_a, user_a):
    """``geocode=False`` leaves the location in ``pending``."""
    cust = await cust_repo.create(tenant_a, name="Acme")
    loc = await service.create(
        tenant_id=tenant_a,
        user_id=user_a,
        customer_id=cust.id,
        address_fields=dict(_VALID_ADDRESS),
        label="x",
        geocode=False,
    )
    assert loc.geocode_status == "pending"
    assert loc.lat is None


async def test_update_location_address_auto_regeocodes(service, cust_repo, tenant_a, user_a):
    """Changing an address field re-geocodes by default (``auto``)."""
    cust = await cust_repo.create(tenant_a, name="Acme")
    loc = await service.create(
        tenant_id=tenant_a,
        user_id=user_a,
        customer_id=cust.id,
        address_fields=dict(_VALID_ADDRESS),
        label="x",
    )
    first_lat = loc.lat

    updated = await service.update(
        tenant_id=tenant_a,
        user_id=user_a,
        location_id=loc.id,
        patch={"street": "456 Different Ave"},
    )
    assert updated.geocode_status == "ok"
    # Stub coordinates are deterministic on street; they must differ.
    assert updated.lat != first_lat


async def test_update_location_label_only_does_not_regeocode(
    service, cust_repo, audit, tenant_a, user_a
):
    """Label-only updates don't trigger a re-geocode."""
    cust = await cust_repo.create(tenant_a, name="Acme")
    loc = await service.create(
        tenant_id=tenant_a,
        user_id=user_a,
        customer_id=cust.id,
        address_fields=dict(_VALID_ADDRESS),
        label="Old",
    )

    updated = await service.update(
        tenant_id=tenant_a,
        user_id=user_a,
        location_id=loc.id,
        patch={"label": "New"},
    )
    update_evt = next(e for e in audit.events if e.event_type == "location.updated")
    assert update_evt.details["regeocoded"] is False
    assert updated.label == "New"


async def test_manual_set_coordinates_overrides_geocoder_status(
    service, cust_repo, audit, tenant_a, user_a
):
    """Manual coordinate override sets status/source to ``manual``."""
    cust = await cust_repo.create(tenant_a, name="Acme")
    loc = await service.create(
        tenant_id=tenant_a,
        user_id=user_a,
        customer_id=cust.id,
        address_fields=dict(_VALID_ADDRESS),
        label="x",
    )

    updated = await service.manual_set_coordinates(
        tenant_id=tenant_a,
        user_id=user_a,
        location_id=loc.id,
        lat=39.951,
        lng=-75.165,
    )
    assert updated.geocode_status == "manual"
    assert updated.geocode_source == "manual"
    assert any(e.event_type == "location.coordinates_set_manual" for e in audit.events)


async def test_create_location_other_tenant_customer_raises_not_found(
    service, cust_repo, tenant_a, tenant_b, user_a
):
    """Creating a location for a foreign-tenant customer raises CustomerNotFoundError."""
    cust = await cust_repo.create(tenant_a, name="Tenant A Co")
    with pytest.raises(CustomerNotFoundError):
        await service.create(
            tenant_id=tenant_b,
            user_id=user_a,
            customer_id=cust.id,
            address_fields=dict(_VALID_ADDRESS),
            label="x",
        )


async def test_create_location_unknown_customer_raises(service, tenant_a, user_a):
    """Unknown customer id surfaces :class:`CustomerNotFoundError`."""
    with pytest.raises(CustomerNotFoundError):
        await service.create(
            tenant_id=tenant_a,
            user_id=user_a,
            customer_id=uuid4(),
            address_fields=dict(_VALID_ADDRESS),
            label="x",
        )
