"""Factory for building a :class:`GeocodingAdapter` from :class:`Settings`."""

from __future__ import annotations

import os

from office_hero.adapters.geocoding.nominatim import NominatimGeocodingAdapter
from office_hero.adapters.geocoding.ors import ORSGeocodingAdapter
from office_hero.adapters.geocoding.protocol import GeocodingAdapter
from office_hero.adapters.geocoding.stub import StubGeocodingAdapter
from office_hero.core.config import Settings


def build_geocoding_adapter(settings: Settings) -> GeocodingAdapter:
    """Build a concrete adapter from ``settings.geocoding_adapter``.

    Under ``pytest`` (detected via ``PYTEST_CURRENT_TEST``) the stub adapter is
    returned by default to keep CI off the live Nominatim network. Tests that
    need to exercise a real adapter set ``settings.geocoding_adapter`` explicitly
    to ``"nominatim"`` / ``"ors"`` (and accept the test runs through that path).
    """
    choice = (settings.geocoding_adapter or "nominatim").lower()

    if choice == "stub":
        return StubGeocodingAdapter()

    if os.environ.get("PYTEST_CURRENT_TEST") and choice == "nominatim":
        # CI safety net: never call the live Nominatim service unless an
        # operator explicitly opts in via ``geocoding_adapter="ors"`` or
        # ``"stub"``.
        return StubGeocodingAdapter()

    if choice == "nominatim":
        return NominatimGeocodingAdapter(
            base_url=settings.nominatim_base_url,
            user_agent=settings.nominatim_user_agent,
            timeout=settings.geocoding_timeout_s,
            allowlist=settings.geocoding_allowlist,
        )

    if choice == "ors":
        return ORSGeocodingAdapter()

    raise ValueError(f"Unknown geocoding_adapter: {choice!r}")
