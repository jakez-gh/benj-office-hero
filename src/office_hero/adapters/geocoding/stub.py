"""Deterministic stub geocoder for tests (no network, no asyncio sleeps).

Mapping street -> coordinates is hash-derived so a given input always produces
the same output, which makes service-layer tests easy to assert against.
"""

from __future__ import annotations

from office_hero.adapters.geocoding.protocol import (
    AddressInput,
    Coordinates,
    GeocodingAdapter,
)


class StubGeocodingAdapter(GeocodingAdapter):
    """Deterministic geocoder for unit/API tests.

    The output is fully determined by ``address.street`` so tests can pin exact
    lat/lng values. ``"FAIL"`` anywhere in the street triggers a ``None``
    return so tests can exercise the not-resolvable code path without
    monkeypatching.
    """

    SOURCE: str = "stub"

    async def geocode(self, address: AddressInput) -> Coordinates | None:
        """Return deterministic coordinates derived from ``address.street``."""
        if "FAIL" in address.street.upper():
            return None

        # ``hash`` returns a signed int; mask to a positive range. Using
        # ``abs`` would lose one possible value but is clearer.
        seed = abs(hash(address.street))
        lat = 40.0 + (seed % 1000) / 1000.0  # 40.000 .. 40.999
        lng = -75.0 - ((seed // 1000) % 1000) / 1000.0  # -75.999 .. -75.000

        formatted = f"{address.street}, {address.city}, {address.state} {address.postal_code}"
        return Coordinates(
            lat=lat,
            lng=lng,
            formatted_address=formatted,
            source=self.SOURCE,
        )
