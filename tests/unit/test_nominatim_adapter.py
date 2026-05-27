"""Unit tests for :class:`NominatimGeocodingAdapter`.

Network calls are stubbed via ``httpx.MockTransport`` so the tests never hit
the real Nominatim service (Nominatim ToS would not be happy with a CI run
spamming them).
"""

from __future__ import annotations

import time

import httpx
import pytest

from office_hero.adapters.geocoding.nominatim import NominatimGeocodingAdapter
from office_hero.adapters.geocoding.protocol import AddressInput
from office_hero.core.exceptions import GeocodingError

_ALLOWLIST = ["nominatim.openstreetmap.org"]
_BASE_URL = "https://nominatim.openstreetmap.org"
_USER_AGENT = "office-hero/test (contact@example.com)"


def _make_adapter(handler, *, timeout: float = 5.0) -> NominatimGeocodingAdapter:
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, timeout=timeout)
    return NominatimGeocodingAdapter(
        base_url=_BASE_URL,
        user_agent=_USER_AGENT,
        timeout=timeout,
        allowlist=_ALLOWLIST,
        client=client,
    )


def _hit(payload):
    """Handler factory returning a 200 with ``payload`` for every call."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload, request=request)

    return handler


async def test_nominatim_returns_coordinates_on_match():
    """A 200 with a non-empty body yields parsed Coordinates."""
    payload = [{"lat": "39.9526", "lon": "-75.1652", "display_name": "Philly"}]
    adapter = _make_adapter(_hit(payload))

    coords = await adapter.geocode(
        AddressInput(
            street="123 Main St",
            city="Philadelphia",
            state="PA",
            postal_code="19103",
            country="US",
        )
    )
    assert coords is not None
    assert coords.lat == pytest.approx(39.9526)
    assert coords.lng == pytest.approx(-75.1652)
    assert coords.source == "nominatim"


async def test_nominatim_returns_none_on_no_match():
    """Empty list -> ``None``."""
    adapter = _make_adapter(_hit([]))
    coords = await adapter.geocode(
        AddressInput(
            street="nowhere",
            city="??",
            state="??",
            postal_code="00000",
            country="US",
        )
    )
    assert coords is None


async def test_nominatim_rate_limit_one_per_second():
    """Second consecutive call must wait >= ~1s (Nominatim ToS)."""
    payload = [{"lat": "0", "lon": "0", "display_name": "x"}]
    adapter = _make_adapter(_hit(payload))
    addr = AddressInput(street="a", city="b", state="c", postal_code="d", country="US")

    await adapter.geocode(addr)
    t0 = time.monotonic()
    await adapter.geocode(addr)
    elapsed = time.monotonic() - t0
    # Allow a small slack window — the gate is precisely ``>= 1.0``.
    assert elapsed >= 0.95


async def test_nominatim_rejects_host_outside_allowlist():
    """Constructing the adapter with an off-allowlist host raises GeocodingError."""
    with pytest.raises(GeocodingError):
        NominatimGeocodingAdapter(
            base_url="https://evil.example.com",
            user_agent=_USER_AGENT,
            timeout=5.0,
            allowlist=_ALLOWLIST,
        )


async def test_nominatim_timeout_raises_geocoding_error():
    """``httpx.TimeoutException`` is translated to GeocodingError."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("simulated timeout")

    adapter = _make_adapter(handler)
    with pytest.raises(GeocodingError):
        await adapter.geocode(
            AddressInput(street="a", city="b", state="c", postal_code="d", country="US")
        )


async def test_nominatim_sends_user_agent_header():
    """The configured ``User-Agent`` must be sent on every request."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["ua"] = request.headers.get("user-agent")
        return httpx.Response(
            200,
            json=[{"lat": "0", "lon": "0", "display_name": "x"}],
            request=request,
        )

    adapter = _make_adapter(handler)
    await adapter.geocode(
        AddressInput(street="a", city="b", state="c", postal_code="d", country="US")
    )
    assert captured["ua"] == _USER_AGENT


async def test_nominatim_bad_status_raises():
    """Non-200 status results in :class:`GeocodingError`."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "down"}, request=request)

    adapter = _make_adapter(handler)
    with pytest.raises(GeocodingError):
        await adapter.geocode(
            AddressInput(street="a", city="b", state="c", postal_code="d", country="US")
        )


async def test_nominatim_missing_user_agent_raises():
    """Empty user_agent is rejected at construction."""
    with pytest.raises(GeocodingError):
        NominatimGeocodingAdapter(
            base_url=_BASE_URL,
            user_agent="",
            timeout=1.0,
            allowlist=_ALLOWLIST,
        )
